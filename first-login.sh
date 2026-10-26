#!/usr/bin/env bash
# Apply the profile at the first Plasma login when windows11.sh ran from another desktop.
#   first-login.sh --schedule [profile options]   remember the options and register the login entry
#   first-login.sh                                 (from the login entry) apply once, then remove it
set -euo pipefail
HERE=$(cd -- "$(dirname -- "$(readlink -f -- "${BASH_SOURCE[0]}")")" && pwd)
STATE="${XDG_STATE_HOME:-$HOME/.local/state}/kde-windows-style"
ENTRY="${XDG_CONFIG_HOME:-$HOME/.config}/autostart/kde-windows-style-first-login.desktop"
if [[ "${1:-}" == --schedule ]]; then
    shift
    mkdir -p "$STATE" "$(dirname -- "$ENTRY")"
    printf '%s\0' "$@" > "$STATE/first-login-args"
    cat > "$ENTRY" <<EOF
[Desktop Entry]
Type=Application
Name=KDE Windows Style: primeira configuração
Exec=bash "$HERE/first-login.sh"
OnlyShowIn=KDE;
NoDisplay=true
X-KDE-autostart-phase=2
EOF
    exit 0
fi
# Plasma may still be starting its shell right after login.
for _ in $(seq 30); do
    qdbus6 org.kde.plasmashell /PlasmaShell >/dev/null 2>&1 && break
    sleep 2
done
args=()
if [[ -f "$STATE/first-login-args" ]]; then mapfile -d '' -t args < "$STATE/first-login-args"; fi
log="$STATE/first-login.log"
if python3 "$HERE/profile.py" "${args[@]}" > "$log" 2>&1; then
    rm -f -- "$ENTRY" "$STATE/first-login-args"
    notify-send -a 'KDE Windows Style' -i preferences-desktop-theme 'Visual Windows 11 aplicado' \
        'Ajuste o que quiser pelo app KDE Windows Style no menu Iniciar.' 2>/dev/null || true
else
    notify-send -a 'KDE Windows Style' -i dialog-warning 'Não foi possível aplicar o visual' \
        "Veja $log ou rode o app KDE Windows Style." 2>/dev/null || true
fi
