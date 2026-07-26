#!/usr/bin/env bash
# Demo path: optional daily score → sync JSON to frontend → print URLs.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

RUN_DAILY=0
SKIP_SCORE=0
for arg in "$@"; do
  case "$arg" in
    --run-daily) RUN_DAILY=1 ;;
    --skip-score) SKIP_SCORE=1 ;;
    -h|--help)
      echo "Usage: bash scripts/demo_day.sh [--run-daily] [--skip-score]"
      echo "  --run-daily   ingest + train-baseline + score (slow)"
      echo "  (default)     only sync existing alerts → frontend public/"
      exit 0
      ;;
  esac
done

export PYTHONPATH="${PYTHONPATH:-.}:$ROOT"

if [[ "$RUN_DAILY" -eq 1 && "$SKIP_SCORE" -eq 0 ]]; then
  echo "==> run-daily (ingest → baseline → score)"
  python scripts/run_anomaly_monitor.py run-daily
fi

echo "==> status"
python scripts/run_anomaly_monitor.py status || true

echo "==> sync frontend data"
bash scripts/sync_frontend_data.sh

echo ""
echo "Demo ready:"
echo "  Frontend:  cd src/frontend && npm run dev   → http://127.0.0.1:3000"
echo "  Streamlit: streamlit run app.py             → http://localhost:8501"
echo "  Board:     public/data/risk_report_latest.json"
echo "  WF:        public/data/walkforward_summary.json"
