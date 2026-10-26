#!/usr/bin/env bash
# Download the complete package; themes, icons, GUI runtime and DoorOS are included.
set -euo pipefail
VERSION=v1.0.0
NAME=kde-windows-style-ubuntu26.04-x86_64.tar.xz
BASE="https://github.com/Rk7gamerYT/kde-windows-style/releases/download/$VERSION"
for arg in "$@"; do
    if [[ "$arg" == --dry-run ]]; then
        echo "Baixar pacote completo $NAME e verificar checksum; instalar no usuário, sem aplicar alterações ao abrir o app."
        exit 0
    fi
done
if [[ $EUID == 0 ]]; then echo 'Execute sem sudo.' >&2; exit 1; fi
work=$(mktemp -d)
trap 'rm -rf -- "$work"' EXIT
curl -fL --retry 3 "$BASE/$NAME" -o "$work/$NAME"
curl -fsSL --retry 3 "$BASE/$NAME.sha256" -o "$work/$NAME.sha256"
(cd "$work" && sha256sum -c "$NAME.sha256")
tar -xJf "$work/$NAME" -C "$work"
bash "$work/kde-windows-style/install-local.sh"
