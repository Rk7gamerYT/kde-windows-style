#!/usr/bin/env bash
# One command installs everything and applies the full Windows 11 look:
#   curl -fsSL https://raw.githubusercontent.com/Rk7gamerYT/kde-windows-style/main/windows11.sh | bash
# It installs missing system tools (asks for your password once), the app, the taskbar widgets,
# DoorOS-Dolphin and the theme, then applies everything with a backup.
# Extra options go to profile.py, e.g. `bash -s -- --theme light --opacity 94`.
# Own options: --no-dooros (skip DoorOS-Dolphin), --no-deps (do not install system packages).
set -euo pipefail
REPO=Rk7gamerYT/kde-windows-style
REF=${KDE_WINDOWS_STYLE_REF:-main}
APP_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/kde-windows-style/app"
DOOROS=1 DEPS=1
PROFILE_ARGS=()
for arg in "$@"; do
    case "$arg" in
        --dry-run)
            echo "Instalar ferramentas do sistema que faltarem, o app em $APP_DIR, os widgets da barra e o DoorOS-Dolphin;"
            echo "aplicar visual Windows 11, menu Iniciar, barra, bandeja e atalhos, com backup."
            echo "Desfazer depois: $APP_DIR/kde-windows-style.sh --restore"
            exit 0 ;;
        --no-dooros) DOOROS=0 ;;
        --no-deps) DEPS=0 ;;
        *) PROFILE_ARGS+=("$arg") ;;
    esac
done
if [[ $EUID == 0 ]]; then echo 'Execute sem sudo; a senha é pedida só se precisar instalar pacotes.' >&2; exit 1; fi
if [[ ":${XDG_CURRENT_DESKTOP^^}:" != *:KDE:* ]]; then
    echo 'Entre numa sessão KDE Plasma 6 e rode este comando de novo.' >&2; exit 1
fi
if [[ -e "$APP_DIR" && ! -f "$APP_DIR/.managed" ]]; then
    echo "A pasta $APP_DIR já existe e não pertence ao instalador." >&2; exit 1
fi
step() { printf '\n==> %s\n' "$*"; }

# 1. System tools used by the theme, the taskbar widgets and the app, by package manager.
#    Each entry is command:package; only missing commands are installed.
if [[ $DEPS == 1 ]]; then
    step 'Conferindo ferramentas do sistema'
    if command -v apt-get >/dev/null; then
        PM=(apt-get install -y --no-install-recommends)
        NEEDS="qdbus6:qdbus-qt6 gdbus:libglib2.0-bin kwriteconfig6:libkf6config-bin kreadconfig6:libkf6config-bin
               curl:curl nmcli:network-manager pactl:pulseaudio-utils bluetoothctl:bluez rfkill:rfkill patch:patch
               spectacle:kde-spectacle krunner:plasma-workspace"
    elif command -v dnf >/dev/null; then
        PM=(dnf install -y)
        NEEDS="qdbus6:qt6-qttools gdbus:glib2 kwriteconfig6:kf6-kconfig kreadconfig6:kf6-kconfig curl:curl
               nmcli:NetworkManager pactl:pulseaudio-utils bluetoothctl:bluez rfkill:util-linux patch:patch spectacle:spectacle"
    elif command -v pacman >/dev/null; then
        PM=(pacman -S --needed --noconfirm)
        NEEDS="qdbus6:qt6-tools gdbus:glib2 kwriteconfig6:kconfig kreadconfig6:kconfig curl:curl nmcli:networkmanager
               pactl:libpulse bluetoothctl:bluez-utils rfkill:util-linux patch:patch spectacle:spectacle"
    elif command -v zypper >/dev/null; then
        PM=(zypper --non-interactive install)
        NEEDS="qdbus6:qt6-tools-qdbus gdbus:glib2-tools kwriteconfig6:kf6-kconfig kreadconfig6:kf6-kconfig curl:curl
               nmcli:NetworkManager pactl:pulseaudio-utils bluetoothctl:bluez rfkill:util-linux patch:patch spectacle:spectacle"
    else
        PM=() NEEDS=""
        echo 'Gerenciador de pacotes não reconhecido; usando só o que já está instalado.'
    fi
    missing=()
    for pair in $NEEDS; do
        command -v "${pair%%:*}" >/dev/null || missing+=("${pair#*:}")
    done
    # The app's graphical runtime needs venv when the downloaded copy has no bundled wheels.
    if command -v apt-get >/dev/null && ! python3 -c 'import ensurepip' 2>/dev/null; then missing+=(python3-venv); fi
    if (( ${#missing[@]} )); then
        mapfile -t missing < <(printf '%s\n' "${missing[@]}" | sort -u)
        echo "Instalando: ${missing[*]}"
        if [[ ${PM[0]} == apt-get ]]; then sudo apt-get update -qq; fi
        sudo env DEBIAN_FRONTEND=noninteractive "${PM[@]}" "${missing[@]}"
    else
        echo 'Tudo presente.'
    fi
fi

# 2. The app itself: this folder when run from a checkout or package, otherwise the repository.
step 'Instalando o app KDE Windows Style'
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
    # Keep a DoorOS-Dolphin already compiled in the app folder; rebuilding it takes a while.
    tar -C "$SOURCE" --exclude='./.git' --exclude='./.venv' --exclude='./.runtime' --exclude='./.runtime.lock' \
        --exclude='./dist' --exclude='__pycache__' -cf - . | tar -C "$APP_DIR" -xf -
fi
touch "$APP_DIR/.managed"
bash "$APP_DIR/launch.sh" --setup

# 3. DoorOS-Dolphin: bundled in the release package; otherwise compiled once (Debian/Ubuntu).
if [[ $DOOROS == 1 ]]; then
    step 'Preparando o DoorOS-Dolphin'
    if [[ -x "$APP_DIR/vendor/dooros-dolphin/usr/bin/dolphin" ]]; then
        python3 "$APP_DIR/dooros.py" --install
    elif command -v apt-get >/dev/null && [[ $DEPS == 1 ]]; then
        echo 'Compilando uma única vez; pode levar de 10 a 20 minutos.'
        sudo python3 -I "$APP_DIR/build-deps.py"
        if python3 "$APP_DIR/dooros.py" --build && python3 "$APP_DIR/dooros.py" --install; then :; else
            echo 'O DoorOS-Dolphin não compilou; o resto do visual continua. Tente depois pela aba DoorOS-Dolphin do app.' >&2
        fi
    else
        echo 'Sem DoorOS-Dolphin pré-compilado para este sistema; pulei essa parte. O resto do visual é aplicado.'
    fi
fi

# 4. Theme, icons, window borders, Start menu, taskbar widgets, tray and shortcuts, with a backup.
step 'Aplicando o visual Windows 11'
python3 "$APP_DIR/profile.py" "${PROFILE_ARGS[@]}"
printf '\nPronto. O app KDE Windows Style está no menu Iniciar para ajustes finos.\n'
