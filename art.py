#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Il·lustracions originals de la web (SVG), inspirades en l'ambient de cada facció però sense
reproduir cap disseny del joc. Escriu web/img/{space,terran,zerg,protoss}.svg, les icones i la favicona.
"""
import math, os, random

DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web", "img")
W, H = 1600, 600


def svg(cos, defs="", w=W, h=H):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" preserveAspectRatio="xMidYMid slice">'
            f"<defs>{defs}</defs>{cos}</svg>")


def estrelles(r, n, y_max=H, colors=("#ffffff", "#cfe3ff", "#ffe9c9"), mida=(0.4, 1.6), opac=(0.3, 1.0)):
    out = []
    for _ in range(n):
        x, y = r.uniform(0, W), r.uniform(0, y_max)
        rad = r.uniform(*mida) ** 1.6
        out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{rad:.2f}" fill="{r.choice(colors)}" opacity="{r.uniform(*opac):.2f}"/>')
    # unes quantes de brillants amb creu
    for _ in range(n // 40):
        x, y, s = r.uniform(0, W), r.uniform(0, y_max * .8), r.uniform(5, 11)
        out.append(f'<g opacity=".85"><circle cx="{x:.1f}" cy="{y:.1f}" r="1.6" fill="#fff"/>'
                   f'<path d="M{x - s:.1f} {y:.1f}H{x + s:.1f}M{x:.1f} {y - s:.1f}V{y + s:.1f}" stroke="#fff" stroke-width=".6" opacity=".7"/></g>')
    return "".join(out)


def roca(r, cx, base, amp, alt, color, n=9):
    """Una roca de perfil irregular assentada a 'base'."""
    pts = []
    for i in range(n + 1):
        a = math.pi * i / n
        rr = amp * r.uniform(.75, 1.05)
        pts.append((cx - math.cos(a) * rr, base - math.sin(a) * alt * r.uniform(.7, 1.1)))
    d = "M" + " L".join(f"{x:.1f} {y:.1f}" for x, y in pts) + "Z"
    return f'<path d="{d}" fill="{color}"/>'


# ------------------------------------------------------------------ espai: planetes i naus per darrere
def espai():
    r = random.Random(7)
    defs = """
