#!/usr/bin/env bash
# Offline installation from the complete downloaded package.
set -euo pipefail
HERE=$(cd -- "$(dirname -- "$(readlink -f -- "${BASH_SOURCE[0]}")")" && pwd)
APP_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/kde-windows-style/app"
if [[ $EUID == 0 ]]; then echo 'Execute sem sudo.' >&2; exit 1; fi
if [[ -e "$APP_DIR" && ! -f "$APP_DIR/.managed" && "$HERE" != "$APP_DIR" ]]; then
    echo "A pasta $APP_DIR já existe e não pertence ao instalador." >&2; exit 1
fi
mkdir -p "$APP_DIR"
if [[ "$HERE" != "$APP_DIR" ]]; then
    tar -C "$HERE" --exclude='./.git' --exclude='./.venv' --exclude='./.runtime' --exclude='./__pycache__' -cf - . | tar -C "$APP_DIR" -xf -
fi
touch "$APP_DIR/.managed"
bash "$APP_DIR/launch.sh" --setup
bash "$APP_DIR/kde-windows-style.sh" --install-menu
python3 "$APP_DIR/dooros.py" --install
printf '\nInstalado. Abra KDE Windows Style pelo menu do KDE.\n'
