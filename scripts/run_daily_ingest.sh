#!/usr/bin/env bash
# =============================================================================
# run_daily_ingest.sh — organized daily TLE ingestion pipeline for Athena-SDA
# =============================================================================
#
#  Stage 1  space weather   GFZ F10.7 / Ap / Kp            [--skip-weather]
#  Stage 2  ingest-daily    CelesTrak TLEs -> data/daily/  [--force re-fetch]
#  Stage 3  train-baseline  series (past) -> IF normality  [--skip-train]
#  Stage 4  score           today vs baseline + pairs      [--skip-score]
#  Stage 5  sync frontend   data/alerts -> public/data/    [--skip-sync]
#
# Idempotent: ingest is skipped when today's snapshot already exists
# (unless --force). Safe to run from cron multiple times.
#
#  Logs     : data/daily/logs/run_YYYY-MM-DD.log           (keeps last 30)
#  Manifest : data/daily/last_run.json                     (per-stage status)
#
# Usage:
#   bash scripts/run_daily_ingest.sh                       # full daily run
#   bash scripts/run_daily_ingest.sh --force               # re-fetch today
#   bash scripts/run_daily_ingest.sh --skip-train --skip-score
#   bash scripts/run_daily_ingest.sh --dry-run             # print stages only
# =============================================================================
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

# Pick the venv interpreter when present (cron PATH may lack python).
if [[ -x "$ROOT/.venv/bin/python" ]]; then
  PY="$ROOT/.venv/bin/python"
else
  PY="$(command -v python3 || command -v python)"
fi

DAY="$(date -u +%Y-%m-%d)"

LOGS_DIR="$ROOT/data/daily/logs"
MANIFEST="$ROOT/data/daily/last_run.json"
RUN_LOG="$LOGS_DIR/run_$DAY.log"
STAGE_TMP="$(mktemp)"

# --- defaults ---
FORCE=0
DRY_RUN=0
SKIP_WEATHER=0
SKIP_TRAIN=0
SKIP_SCORE=0
SKIP_SYNC=0
SOURCE="celestrak"

usage() {
  sed -n '2,23p' "$0" | sed 's/^# \{0,1\}//'
  echo "Flags:"
  echo "  --force         Re-fetch today's TLEs even if a snapshot exists"
  echo "  --source X      TLE source for ingest (celestrak|hf|both; default celestrak)"
  echo "  --skip-weather  Skip GFZ space-weather refresh"
  echo "  --skip-train    Skip baseline retrain"
  echo "  --skip-score    Skip scoring / alerting"
  echo "  --skip-sync     Skip frontend data sync"
  echo "  --dry-run       Print the pipeline and exit without running"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --force) FORCE=1 ;;
    --source) SOURCE="$2"; shift ;;
    --skip-weather) SKIP_WEATHER=1 ;;
    --skip-train) SKIP_TRAIN=1 ;;
    --skip-score) SKIP_SCORE=1 ;;
    --skip-sync) SKIP_SYNC=1 ;;
    --dry-run) DRY_RUN=1 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1"; usage; exit 2 ;;
  esac
  shift
done

mkdir -p "$LOGS_DIR"

# Rotate logs: keep the last 30 run_*.log files (robust when none exist yet).
ls -1t "$LOGS_DIR"/run_*.log 2>/dev/null | tail -n +31 | xargs -r rm -f -- || true

log() { printf '[%s] %s\n' "$(date -u +%H:%M:%S)" "$*" | tee -a "$RUN_LOG"; }