<linearGradient id="cel" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#05060d"/><stop offset=".6" stop-color="#0b1024"/><stop offset="1" stop-color="#140f2a"/></linearGradient>
<radialGradient id="neb1" cx=".5" cy=".5" r=".5"><stop offset="0" stop-color="#7a3fd1" stop-opacity=".55"/><stop offset="1" stop-color="#7a3fd1" stop-opacity="0"/></radialGradient>
<radialGradient id="neb2" cx=".5" cy=".5" r=".5"><stop offset="0" stop-color="#1fa6c9" stop-opacity=".45"/><stop offset="1" stop-color="#1fa6c9" stop-opacity="0"/></radialGradient>
<radialGradient id="neb3" cx=".5" cy=".5" r=".5"><stop offset="0" stop-color="#d9562b" stop-opacity=".35"/><stop offset="1" stop-color="#d9562b" stop-opacity="0"/></radialGradient>
<radialGradient id="planeta" cx=".35" cy=".3" r=".8"><stop offset="0" stop-color="#e9b26b"/><stop offset=".45" stop-color="#b8673a"/><stop offset=".8" stop-color="#4a2033"/><stop offset="1" stop-color="#1a0c1c"/></radialGradient>
<radialGradient id="lluna" cx=".3" cy=".3" r=".9"><stop offset="0" stop-color="#b9d2e6"/><stop offset=".6" stop-color="#4d6680"/><stop offset="1" stop-color="#121a2a"/></radialGradient>
<radialGradient id="planeta2" cx=".4" cy=".35" r=".8"><stop offset="0" stop-color="#5fd0c0"/><stop offset=".6" stop-color="#1d5d73"/><stop offset="1" stop-color="#071624"/></radialGradient>
<linearGradient id="anell" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#f3d7a8" stop-opacity="0"/><stop offset=".3" stop-color="#f3d7a8" stop-opacity=".8"/><stop offset=".7" stop-color="#c98a5a" stop-opacity=".7"/><stop offset="1" stop-color="#c98a5a" stop-opacity="0"/></linearGradient>
<clipPath id="davant-planeta"><rect x="0" y="388" width="1600" height="300"/></clipPath>
<radialGradient id="flama-t" cx=".5" cy=".5" r=".5"><stop offset="0" stop-color="#fff6d5"/><stop offset=".35" stop-color="#ffb347"/><stop offset=".7" stop-color="#ff5a1f" stop-opacity=".6"/><stop offset="1" stop-color="#ff5a1f" stop-opacity="0"/></radialGradient>
<radialGradient id="flama-p" cx=".5" cy=".5" r=".5"><stop offset="0" stop-color="#eaffff"/><stop offset=".35" stop-color="#6fe6ff"/><stop offset=".75" stop-color="#2a7dff" stop-opacity=".5"/><stop offset="1" stop-color="#2a7dff" stop-opacity="0"/></radialGradient>
<radialGradient id="flama-z" cx=".5" cy=".5" r=".5"><stop offset="0" stop-color="#f6ffd9"/><stop offset=".35" stop-color="#b6f04a"/><stop offset=".75" stop-color="#5bb02a" stop-opacity=".5"/><stop offset="1" stop-color="#5bb02a" stop-opacity="0"/></radialGradient>
<linearGradient id="casc-t" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#8a96a3"/><stop offset=".5" stop-color="#4b545e"/><stop offset="1" stop-color="#23292f"/></linearGradient>
<linearGradient id="casc-p" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#ffe7a6"/><stop offset=".45" stop-color="#c99a3c"/><stop offset="1" stop-color="#5a4016"/></linearGradient>
<linearGradient id="casc-z" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#8a4f7d"/><stop offset=".55" stop-color="#4b2340"/><stop offset="1" stop-color="#1f0d1c"/></linearGradient>
<filter id="borr" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="18"/></filter>
<filter id="brill" x="-100%" y="-100%" width="300%" height="300%"><feGaussianBlur stdDeviation="6"/></filter>
"""
    cos = ['<rect width="1600" height="600" fill="url(#cel)"/>',
           '<ellipse cx="380" cy="160" rx="420" ry="170" fill="url(#neb1)"/>',
           '<ellipse cx="620" cy="260" rx="300" ry="130" fill="url(#neb2)"/>',
           '<ellipse cx="180" cy="420" rx="260" ry="120" fill="url(#neb3)"/>',
           estrelles(r, 420)]
    # planeta gran amb anell (l'anell passa per darrere i per davant)
    cx, cy, R = 1250, 330, 210
    cos.append(f'<g transform="rotate(-14 {cx} {cy})"><ellipse cx="{cx}" cy="{cy}" rx="{R * 1.75}" ry="{R * .32}" fill="none" stroke="url(#anell)" stroke-width="16" opacity=".55"/></g>')
    cos.append(f'<circle cx="{cx}" cy="{cy}" r="{R}" fill="url(#planeta)"/>')
    for i in range(7):  # bandes atmosfèriques
        yy = cy - R + 50 + i * 52
        cos.append(f'<ellipse cx="{cx}" cy="{yy}" rx="{R * .97}" ry="9" fill="#fff" opacity="{.04 + .02 * (i % 3)}" transform="rotate(-14 {cx} {cy})"/>')
    cos.append(f'<g transform="rotate(-14 {cx} {cy})" clip-path="url(#davant-planeta)"><ellipse cx="{cx}" cy="{cy}" rx="{R * 1.75}" ry="{R * .32}" fill="none" stroke="url(#anell)" stroke-width="16"/></g>')
    cos.append(f'<circle cx="{cx}" cy="{cy}" r="{R}" fill="none" stroke="#ffcf8a" stroke-opacity=".25" stroke-width="3"/>')
    cos.append('<circle cx="960" cy="120" r="46" fill="url(#lluna)"/>')
    cos.append('<circle cx="120" cy="90" r="26" fill="url(#planeta2)"/>')

    # nau "industrial" (inspiració terran): casc quadrat, dos motors rodons
    def nau_t(x, y, s):
        g = [f'<g transform="translate({x} {y}) scale({s})">',
             '<ellipse cx="-38" cy="40" rx="46" ry="46" fill="url(#flama-t)" filter="url(#brill)"/>',
             '<ellipse cx="38" cy="40" rx="46" ry="46" fill="url(#flama-t)" filter="url(#brill)"/>',
             '<path d="M-90 -10 L-70 -40 L70 -40 L90 -10 L96 50 L60 70 L-60 70 L-96 50Z" fill="url(#casc-t)" stroke="#11161b" stroke-width="3"/>',
             '<path d="M-130 20 L-92 6 L-92 40 L-140 44Z M130 20 L92 6 L92 40 L140 44Z" fill="#3b434b" stroke="#11161b" stroke-width="3"/>',
             '<rect x="-60" y="-34" width="120" height="10" fill="#ffcc33" opacity=".85"/>',
             '<path d="M-60 -34 l10 10 M-40 -34 l10 10 M-20 -34 l10 10 M0 -34 l10 10 M20 -34 l10 10 M40 -34 l10 10" stroke="#222" stroke-width="5"/>',
             '<circle cx="-38" cy="40" r="22" fill="#1b2026" stroke="#77818b" stroke-width="4"/><circle cx="38" cy="40" r="22" fill="#1b2026" stroke="#77818b" stroke-width="4"/>',
             '<circle cx="-38" cy="40" r="13" fill="#fff1c2"/><circle cx="38" cy="40" r="13" fill="#fff1c2"/>',
             '<path d="M-70 0 H70 M-80 20 H-62 M62 20 H80" stroke="#1c2228" stroke-width="2"/>',
             '<circle cx="-136" cy="40" r="3" fill="#ff4b3a"/><circle cx="136" cy="40" r="3" fill="#56ff7a"/>',
             '</g>']
        return "".join(g)

    # nau "elegant" (inspiració protoss): ala en mitja lluna daurada i motors en escletxa blava
    def nau_p(x, y, s):
        return (f'<g transform="translate({x} {y}) scale({s})">'
                '<ellipse cx="0" cy="38" rx="130" ry="26" fill="url(#flama-p)" filter="url(#brill)"/>'
                '<path d="M-170 10 Q-90 -60 0 -52 Q90 -60 170 10 Q120 0 70 26 L0 40 L-70 26 Q-120 0 -170 10Z" fill="url(#casc-p)" stroke="#3a2a0e" stroke-width="2"/>'
                '<path d="M-40 -46 Q0 -90 40 -46 L22 30 L-22 30Z" fill="#d8b25a" stroke="#3a2a0e" stroke-width="2"/>'
                '<path d="M-110 18 Q-60 30 -22 34 M110 18 Q60 30 22 34" stroke="#7ff0ff" stroke-width="5" stroke-linecap="round"/>'
                '<path d="M-110 18 Q-60 30 -22 34 M110 18 Q60 30 22 34" stroke="#eaffff" stroke-width="2" stroke-linecap="round"/>'
                '<path d="M-14 -40 L0 -66 L14 -40 L0 -20Z" fill="#7ff0ff" opacity=".9"/>'
                '<path d="M-150 8 Q-90 -40 -40 -44 M150 8 Q90 -40 40 -44" stroke="#fff3c4" stroke-width="1.5" fill="none" opacity=".6"/>'
                '</g>')

    # nau "orgànica" (inspiració zerg): closca segmentada, espines i sacs que brillen
    def nau_z(x, y, s):
        seg = "".join(f'<path d="M{-70 + i * 4} {-30 + i * 16} Q0 {-52 + i * 16} {70 - i * 4} {-30 + i * 16}" stroke="#2a1026" stroke-width="3" fill="none"/>' for i in range(4))
        return (f'<g transform="translate({x} {y}) scale({s})">'
                '<ellipse cx="-30" cy="58" rx="34" ry="30" fill="url(#flama-z)" filter="url(#brill)"/>'
                '<ellipse cx="30" cy="58" rx="34" ry="30" fill="url(#flama-z)" filter="url(#brill)"/>'
                '<path d="M-80 -20 Q-90 -70 -40 -78 Q0 -95 40 -78 Q90 -70 80 -20 Q78 40 30 62 L-30 62 Q-78 40 -80 -20Z" fill="url(#casc-z)" stroke="#170814" stroke-width="3"/>'
                + seg +
                '<path d="M-78 -30 L-128 -70 L-84 -8Z M78 -30 L128 -70 L84 -8Z M-40 -76 L-58 -120 L-22 -84Z M40 -76 L58 -120 L22 -84Z" fill="#5c2b4f" stroke="#170814" stroke-width="2"/>'
                '<ellipse cx="-30" cy="54" rx="16" ry="12" fill="#c8f56a"/><ellipse cx="30" cy="54" rx="16" ry="12" fill="#c8f56a"/>'
                '<circle cx="-56" cy="10" r="6" fill="#b6f04a" opacity=".7"/><circle cx="56" cy="10" r="6" fill="#b6f04a" opacity=".7"/>'
                '</g>')

    cos.append('<g opacity=".95">' + nau_p(560, 400, .55) + "</g>")
    cos.append(nau_z(330, 470, .62))
    cos.append(nau_t(760, 500, .8))
    return svg("".join(cos), defs)


# ------------------------------------------------------------------ terran: indústria, canons i gas verd
def terran():
    r = random.Random(3)
    defs = """
