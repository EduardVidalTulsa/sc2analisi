#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Resum d'una partida en un paràgraf, escrit per Gemini a partir dels fets que n'ha tret analitza.py.

A Gemini no hi van els noms: els jugadors són "A" i "B" i el text torna amb {A} i {B}, que la web
substitueix pels noms (jugadors[0] i jugadors[1] de la partida). La clau ve de GEMINI_API_KEY o de
/etc/sc2/gemini.env (projecte sense facturació: nivell gratuït, amb límit de crides per dia).

Es desen a html/data/summaries/<id>.<idioma>.json. L'anglès el va fent el servei sc2-resums
(python resum.py treballa html); la resta són traduccions de l'anglès que la web demana quan algú les vol
(/api/summary).

    python resum.py <partida.json> [idioma]     prova: escriu el resum (fet de zero) per stdout
    python resum.py treballa <dir html>          fa els que falten, de la partida més nova a la més vella
"""
import fcntl, json, os, re, sys, time, urllib.error, urllib.request

# Quota gratuïta del projecte (AI Studio → Rate limit): Flash 20 crides/dia i 5/min, Flash-Lite 500/dia i 15/min.
# El Flash escriu millor; el Lite és més ràpid i n'hi ha més. Cada model té la seva quota: si un va ple, l'altre.
FLASH, LITE = "gemini-3.5-flash", "gemini-3.5-flash-lite"
MODELS = [FLASH, LITE]          # el servei sc2-resums: les partides noves amb el Flash mentre n'hi hagi
MODELS_WEB = [LITE, FLASH]      # quan algú espera a la web: el ràpid
# Del Flash-Lite, el servei en gasta com a molt LITE_SERVEI al dia i la resta (fins a les 500 de Google) queda per a
# les traduccions que demanen els visitants. El Flash no el limitem: Google ja en dona poques i respon 429.
# El comptador el comparteixen el servei i la web; el dia és el de Google (hora del Pacífic).
LITE_DIA = 500
LITE_SERVEI = 400
COMPTADOR = "/var/lib/sc2/gemini-dia.json"
IDIOMES = {"ca": "català", "en": "English", "zh": "简体中文", "hi": "हिन्दी", "es": "español",
           "ar": "العربية", "fr": "français", "bn": "বাংলা", "pt": "português do Brasil"}


class ClauDolenta(Exception):
    """La clau de Gemini d'un usuari no funciona (incorrecta, revocada o sense accés a l'API)."""


class Limit(Exception):
    """Tots els models han tornat 429 o s'ha acabat la nostra part de la quota del dia: ja es farà més endavant."""


def _mes():
    return time.strftime("%Y-%m", time.gmtime())  # per a l'estadística de les claus dels usuaris


def _dia():
    from datetime import datetime
    from zoneinfo import ZoneInfo
    return datetime.now(ZoneInfo("America/Los_Angeles")).strftime("%Y-%m-%d")  # la quota de Google es renova aquí


def gastades():
    """Crides al Flash-Lite que hem fet avui."""
    try:
        return json.load(open(COMPTADOR)).get(_dia(), 0)
    except (OSError, ValueError):
        return 0


def _compta(limit=None):
    """Amb limit: Limit si avui ja s'han fet les crides al Flash-Lite permeses. Sense: compta una crida feta.
    Amb bloqueig de fitxer, que hi escriuen dos processos (el servei i la web)."""
    with open(COMPTADOR, "a+") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        f.seek(0)
        try:
            d = json.loads(f.read() or "{}")
        except ValueError:
            d = {}
        n = d.get(_dia(), 0)
        if limit is not None:
            if n >= limit:
                raise Limit()
            return
        f.seek(0); f.truncate(); f.write(json.dumps({_dia(): n + 1})); f.flush()  # només el dia en curs


def _clau():
    k = os.environ.get("GEMINI_API_KEY")
    if not k and os.path.exists("/etc/sc2/gemini.env"):
        for l in open("/etc/sc2/gemini.env"):
            if l.startswith("GEMINI_API_KEY="):
                k = l.strip().split("=", 1)[1]
    if not k:
        raise RuntimeError("falta GEMINI_API_KEY")
    return k

def mmss(s):
    return None if s is None else f"{int(s) // 60}:{int(s) % 60:02d}"


def _a(serie, t):
    """El punt d'una sèrie [{t, ...}] més proper al segon t (o None si la partida ja s'havia acabat)."""
    if not serie or t > serie[-1]["t"] + 30:
        return None
    return min(serie, key=lambda p: abs(p["t"] - t))