# run_stage <name> [--skip] -- <command...>
# Records per-stage status into $STAGE_TMP and continues on failure so that
# later stages (e.g. frontend sync) still run and the manifest reflects reality.
run_stage() {
  local name="$1"; shift
  local skip=0
  if [[ "$1" == "--skip" ]]; then skip=1; shift; fi
  [[ "$1" == "--" ]] && shift

  if [[ "$skip" -eq 1 ]]; then
    log "SKIP  $name"
    printf '%s|skipped|0|0\n' "$name" >> "$STAGE_TMP"
    return 0
  fi
  if [[ "$DRY_RUN" -eq 1 ]]; then
    log "PLAN  $name :: $*"
    printf '%s|planned|0|0\n' "$name" >> "$STAGE_TMP"
    return 0
  fi

  log "RUN   $name :: $*"
  local t0 t1 code
  t0="$(date +%s)"
  if "$@" >>"$RUN_LOG" 2>&1; then
    code=0
    log "OK    $name"
  else
    code=$?
    log "FAIL  $name (exit $code)"
  fi
  t1="$(date +%s)"
  printf '%s|%s|%s|%s\n' "$name" "$([ "$code" -eq 0 ] && echo ok || echo failed)" "$code" "$((t1-t0))" >> "$STAGE_TMP"
}

# ---------------------------------------------------------------------------
log "=== Athena-SDA daily pipeline $DAY (force=$FORCE source=$SOURCE) ==="
log "log: $RUN_LOG"

if [[ "$DRY_RUN" -eq 1 ]]; then
  log "(dry-run — no commands executed)"
fi

run_stage "space_weather" $([ "$SKIP_WEATHER" -eq 1 ] && echo --skip) -- \
  "$PY" scripts/run_anomaly_monitor.py seed-space-weather

INGEST_ARGS=(--source "$SOURCE" --skip-if-fresh)
[[ "$FORCE" -eq 1 ]] && INGEST_ARGS=(--source "$SOURCE" --force)
run_stage "ingest_daily" -- \
  "$PY" scripts/run_anomaly_monitor.py ingest-daily "${INGEST_ARGS[@]}"

run_stage "train_baseline" $([ "$SKIP_TRAIN" -eq 1 ] && echo --skip) -- \
  "$PY" scripts/run_anomaly_monitor.py train-baseline --holdout-days 1 --sample-mode hybrid

run_stage "score" $([ "$SKIP_SCORE" -eq 1 ] && echo --skip) -- \
  "$PY" scripts/run_anomaly_monitor.py score

run_stage "sync_frontend" $([ "$SKIP_SYNC" -eq 1 ] && echo --skip) -- \
  "$PY" scripts/sync_frontend_data.py --quiet

# ---------------------------------------------------------------------------
# Write the manifest (valid JSON via python).
# ---------------------------------------------------------------------------
STAGE_FILE="$STAGE_TMP"
"$PY" - "$MANIFEST" "$DAY" "$STAGE_FILE" <<'PYEOF'
import json
import sys
from datetime import datetime, timezone

manifest_path, day, stage_file = sys.argv[1], sys.argv[2], sys.argv[3]

stages = {}
any_failed = False
with open(stage_file, encoding="utf-8") as fh:
    for line in fh:
        line = line.rstrip("\n")
        if not line:
            continue
        name, status, code, secs = line.split("|")
        stages[name] = {"status": status, "exit_code": int(code), "seconds": int(secs)}
        if status == "failed":
            any_failed = True

overall = "failed" if any_failed else "ok"
manifest = {
    "day": day,
    "finished_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "overall": overall,
    "stages": stages,
}
with open(manifest_path, "w", encoding="utf-8") as fh:
    json.dump(manifest, fh, indent=2)
print(f"manifest -> {manifest_path} (overall = {overall})")
PYEOF

rm -f "$STAGE_TMP"

echo ""
echo "=== done ($DAY) ==="
echo "  log:      $RUN_LOG"
echo "  manifest: $MANIFEST"
grep -E '^\[[0-9:]+\] (OK|FAIL|SKIP)' "$RUN_LOG" | sed 's/^/  /' || true

OVERALL="$("$PY" -c "import json,sys; print(json.load(open(sys.argv[1],encoding='utf-8')).get('overall',''))" "$MANIFEST")"
if [[ "$OVERALL" != "ok" ]]; then
  echo "daily pipeline overall=$OVERALL — see $RUN_LOG" >&2
  exit 1
fi
