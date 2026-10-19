#!/usr/bin/env sh
# POSIX public entrypoint. Invoke with `sh` so executable bits are not required.
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)

if [ "${1:-}" = "--probe" ]; then
  exec python3 "$SCRIPT_DIR/baseline.py" probe
fi

exec python3 "$SCRIPT_DIR/baseline.py" init "$@"