def fets(r):
    """Els fets de la partida, amb els jugadors com a A i B. Només números: res que Gemini hagi d'endevinar."""
    js = r["jugadors"]
    pid = {j["pid"]: "AB"[i] for i, j in enumerate(js)}
    out = dict(map=r["mapa_nom"], length=mmss(r["durada"]), ranked=r.get("competitiu"), players={})
    pct_ctrl = ((r.get("control") or {}).get("pct") or {})
    for j in js:
        p, s = str(j["pid"]), r["stats"].get(str(j["pid"]), [])
        moments = {}
        for m in (4, 6, 8, 10, 12, 15, 20):
            x = _a(s, m * 60)
            if x:
                moments[f"{m}min"] = dict(workers=x["treb"], army_value=x["exer"], supply=f'{x["sup"]}/{x["supmax"]}',
                                          unspent=x["banc"])
        pct = pct_ctrl.get(p) or []
        out["players"]["AB"[js.index(j)]] = dict(
            race=j["raça"], result={"V": "win", "D": "loss"}.get(j["resultat"], "?"),
            mmr=j.get("mmr"), apm=j.get("apm"), epm=j.get("epm"), spending_quotient=j.get("sq"),
            bases_at=[mmss(t) for t in j.get("t_bases") or []],
            first_orders=[f"{mmss(t)} {n}" + (f" x{k}" if k > 1 else "") for t, n, k in (r.get("ordre") or {}).get(p, [])[:25]],
            snapshots=moments,
            map_control_pct={f"{m}min": pct[m * 6] for m in (4, 8, 12, 16) if m * 6 < len(pct)},
        )
    bs = []
    for b in r["batalles"]:
        bs.append(dict(
            start=mmss(b["t0"]), end=mmss(b["t1"]), kind=b["tipus"], more_value_lost_by_opponent_of=pid.get(b.get("guanya")),
            army_before={pid[int(k)]: v for k, v in (b.get("exercit_abans") or {}).items() if int(k) in pid},
            losses={pid[int(k)]: dict(value=v["valor"], workers=v["treb"], structures=v["estr"], units=v["unitats"])
                    for k, v in b["perdues"].items() if int(k) in pid},
        ))
    # les escaramusses petites no expliquen la partida: les més grosses, en ordre de temps
    grosses = sorted(bs, key=lambda b: -sum(x["value"] for x in b["losses"].values()))[:12]
    out["fights"] = sorted(grosses, key=lambda b: b["start"].zfill(6))
    out["fights_total"] = len(bs)
    return out


PROMPT = """You are an expert StarCraft II caster. Write ONE paragraph (90-140 words) in {idioma}
summarising this 1v1 game: the opening (expansions, first units), the key moments (big fights,
worker kills, who controls the map) and why the winner won.

Rules:
- Use ONLY the data below. Do not invent strategies, units, upgrades or moments that are not there.
- Refer to the players exactly as "{{A}}" and "{{B}}" (with the braces), never "player A".
- Times as m:ss. Unit and building names ALWAYS in English as in the game, never translated, with normal
  spacing (Spawning Pool, Siege Tank, Overlord).
- Short, concrete caster tone: start straight with the facts, no exclamations or rhetorical openings, no lists,
  no headings, no generic praise. Write natural, correct {idioma}.
- "army_value", "value" and "unspent" are resources (minerals+gas). "map_control_pct" is the share of the map
  each player dominates: differences under 5 points mean nobody really controls it, so don't stress them.
- In "fights", "more_value_lost_by_opponent_of" only says who lost less value there, not who won the game.
  The game result is in "players.*.result".

Data:
{dades}"""


def gemini(prompt, model, clau=None):
    cos = json.dumps(dict(contents=[dict(parts=[dict(text=prompt)])],
                          generationConfig=dict(temperature=0.4, maxOutputTokens=8192))).encode()
    req = urllib.request.Request(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                                 data=cos, headers={"Content-Type": "application/json", "x-goog-api-key": clau or _clau()})
    with urllib.request.urlopen(req, timeout=90) as r:
        d = json.load(r)
    c = d["candidates"][0]
    if c.get("finishReason") != "STOP":  # tallat (MAX_TOKENS) o bloquejat: no ens serveix
        raise RuntimeError("gemini: " + str(c.get("finishReason")))
    return "".join(p.get("text", "") for p in c["content"]["parts"] if not p.get("thought")).strip()


# Idiomes amb traducció oficial de l'SC2: s'hi fan servir els noms d'unitats del joc en aquell idioma.
# En la resta (català, hindi, àrab, bengalí) els jugadors els coneixen en anglès.
# Gemini Lite s'inventa els noms "oficials" (es: "charca de hidraliscos", fr: "fumière"): fins que tinguem un
# glossari tret del joc, l'anglès a tot arreu. Quan hi sigui: {"es": "Spanish (Spain)", "fr": "French", ...}
JOC_TRADUIT = {}

