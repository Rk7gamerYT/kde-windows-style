#!/usr/bin/env bash
# One command: install the app for this user and apply the full Windows 11 look and shortcuts.
#   curl -fsSL https://raw.githubusercontent.com/Rk7gamerYT/kde-windows-style/main/windows11.sh | bash
# Extra options go to profile.py, e.g. `bash -s -- --theme light --opacity 94`.
set -euo pipefail
REPO=Rk7gamerYT/kde-windows-style
REF=${KDE_WINDOWS_STYLE_REF:-main}
APP_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/kde-windows-style/app"
for arg in "$@"; do
    if [[ "$arg" == --dry-run ]]; then
        echo "Instalar o app em $APP_DIR e aplicar visual Windows 11, menu Iniciar e atalhos, com backup."
        echo "Desfazer depois: $APP_DIR/kde-windows-style.sh --restore"
        exit 0
    fi
done
if [[ $EUID == 0 ]]; then echo 'Execute sem sudo.' >&2; exit 1; fi
if [[ ":${XDG_CURRENT_DESKTOP^^}:" != *:KDE:* ]]; then
    echo 'Entre numa sessão KDE Plasma 6 e rode este comando de novo.' >&2; exit 1
fi
if [[ -e "$APP_DIR" && ! -f "$APP_DIR/.managed" ]]; then
    echo "A pasta $APP_DIR já existe e não pertence ao instalador." >&2; exit 1
fi

# Use this folder when run from a checkout or package; otherwise download the repository.
HERE=
if [[ -n "${BASH_SOURCE[0]:-}" && -f "${BASH_SOURCE[0]}" ]]; then
    HERE=$(cd -- "$(dirname -- "$(readlink -f -- "${BASH_SOURCE[0]}")")" && pwd)
fi
work=$(mktemp -d)
trap 'rm -rf -- "$work"' EXIT
if [[ -n "$HERE" && -f "$HERE/profile.py" && -f "$HERE/vendor/win11-plasma.tar.gz" ]]; then
    SOURCE=$HERE
else
    echo "Baixando $REPO ($REF)..."
    curl -fL --retry 3 "https://codeload.github.com/$REPO/tar.gz/$REF" | tar -xz -C "$work"
    SOURCE=$(find "$work" -mindepth 1 -maxdepth 1 -type d | head -n1)
fi

mkdir -p "$APP_DIR"
if [[ "$(readlink -f -- "$SOURCE")" != "$(readlink -f -- "$APP_DIR")" ]]; then
    tar -C "$SOURCE" --exclude='./.git' --exclude='./.venv' --exclude='./.runtime' --exclude='./.runtime.lock' \
        --exclude='./dist' --exclude='__pycache__' -cf - . | tar -C "$APP_DIR" -xf -
fi
touch "$APP_DIR/.managed"
if [[ -x "$APP_DIR/vendor/dooros-dolphin/usr/bin/dolphin" ]]; then python3 "$APP_DIR/dooros.py" --install; fi

python3 "$APP_DIR/profile.py" "$@"
printf '\nO app KDE Windows Style também está no menu Iniciar para ajustes finos.\n'
