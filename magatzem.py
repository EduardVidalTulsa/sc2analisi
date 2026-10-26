# SPDX-License-Identifier: GPL-3.0-or-later
"""Client de l'API privada de l'allotjament PHP (cdn/api.php): replays i base de dades.

La configuració (CDN_URL, CDN_CLAU) ve de l'entorn o, si no hi és, de /etc/sc2/cdn.env.
"""
import json, os, urllib.parse, urllib.request


def _conf():
    url, clau = os.environ.get("CDN_URL"), os.environ.get("CDN_CLAU")
    if not (url and clau) and os.path.exists("/etc/sc2/cdn.env"):
        for l in open("/etc/sc2/cdn.env"):
            k, _, v = l.strip().partition("=")
            if k == "CDN_URL": url = url or v
            if k == "CDN_CLAU": clau = clau or v
    if not (url and clau):
        raise RuntimeError("falta la configuració de l'allotjament PHP (CDN_URL, CDN_CLAU)")
    return url, clau


def _crida(op, params=None, cos=None, binari=None, crua=False, temps=30, tipus="application/octet-stream"):
    url, clau = _conf()
    q = urllib.parse.urlencode(dict(op=op, **(params or {})))
    dades = binari if binari is not None else (json.dumps(cos).encode() if cos is not None else None)
    req = urllib.request.Request(f"{url}?{q}", data=dades, method="POST" if dades is not None else "GET")
    req.add_header("X-Clau", clau)
    req.add_header("User-Agent", "sc2analisi/1")
    if binari is not None:
        req.add_header("Content-Type", tipus)
    elif cos is not None:
        req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=temps) as r:
        return r.read() if crua else json.load(r)


# ---- replays
def puja_replay(rid, fitxer, origen="enviat", nom=None):
    # com a fitxer d'un formulari multipart: el ModSecurity d'alguns allotjaments bloqueja els cossos binaris "crus"
    frontera = "----sc2" + os.urandom(12).hex()
    cos = (f"--{frontera}\r\nContent-Disposition: form-data; name=\"replay\"; filename=\"{rid}.SC2Replay\"\r\n"
           f"Content-Type: application/octet-stream\r\n\r\n").encode() + open(fitxer, "rb").read() + f"\r\n--{frontera}--\r\n".encode()
    _crida("replay_puja", dict(id=rid, origen=origen, **({"nom": nom} if nom else {})), binari=cos,
           tipus="multipart/form-data; boundary=" + frontera, temps=120)


def baixa_replay(rid, desti):
    dades = _crida("replay_baixa", dict(id=rid), crua=True, temps=120)
    with open(desti + ".tmp", "wb") as f:
        f.write(dades)
    os.replace(desti + ".tmp", desti)


def replays():
    return _crida("replays")


# ---- usuaris i sessions
def desa_usuari(uid, battletag, toons):
    _crida("usuari_desa", cos=dict(id=uid, battletag=battletag, toons=toons))


def nova_sessio(clau_hash, uid, caduca):
    _crida("sessio_nova", cos=dict(clau=clau_hash, usuari=uid, caduca=caduca))


def usuari_sessio(clau_hash):
    return _crida("sessio_usuari", cos=dict(clau=clau_hash))["usuari"]


def tanca_sessio(clau_hash):
    _crida("sessio_tanca", cos=dict(clau=clau_hash))


# ---- registre de perfils: quines partides ha pujat cada jugador
def afegeix_a_perfil(toon, rid):
    _crida("perfil_afegeix", cos=dict(toon=toon, partida=rid))


def perfils():
    return _crida("perfils")


# ---- baixades: l'usuari decideix si els replays que ha pujat es poden baixar
def posa_compartir(uid, compartir):
    _crida("usuari_compartir", cos=dict(id=uid, compartir=bool(compartir)))


def baixable(rid, jo_toon):
    return _crida("replay_permis", dict(id=rid, jo=jo_toon))["baixable"]


def enllac_baixada(rid, nom, minuts=10):
    """Enllaç signat a r.php de l'allotjament PHP, que caduca en uns minuts."""
    import hashlib, hmac, time
    url, clau = _conf()
    e = str(int(time.time()) + minuts * 60)
    s = hmac.new(clau.encode(), f"{rid}|{e}|{nom}".encode(), hashlib.sha256).hexdigest()
    return url.rsplit("/", 1)[0] + "/r.php?" + urllib.parse.urlencode(dict(id=rid, e=e, n=nom, s=s))


# ---- claus de Gemini dels usuaris
# Es desen xifrades (AES-GCM) a MySQL; la clau per desxifrar-les només és al servidor (/etc/sc2/claus.key).
# L'id de l'usuari va com a dada associada: una clau xifrada copiada a un altre usuari no es desxifra.
CLAUS_KEY = "/etc/sc2/claus.key"


def _aes():
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    return AESGCM(bytes.fromhex(open(CLAUS_KEY).read().strip()))


def desa_clau(uid, clau, lang):
    import base64
    nonce = os.urandom(12)
    xifrada = base64.b64encode(nonce + _aes().encrypt(nonce, clau.encode(), str(uid).encode())).decode()
    _crida("clau_desa", cos=dict(usuari=uid, xifrada=xifrada, final=clau[-4:], lang=lang))


def esborra_clau(uid):
    _crida("clau_esborra", cos=dict(usuari=uid))


def info_clau(uid):
    """L'estat de la clau d'un usuari (sense la clau): {final, lang, afegida, estat, error, mes, fets, ultim} o None."""
    return _crida("clau_info", cos=dict(usuari=uid))["clau"]


def claus_actives():
    """[{usuari, clau, lang, toons}] de les claus que funcionen, ja desxifrades."""
    import base64
    out = []
    for c in _crida("claus_actives"):
        d = base64.b64decode(c["xifrada"])
        try:
            clau = _aes().decrypt(d[:12], d[12:], str(c["usuari"]).encode()).decode()
        except Exception:
            continue
        out.append(dict(usuari=c["usuari"], clau=clau, lang=c["lang"] or "en", toons=c["toons"]))
    return out


def estat_clau(uid, estat, error=None):
    _crida("clau_estat", cos=dict(usuari=uid, estat=estat, error=error))


def us_clau(uid, mes):
    _crida("clau_us", cos=dict(usuari=uid, mes=mes))