PROMPT_TRADUEIX = """Translate this StarCraft II game summary from English into {idioma}.

Rules:
- Keep "{{A}}" and "{{B}}" exactly as they are (with the braces): they are the players' names.
- Keep every number and time (m:ss) exactly. Keep the map name exactly as written (e.g. "Washout LE").
- {noms}
- Natural, correct {idioma}, same caster tone and length. Output only the translation, as one paragraph.

Summary:
{text}"""


def resum(r, lang="ca", models=None, limit=LITE_DIA, clau=None):
    """{"text", "model"}: el text amb {A} i {B} per posar-hi els noms."""
    prompt = PROMPT.format(idioma=IDIOMES[lang], dades=json.dumps(fets(r), ensure_ascii=False, separators=(",", ":")))
    return _demana(prompt, models, limit, clau)


def tradueix(text_en, lang, models=None, limit=LITE_DIA, clau=None):
    """El resum anglès en un altre idioma, amb els noms d'unitats com els coneix qui juga en aquell idioma."""
    if lang in JOC_TRADUIT:
        noms = (f"Unit, building and upgrade names: use the official names from the {JOC_TRADUIT[lang]} version of "
                "StarCraft II. If you are not sure of an official name, keep the English one.")
    else:
        noms = ("Unit, building and upgrade names: keep them in English exactly as written (StarCraft II has no "
                f"{IDIOMES[lang]} version, so players know them in English). Do not translate them.")
    return _demana(PROMPT_TRADUEIX.format(idioma=IDIOMES[lang], noms=noms, text=text_en), models, limit, clau)


def _demana(prompt, models=None, limit=LITE_DIA, clau=None):
    """Prova els models en ordre; torna {"text", "model"} o Limit si tots van plens o s'ha acabat la nostra part del
    Flash-Lite d'avui. Amb la clau d'un usuari no compta per a la nostra quota (és la seva); si no va, ClauDolenta."""
    models = models or MODELS
    if not clau:
        try:
            _compta(limit)
        except Limit:
            models = [m for m in models if m != LITE]  # sense Lite; el Flash, si en queda
            if not models:
                raise
    error, plens = None, 0
    for model in models:
        for _ in range(2):
            try:
                text = re.sub(r"\s+", " ", gemini(prompt, model, clau))
                if not clau and model == LITE:
                    _compta()  # només compten les crides al Lite que han tornat un text
                if "{A}" in text or "{B}" in text:
                    return dict(text=text, model=model)
                error = RuntimeError("resposta sense {A}/{B}")
            except urllib.error.HTTPError as ex:
                error = ex
                if ex.code == 429:
                    plens += 1
                    break  # aquest model va ple: el següent
                if ex.code >= 500:
                    time.sleep(5); continue
                if clau and ex.code in (400, 401, 403):
                    raise ClauDolenta(_missatge(ex))
                break  # 404 (model que no hi és) o altres: el següent model
            except (RuntimeError, OSError, KeyError) as ex:
                error = ex
    if plens == len(models):
        raise Limit()
    raise error


def _missatge(ex):
    try:
        return json.loads(ex.read() or b"{}").get("error", {}).get("message", "")[:200] or f"HTTP {ex.code}"
    except ValueError:
        return f"HTTP {ex.code}"


def prova_clau(clau):
    """Comprova la clau d'un usuari amb una crida mínima. Una clau que va però té la quota del dia plena també és bona."""
    try:
        gemini("Reply with the single word: OK", LITE, clau)
    except urllib.error.HTTPError as ex:
        if ex.code == 429:
            return
        if ex.code in (400, 401, 403, 404):
            raise ClauDolenta(_missatge(ex))
        raise


def fitxer(dir_html, rid, lang):
    return os.path.join(dir_html, "data", "summaries", f"{rid}.{lang}.json")


def fes(dir_html, rid, lang, models=None, limit=LITE_DIA, clau=None):
    """Genera i desa el resum d'una partida; torna el que s'ha desat. L'anglès es fa a partir de les dades;
    la resta d'idiomes, traduint l'anglès (que es fa abans si encara no hi és)."""
    if lang == "en":
        x = resum(json.load(open(os.path.join(dir_html, "data", "games", rid + ".json"))), "en", models, limit, clau)
    else:
        fen = fitxer(dir_html, rid, "en")
        en = json.load(open(fen)) if os.path.exists(fen) else fes(dir_html, rid, "en", models, limit, clau)
        x = tradueix(en["text"], lang, models, limit, clau)
        x["de"] = en["model"]
    x["fet"] = int(time.time())
    f = fitxer(dir_html, rid, lang)
    os.makedirs(os.path.dirname(f), exist_ok=True)
    json.dump(x, open(f + ".tmp", "w"), ensure_ascii=False)
    os.replace(f + ".tmp", f)
    return x


