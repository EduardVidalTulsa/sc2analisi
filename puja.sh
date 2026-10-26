#!/bin/sh
# SPDX-License-Identifier: GPL-3.0-or-later
# Builds the site (dist/), compiles the uploader and deploys everything, plus the cdn/ API.
# The data (html/data) are made by analitza.py on the server itself: ./puja.sh analitza  re-analyses everything.
#
# Configuration: copy puja.conf.example to puja.conf (not committed) and fill it in,
# or set the same variables in the environment.
set -e
cd "$(dirname "$0")"
[ -f puja.conf ] && . ./puja.conf
: "${SC2_WEB:?set SC2_WEB (public address of the site) in puja.conf}"
: "${SC2_SERVIDOR:?set SC2_SERVIDOR (ssh target of the web/API server) in puja.conf}"
: "${SC2_DIR:?set SC2_DIR (application directory on the server) in puja.conf}"
: "${SC2_CDN:?set SC2_CDN (ssh target and folder of the PHP host) in puja.conf}"
export SC2_WEB
SRV="$SC2_SERVIDOR"; DIR="$SC2_DIR"; CDN="$SC2_CDN"
GOLD="-s -w -X main.servidor=${SC2_WEB%/}/"

python art.py >/dev/null
python genera.py
tar -cf - analitza.py servei.py magatzem.py resum.py | ssh "$SRV" "tar -xf - -C $DIR"
tar -C dist -cf - . | ssh "$SRV" "tar -xf - -C $DIR/html"
(cd pujador && GOOS=windows GOARCH=amd64 go build -trimpath -ldflags "$GOLD -H windowsgui" -o ../dist-pujador/sc2-pujador.exe . && GOOS=linux GOARCH=amd64 CGO_ENABLED=0 go build -trimpath -ldflags "$GOLD" -o ../dist-pujador/sc2-pujador-linux-x86_64 . && GOOS=linux GOARCH=arm64 CGO_ENABLED=0 go build -trimpath -ldflags "$GOLD" -o ../dist-pujador/sc2-pujador-linux-arm64 .)
ssh "$SRV" "mkdir -p $DIR/html/downloads" && tar -C dist-pujador -cf - . | ssh "$SRV" "tar -xf - -C $DIR/html/downloads"
scp -q cdn/api.php cdn/r.php cdn/.htaccess "$CDN"
ssh "$SRV" "systemctl restart sc2-envia sc2-resums"
if [ "$1" = analitza ]; then
  ssh "$SRV" "cd $DIR && SC2_TOON='${SC2_TOON:-}' .venv/bin/python analitza.py maps html 2>&1 | tail -1 && chown -R sc2:sc2 html/data enviats maps"
fi