<linearGradient id="cel" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#0d1116"/><stop offset=".55" stop-color="#3a2a22"/><stop offset=".8" stop-color="#9a4b22"/><stop offset="1" stop-color="#e0882f"/></linearGradient>
<linearGradient id="terra" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#2a2622"/><stop offset="1" stop-color="#0e0d0c"/></linearGradient>
<linearGradient id="metall" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#2b3138"/><stop offset=".5" stop-color="#5b6570"/><stop offset="1" stop-color="#22272d"/></linearGradient>
<linearGradient id="barril" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#1d4a24"/><stop offset=".35" stop-color="#3f9a3c"/><stop offset=".6" stop-color="#2c6e2c"/><stop offset="1" stop-color="#112a14"/></linearGradient>
<radialGradient id="gas" cx=".5" cy=".5" r=".5"><stop offset="0" stop-color="#9dff6a" stop-opacity=".8"/><stop offset="1" stop-color="#4bd13a" stop-opacity="0"/></radialGradient>
<radialGradient id="sol" cx=".5" cy=".5" r=".5"><stop offset="0" stop-color="#ffd27a"/><stop offset=".4" stop-color="#ff8a3a" stop-opacity=".6"/><stop offset="1" stop-color="#ff8a3a" stop-opacity="0"/></radialGradient>
<linearGradient id="feix" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fff2c0" stop-opacity=".35"/><stop offset="1" stop-color="#fff2c0" stop-opacity="0"/></linearGradient>
<pattern id="perill" width="24" height="24" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width="12" height="24" fill="#e3b23c"/><rect x="12" width="12" height="24" fill="#16181a"/></pattern>
<filter id="fum" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="14"/></filter>
<filter id="brill" x="-100%" y="-100%" width="300%" height="300%"><feGaussianBlur stdDeviation="8"/></filter>
"""
    c = ['<rect width="1600" height="600" fill="url(#cel)"/>', estrelles(r, 120, y_max=220, opac=(.2, .7)),
         '<circle cx="1180" cy="420" r="260" fill="url(#sol)"/>']
    # serralada llunyana
    pts = [(0, 430)] + [(x, 430 - r.uniform(20, 110)) for x in range(0, 1700, 80)] + [(1600, 430), (1600, 600), (0, 600)]
    c.append('<path d="M' + " L".join(f"{x} {y:.0f}" for x, y in pts) + 'Z" fill="#2b211d" opacity=".9"/>')
    # fàbrica amb xemeneies i fum
    c.append('<g fill="#15181c">'
             '<rect x="980" y="300" width="300" height="160"/><path d="M980 300 L1030 260 L1080 300 L1130 260 L1180 300 L1230 260 L1280 300Z"/>'
             '<rect x="1010" y="170" width="26" height="140"/><rect x="1060" y="200" width="22" height="110"/><rect x="1300" y="240" width="120" height="220"/>'
             '<rect x="1330" y="120" width="14" height="130"/><path d="M1325 120 h24 v-6 h-24z"/></g>')
    for i, (x, y) in enumerate([(1023, 165), (1071, 195)]):
        for k in range(5):
            c.append(f'<circle cx="{x - k * 34 - r.uniform(0, 10):.0f}" cy="{y - k * 26:.0f}" r="{18 + k * 10}" fill="#6b625c" opacity="{.45 - k * .07:.2f}" filter="url(#fum)"/>')
    for k in range(18):  # finestres il·luminades
        x, y = 995 + (k % 9) * 31, 330 + (k // 9) * 40
        c.append(f'<rect x="{x}" y="{y}" width="14" height="9" fill="#ffc35a" opacity="{r.uniform(.4, .95):.2f}"/>')
    c.append('<circle cx="1337" cy="116" r="5" fill="#ff3b2f"/><circle cx="1337" cy="116" r="14" fill="#ff3b2f" opacity=".35" filter="url(#brill)"/>')
    # feixos de llum
    c.append('<path d="M1360 260 L1180 600 L1420 600Z" fill="url(#feix)"/><path d="M1040 300 L860 600 L1060 600Z" fill="url(#feix)" opacity=".6"/>')
    # canó: base amb erugues, torreta i canó llarg
    c.append('<g transform="translate(380 420)">'
             '<rect x="-130" y="40" width="260" height="46" rx="22" fill="#1b1f24" stroke="#3a424b" stroke-width="4"/>'
             + "".join(f'<circle cx="{-105 + i * 42}" cy="63" r="15" fill="#2c333b" stroke="#11151a" stroke-width="3"/>' for i in range(6)) +
             '<path d="M-110 40 L-90 -10 L95 -10 L115 40Z" fill="url(#metall)" stroke="#11151a" stroke-width="3"/>'
             '<rect x="-80" y="0" width="150" height="14" fill="url(#perill)" opacity=".9"/>'
             '<path d="M-60 -10 L-40 -60 L50 -60 L70 -10Z" fill="#3c454f" stroke="#11151a" stroke-width="3"/>'
             '<g transform="rotate(-16 40 -40)"><rect x="40" y="-52" width="300" height="20" fill="url(#metall)" stroke="#11151a" stroke-width="3"/>'
             '<rect x="320" y="-58" width="36" height="32" fill="#2b3138" stroke="#11151a" stroke-width="3"/>'
             '<rect x="100" y="-56" width="10" height="28" fill="#1a1f24"/><rect x="200" y="-56" width="10" height="28" fill="#1a1f24"/></g>'
             '<circle cx="-10" cy="-38" r="8" fill="#ffcc33"/></g>')
    # búnquer amb sacs
    c.append('<g transform="translate(720 450)"><path d="M-110 30 L-90 -40 L90 -40 L110 30Z" fill="#262b31" stroke="#0f1215" stroke-width="3"/>'
             '<rect x="-60" y="-20" width="120" height="14" fill="#090b0d"/><rect x="-56" y="-18" width="112" height="4" fill="#ffb347" opacity=".6"/>'
             + "".join(f'<ellipse cx="{-120 + i * 30}" cy="{36 + (i % 2) * 4}" rx="18" ry="11" fill="#6d5d45" stroke="#2c241a" stroke-width="2"/>' for i in range(9)) +
             '</g>')
    # terra
    c.append('<path d="M0 470 Q400 440 800 470 T1600 460 V600 H0Z" fill="url(#terra)"/>')
    # barrils de gas verd
    def barril(x, y, s=1.0, tomb=0):
        return (f'<g transform="translate({x} {y}) rotate({tomb}) scale({s})">'
                '<ellipse cx="0" cy="-30" rx="60" ry="60" fill="url(#gas)" filter="url(#brill)"/>'
                '<rect x="-34" y="-80" width="68" height="96" rx="6" fill="url(#barril)" stroke="#0b1a0d" stroke-width="3"/>'
                '<rect x="-34" y="-60" width="68" height="8" fill="#0f2a12"/><rect x="-34" y="-12" width="68" height="8" fill="#0f2a12"/>'
                '<ellipse cx="0" cy="-80" rx="34" ry="8" fill="#5fd35a" stroke="#0b1a0d" stroke-width="3"/>'
                '<circle cx="12" cy="-81" r="4" fill="#d6ffb3"/>'
                '<path d="M-12 -44 L0 -30 L12 -44 Z" fill="#d6ff7a" opacity=".85"/></g>')
    c.append(barril(120, 560, 1.0) + barril(205, 566, 1.05) + barril(160, 480, .95) + barril(290, 572, .9, 78))
    c.append(barril(1470, 560, .9) + barril(1540, 566, .95))
    # roques del primer pla
    for x in (40, 560, 900, 1380):
        c.append(roca(r, x, 600, r.uniform(60, 110), r.uniform(40, 80), "#1a1714"))
    c.append('<rect x="0" y="592" width="1600" height="8" fill="url(#perill)"/>')
    return svg("".join(c), defs)


# ------------------------------------------------------------------ zerg: cova i massa enganxosa
def zerg():
    r = random.Random(11)
    defs = """