def treballa(dir_html):
    """Bucle del servei sc2-resums. A cada volta:
    1. les partides dels usuaris que han posat la seva clau de Gemini (les del seu perfil, de la més nova a la més vella),
       en anglès i en el seu idioma, amb la seva quota;
    2. la resta de la llista del servidor (data/games.json), primer les de més MMR, amb la nostra quota (LITE_SERVEI al dia).
    El resum és un per partida: si els dos jugadors tenen clau, el fa el primer que hi arriba."""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import magatzem
    fallides = {}   # (id, idioma) -> intents: una partida que falla sempre no ha de bloquejar la cua
    espera = {}     # usuari (o None, la nostra quota) -> fins quan no ho tornem a provar
    dolenta = {}    # usuari -> errors de permís seguits: en un projecte nou, l'accés triga uns minuts a activar-se
    POR_VOLTA = 10  # partides per usuari i volta: que cap clau no faci esperar les altres
    falta = lambda rid, lang: not os.path.exists(fitxer(dir_html, rid, lang)) and fallides.get((rid, lang), 0) < 3

    def fes_una(rid, lang, **kw):
        try:
            x = fes(dir_html, rid, lang, **kw)
            return x
        except (Limit, ClauDolenta):
            raise
        except Exception as ex:
            fallides[(rid, lang)] = fallides.get((rid, lang), 0) + 1
            print("error", rid, lang, repr(ex)[:300], flush=True)
        finally:
            time.sleep(15)  # a poc a poc: el nivell gratuït té límit per minut

    while True:
        try:
            llista = json.load(open(os.path.join(dir_html, "data", "games.json")))
        except (OSError, ValueError):
            llista = []

        # 1. amb les claus dels usuaris
        try:
            claus = magatzem.claus_actives()
        except Exception as ex:
            print("cdn:", repr(ex)[:200], flush=True); claus = []
        for c in claus:
            u = c["usuari"]
            if espera.get(u, 0) > time.time():
                continue
            toons = set(c["toons"])
            seves = [g["id"] for g in llista if any(j.get("toon") in toons for j in g["jugadors"])]
            fetes = 0
            try:
                for rid in seves:
                    if fetes >= POR_VOLTA:
                        break
                    for lang in dict.fromkeys(["en", c["lang"] if c["lang"] in IDIOMES else "en"]):
                        if falta(rid, lang) and fes_una(rid, lang, models=MODELS_WEB, clau=c["clau"]):
                            magatzem.us_clau(u, _mes()); fetes += 1; dolenta.pop(u, None)
                            print("ok", rid, lang, "amb la clau de", u, flush=True)
            except Limit:
                espera[u] = time.time() + 6 * 3600  # la seva quota del dia: ja continuarem
                print("quota plena de", u, flush=True)
            except ClauDolenta as ex:
                # pot ser temporal: només la donem per dolenta al tercer error seguit, amb 15 min entre intents
                dolenta[u] = dolenta.get(u, 0) + 1
                if dolenta[u] >= 3:
                    magatzem.estat_clau(u, "error", str(ex)); dolenta.pop(u)
                else:
                    espera[u] = time.time() + 900
                print("clau dolenta de", u, f"({dolenta.get(u, 3)}/3)", str(ex)[:120], flush=True)

        # 2. la resta, amb la nostra quota
        if espera.get(None, 0) <= time.time():
            mmr = lambda g: (lambda ms: sum(ms) / len(ms) if ms else 0)([j["mmr"] for j in g["jugadors"] if j.get("mmr")])
            pendents = [g["id"] for g in sorted(llista, key=lambda g: (mmr(g), g["data"]), reverse=True) if falta(g["id"], "en")]
            try:
                for rid in pendents[:POR_VOLTA]:
                    x = fes_una(rid, "en", models=MODELS, limit=LITE_SERVEI)
                    if x:
                        print("ok", rid, x["model"], f"(Lite: {gastades()}/{LITE_SERVEI} avui)", flush=True)
            except Limit:
                espera[None] = time.time() + 3600
                print(f"quota plena (Lite: {gastades()}/{LITE_SERVEI} avui, {len(pendents)} pendents): espero 1 h", flush=True)
        time.sleep(60)


if __name__ == "__main__":
    if sys.argv[1] == "treballa":
        treballa(sys.argv[2])
    else:
        r = json.load(open(sys.argv[1]))
        x = resum(r, sys.argv[2] if len(sys.argv) > 2 else "ca")
        print(x["model"])
        print(x["text"].replace("{A}", r["jugadors"][0]["nom"]).replace("{B}", r["jugadors"][1]["nom"]))
