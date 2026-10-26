#!/bin/sh
# SPDX-License-Identifier: GPL-3.0-or-later
# Installs the sc2analisi uploader on Linux:
#   curl -fsSL https://sc2.lestudi.com/install.sh | sh
# (genera.py replaces @WEB@ with the address of the site it is published on, SC2_WEB.)
# It downloads the binary for this machine and runs it: the binary copies itself to ~/.local/bin/sc2-pujador,
# starts with your session (systemd user unit or desktop autostart) and opens your profile.
# To remove it: ~/.local/bin/sc2-pujador --uninstall
#
# Everything is inside main(), called on the last line: if the download is cut short, nothing runs.
set -eu

main() {
    servidor="@WEB@"
    if [ "$(uname -s)" != "Linux" ]; then
        echo "This installer is for Linux. On Windows, download it from $servidor" >&2
        exit 1
    fi
    case "$(uname -m)" in
        x86_64 | amd64) fitxer="sc2-pujador-linux-x86_64" ;;
        aarch64 | arm64) fitxer="sc2-pujador-linux-arm64" ;;
        *) echo "Unsupported architecture: $(uname -m)" >&2; exit 1 ;;
    esac

    tmp="$(mktemp -d)"
    trap 'rm -rf "$tmp"' EXIT
    echo "Downloading $fitxer…"
    if command -v curl >/dev/null 2>&1; then
        curl -fsSL "$servidor/downloads/$fitxer" -o "$tmp/sc2-pujador"
    else
        wget -qO "$tmp/sc2-pujador" "$servidor/downloads/$fitxer"
    fi
    chmod +x "$tmp/sc2-pujador"
    # no stdin: with "curl | sh", stdin is this very script
    "$tmp/sc2-pujador" </dev/null
    echo "Done. The uploader is in ~/.local/bin/sc2-pujador and uploads new games by itself."
    echo "To remove it: ~/.local/bin/sc2-pujador --uninstall"
}

main "$@"