<radialGradient id="fons" cx=".55" cy=".55" r=".8"><stop offset="0" stop-color="#3a1534"/><stop offset=".6" stop-color="#1a0a17"/><stop offset="1" stop-color="#08040a"/></radialGradient>
<linearGradient id="roca" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#1f1219"/><stop offset="1" stop-color="#3a2230"/></linearGradient>
<linearGradient id="creep" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#9b3f8a"/><stop offset=".4" stop-color="#5e1f57"/><stop offset="1" stop-color="#22091f"/></linearGradient>
<radialGradient id="ou" cx=".4" cy=".35" r=".7"><stop offset="0" stop-color="#f2ff9a"/><stop offset=".45" stop-color="#a7d63a"/><stop offset="1" stop-color="#2d3a10"/></radialGradient>
<radialGradient id="aura" cx=".5" cy=".5" r=".5"><stop offset="0" stop-color="#c6ff5a" stop-opacity=".55"/><stop offset="1" stop-color="#c6ff5a" stop-opacity="0"/></radialGradient>
<radialGradient id="boira" cx=".5" cy=".5" r=".5"><stop offset="0" stop-color="#b453a0" stop-opacity=".35"/><stop offset="1" stop-color="#b453a0" stop-opacity="0"/></radialGradient>
<filter id="borr" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="20"/></filter>
<filter id="brill" x="-100%" y="-100%" width="300%" height="300%"><feGaussianBlur stdDeviation="9"/></filter>
"""
    c = ['<rect width="1600" height="600" fill="url(#fons)"/>',
         '<ellipse cx="900" cy="330" rx="600" ry="200" fill="url(#boira)"/>']
    # sostre de la cova amb estalactites
    sost = "M0 0 H1600 V120"
    x = 1600
    while x > 0:
        w = r.uniform(30, 90); h = r.uniform(30, 160)
        sost += f" L{x - w / 2:.0f} {120 + h:.0f} L{x - w:.0f} {110 + r.uniform(-15, 25):.0f}"
        x -= w
    sost += " L0 120Z"
    c.append(f'<path d="{sost}" fill="url(#roca)"/>')
    # massa enganxosa que regalima del sostre
    for _ in range(26):
        x = r.uniform(0, W); l = r.uniform(40, 230); w = r.uniform(6, 18)
        c.append(f'<path d="M{x - w:.0f} 100 Q{x - w * .3:.0f} {100 + l * .6:.0f} {x:.0f} {100 + l:.0f} Q{x + w * .3:.0f} {100 + l * .6:.0f} {x + w:.0f} 100Z" fill="#6d2463" opacity=".9"/>')
        c.append(f'<circle cx="{x:.0f}" cy="{100 + l + w * .8:.0f}" r="{w * .6:.1f}" fill="#8f3a82"/>')
        c.append(f'<path d="M{x - w * .4:.0f} 110 Q{x - w * .1:.0f} {100 + l * .5:.0f} {x:.0f} {100 + l * .9:.0f}" stroke="#d27bc4" stroke-width="2" fill="none" opacity=".5"/>')
    # parets laterals
    c.append('<path d="M0 0 V600 H160 Q120 450 190 320 Q140 200 220 80 L240 0Z" fill="#140a11"/>')
    c.append('<path d="M1600 0 V600 H1430 Q1490 430 1400 300 Q1470 180 1380 60 L1360 0Z" fill="#140a11"/>')
    # terra cobert de massa: capes ondulades i brillants
    for i, (y, col, op) in enumerate([(430, "#3d1236", 1), (470, "url(#creep)", 1), (520, "#2a0b25", 1)]):
        d = f"M0 {y}"
        for x in range(0, 1700, 100):
            d += f" Q{x + 50} {y - r.uniform(10, 40):.0f} {x + 100} {y + r.uniform(-8, 8):.0f}"
        d += " V600 H0Z"
        c.append(f'<path d="{d}" fill="{col}" opacity="{op}"/>')
    # venes que brillen
    for _ in range(14):
        x0 = r.uniform(100, 1500); y0 = r.uniform(470, 580)
        d = f"M{x0:.0f} {y0:.0f}"
        for _k in range(4):
            x0 += r.uniform(-60, 60); y0 += r.uniform(-14, 14)
            d += f" T{x0:.0f} {y0:.0f}"
        c.append(f'<path d="{d}" stroke="#c35bb1" stroke-width="{r.uniform(1.5, 3.5):.1f}" fill="none" opacity=".55"/>')
    # ous en grups
    def ou(x, y, s):
        return (f'<g transform="translate({x} {y}) scale({s})"><ellipse cx="0" cy="-20" rx="70" ry="60" fill="url(#aura)" filter="url(#brill)"/>'
                '<path d="M0 -70 C35 -70 44 -20 40 0 C36 18 -36 18 -40 0 C-44 -20 -35 -70 0 -70Z" fill="url(#ou)" stroke="#20280a" stroke-width="3"/>'
                '<path d="M-20 -48 C-10 -30 -12 -10 -22 4 M14 -56 C24 -36 22 -14 12 6" stroke="#4d5e17" stroke-width="3" fill="none"/>'
                '<path d="M-50 10 Q0 -6 50 10 Q0 24 -50 10Z" fill="#5e1f57"/></g>')
    for x, y, s in [(330, 520, 1.0), (400, 540, .8), (270, 548, .75), (1120, 515, .9), (1190, 545, .7), (1260, 530, .85), (760, 560, .6)]:
        c.append(ou(x, y, s))
    # espines i tentacles
    for x in (560, 640, 980, 1040, 1330):
        h = r.uniform(80, 170); b = r.uniform(12, 22)
        c.append(f'<path d="M{x - b:.0f} 520 Q{x - b * .2:.0f} {520 - h * .6:.0f} {x + r.uniform(-30, 30):.0f} {520 - h:.0f} Q{x + b * .4:.0f} {520 - h * .5:.0f} {x + b:.0f} 520Z" fill="#4a1a43" stroke="#1b0718" stroke-width="2"/>')
    c.append('<path d="M840 600 C820 520 900 500 880 440 C870 410 900 390 930 400" stroke="#6d2463" stroke-width="16" fill="none" stroke-linecap="round"/>')
    c.append('<path d="M840 600 C820 520 900 500 880 440 C870 410 900 390 930 400" stroke="#c35bb1" stroke-width="3" fill="none" stroke-linecap="round" opacity=".6"/>')
    # partícules (espores)
    for _ in range(80):
        c.append(f'<circle cx="{r.uniform(0, W):.0f}" cy="{r.uniform(150, 560):.0f}" r="{r.uniform(.6, 2.2):.1f}" fill="#d9ff8a" opacity="{r.uniform(.15, .6):.2f}"/>')
    return svg("".join(c), defs)


# ------------------------------------------------------------------ protoss: forat negre i cristalls
def protoss():
    r = random.Random(5)
    defs = """
