#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""API de sc2.lestudi.com, darrere nginx a 127.0.0.1:8765.

POST /api/upload[?player=<toon>]  replay com a cos → l'analitza (procés a part, amb límits) i torna {"id", "perfil"}
GET  /api/login?return=<ruta>     comença el login amb Battle.net
GET  /api/battlenet               tornada de Battle.net (OAuth): crea la sessió (adreça registrada a Battle.net)
GET  /api/me                      qui ha entrat: {"battletag", "toons": [{"toon", "nom"}], "compartir"} o {}
POST /api/logout                  tanca la sessió
POST /api/share                   {"compartir": bool}: si els replays que has pujat es poden baixar
GET  /api/download?id=<id>[&check=1]  redirigeix a un enllaç signat de l'allotjament PHP (o {"baixable"})
GET  /api/summary?id=<id>&lang=<codi> el resum de la partida en aquest idioma; si no hi és, el fa ara
GET  /api/key                     l'estat de la clau de Gemini de qui ha entrat (mai la clau)
POST /api/key                     {"clau", "lang"}: la prova i la desa xifrada; {"esborra": true}: l'esborra

Les rutes i paràmetres d'abans (en català) continuen funcionant: el pujador ja instal·lat envia a /api/envia?jugador=.
"""
import hashlib, http.cookies, json, os, re, resource, secrets, subprocess, sys, threading, time
import urllib.error, urllib.parse, urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit, parse_qs

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import magatzem, resum  # noqa: E402

ARREL = os.path.dirname(os.path.abspath(__file__))
PYTHON = os.path.join(ARREL, ".venv", "bin", "python")
ENVIATS = os.path.join(ARREL, "enviats")
HTML = os.path.join(ARREL, "html")
MAPES = os.path.join(ARREL, "maps")
MAX = 8 * 1024 * 1024
UN_A_UN = threading.Semaphore(1)  # és una RPi: d'un en un

WEB = os.environ.get("SC2_WEB", "https://sc2.lestudi.com").rstrip("/")  # la redirecció de Battle.net en surt
TORNADA = WEB + "/api/battlenet"
BNET_ID = os.environ.get("BNET_CLIENT_ID", "")
BNET_SECRET = os.environ.get("BNET_CLIENT_SECRET", "")
DIES_SESSIO = 30
# perquè altres webs germanes (ma.lestudi.com) comparteixin l'inici de sessió: la galeta val per a tot el domini
# i el login pot tornar a aquestes adreces. Buit = només aquesta web.
GALETA_DOMINI = os.environ.get("SC2_GALETA_DOMINI", "")
ALTRES_WEBS = {h.strip() for h in os.environ.get("SC2_ALTRES_WEBS", "").split(",") if h.strip()}
RE_TOON = re.compile(r"[1-9]-S2-[1-9]-[0-9]{1,12}")
RE_ID = re.compile(r"[0-9a-f]{12}")
RE_CLAU_GEMINI = re.compile(r"[A-Za-z0-9._-]{20,120}")
# rutes i paràmetres d'abans → els d'ara
ALIES = {"/api/envia": "/api/upload", "/api/jo": "/api/me", "/api/entra": "/api/login", "/api/surt": "/api/logout",
         "/api/compartir": "/api/share", "/api/baixa": "/api/download", "/api/resum": "/api/summary", "/api/clau": "/api/key"}
PARAMS_ALIES = {"jugador": "player", "torna": "return", "comprova": "check"}


def ruta(path):
    """(ruta d'ara, consulta amb els noms de paràmetre d'ara)."""
    url = urlsplit(path)
    q = parse_qs(url.query)
    for vell, nou in PARAMS_ALIES.items():
        if vell in q and nou not in q:
            q[nou] = q.pop(vell)
    return ALIES.get(url.path, url.path), q
JO_TOON = os.environ.get("SC2_TOON", "")  # les partides d'origen "meu" són d'aquest toon
RESUMS = threading.Semaphore(2)  # crides a Gemini alhora des de la web


MA_UPLOAD = os.environ.get("SC2_MA_UPLOAD", "")  # p. ex. http://127.0.0.1:8767/api/upload (servei de ma.lestudi.com)


def envia_a_ma(dades, toon, galetes):
    """Passa una partida que no és 1v1 al servei de Marine Arena; torna la seva resposta o None si no la vol."""
    if not MA_UPLOAD:
        return None
    req = urllib.request.Request(MA_UPLOAD + (f"?player={toon}" if toon else ""), data=dades, method="POST",
                                 headers={"Content-Type": "application/octet-stream", **({"Cookie": galetes} if galetes and not toon else {})})
    try:
        with urllib.request.urlopen(req, timeout=200) as r:
            return dict(json.loads(r.read()), web="ma")
    except urllib.error.HTTPError as ex:
        if ex.code != 422:
            sys.stderr.write(f"ma: {ex.code}\n")
    except Exception as ex:
        sys.stderr.write(f"ma: {ex!r}\n")
    return None


def limits():
    resource.setrlimit(resource.RLIMIT_CPU, (60, 60))
    resource.setrlimit(resource.RLIMIT_AS, (1536 << 20, 1536 << 20))


# ---------------------------------------------------------------- usuaris i sessions
# Viuen a MySQL de l'allotjament PHP, a través de cdn/api.php (magatzem.py). La sessió es guarda
# com a sha256 de la galeta; per no fer una crida transatlàntica a cada pàgina, en tenim 60 s de memòria cau.
_cau = {}
_cau_lock = threading.Lock()


def _hash(clau):
    return hashlib.sha256(clau.encode()).hexdigest()


def desa_usuari(uid, battletag, toons):
    magatzem.desa_usuari(uid, battletag, toons)


def nova_sessio(uid):
    clau = secrets.token_urlsafe(32)
    magatzem.nova_sessio(_hash(clau), uid, int(time.time()) + DIES_SESSIO * 86400)
    return clau


def usuari_de(clau):
    if not clau:
        return None
    h = _hash(clau)
    with _cau_lock:
        if h in _cau and _cau[h][0] > time.time():
            return _cau[h][1]
    try:
        u = magatzem.usuari_sessio(h)
    except Exception as ex:
        sys.stderr.write(f"cdn: {ex!r}\n")
        return None
    with _cau_lock:
        if len(_cau) > 1000:
            _cau.clear()
        _cau[h] = (time.time() + 60, u)
    return u


def posa_compartir(clau, u, compartir):
    magatzem.posa_compartir(u["id"], compartir)
    with _cau_lock:
        _cau.pop(_hash(clau), None)
    # el permís de baixada de les partides ja consultades pot haver canviat
    with _permis_lock:
        _permis.clear()


# si un replay es pot baixar: també 60 s de memòria cau, que cada pàgina de partida ho pregunta
_permis = {}
_permis_lock = threading.Lock()


def baixable(rid):
    with _permis_lock:
        if rid in _permis and _permis[rid][0] > time.time():
            return _permis[rid][1]
    try:
        ok = magatzem.baixable(rid, JO_TOON)
    except Exception as ex:
        sys.stderr.write(f"cdn: {ex!r}\n")
        return False
    with _permis_lock:
        if len(_permis) > 5000:
            _permis.clear()
        _permis[rid] = (time.time() + 60, ok)
    return ok


def nom_fitxer(rid):
    """<mapa> - <jugador> vs <jugador>: el nom amb què es baixa el replay."""
    try:
        r = json.load(open(os.path.join(HTML, "data", "games", rid + ".json")))
        return f'{r["mapa_nom"]} - {" vs ".join(j["nom"] for j in r["jugadors"])}'[:150]
    except (OSError, ValueError, KeyError):
        return rid


def tanca_sessio(clau):
    h = _hash(clau)
    with _cau_lock:
        _cau.pop(h, None)
    magatzem.tanca_sessio(h)


# ---------------------------------------------------------------- Battle.net
def bnet(url, dades=None, token=None, basic=False):
    req = urllib.request.Request(url, data=urllib.parse.urlencode(dades).encode() if dades else None)
    if token:
        req.add_header("Authorization", "Bearer " + token)
    if basic:
        import base64
        req.add_header("Authorization", "Basic " + base64.b64encode(f"{BNET_ID}:{BNET_SECRET}".encode()).decode())
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)


def perfils_sc2(account_id, token):
    """Comptes de StarCraft II d'un compte de Battle.net, com a toons (regió-S2-realm-id)."""
    for host in ("eu", "us", "kr"):
        try:
            ps = bnet(f"https://{host}.api.blizzard.com/sc2/player/{account_id}", token=token)
        except Exception:
            continue
        toons = [dict(toon=f'{p["regionId"]}-S2-{p["realmId"]}-{p["profileId"]}', nom=p.get("name", ""))
                 for p in ps if all(k in p for k in ("regionId", "realmId", "profileId"))]
        if toons:
            return toons
    return []


