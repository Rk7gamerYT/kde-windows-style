#!/usr/bin/env bash
set -euo pipefail
HERE=$(cd -- "$(dirname -- "$(readlink -f -- "${BASH_SOURCE[0]}")")" && pwd)
exec python3 "$HERE/dooros.py" --open -- "$@"