<linearGradient id="cel" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#03050c"/><stop offset=".7" stop-color="#0a1430"/><stop offset="1" stop-color="#14254a"/></linearGradient>
<radialGradient id="disc" cx=".5" cy=".5" r=".5"><stop offset=".35" stop-color="#000" stop-opacity="0"/><stop offset=".42" stop-color="#fff4d6"/><stop offset=".55" stop-color="#ffb84d"/><stop offset=".75" stop-color="#ff6a2a" stop-opacity=".55"/><stop offset="1" stop-color="#7a2bff" stop-opacity="0"/></radialGradient>
<radialGradient id="halo" cx=".5" cy=".5" r=".5"><stop offset=".3" stop-color="#7fd8ff" stop-opacity=".35"/><stop offset="1" stop-color="#7fd8ff" stop-opacity="0"/></radialGradient>
<linearGradient id="cristall" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#e6fdff"/><stop offset=".4" stop-color="#5fd6ff"/><stop offset="1" stop-color="#1b4dbb"/></linearGradient>
<linearGradient id="cristall2" x1="1" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#a8f1ff"/><stop offset="1" stop-color="#123a8f"/></linearGradient>
<linearGradient id="or" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#5c4114"/><stop offset=".45" stop-color="#f1cf7a"/><stop offset=".6" stop-color="#c79a3e"/><stop offset="1" stop-color="#4a320d"/></linearGradient>
<linearGradient id="terra" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#1a2440"/><stop offset="1" stop-color="#070b16"/></linearGradient>
<radialGradient id="llum" cx=".5" cy=".5" r=".5"><stop offset="0" stop-color="#9ff0ff" stop-opacity=".7"/><stop offset="1" stop-color="#9ff0ff" stop-opacity="0"/></radialGradient>
<filter id="brill" x="-100%" y="-100%" width="300%" height="300%"><feGaussianBlur stdDeviation="10"/></filter>
<filter id="borr" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="4"/></filter>
"""
    c = ['<rect width="1600" height="600" fill="url(#cel)"/>', estrelles(r, 380, y_max=460)]
    # forat negre: halo, disc d'acreció inclinat, ombra i anell de fotons
    bx, by = 1150, 200
    c.append(f'<circle cx="{bx}" cy="{by}" r="260" fill="url(#halo)"/>')
    c.append(f'<g transform="rotate(-12 {bx} {by})"><ellipse cx="{bx}" cy="{by}" rx="290" ry="70" fill="url(#disc)" filter="url(#borr)"/></g>')
    c.append(f'<circle cx="{bx}" cy="{by}" r="78" fill="none" stroke="#ffe2a6" stroke-width="10" opacity=".75" filter="url(#borr)"/>')
    c.append(f'<circle cx="{bx}" cy="{by}" r="70" fill="#000"/>')
    # la part del disc que passa per davant del forat
    c.append(f'<g transform="rotate(-12 {bx} {by})"><path d="M{bx - 290} {by} A290 70 0 0 0 {bx + 290} {by} L{bx + 120} {by} A120 22 0 0 1 {bx - 120} {by}Z" fill="url(#disc)" opacity=".9" filter="url(#borr)"/></g>')
    c.append(f'<ellipse cx="{bx}" cy="{by - 60}" rx="140" ry="40" fill="none" stroke="#ffd58a" stroke-width="3" opacity=".35" transform="rotate(-12 {bx} {by})"/>')
    # terreny
    c.append('<path d="M0 470 Q300 430 640 460 Q980 490 1300 450 Q1460 430 1600 450 V600 H0Z" fill="url(#terra)"/>')
    # temple / obelisc daurat amb cristall flotant
    c.append('<g transform="translate(420 470)">'
             '<ellipse cx="0" cy="-230" rx="110" ry="110" fill="url(#llum)" filter="url(#brill)"/>'
             '<path d="M-110 0 L-80 -40 L80 -40 L110 0Z" fill="url(#or)" stroke="#2a1c06" stroke-width="2"/>'
             '<path d="M-70 -40 Q-90 -150 -40 -230 L-26 -224 Q-60 -140 -40 -40Z" fill="url(#or)" stroke="#2a1c06" stroke-width="2"/>'
             '<path d="M70 -40 Q90 -150 40 -230 L26 -224 Q60 -140 40 -40Z" fill="url(#or)" stroke="#2a1c06" stroke-width="2"/>'
             '<path d="M0 -320 L34 -240 L0 -170 L-34 -240Z" fill="url(#cristall)" stroke="#bff6ff" stroke-width="2"/>'
             '<path d="M0 -320 L0 -170 M-34 -240 L34 -240" stroke="#e6fdff" stroke-width="1.5" opacity=".7"/>'
             '<path d="M-24 -60 h48" stroke="#7ff0ff" stroke-width="4" stroke-linecap="round"/></g>')
    # cristalls que surten de terra
    def cristall(x, y, h, w, ang, grad="cristall"):
        return (f'<g transform="translate({x} {y}) rotate({ang})">'
                f'<path d="M0 {-h} L{w} {-h * .72} L{w * .8} 0 L{-w * .8} 0 L{-w} {-h * .72}Z" fill="url(#{grad})" stroke="#bff6ff" stroke-width="1.5" opacity=".95"/>'
                f'<path d="M0 {-h} L{w * .15} 0 M0 {-h} L{-w} {-h * .72}" stroke="#ffffff" stroke-width="1" opacity=".55"/></g>')
    for x, y, h, w, a in [(150, 520, 180, 30, -12), (200, 530, 120, 22, 8), (110, 540, 90, 18, -25), (250, 540, 70, 14, 20),
                          (820, 500, 140, 26, -6), (870, 510, 90, 18, 14), (780, 515, 70, 14, -22),
                          (1440, 500, 220, 36, 6), (1500, 520, 140, 24, 22), (1380, 520, 110, 20, -18), (1550, 540, 80, 16, 30)]:
        c.append(f'<ellipse cx="{x}" cy="{y - h * .45:.0f}" rx="{w * 2.4:.0f}" ry="{h * .6:.0f}" fill="url(#llum)" opacity=".5" filter="url(#brill)"/>')
        c.append(cristall(x, y, h, w, a, "cristall" if h > 100 else "cristall2"))
    # roques
    for x in (40, 620, 1000, 1240):
        c.append(roca(r, x, 600, r.uniform(70, 120), r.uniform(40, 80), "#0b1122"))
    # pols de llum
    for _ in range(60):
        c.append(f'<circle cx="{r.uniform(0, W):.0f}" cy="{r.uniform(250, 560):.0f}" r="{r.uniform(.6, 2):.1f}" fill="#bff6ff" opacity="{r.uniform(.2, .7):.2f}"/>')
    return svg("".join(c), defs)


# ------------------------------------------------------------------ icones (24x24, un sol color: es pinten amb mask)
ICONES = {
    "terran": '<path d="M6 4h12v3H6zM5 8h14v12H5z M7 11h10v2H7z" fill="#000"/>',  # barril
    "zerg": '<path d="M12 2c4 0 6 6 6 10 0 5-3 8-6 8s-6-3-6-8c0-4 2-10 6-10z M9 7c1 3 1 6-1 9" fill="#000"/>',  # ou
    "protoss": '<path d="M12 1l6 9-6 13-6-13z" fill="#000"/>',  # cristall
    "space": '<circle cx="12" cy="12" r="6" fill="#000"/><ellipse cx="12" cy="12" rx="11" ry="3.5" fill="none" stroke="#000" stroke-width="1.6" transform="rotate(-20 12 12)"/>',  # planeta
}


def main():
    os.makedirs(DIR, exist_ok=True)
    for nom, f in (("space", espai), ("terran", terran), ("zerg", zerg), ("protoss", protoss)):
        open(os.path.join(DIR, nom + ".svg"), "w").write(f())
    for nom, cos in ICONES.items():
        open(os.path.join(DIR, "ico-" + nom + ".svg"), "w").write(
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">{cos}</svg>')
    open(os.path.join(DIR, "icon.svg"), "w").write(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32"><rect width="32" height="32" rx="7" fill="#0b1024"/>'
        '<circle cx="16" cy="16" r="7" fill="#e9b26b"/><ellipse cx="16" cy="16" rx="14" ry="4" fill="none" stroke="#7fd8ff" stroke-width="2" transform="rotate(-20 16 16)"/></svg>')
    print("art generat a", DIR)


if __name__ == "__main__":
    main()
