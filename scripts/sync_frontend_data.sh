#!/usr/bin/env bash
# Thin wrapper — canonical sync is scripts/sync_frontend_data.py
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
if [[ -x "$ROOT/.venv/bin/python" ]]; then
  PY="$ROOT/.venv/bin/python"
else
  PY="$(command -v python3 || command -v python)"
fi
exec "$PY" "$ROOT/scripts/sync_frontend_data.py" "$@"
