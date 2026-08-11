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
copy_if "feature_ablation_latest.json"
copy_if "paper_validation_latest.json"

# Walk-forward per-event curves (event replay UI, patent 265 temporal tiles)
WF_SRC="$SRC/walkforward"
WF_DST="$DST/walkforward"
if [[ -d "$WF_SRC" ]]; then
  mkdir -p "$WF_DST"
  cp -f "$WF_SRC"/wf_*.json "$WF_DST"/ 2>/dev/null || true
  echo "  + walkforward/ ($(ls -1 "$WF_DST" 2>/dev/null | wc -l) event curves)"
fi

# Quant HTML reports (if generated)
RDIR="$ROOT/data/alerts/reports"
RDST="$ROOT/src/frontend/public/reports"
if [[ -d "$RDIR" ]]; then
  mkdir -p "$RDST"
  rsync -a "$RDIR/" "$RDST/" 2>/dev/null || cp -f "$RDIR"/* "$RDST/" 2>/dev/null || true
  echo "  + reports/ ($(ls -1 "$RDST" 2>/dev/null | wc -l) files)"
fi
echo "Done."
