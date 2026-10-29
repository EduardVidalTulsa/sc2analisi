#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Analitza replays de SC2 (només tracker events) i genera JSON per a la web estàtica.

Ús: analitza.py <dir_replays> <dir_mapes .s2ma> <dir_sortida html>
Escriu data/games.json, data/games/<id>.json i data/maps/<mapa>.json + .png
"""
import sys, types, importlib, os, re, json, glob, struct, hashlib, html, math, io
from collections import defaultdict

sys.modules.setdefault("imp", types.ModuleType("imp"))  # s2protocol encara importa imp
sys.path.insert(1, os.path.dirname(os.path.abspath(__file__)))  # magatzem.py (amb python -I no hi és)
import mpyq
import numpy as np
from PIL import Image

import s2protocol.versions as V

JO_TOON = os.environ.get("SC2_TOON", "")  # el jugador de les partides d'origen "meu" (variable d'entorn)
LOOPS = 22.4  # game loops per segon (velocitat faster)

_LATEST = V.list_all()[-1][:-3]


def proto(build):
    try:
        return importlib.import_module(f"s2protocol.versions.protocol{build:05d}")
    except ImportError:
        # els protocols recents són idèntics: fem servir el darrer
        return importlib.import_module("s2protocol.versions." + _LATEST)


# ---------------------------------------------------------------- costos
# (minerals, gas, supply, categoria) — categoria: w=treballador, a=exèrcit, s=estructura, t=townhall
C = {}
def _c(cat, txt):
    for l in txt.strip().splitlines():
        n, m, g, s = l.split()
        C[n] = (int(m), int(g), float(s), cat)

_c("w", """
SCV 50 0 1
Probe 50 0 1
Drone 50 0 1
""")
_c("a", """
Marine 50 0 1
Marauder 100 25 2
Reaper 50 50 1
Ghost 150 125 2
GhostAlternate 150 125 2
GhostNova 150 125 2
Hellion 100 0 2
HellionTank 100 0 2
WidowMine 75 25 2
WidowMineBurrowed 75 25 2
Cyclone 125 50 3
SiegeTank 150 125 3
SiegeTankSieged 150 125 3
ThorAP 300 200 6
Thor 300 200 6
VikingFighter 150 75 2
VikingAssault 150 75 2
Medivac 100 100 2
Liberator 150 125 3
LiberatorAG 150 125 3
Raven 100 150 2
Banshee 150 100 3
Battlecruiser 400 300 6
Zealot 100 0 2
Stalker 125 50 2
Sentry 50 100 2
Adept 100 25 2
HighTemplar 50 150 2
DarkTemplar 125 125 2
Immortal 275 100 4
Colossus 300 200 6
Disruptor 150 150 3
Archon 175 275 4
Observer 25 75 1
ObserverSiegeMode 25 75 1
WarpPrism 250 0 2
WarpPrismPhasing 250 0 2
Phoenix 150 100 2
VoidRay 250 150 4
Oracle 150 150 3
Carrier 350 250 6
Tempest 250 175 5
Mothership 400 400 8
Zergling 25 0 0.5
ZerglingBurrowed 25 0 0.5
Queen 150 0 2
QueenBurrowed 150 0 2
Roach 75 25 2
RoachBurrowed 75 25 2
Ravager 100 100 3
RavagerBurrowed 100 100 3
Baneling 50 25 0.5
BanelingBurrowed 50 25 0.5
Hydralisk 100 50 2
HydraliskBurrowed 100 50 2
LurkerMP 150 150 3
LurkerMPBurrowed 150 150 3
Infestor 100 150 2
InfestorBurrowed 100 150 2
SwarmHostMP 100 75 3
SwarmHostBurrowedMP 100 75 3
Ultralisk 275 200 6
UltraliskBurrowed 275 200 6
Mutalisk 100 100 2
Corruptor 150 100 2
BroodLord 300 250 4
Viper 100 200 3
Overseer 150 50 0
OverseerSiegeMode 150 50 0
Overlord 100 0 0
OverlordTransport 125 25 0
""")
_c("t", """
CommandCenter 400 0 0
CommandCenterFlying 400 0 0
OrbitalCommand 550 0 0
OrbitalCommandFlying 550 0 0
PlanetaryFortress 550 150 0
Nexus 400 0 0
Hatchery 300 0 0
Lair 450 100 0
Hive 650 250 0
""")
_c("s", """
SupplyDepot 100 0 0
SupplyDepotLowered 100 0 0
Refinery 75 0 0
RefineryRich 75 0 0
Barracks 150 0 0
BarracksFlying 150 0 0
EngineeringBay 125 0 0
Bunker 100 0 0
MissileTurret 100 0 0
SensorTower 125 50 0
Factory 150 100 0
FactoryFlying 150 100 0
GhostAcademy 150 50 0
Armory 150 50 0
Starport 150 100 0
StarportFlying 150 100 0
FusionCore 150 150 0
BarracksTechLab 50 25 0
BarracksReactor 50 50 0
FactoryTechLab 50 25 0
FactoryReactor 50 50 0
StarportTechLab 50 25 0
StarportReactor 50 50 0
Pylon 100 0 0
Assimilator 75 0 0
AssimilatorRich 75 0 0
Gateway 150 0 0
WarpGate 150 0 0
Forge 150 0 0
PhotonCannon 150 0 0
ShieldBattery 100 0 0
CyberneticsCore 150 0 0
TwilightCouncil 150 100 0
RoboticsFacility 150 100 0
Stargate 150 150 0
TemplarArchive 150 200 0
DarkShrine 150 150 0
RoboticsBay 150 150 0
FleetBeacon 300 200 0
SpawningPool 200 0 0
Extractor 25 0 0
ExtractorRich 25 0 0
EvolutionChamber 75 0 0
RoachWarren 150 0 0
BanelingNest 100 50 0
SpineCrawler 100 0 0
SpineCrawlerUprooted 100 0 0
SporeCrawler 75 0 0
SporeCrawlerUprooted 75 0 0
HydraliskDen 100 100 0
LurkerDenMP 100 150 0
InfestationPit 100 100 0
Spire 200 200 0
GreaterSpire 300 350 0
NydusNetwork 150 150 0
NydusCanal 75 75 0
UltraliskCavern 150 200 0
""")
# temps de fabricació (segons de joc a velocitat "faster"), per saber quan un edifici comença a fer una unitat:
# el replay només diu quan neix. Sense Chrono Boost; les unitats de WarpGate fan servir el temps del Gateway.
TEMPS_FER = {
    "SCV": 12, "Marine": 18, "Marauder": 21, "Reaper": 32, "Ghost": 29, "Hellion": 21, "HellionTank": 21,
    "WidowMine": 21, "Cyclone": 32, "SiegeTank": 32, "Thor": 43, "VikingFighter": 30, "Medivac": 30,
    "Liberator": 43, "Raven": 43, "Banshee": 43, "Battlecruiser": 64,
    "Probe": 12, "Zealot": 27, "Stalker": 30, "Sentry": 26, "Adept": 30, "HighTemplar": 39, "DarkTemplar": 39,
    "Immortal": 39, "Colossus": 54, "Disruptor": 36, "Observer": 21, "WarpPrism": 36, "Phoenix": 25,
    "Oracle": 37, "VoidRay": 37, "Tempest": 43, "Carrier": 64, "Mothership": 89,
    "Queen": 36,
}

DEFENSA = {"Bunker", "MissileTurret", "PhotonCannon", "ShieldBattery", "SpineCrawler",
           "SporeCrawler", "PlanetaryFortress"}

# noms per mostrar (abreujats al client si cal)
NOMS = {"HellionTank": "Hellbat", "ThorAP": "Thor", "VikingFighter": "Viking", "VikingAssault": "Viking",
        "SiegeTankSieged": "SiegeTank", "WidowMineBurrowed": "WidowMine", "LiberatorAG": "Liberator",
        "LurkerMP": "Lurker", "LurkerMPBurrowed": "Lurker", "SwarmHostMP": "SwarmHost",
        "SwarmHostBurrowedMP": "SwarmHost", "LurkerDenMP": "LurkerDen", "SupplyDepotLowered": "SupplyDepot",
        "ObserverSiegeMode": "Observer", "OverseerSiegeMode": "Overseer", "WarpPrismPhasing": "WarpPrism",
        "GhostAlternate": "Ghost", "GhostNova": "Ghost", "AssimilatorRich": "Assimilator",
        "RefineryRich": "Refinery", "ExtractorRich": "Extractor"}
def nom(t):
    t = NOMS.get(t, t)
    if t.endswith("Burrowed"):
        t = t[:-8]
    if t.endswith("Flying"):
        t = t[:-6]
    return t


def neteja_nom(b):
    s = b.decode("utf-8", "replace")
    s = html.unescape(s.replace("<sp/>", " "))
    return re.sub(r"^<[^>]*>\s*", "", s).strip()


# ---------------------------------------------------------------- mapes
def llegeix_mapa(path):
    a = mpyq.MPQArchive(path)
    m = a.read_file("MapInfo")
    w, h = struct.unpack_from("<II", m, 16)
    mt = re.search(rb"([\x20-\x7e]+)\x00([\x20-\x7e]+)\x00", m[24:])
    l, b, r, t = struct.unpack_from("<IIII", m, 24 + mt.end())
    gs = a.read_file("enUS.SC2Data\\LocalizedData\\GameStrings.txt") or b""
    mm = re.search(rb"DocInfo/Name=(.*)", gs)
    nom_mapa = mm.group(1).strip().decode() if mm else os.path.basename(path)
    cl = a.read_file("t3SyncCliffLevel")
    cw, chh = struct.unpack_from("<II", cl, 8)
    # la capçalera fa 32 bytes (no 16): les dades són els darrers cw*chh valors
    cliff = np.frombuffer(cl[len(cl) - cw * chh * 2:], dtype="<u2").reshape(chh, cw)
    return dict(nom=nom_mapa, w=w, h=h, camera=(l, b, r, t), cliff=cliff)


PALETA = [(14, 17, 22), (40, 46, 56), (62, 70, 82), (88, 98, 112), (118, 128, 142)]

def exporta_mapa(mp, recursos, dir_out, slug):
    """PNG del relleu (1 px per cel·la) + JSON amb dimensions i recursos."""
    c = mp["cliff"].astype(np.int32)
    nivells = sorted(set(np.unique(c)) - {0})
    # els nivells "bons" són múltiples de 64; els intermedis són rampes
    img = np.zeros(c.shape + (3,), np.uint8)
    img[:] = PALETA[0]
    for v in nivells:
        f = min(v / 64.0, 4.0)
        lo, hi = int(math.floor(f)), int(math.ceil(f))
        a_, b_ = PALETA[min(lo, 4)], PALETA[min(hi, 4)]
        k = f - lo
        img[c == v] = [round(a_[i] * (1 - k) + b_[i] * k) for i in range(3)]
    # vores de cingle
    vora = np.zeros(c.shape, bool)
    vora[1:, :] |= (np.abs(c[1:, :] - c[:-1, :]) >= 32)
    vora[:, 1:] |= (np.abs(c[:, 1:] - c[:, :-1]) >= 32)
    img[vora & (c > 0)] = (92, 101, 114)
    Image.fromarray(img[::-1]).save(os.path.join(dir_out, slug + ".png"), optimize=True)
    # màscara de cel·les jugables, en baixa resolució (2x2) per al control de mapa
    jug = (c > 0)
    l, b, r, t = mp["camera"]
    json.dump(dict(nom=mp["nom"], w=int(c.shape[1]), h=int(c.shape[0]), camera=[l, b, r, t],
                   jugable=_rle(jug), recursos=recursos),
              open(os.path.join(dir_out, slug + ".json"), "w"), separators=(",", ":"))


def _rle(mask):
    """Codifica una màscara booleana fila a fila (des de y=0) com a llista de llargades alternes."""
    flat = mask.reshape(-1)
    out, cur, n = [], False, 0
    for v in flat:
        if v == cur:
            n += 1
        else:
            out.append(n); cur = v; n = 1
    out.append(n)
    return out


# ---------------------------------------------------------------- bases
def lloc_townhall(punts):
    """On va el townhall: el punt que queda a ~7 cel·les de tots els minerals i gèisers."""
    cx = sum(p[0] for p in punts) / len(punts); cy = sum(p[1] for p in punts) / len(punts)
    P = np.array(punts, float)
    millor, sc = (cx, cy), 1e18
    for x in np.arange(cx - 10, cx + 10.01, .5):
        for y in np.arange(cy - 10, cy + 10.01, .5):
            d = np.hypot(P[:, 0] - x, P[:, 1] - y)
            s_ = ((d - 7.0) ** 2).sum()
            if s_ < sc:
                millor, sc = (x, y), s_
    return millor


def troba_bases(recursos):
    """Agrupa els recursos en bases: primer els minerals (enllaç curt, perquè dues línies veïnes no
    s'ajuntin) i després cada gèiser al grup de minerals més proper."""
    mins = [(x, y) for (x, y, k) in recursos if k == "m"]
    geis = [(x, y) for (x, y, k) in recursos if k == "g"]
    grups = []
    for p in mins:
        tocats = [g for g in grups if any((p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2 <= 5 ** 2 for q in g)]
        nou = [p]
        for g in tocats:
            nou += g; grups.remove(g)
        grups.append(nou)
    grups = [g for g in grups if len(g) >= 4]
    for p in geis:
        cand = [(min((p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2 for q in g), i) for i, g in enumerate(grups)]
        if cand and min(cand)[0] <= 12 ** 2:
            grups[min(cand)[1]].append(p)
    return grups


def distancies_a_peu(mapa, x, y, bases):
    """Distància caminant (BFS en 8 direccions sobre el relleu) des de (x,y) fins a cada base.
    Es pot passar entre cel·les veïnes si el nivell canvia poc (les rampes ho fan de 8 en 8, els cingles de 64)."""
    euclid = [math.hypot(b["x"] - x, b["y"] - y) for b in bases]
    if not mapa:
        return euclid
    c = mapa["cliff"].astype(np.int32)
    H, W = c.shape
    dist = np.full((H, W), -1, np.int32)
    from collections import deque
    sx, sy = int(x), int(y)
    dist[sy, sx] = 0
    q = deque([(sx, sy)])
    while q:
        cx, cy = q.popleft()
        dc, nd = c[cy, cx], dist[cy, cx] + 1
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)):
            nx, ny = cx + dx, cy + dy
            if 0 <= nx < W and 0 <= ny < H and dist[ny, nx] < 0 and c[ny, nx] > 0 and abs(int(c[ny, nx]) - dc) < 32:
                dist[ny, nx] = nd
                q.append((nx, ny))
    out = []
    for i, b in enumerate(bases):
        bx, by = int(b["x"]), int(b["y"])
        fin = dist[max(0, by - 1):by + 2, max(0, bx - 1):bx + 2]
        fin = fin[fin >= 0]
        out.append(float(fin.min()) if fin.size else 1e6 + euclid[i])
    return out


# ---------------------------------------------------------------- partida
class Unitat:
    __slots__ = ("id", "p", "tipus", "t0", "t1", "fet", "x", "y", "mort_x", "mort_y", "assassi",
                 "pos", "tipus_hist", "mostres", "creador")

def analitza(path, mapes):
    a = mpyq.MPQArchive(path)
    cap = proto(_build_ultim()).decode_replay_header(a.header["user_data_header"]["content"])
    build = cap["m_version"]["m_baseBuild"]
    P = proto(build)
    det = P.decode_replay_details(a.read_file("replay.details"))
    jug = [x for x in det["m_playerList"] if x["m_observe"] == 0]
    if len(jug) != 2:
        return None
    ini = P.decode_replay_initdata(a.read_file("replay.initData"))
    ls = ini["m_syncLobbyState"]
    gd = ls["m_gameDescription"]
    durada = cap["m_elapsedGameLoops"] / LOOPS
    if durada < 60:
        return None

    mapa = mapes.get(det["m_cacheHandles"][-1])

    jugadors = []
    for i, x in enumerate(det["m_playerList"]):
        if x["m_observe"]:
            continue
        toon = f'{x["m_toon"]["m_region"]}-S2-{x["m_toon"]["m_realm"]}-{x["m_toon"]["m_id"]}'
        uid = None
        for s in ls["m_lobbyState"]["m_slots"]:
            if s["m_toonHandle"].decode() == toon:
                uid = s["m_userId"]
        mmr = None
        if uid is not None and uid < len(ls["m_userInitialData"]):
            mmr = ls["m_userInitialData"][uid].get("m_scaledRating")
        jugadors.append(dict(pid=i + 1, uid=uid, nom=neteja_nom(x["m_name"]), raça=x["m_race"].decode(),
                             resultat={1: "V", 2: "D"}.get(x["m_result"], "?"), toon=toon,
                             mmr=mmr if mmr and mmr > 0 else None, jo=(toon == JO_TOON)))
    pids = [j["pid"] for j in jugadors]

    # ---- tracker events
    unitats = {}          # (index, recycle) -> Unitat
    per_index = {}        # index -> Unitat viva amb aquest index
    recursos = []
    stats = {p: [] for p in pids}
    millores = {p: [] for p in pids}
    for e in P.decode_replay_tracker_events(a.read_file("replay.tracker.events")):
        ev = e["_event"].rsplit(".", 1)[-1]
        t = e["_gameloop"] / LOOPS
        if ev in ("SUnitBornEvent", "SUnitInitEvent"):
            tipus = e["m_unitTypeName"].decode()
            if e["_gameloop"] == 0 and ("Mineral" in tipus or "Geyser" in tipus or "Vespene" in tipus):
                recursos.append((e["m_x"], e["m_y"], "g" if ("Geyser" in tipus or "Vespene" in tipus) else "m"))
                continue
            p = e["m_controlPlayerId"]
            if p not in pids:
                continue
            u = Unitat()
            u.id = (e["m_unitTagIndex"], e["m_unitTagRecycle"]); u.p = p; u.tipus = tipus
            u.t0 = t; u.t1 = None; u.fet = t if ev == "SUnitBornEvent" else None
            u.x, u.y = e["m_x"], e["m_y"]; u.mort_x = u.mort_y = None; u.assassi = None
            u.pos = [(round(t, 1), e["m_x"], e["m_y"])]; u.tipus_hist = [(t, tipus)]; u.mostres = []
            u.creador = (e["m_creatorUnitTagIndex"], e["m_creatorUnitTagRecycle"]) if e.get("m_creatorUnitTagIndex") is not None else None
            unitats[u.id] = u; per_index[u.id[0]] = u
            # un treballador surt al costat de l'edifici que l'ha fet: així sabem on és un CC que ha volat
            if tipus in ("SCV", "Probe") and e.get("m_creatorUnitTagIndex") is not None:
                cr = unitats.get((e["m_creatorUnitTagIndex"], e["m_creatorUnitTagRecycle"]))
                if cr:
                    cr.mostres.append((t, e["m_x"], e["m_y"]))
        elif ev == "SUnitDoneEvent":
            u = unitats.get((e["m_unitTagIndex"], e["m_unitTagRecycle"]))
            if u:
                u.fet = t
        elif ev == "SUnitTypeChangeEvent":
            u = unitats.get((e["m_unitTagIndex"], e["m_unitTagRecycle"]))
            if u:
                tn = e["m_unitTypeName"].decode()
                u.tipus = tn; u.tipus_hist.append((t, tn))
        elif ev == "SUnitDiedEvent":
            u = unitats.get((e["m_unitTagIndex"], e["m_unitTagRecycle"]))
            if u:
                u.t1 = t; u.mort_x, u.mort_y = e["m_x"], e["m_y"]; u.assassi = e["m_killerPlayerId"]
                u.pos.append((round(t, 1), e["m_x"], e["m_y"]))
        elif ev == "SUnitPositionsEvent":
            idx = e["m_firstUnitIndex"]; it = e["m_items"]
            for k in range(0, len(it), 3):
                idx += it[k]
                u = per_index.get(idx)
                if u and u.t1 is None:
                    u.pos.append((round(t, 1), it[k + 1], it[k + 2]))
        elif ev == "SPlayerStatsEvent":
            p = e["m_playerId"]
            if p in stats:
                s = e["m_stats"]
                stats[p].append(dict(
                    t=round(t),
                    min=s["m_scoreValueMineralsCollectionRate"], gas=s["m_scoreValueVespeneCollectionRate"],
                    treb=s["m_scoreValueWorkersActiveCount"],
                    exer=s["m_scoreValueMineralsUsedCurrentArmy"] + s["m_scoreValueVespeneUsedCurrentArmy"],
                    sup=round(s["m_scoreValueFoodUsed"] / 4096), supmax=round(s["m_scoreValueFoodMade"] / 4096),
                    banc=s["m_scoreValueMineralsCurrent"] + s["m_scoreValueVespeneCurrent"],
                    perdut=s["m_scoreValueMineralsLostArmy"] + s["m_scoreValueVespeneLostArmy"],
                    mort=s["m_scoreValueMineralsKilledArmy"] + s["m_scoreValueVespeneKilledArmy"],
                ))
        elif ev == "SUpgradeEvent":
            p = e["m_playerId"]
            nm = e["m_upgradeTypeName"].decode()
            if p in millores and e["_gameloop"] > 0 and not nm.startswith(("Spray", "Reward", "Game")):
                millores[p].append((round(t), nm))

    us = list(unitats.values())

    # ---- APM i EPM, per minut real
    # APM: ordres, seleccions i grups de control (sense càmera).
    # EPM (accions efectives): només ordres i assignacions de grup de control; no compten les seleccions,
    # recuperar un grup ni repetir la mateixa ordre en menys de mig segon (l'"spam" de clics).
    nmin = int(durada // 60) + 1
    accions = {p: [0] * nmin for p in pids}
    efectives = {p: [0] * nmin for p in pids}
    darrera = {}  # p -> (clau de l'ordre, gameloop)
    de_usuari = {j["uid"]: j["pid"] for j in jugadors if j["uid"] is not None}
    # càmera: on mira cada jugador (centre de la pantalla, en cel·les); només els moviments de més d'una cel·la
    camera = {p: [] for p in pids}
    for e in P.decode_replay_game_events(a.read_file("replay.game.events")):
        ev = e["_event"]
        if ev.endswith("CameraUpdateEvent"):
            p, tg = de_usuari.get(e["_userid"]["m_userId"]), e.get("m_target")
            if p is not None and tg:
                x, y, c = round(tg["x"] / 256, 1), round(tg["y"] / 256, 1), camera[p]
                if not c or abs(c[-1][1] - x) + abs(c[-1][2] - y) > 1:
                    c.append([round(e["_gameloop"] / LOOPS, 1), x, y])
            continue
        if not (ev.endswith(("CmdEvent", "SelectionDeltaEvent", "ControlGroupUpdateEvent",
                             "CmdUpdateTargetPointEvent", "CmdUpdateTargetUnitEvent"))):
            continue
        p = de_usuari.get(e["_userid"]["m_userId"])
        if p is None:
            continue
        m = int(e["_gameloop"] / LOOPS // 60)
        if m >= nmin:
            continue
        accions[p][m] += 1
        if ev.endswith("SelectionDeltaEvent"):
            continue
        if ev.endswith("ControlGroupUpdateEvent"):
            if e.get("m_controlGroupUpdate") in (0, 1, 3):  # assignar, afegir, assignar i treure (no recuperar)
                efectives[p][m] += 1
            continue
        abil = e.get("m_abil") or {}
        clau = (ev.rsplit(".", 1)[-1], abil.get("m_abilLink"), abil.get("m_abilCmdIndex"))
        ant = darrera.get(p)
        if not (ant and ant[0] == clau and e["_gameloop"] - ant[1] < LOOPS / 2):
            efectives[p][m] += 1
        darrera[p] = (clau, e["_gameloop"])
    for j in jugadors:
        j["apm"] = round(sum(accions[j["pid"]]) / (durada / 60)) if durada else None
        j["epm"] = round(sum(efectives[j["pid"]]) / (durada / 60)) if durada else None
    apm = {p: v for p, v in accions.items()}
    epm = {p: v for p, v in efectives.items()}

    # ---- bases
    grups = troba_bases(recursos)
    bases = []
    for g in grups:
        cx, cy = lloc_townhall(g)
        bases.append(dict(x=round(cx, 1), y=round(cy, 1), ocupacio=[]))
    townhalls = [u for u in us if C.get(u.tipus_hist[0][1], (0, 0, 0, ""))[3] == "t"]
    def base_de(x, y):
        # base més propera (el townhall ha de ser a menys de 8 cel·les del lloc previst)
        millor, dmin = None, 8 ** 2
        for i, b in enumerate(bases):
            d = (b["x"] - x) ** 2 + (b["y"] - y) ** 2
            if d < dmin:
                millor, dmin = i, d
        return millor

    for u in townhalls:
        fi = u.t1
        # trams entre enlairaments i aterratges (només els CC volen)
        vols, enlairat = [], None
        for tt, tn in u.tipus_hist[1:]:
            if tn.endswith("Flying") and enlairat is None:
                enlairat = tt
            elif not tn.endswith("Flying") and enlairat is not None:
                vols.append((enlairat, tt)); enlairat = None
        trams = [(u.t0, u.fet, vols[0][0] if vols else (enlairat if enlairat is not None else fi), base_de(u.x, u.y))]
        for n, (_, aterra) in enumerate(vols):
            seguent = vols[n + 1][0] if n + 1 < len(vols) else (enlairat if enlairat is not None else fi)
            # on ha aterrat: el primer treballador que en surt després d'aterrar
            m = next((m for m in u.mostres if m[0] >= aterra and (seguent is None or m[0] < seguent)), None)
            trams.append((aterra, aterra, seguent, base_de(m[1], m[2]) if m else None))
        for n, (t0_, fet_, t1_, bi) in enumerate(trams):
            if bi is None:
                continue
            # un tram que acaba enlairant-se sense haver fet cap treballador és de pas, no una base
            surt_volant = t1_ is not None and t1_ != fi
            if surt_volant and fet_ is not None and not any(fet_ <= m[0] < t1_ for m in u.mostres):
                continue
            bases[bi]["ocupacio"].append(dict(p=u.p, t0=round(t0_), fet=round(fet_) if fet_ is not None else None,
                                              t1=round(t1_) if t1_ is not None else None,
                                              tipus=[nom(tn) for _, tn in u.tipus_hist][-1]))
    # main de cada jugador = base on tenia townhall al segon 0
    for j in jugadors:
        for i, b in enumerate(bases):
            if any(o["p"] == j["pid"] and o["t0"] == 0 for o in b["ocupacio"]):
                j["main"] = i
    # natural = base més propera a la main, caminant
    dist_terra = {}
    for j in jugadors:
        if "main" in j:
            th = next(u for u in townhalls if u.p == j["pid"] and u.t0 == 0)
            dist_terra[j["pid"]] = d = distancies_a_peu(mapa, th.x, th.y, bases)
            cand = sorted((d[i], i) for i in range(len(bases)) if i != j["main"])
            if cand:
                j["natural"] = cand[0][1]
    for i, b in enumerate(bases):
        b["nom"] = None
        for j in jugadors:
            # el nom és un codi que tradueix la web: "main", "nat" o el número de base
            if j.get("main") == i: b["nom"] = "main"; b["de"] = j["pid"]
            if j.get("natural") == i: b["nom"] = "nat"; b["de"] = j["pid"]
    # resta de bases: per número segons distància a la meva main
    jo = next((j for j in jugadors if j["jo"]), jugadors[0])
    if "main" in jo:
        m = bases[jo["main"]]
        d = dist_terra.get(jo["pid"]) or [0] * len(bases)
        resta = sorted([i for i, b in enumerate(bases) if not b["nom"]], key=lambda i: d[i])
        for n, i in enumerate(resta):
            bases[i]["nom"] = str(n + 3)

    # moments en què cada jugador té N bases (townhall acabat)
    # (comptem bases diferents: un CC fet a la main i que vola a la natural no és una base nova fins que aterra)
    for j in jugadors:
        fets = sorted(min(o["fet"] for o in b["ocupacio"] if o["p"] == j["pid"] and o["fet"] is not None)
                      for b in bases if any(o["p"] == j["pid"] and o["fet"] is not None for o in b["ocupacio"]))
        j["t_bases"] = fets[:6]

    # ---- batalles: agrupació de morts en espai i temps
    morts = []
    for u in us:
        if u.t1 is None:
            continue
        tip = u.tipus
        if tip not in C:
            continue
        mi, ga, su, cat = C[tip]
        # una estructura que no s'havia acabat val el que s'hi ha invertit (aproximem al 100%)
        morts.append(dict(t=u.t1, x=u.mort_x, y=u.mort_y, p=u.p, tipus=nom(tip), valor=mi + ga, cat=cat,
                          assassi=u.assassi))
    morts.sort(key=lambda m: m["t"])
    clusters = []
    for m in morts:
        if m["assassi"] in (None, 0) and m["cat"] in ("s", "t"):
            continue  # cancel·lacions i similars
        cand = None
        for c in reversed(clusters):
            if m["t"] - c["fi"] > 20:
                if m["t"] - c["fi"] > 60:
                    break
                continue
            if m["t"] - c["ini"] > 90:
                continue  # una lluita molt llarga la partim en trams
            d2 = (m["x"] - c["cx"]) ** 2 + (m["y"] - c["cy"]) ** 2
            if d2 < 20 ** 2:
                cand = c; break
        if cand is None:
            cand = dict(morts=[], ini=m["t"], fi=m["t"], cx=m["x"], cy=m["y"])
            clusters.append(cand)
        cand["morts"].append(m)
        cand["fi"] = m["t"]
        n = len(cand["morts"])
        cand["cx"] += (m["x"] - cand["cx"]) / n
        cand["cy"] += (m["y"] - cand["cy"]) / n

    def stat_a(p, t):
        ss = [s for s in stats[p] if s["t"] <= t]
        return ss[-1] if ss else (stats[p][0] if stats[p] else None)

    batalles = []
    for c in clusters:
        ms = c["morts"]
        total = sum(m["valor"] for m in ms)
        if total < 250 and len(ms) < 4:
            continue
        perd = {p: dict(valor=0, treb=0, estr=0, exer=0, unitats=defaultdict(int)) for p in pids}
        for m in ms:
            q = perd[m["p"]]
            q["valor"] += m["valor"]
            q["unitats"][m["tipus"]] += 1
            if m["cat"] == "w": q["treb"] += 1
            elif m["cat"] in ("s", "t"): q["estr"] += m["valor"]
            else: q["exer"] += m["valor"]
        t0, t1 = ms[0]["t"], ms[-1]["t"]
        r = max(math.hypot(m["x"] - c["cx"], m["y"] - c["cy"]) for m in ms)
        a_, b_ = pids
        va, vb = perd[a_]["valor"], perd[b_]["valor"]
        guanya = a_ if va < vb else b_
        perdedor = b_ if guanya == a_ else a_
        vp, vg = perd[perdedor], perd[guanya]
        if any(m["cat"] == "t" and m["p"] == perdedor for m in ms):
            tipus = "base"
        elif vp["estr"] >= 0.5 * vp["valor"] and vp["estr"] >= 300:
            tipus = "estructures"
        elif vp["treb"] >= 3 and vp["exer"] < 0.4 * vp["valor"] and vg["valor"] < 0.5 * vp["valor"]:
            tipus = "treballadors"
        elif total >= 1500:
            tipus = "batalla"
        else:
            tipus = "escaramussa"
        # base més propera (índex a bases)
        bnom = None
        if bases:
            bi = min(range(len(bases)), key=lambda i: (bases[i]["x"] - c["cx"]) ** 2 + (bases[i]["y"] - c["cy"]) ** 2)
            if math.hypot(bases[bi]["x"] - c["cx"], bases[bi]["y"] - c["cy"]) < 22:
                bnom = bi
        exercit_abans = {p: (stat_a(p, t0 - 1) or {}).get("exer", 0) for p in pids}
        batalles.append(dict(
            t0=round(t0), t1=round(t1), x=round(c["cx"], 1), y=round(c["cy"], 1), r=round(max(r, 4), 1),
            tipus=tipus, total=total, guanya=guanya if va != vb else None, lloc=bnom,
            perdues={p: dict(valor=v["valor"], treb=v["treb"], estr=v["estr"], exer=v["exer"],
                             unitats=dict(sorted(v["unitats"].items(), key=lambda kv: -kv[1])))
                     for p, v in perd.items()},
            exercit_abans=exercit_abans,
            morts=[[round(m["t"], 1), m["x"], m["y"], m["p"]] for m in ms],
        ))

    # moment clau: batalla amb més diferència de pèrdues
    for b in batalles:
        a_, b_ = pids
        b["diferencia"] = abs(b["perdues"][a_]["valor"] - b["perdues"][b_]["valor"])
    if batalles:
        max(batalles, key=lambda b: b["diferencia"])["clau"] = True

    # ---- què fa cada edifici: [comença, acaba, unitat], a partir del creador de cada unitat que neix
    produccio = defaultdict(list)
    for u in us:
        tip0 = u.tipus_hist[0][1]
        if u.creador and tip0 in TEMPS_FER and u.t0 > 0:
            produccio[u.creador].append([round(max(0, u.t0 - TEMPS_FER[tip0]), 1), round(u.t0, 1), nom(tip0)])

    # ---- entitats per al control de mapa (al client): estructures i trajectòries d'unitats
    # [jugador, tipus, comença, mor, x, y, acabada, produccions]
    estructures = []
    exercit = []
    for u in us:
        tip0 = u.tipus_hist[0][1]
        info = C.get(u.tipus) or C.get(tip0)
        if not info:
            if tip0.startswith("CreepTumor"):
                estructures.append([u.p, "tumor", round(u.t0), round(u.t1) if u.t1 is not None else None, u.x, u.y])
            continue
        cat = info[3]
        if cat in ("s", "t"):
            k = "th" if cat == "t" else ("def" if nom(u.tipus) in DEFENSA else "s")
            estructures.append([u.p, k, round(u.t0), round(u.t1) if u.t1 is not None else None, u.x, u.y,
                                round(u.fet, 1) if u.fet is not None else None, sorted(produccio.get(u.id, []))])
        elif cat == "a" and u.tipus not in ("Overlord", "Overseer", "OverseerSiegeMode", "Observer",
                                             "ObserverSiegeMode", "OverlordTransport"):
            exercit.append([u.p, round(info[0] + info[1]), round(u.t1) if u.t1 is not None else None, u.pos])

    # ---- ordre de construcció (primeres 40 coses, sense treballadors)
    ordre = {}
    for p in pids:
        coses = []
        for u in us:
            if u.p != p or u.t0 < 1:
                continue
            tip0 = u.tipus_hist[0][1]
            if tip0 in C and C[tip0][3] != "w":
                coses.append((round(u.t0), nom(tip0)))
        coses += [(t, "⬆ " + n) for t, n in millores[p]]
        coses.sort()
        # agrupa repeticions consecutives
        out = []
        for t, n in coses:
            if out and out[-1][1] == n and t - out[-1][0] < 15:
                out[-1][2] += 1
            else:
                out.append([t, n, 1])
        ordre[p] = out[:60]

    control = control_mapa(mapa, estructures, exercit, pids, durada) if mapa else None

    utc = det["m_timeUTC"]
    ts = (utc - 116444735995904000) / 1e7
    rid = hashlib.sha1(open(path, "rb").read()).hexdigest()[:12]
    return dict(
        id=rid, fitxer=os.path.basename(path), build=build, data=round(ts),
        mapa=mapa["slug"] if mapa else None, mapa_nom=det["m_title"].decode(),
        durada=round(durada), jugadors=jugadors, bases=bases, batalles=batalles,
        stats=stats, apm=apm, epm=epm, control=control, estructures=estructures, exercit=exercit, ordre=ordre, camera=camera,
        competitiu=bool(gd["m_gameOptions"].get("m_competitive")),
        _recursos=[list(r) for r in recursos], _mapa=mapa,
    )


# ---------------------------------------------------------------- control de mapa
# Model d'influència: cada font suma w·exp(-d²/2σ²) (d en cel·les). Una cel·la jugable és d'un
# jugador si la seva influència passa LLINDAR i és DOMINI vegades la del rival.
# El mateix model és a web/partida.js (influencia()): si canvies res aquí, canvia-ho allà.
FONTS = {"th": (4.0, 12), "def": (2.0, 9), "s": (1.5, 8), "tumor": (1.0, 7)}
SIGMA_EXER, CADUCA_EXER = 8, 30.0
LLINDAR, DOMINI = 0.15, 1.5
RES = 2  # cel·les per píxel de la graella

def pes_exercit(valor, antiguitat):
    return min(valor / 150.0, 3.0) * math.exp(-antiguitat / CADUCA_EXER) if antiguitat <= 60 else 0.0

def control_mapa(mapa, estructures, exercit, pids, durada, pas=10):
    c = mapa["cliff"]
    H, W = c.shape
    gh, gw = (H + RES - 1) // RES, (W + RES - 1) // RES
    jug = np.zeros((gh * RES, gw * RES), bool); jug[:H, :W] = c > 0
    jug = jug.reshape(gh, RES, gw, RES).any(axis=(1, 3))
    n_jug = jug.sum()
    # FFT amb farciment per evitar que la influència doni la volta
    PH, PW = gh * 2, gw * 2
    nuclis = {}
    def nucli(sig):
        if sig not in nuclis:
            sg = sig / RES
            yy = np.minimum(np.arange(PH), PH - np.arange(PH))[:, None]
            xx = np.minimum(np.arange(PW), PW - np.arange(PW))[None, :]
            nuclis[sig] = np.fft.rfft2(np.exp(-(xx ** 2 + yy ** 2) / (2 * sg * sg)))
        return nuclis[sig]
    sigs = sorted(set(v[1] for v in FONTS.values()) | {SIGMA_EXER})
    sortida = {p: [] for p in pids}
    temps = list(range(0, int(durada) + 1, pas))
    for t in temps:
        inf = {}
        for p in pids:
            imp = {sg: np.zeros((PH, PW)) for sg in sigs}
            for (q, k, t0, t1, x, y, *_) in estructures:
                if q == p and t0 <= t and (t1 is None or t1 > t):
                    w, sg = FONTS[k]
                    imp[sg][min(int(y) // RES, gh - 1), min(int(x) // RES, gw - 1)] += w
            for (q, valor, t1, pos) in exercit:
                if q != p or pos[0][0] > t or (t1 is not None and t1 <= t):
                    continue
                darrer = None
                for mostra in pos:
                    if mostra[0] <= t: darrer = mostra
                    else: break
                w = pes_exercit(valor, t - darrer[0])
                if w > 0:
                    imp[SIGMA_EXER][min(int(darrer[2]) // RES, gh - 1), min(int(darrer[1]) // RES, gw - 1)] += w
            tot = np.zeros((PH, PW))
            for sg, im in imp.items():
                if im.any():
                    tot += np.fft.irfft2(np.fft.rfft2(im) * nucli(sg), s=(PH, PW))
            inf[p] = tot[:gh, :gw]
        a, b = pids
        A, B = inf[a], inf[b]
        sa = jug & (A > LLINDAR) & (A > DOMINI * B)
        sb = jug & (B > LLINDAR) & (B > DOMINI * A)
        sortida[a].append(round(100 * sa.sum() / n_jug, 1))
        sortida[b].append(round(100 * sb.sum() / n_jug, 1))
    return dict(pas=pas, pct=sortida)


def _build_ultim():
    return int(_LATEST.replace("protocol", ""))


def slugify(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


class Mapes:
    """Mapes .s2ma per hash, carregats quan calen. Si falta i es pot, el baixa del dipòsit de Blizzard
    (el nom del fitxer és el sha256 del contingut, així que el comprovem)."""
    def __init__(self, dir_mapes, baixa=False):
        self.dir, self.baixa, self.cache = dir_mapes, baixa, {}

    def get(self, handle):
        regio, h = handle[4:8].strip(b"\x00").decode(errors="replace").lower(), handle[8:].hex()
        if h in self.cache:
            return self.cache[h]
        f = os.path.join(self.dir, h + ".s2ma")
        if not os.path.exists(f) and self.baixa:
            self._baixa(regio, h, f)
        mp = None
        if os.path.exists(f):
            try:
                mp = llegeix_mapa(f)
                mp["slug"] = slugify(mp["nom"]) + "-" + h[:6]
            except Exception as ex:
                print("mapa", f, repr(ex), file=sys.stderr)
        self.cache[h] = mp
        return mp

    def _baixa(self, regio, h, f):
        import urllib.request
        for r in dict.fromkeys([regio, "eu", "us", "kr"]):
            if not re.fullmatch(r"[a-z]{2}", r):
                continue
            try:
                with urllib.request.urlopen(f"https://{r}-s2-depot.classic.blizzard.com/{h}.s2ma", timeout=30) as resp:
                    dades = resp.read(60_000_000)
            except Exception:
                continue
            if hashlib.sha256(dades).hexdigest() == h:
                open(f + ".tmp", "wb").write(dades); os.replace(f + ".tmp", f)
                return


TOON = re.compile(r"^[1-9]-S2-[1-9]-[0-9]{1,12}$")


def desa(r, dir_out):
    """Escriu la partida i, si cal, el mapa. Retorna l'entrada (sense "jo") per als índexs."""
    recursos = r.pop("_recursos")
    dm = os.path.join(dir_out, "data", "maps")
    if r["mapa"] and not os.path.exists(os.path.join(dm, r["mapa"] + ".json")):
        exporta_mapa(r.pop("_mapa"), recursos, dm, r["mapa"])
    r.pop("_mapa", None)
    escriu_json(os.path.join(dir_out, "data", "games", r["id"] + ".json"), r)
    return entrada(r)


def spending_quotient(stats):
    """SQ = 35·(0,00137·I − ln U) + 240: I = ingressos mitjans (minerals+gas/min), U = recursos mitjans sense gastar,
    sobre tota la partida (la fórmula habitual, per poder-la comparar amb altres webs).
    El mateix càlcul és a web/partida.js (sq): si en canvies res, canvia-ho allà."""
    ss = stats
    if len(ss) < 6:
        return None
    ing = sum(s["min"] + s["gas"] for s in ss) / len(ss)
    banc = max(1.0, sum(s["banc"] for s in ss) / len(ss))
    return round(35 * (0.00137 * ing - math.log(banc)) + 240)


def entrada(r):
    for j in r["jugadors"]:
        st = r["stats"].get(j["pid"]) or r["stats"].get(str(j["pid"])) or []
        j["sq"] = spending_quotient(st)
    return dict(
        id=r["id"], data=r["data"], mapa=r["mapa_nom"], slug=r["mapa"], durada=r["durada"],
        competitiu=r["competitiu"],
        jugadors=[{k: j.get(k) for k in ("pid", "toon", "nom", "raça", "resultat", "mmr", "t_bases", "apm", "epm", "sq")} for j in r["jugadors"]],
        batalles=len(r["batalles"]),
        control={str(m): {p: v[m * 6] for p, v in r["control"]["pct"].items()}
                 for m in (4, 6, 8, 10, 12) if r["control"] and m * 6 < len(next(iter(r["control"]["pct"].values())))}
                if r["control"] else None,
    )


def per_a(e, toon):
    """L'entrada vista des del jugador 'toon' (marca "jo")."""
    e = dict(e)
    e["jugadors"] = [dict(j, jo=(j["toon"] == toon)) for j in e["jugadors"]]
    return e


def escriu_json(f, dades):
    json.dump(dades, open(f + ".tmp", "w"), separators=(",", ":"), ensure_ascii=False)
    os.replace(f + ".tmp", f)


def prepara(dir_out):
    for d in ("games", "maps", "players"):
        os.makedirs(os.path.join(dir_out, "data", d), exist_ok=True)


def escriu_partides(dir_out):
    """data/games.json: totes les partides registrades a qualsevol perfil (de la més nova a la més vella), per a la
    llista del servidor que veuen els convidats. Les enviades des del navegador sense perfil no hi surten (no es llisten)."""
    totes = {}
    for f in glob.glob(os.path.join(dir_out, "data", "players", "*.json")):
        for e in json.load(open(f)):
            totes[e["id"]] = dict(e, jugadors=[{k: v for k, v in j.items() if k != "jo"} for j in e["jugadors"]])
    escriu_json(os.path.join(dir_out, "data", "games.json"), sorted(totes.values(), key=lambda x: -x["data"]))


def registre(dir_base=None):
    """Quines partides ha pujat cada jugador: {toon: [ids]} (a MySQL de l'allotjament PHP, via cdn/api.php)."""
    import magatzem
    return magatzem.perfils()


def main(dir_mapes, dir_out):
    """Regenera-ho tot a partir dels replays guardats a l'allotjament PHP: els meus (origen "meu") i els
    enviats que algú ha afegit al seu perfil. Cada replay es baixa a un directori temporal i s'esborra."""
    import magatzem, tempfile
    prepara(dir_out)
    mapes = Mapes(dir_mapes, baixa=True)
    reg = registre()
    de_qui = defaultdict(set)  # id -> toons que l'han pujat
    for toon, ids in reg.items():
        for i in ids:
            de_qui[i].add(toon)
    perfils = defaultdict(dict)  # toon -> id -> entrada
    with tempfile.TemporaryDirectory() as tmp:
        for rep in magatzem.replays():
            rid = rep["id"]
            llistadors = set(de_qui.get(rid, ()))
            if rep["origen"] == "meu":
                llistadors.add(JO_TOON)
            f = os.path.join(tmp, rid + ".SC2Replay")
            try:
                magatzem.baixa_replay(rid, f)
                r = analitza(f, mapes)
            except Exception as ex:
                print("ERROR", rid, repr(ex), file=sys.stderr); r = None
            finally:
                if os.path.exists(f):
                    os.remove(f)
            if not r:
                continue
            e = desa(r, dir_out)
            print("ok", r["id"], r["mapa_nom"], [j["nom"] for j in r["jugadors"]], file=sys.stderr)
            # una partida llistada (de qui l'ha pujat) surt a la pàgina de tots dos jugadors
            if any(j["toon"] in llistadors for j in e["jugadors"]):
                for j in e["jugadors"]:
                    if TOON.match(j["toon"] or ""):  # l'ordinador (0-S2-0-0) no té pàgina
                        perfils[j["toon"]][e["id"]] = per_a(e, j["toon"])
    for toon, es in perfils.items():
        escriu_json(os.path.join(dir_out, "data", "players", toon + ".json"), sorted(es.values(), key=lambda x: -x["data"]))
    escriu_partides(dir_out)
    print(sum(len(v) for v in perfils.values()), "entrades a", len(perfils), "perfils", file=sys.stderr)


def reindexa(dir_out):
    """Refà els índexs de perfil (data/players) a partir de les partides ja analitzades, sense tornar-les a analitzar."""
    reg = registre()
    perfils = defaultdict(list)
    for f in glob.glob(os.path.join(dir_out, "data", "games", "*.json")):
        r = json.load(open(f))
        e = entrada(r)
        llistada = any(j.get("jo") for j in r["jugadors"]) or any(r["id"] in ids for ids in reg.values())
        if llistada:
            # surt a la pàgina de tots dos jugadors
            for j in e["jugadors"]:
                if TOON.match(j["toon"] or ""):  # l'ordinador (0-S2-0-0) no té pàgina
                    perfils[j["toon"]].append(per_a(e, j["toon"]))
    for t, es in perfils.items():
        escriu_json(os.path.join(dir_out, "data", "players", t + ".json"), sorted(es, key=lambda x: -x["data"]))
    escriu_partides(dir_out)
    print({t: len(es) for t, es in perfils.items()}, file=sys.stderr)


def una(replay, dir_mapes, dir_out, toon=None):
    """Una partida enviada per algú. Escriu {"id", "perfil"} per stdout; codi 2 si no és 1v1.
    Si ve amb 'toon' i aquest jugador hi apareix, s'afegeix al seu perfil."""
    prepara(dir_out)
    rid = hashlib.sha1(open(replay, "rb").read()).hexdigest()[:12]
    fp = os.path.join(dir_out, "data", "games", rid + ".json")
    if os.path.exists(fp):
        e = entrada(json.load(open(fp)))
    else:
        r = analitza(replay, Mapes(dir_mapes, baixa=True))
        if not r:
            print("no-1v1", file=sys.stderr); sys.exit(2)
        for j in r["jugadors"]:
            j["jo"] = False  # aquí no hi ha "jo": la web deixa triar el punt de vista
        e = desa(r, dir_out)
    perfil = None
    if toon and TOON.match(toon) and any(j["toon"] == toon for j in e["jugadors"]):
        import magatzem
        magatzem.afegeix_a_perfil(toon, rid)
        for j in e["jugadors"]:  # també a la pàgina del rival
            if not TOON.match(j["toon"] or ""):
                continue
            fj = os.path.join(dir_out, "data", "players", j["toon"] + ".json")
            idx = [x for x in (json.load(open(fj)) if os.path.exists(fj) else []) if x["id"] != rid]
            idx.append(per_a(e, j["toon"]))
            escriu_json(fj, sorted(idx, key=lambda x: -x["data"]))
        escriu_partides(dir_out)
        perfil = toon
    print(json.dumps({"id": rid, "perfil": perfil}))


if __name__ == "__main__":
    if sys.argv[1] == "una":
        una(*sys.argv[2:6])
    elif sys.argv[1] == "reindexa":
        prepara(sys.argv[2]); reindexa(sys.argv[2])
    else:
        main(*sys.argv[1:3])
