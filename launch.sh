#!/usr/bin/env bash
set -euo pipefail
HERE=$(cd -- "$(dirname -- "$(readlink -f -- "${BASH_SOURCE[0]}")")" && pwd)
unset QT_STYLE_OVERRIDE QT_QPA_PLATFORMTHEME QT_PLUGIN_PATH
# The release package bundles the Qt wheels; a copy downloaded from GitHub only has their checksums.
if [[ -f "$HERE/vendor/wheels/SHA256SUMS.json" ]] && compgen -G "$HERE/vendor/wheels/*.whl" > /dev/null; then
    python3 "$HERE/runtime_setup.py"
    if [[ "${1:-}" == --setup ]]; then exit 0; fi
    export PYTHONPATH="$HERE/.runtime${PYTHONPATH:+:$PYTHONPATH}"
    exec python3 "$HERE/gui.py" "$@"
fi
# Developer checkout or GitHub download: install PySide6 in a private venv (the release package includes it).
if [ ! -x "$HERE/.venv/bin/python" ]; then python3 -m venv "$HERE/.venv"; fi
if ! "$HERE/.venv/bin/python" -c 'import PySide6.QtWidgets' 2>/dev/null; then
    "$HERE/.venv/bin/python" -m pip install 'PySide6-Essentials==6.12.0'
fi
if [[ "${1:-}" == --setup ]]; then exit 0; fi
exec "$HERE/.venv/bin/python" "$HERE/gui.py" "$@"
