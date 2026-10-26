#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Genera la web estàtica a dist/: català a l'arrel i la resta d'idiomes a /<codi>/.

Copia els fitxers de web/ (css, js, fonts, img) a dist/ i munta cada pàgina a partir de
plantilles/base.html + plantilles/<pàgina>.html amb els textos de textos.py.
"""
import hashlib, html, json, os, re, shutil

from textos import IDIOMES, NOM_IDIOMA, LOCALE, RTL, T

ARREL = os.path.dirname(os.path.abspath(__file__))
DIST = os.path.join(ARREL, "dist")
# l'adreça pública de la web (puja.sh la passa amb SC2_WEB): enllaços entre idiomes, ordre d'instal·lació, install.sh
DOMINI = os.environ.get("SC2_WEB", "https://sc2.lestudi.com").rstrip("/") + "/"
PAGINES = {"index": ("titol_index", "peu"), "game": ("titol_partida", "peu_partida")}


def prefix(lang):
    return "" if lang == "ca" else lang + "/"


def textos(lang):
    out = {}
    for k, v in T.items():
        assert lang in v, f"falta {lang} a {k}"
        out[k[3:] if k.startswith("js.") else k] = v[lang]
    return out


def omple(plantilla, vals):
    def sub(m):
        k = m.group(1)
        if k not in vals:
            raise KeyError(f"text sense definir: {k}")
        return vals[k]
    return re.sub(r"\{\{([a-zA-Z0-9_.]+)\}\}", sub, plantilla)


def versiona(pagina, dir_pagina):
    """Afegeix ?v=<hash del contingut> als .js i .css propis: quan canvien, el navegador no pot fer servir els vells
    (encara que se'ls hagi guardat a la memòria cau abans que el servidor enviés Cache-Control: no-cache)."""
    def sub(m):
        f = os.path.normpath(os.path.join(dir_pagina, m.group(2)))
        if not os.path.exists(f):
            return m.group(0)
        return f'{m.group(1)}="{m.group(2)}?v={hashlib.sha1(open(f, "rb").read()).hexdigest()[:8]}"'
    return re.sub(r'(src|href)="((?:\.\./)?[\w-]+\.(?:js|css))"', sub, pagina)


def main():
    if os.path.exists(DIST):
        shutil.rmtree(DIST)
    shutil.copytree(os.path.join(ARREL, "web"), DIST)
    base = open(os.path.join(ARREL, "plantilles", "base.html")).read()
    for pag, (clau_titol, clau_peu) in PAGINES.items():
        cos = open(os.path.join(ARREL, "plantilles", pag + ".html")).read()
        for lang in IDIOMES:
            arrel = "" if lang == "ca" else "../"
            tx = textos(lang)
            vals = {k: v for k, v in tx.items()}
            # els textos van dins d'HTML: els que no porten etiquetes s'escapen
            for k, v in list(vals.items()):
                if "<" not in v:
                    vals[k] = html.escape(v, quote=True)
            nom_fitxer = pag + ".html"
            vals.update(
                lang=lang, web=DOMINI.rstrip("/"), dir="rtl" if lang in RTL else "ltr", locale=LOCALE[lang], arrel=arrel, pagina=pag,
                titol=vals[clau_titol], peu=tx[clau_peu],
                T_json=json.dumps(tx, ensure_ascii=False).replace("</", "<\\/"),
                alternates="\n".join(
                    f'<link rel="alternate" hreflang="{l}" href="{DOMINI}{prefix(l)}{"" if pag == "index" else nom_fitxer}">'
                    for l in IDIOMES),
                opcions_idioma="".join(
                    f'<option value="{arrel}{prefix(l)}{nom_fitxer}"{" selected" if l == lang else ""}>{NOM_IDIOMA[l]}</option>'
                    for l in IDIOMES),
                tornar="" if pag == "index" else f'<a class="tornar" href="./">{vals["tornar"]}</a>',
            )
            vals["cos"] = omple(cos, vals)
            desti = os.path.join(DIST, prefix(lang), nom_fitxer)
            os.makedirs(os.path.dirname(desti), exist_ok=True)
            open(desti, "w").write(versiona(omple(base, vals), os.path.dirname(desti)))
    # l'instal·lador de Linux apunta a aquesta mateixa web
    f = os.path.join(DIST, "install.sh")
    sh = open(f).read().replace("@WEB@", DOMINI.rstrip("/"))
    open(f, "w").write(sh)
    print("dist/ generat:", len(IDIOMES), "idiomes ·", DOMINI)


if __name__ == "__main__":
    main()