class H(BaseHTTPRequestHandler):
    def respon(self, codi, dades, galetes=()):
        cos = json.dumps(dades).encode()
        self.send_response(codi)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        for g in galetes:
            self.send_header("Set-Cookie", g)
        self.send_header("Content-Length", str(len(cos)))
        self.end_headers()
        self.wfile.write(cos)

    def redirigeix(self, url, galetes=()):
        self.send_response(302)
        self.send_header("Location", url)
        self.send_header("Cache-Control", "no-store")
        for g in galetes:
            self.send_header("Set-Cookie", g)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def galeta(self, nom):
        c = http.cookies.SimpleCookie(self.headers.get("Cookie") or "")
        return c[nom].value if nom in c else None

    @staticmethod
    def torna_segura(t):
        # només rutes del mateix lloc o de les webs germanes, per no fer de redirector obert
        if t and t.startswith("/") and not t.startswith("//"):
            return t
        u = urlsplit(t or "")
        if u.scheme == "https" and u.hostname in ALTRES_WEBS and not u.username and not u.port:
            return t
        return "/"

    def do_GET(self):
        p, q = ruta(self.path)
        if p == "/api/me":
            u = usuari_de(self.galeta("sc2s"))
            if not u:
                return self.respon(200, {})
            # primer el compte de SC2 amb més partides nostres (un jugador d'EU pot tenir també un compte buit a US)
            for x in u["toons"]:
                f = os.path.join(HTML, "data", "players", x["toon"] + ".json")
                try:
                    x["partides"] = len(json.load(open(f))) if RE_TOON.fullmatch(x["toon"]) else 0
                except (OSError, ValueError):
                    x["partides"] = 0
            u["toons"].sort(key=lambda x: -x["partides"])
            return self.respon(200, {"battletag": u["battletag"], "toons": u["toons"], "compartir": bool(u.get("compartir"))})
        if p == "/api/key":
            u = usuari_de(self.galeta("sc2s"))
            if not u:
                return self.respon(401, {"error": "sessio"})
            try:
                return self.respon(200, {"clau": magatzem.info_clau(u["id"])})
            except Exception as ex:
                sys.stderr.write(f"cdn: {ex!r}\n")
                return self.respon(502, {"error": "cdn"})
        if p == "/api/download":
            rid = (q.get("id") or [""])[0]
            ok = bool(RE_ID.fullmatch(rid)) and baixable(rid)
            if q.get("check"):
                return self.respon(200, {"baixable": ok})
            if not ok:
                return self.respon(403, {"error": "no-baixable"})
            return self.redirigeix(magatzem.enllac_baixada(rid, nom_fitxer(rid)))
        if p == "/api/summary":
            rid, lang = (q.get("id") or [""])[0], (q.get("lang") or [""])[0]
            if not RE_ID.fullmatch(rid) or lang not in resum.IDIOMES or not os.path.exists(os.path.join(HTML, "data", "games", rid + ".json")):
                return self.respon(404, {"error": "no-trobat"})
            f = resum.fitxer(HTML, rid, lang)
            with RESUMS:
                if not os.path.exists(f):  # potser l'ha fet una altra petició mentre esperàvem
                    try:
                        resum.fes(HTML, rid, lang, resum.MODELS_WEB)
                    except resum.Limit:
                        return self.respon(429, {"error": "quota"})
                    except Exception as ex:
                        sys.stderr.write(f"resum {rid} {lang}: {ex!r}\n")
                        return self.respon(502, {"error": "resum"})
            return self.respon(200, json.load(open(f)))
        if p == "/api/login":
            if not BNET_ID:
                return self.respon(503, {"error": "sense-battlenet"})
            estat = secrets.token_urlsafe(24)
            torna = self.torna_segura((q.get("return") or ["/"])[0])
            params = dict(client_id=BNET_ID, redirect_uri=TORNADA, response_type="code", scope="openid sc2.profile", state=estat)
            g = [f"sc2o={estat}|{urllib.parse.quote(torna, safe='')}; Path=/api/; Max-Age=600; HttpOnly; Secure; SameSite=Lax"]
            return self.redirigeix("https://oauth.battle.net/authorize?" + urllib.parse.urlencode(params), g)
        if p == "/api/battlenet":
            desat = (self.galeta("sc2o") or "").split("|", 1)
            esborra = "sc2o=; Path=/api/; Max-Age=0; HttpOnly; Secure; SameSite=Lax"
            if len(desat) != 2 or not secrets.compare_digest(desat[0], (q.get("state") or [""])[0]) or "code" not in q:
                return self.redirigeix("/?login=error", [esborra])
            torna = self.torna_segura(urllib.parse.unquote(desat[1]))
            try:
                tok = bnet("https://oauth.battle.net/token", dict(grant_type="authorization_code", code=q["code"][0], redirect_uri=TORNADA), basic=True)
                info = bnet("https://oauth.battle.net/userinfo", token=tok["access_token"])
                toons = perfils_sc2(info["id"], tok["access_token"])
            except Exception as ex:
                sys.stderr.write(f"battlenet: {ex!r}\n")
                return self.redirigeix("/?login=error", [esborra])
            desa_usuari(int(info["id"]), info.get("battletag", ""), toons)
            clau = nova_sessio(int(info["id"]))
            sessio = f"sc2s={clau}; Path=/; Max-Age={DIES_SESSIO * 86400}; HttpOnly; Secure; SameSite=Lax" + (f"; Domain={GALETA_DOMINI}" if GALETA_DOMINI else "")
            return self.redirigeix(torna, [esborra, sessio])
        return self.respon(404, {"error": "no-trobat"})

    def do_POST(self):
        p, q = ruta(self.path)
        if p == "/api/logout":
            clau = self.galeta("sc2s")
            if clau:
                tanca_sessio(clau)
            # esborra la de la web i, si n'hi ha, la de tot el domini
            fora = ["sc2s=; Path=/; Max-Age=0; HttpOnly; Secure; SameSite=Lax"]
            if GALETA_DOMINI:
                fora.append(f"sc2s=; Path=/; Max-Age=0; HttpOnly; Secure; SameSite=Lax; Domain={GALETA_DOMINI}")
            return self.respon(200, {}, fora)
        if p == "/api/key":
            u = usuari_de(self.galeta("sc2s"))
            if not u:
                return self.respon(401, {"error": "sessio"})
            n = int(self.headers.get("Content-Length") or 0)
            try:
                d = json.loads(self.rfile.read(min(n, 2000)) or b"{}")
            except ValueError:
                return self.respon(400, {"error": "json"})
            if d.get("esborra"):
                magatzem.esborra_clau(u["id"])
                return self.respon(200, {"clau": None})
            clau = str(d.get("clau") or "").strip()
            if not RE_CLAU_GEMINI.fullmatch(clau):
                return self.respon(400, {"error": "format"})
            try:
                resum.prova_clau(clau)
            except resum.ClauDolenta as ex:
                return self.respon(400, {"error": "clau", "detall": str(ex)})
            except Exception as ex:
                sys.stderr.write(f"prova de clau: {ex!r}\n")
                return self.respon(502, {"error": "gemini"})
            lang = d.get("lang") if d.get("lang") in resum.IDIOMES else "en"
            magatzem.desa_clau(u["id"], clau, lang)
            return self.respon(200, {"clau": magatzem.info_clau(u["id"])})
        if p == "/api/share":
            clau = self.galeta("sc2s")
            u = usuari_de(clau)
            if not u:
                return self.respon(401, {"error": "sessio"})
            n = int(self.headers.get("Content-Length") or 0)
            try:
                d = json.loads(self.rfile.read(min(n, 1000)) or b"{}")
            except ValueError:
                return self.respon(400, {"error": "json"})
            posa_compartir(clau, u, bool(d.get("compartir")))
            return self.respon(200, {"compartir": bool(d.get("compartir"))})
        if p != "/api/upload":
            return self.respon(404, {"error": "no-trobat"})
        # ?jugador=2-S2-1-1234567: el programa de pujada diu de qui és el compte; si hi juga, va al seu perfil
        toon = (q.get("player") or [""])[0] or None
        # des del navegador: si has entrat, la partida va al teu perfil (si hi jugues)
        u = None if toon else usuari_de(self.galeta("sc2s"))
        if toon and not RE_TOON.fullmatch(toon):
            return self.respon(400, {"error": "jugador"})
        n = int(self.headers.get("Content-Length") or 0)
        if n <= 0 or n > MAX:
            return self.respon(413, {"error": "mida"})
        dades = self.rfile.read(n)
        if not dades.startswith(b"MPQ\x1b"):
            return self.respon(400, {"error": "no-replay"})
        rid = hashlib.sha1(dades).hexdigest()[:12]
        f = os.path.join(ENVIATS, rid + ".SC2Replay")
        if not os.path.exists(f):
            with open(f, "wb") as fh:
                fh.write(dades)
        candidats = [toon] if toon else [t["toon"] for t in (u or {}).get("toons", [])] or [None]
        resultat = None
        for c in candidats:
            with UN_A_UN:
                try:
                    p = subprocess.run([PYTHON, "-I", os.path.join(ARREL, "analitza.py"), "una", f, MAPES, HTML] + ([c] if c else []),
                                       capture_output=True, timeout=120, preexec_fn=limits, cwd=ARREL)
                except subprocess.TimeoutExpired:
                    return self.respon(500, {"error": "temps"})
            if p.returncode == 2:
                os.remove(f)
                # no és 1v1: potser és de Marine Arena i la vol ma.lestudi.com (així el pujador no ha de canviar)
                ma = envia_a_ma(dades, toon, self.headers.get("Cookie"))
                if ma is not None:
                    return self.respon(200, ma)
                return self.respon(422, {"error": "no-1v1"})
            if p.returncode != 0:
                sys.stderr.write(p.stderr.decode(errors="replace")[-2000:] + "\n")
                return self.respon(500, {"error": "analisi"})
            resultat = json.loads(p.stdout.decode())
            if resultat.get("perfil"):
                break
        # el replay va a l'allotjament PHP i aquí no en queda còpia
        try:
            magatzem.puja_replay(rid, f, "enviat")
            os.remove(f)
        except Exception as ex:
            sys.stderr.write(f"cdn: no s'ha pogut desar {rid}: {ex!r}\n")  # es queda a enviats/ i ja es pujarà
        return self.respon(200, resultat)

    def log_message(self, fmt, *args):
        # sense IPs ni galetes: només el que ha passat (sense query string, que pot portar el codi d'OAuth)
        sys.stderr.write("%s\n" % (fmt % args).split("?")[0])


if __name__ == "__main__":
    os.makedirs(ENVIATS, exist_ok=True)
    ThreadingHTTPServer(("127.0.0.1", 8765), H).serve_forever()
