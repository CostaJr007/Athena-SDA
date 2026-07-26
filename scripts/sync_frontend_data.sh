#!/usr/bin/env bash
# Copy latest ML alert artifacts into the frontend public/ folder for the UI.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="$ROOT/data/alerts"
DST="$ROOT/src/frontend/public/data"
mkdir -p "$DST"

copy_if() {
  local name="$1"
  if [[ -f "$SRC/$name" ]]; then
    cp -f "$SRC/$name" "$DST/$name"
    echo "  + $name"
  else
    echo "  - missing $name (skipped)"
  fi
}

echo "Sync frontend data → $DST"
copy_if "risk_report_latest.json"
copy_if "anomalies_latest.json"
copy_if "proximity_latest.json"
copy_if "walkforward_summary.json"
echo "Done."
