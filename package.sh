#!/usr/bin/env bash
# Reproduce the complete Ubuntu 26.04 x86_64 release archive.
set -euo pipefail
HERE=$(cd -- "$(dirname -- "$(readlink -f -- "${BASH_SOURCE[0]}")")" && pwd)
if [[ "$(uname -m)" != x86_64 ]]; then echo 'Este pacote pré-compilado é para x86_64.' >&2; exit 1; fi
if [[ ! -x "$HERE/vendor/dooros-dolphin/usr/bin/dolphin" ]]; then
    python3 "$HERE/dooros.py" --build
fi
if ! compgen -G "$HERE/vendor/wheels/*.whl" > /dev/null; then
    python3 -m venv "$HERE/.packaging-venv"
    "$HERE/.packaging-venv/bin/python" -m pip download --only-binary=:all: --dest "$HERE/vendor/wheels" 'PySide6-Essentials==6.12.0'
fi
python3 - "$HERE" <<'PY'
from pathlib import Path
import hashlib,json,sys
root=Path(sys.argv[1]);wheels=root/'vendor/wheels'
(wheels/'SHA256SUMS.json').write_text(json.dumps({p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(wheels.glob('*.whl'))},indent=2))
PY
stage=$(mktemp -d)
trap 'rm -rf -- "$stage"' EXIT
mkdir -p "$stage/kde-windows-style" "$HERE/dist"
tar -C "$HERE" --exclude='./.git' --exclude='./.venv' --exclude='./.runtime' --exclude='./.runtime.lock' \
    --exclude='./.packaging-venv' --exclude='./dist' --exclude='__pycache__' --exclude='./.runtime-build-*' \
    -cf - . | tar -C "$stage/kde-windows-style" -xf -
NAME=kde-windows-style-ubuntu26.04-x86_64.tar.xz
XZ_OPT='-T2 -1' tar -cJf "$HERE/dist/$NAME" -C "$stage" kde-windows-style
(cd "$HERE/dist" && sha256sum "$NAME" > "$NAME.sha256")
ls -lh "$HERE/dist/$NAME"
echo "Pronto: $HERE/dist/$NAME"
