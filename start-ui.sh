#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
if [ -x "$root/.venv/bin/python" ]; then
    exec "$root/.venv/bin/python" -m contextops ui "$@"
fi
if command -v contextops >/dev/null 2>&1; then
    exec contextops ui "$@"
fi
printf '%s\n' 'Context Ops is not installed. Follow setup.md, then run ./start-ui.sh.' >&2
exit 1
