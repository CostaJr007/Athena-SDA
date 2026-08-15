#!/usr/bin/env bash
# =============================================================================
# install_daily_cron.sh — schedule Athena-SDA daily TLE ingestion via crontab
# =============================================================================
#
# Installs (or removes) a user crontab entry that runs:
#     bash scripts/run_daily_ingest.sh
# every day at the configured time (default 03:15 UTC, cronie supports CRON_TZ).
#
# The job is idempotent thanks to `--skip-if-fresh` in the orchestrator, so a
# missed/duplicate run is harmless.
#
# Usage:
#   bash scripts/install_daily_cron.sh               # install at 03:15 UTC
#   bash scripts/install_daily_cron.sh --time 06:30  # install at 06:30 UTC
#   bash scripts/install_daily_cron.sh --uninstall   # remove the job
#   bash scripts/install_daily_cron.sh --status      # show current entry
# =============================================================================
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
MARKER="# athena-sda-daily"
TIME="03:15"
ACTION="install"

usage() {
  sed -n '2,18p' "$0" | sed 's/^# \{0,1\}//'
}
while [[ $# -gt 0 ]]; do
  case "$1" in
    --time) TIME="$2"; shift ;;
    --uninstall) ACTION="uninstall" ;;
    --status) ACTION="status" ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1"; usage; exit 2 ;;
  esac
  shift
done

if ! command -v crontab >/dev/null 2>&1; then
  echo "ERROR: 'crontab' not found. Install cronie: sudo dnf install cronie"
  exit 1
fi

# Existing crontab without the Athena line (best-effort).
CUR="$(crontab -l 2>/dev/null | grep -v "^[[:space:]]*$MARKER" || true)"
CUR="$(printf '%s\n' "$CUR" | grep -v "$MARKER" || true)"

case "$ACTION" in
  status)
    if crontab -l 2>/dev/null | grep -q "$MARKER"; then
      echo "Athena-SDA daily job is INSTALLED:"
      crontab -l | grep -A1 "$MARKER" | sed 's/^/  /'
    else
      echo "Athena-SDA daily job is NOT installed."
    fi
    exit 0
    ;;
  uninstall)
    if [[ -z "$CUR" ]]; then
      echo "No crontab or no Athena entry — nothing to remove."
    else
      printf '%s\n' "$CUR" | crontab -
      echo "Removed Athena-SDA daily cron job."
    fi
    exit 0
    ;;
  install) ;;
esac

HOUR="${TIME%%:*}"
MIN="${TIME##*:}"
# validate HH:MM
if ! [[ "$HOUR" =~ ^[0-9]{1,2}$ && "$MIN" =~ ^[0-9]{1,2}$ ]]; then
  echo "ERROR: invalid --time '$TIME' (expected HH:MM)"
  exit 2
fi

# Ensure the log dir exists so the crontab redirect never fails.
mkdir -p "$ROOT/data/daily/logs"

# CRON_TZ is a cronie env assignment (its own line). The job line MUST be a
# real schedule, not a comment — the marker is a trailing crontab comment so
# status/uninstall can find it without disabling the job.
JOB_LINE="CRON_TZ=UTC"
JOB_CMD="$MIN $HOUR * * * cd '$ROOT' && bash scripts/run_daily_ingest.sh >> '$ROOT/data/daily/logs/cron.log' 2>&1 $MARKER"

NEW="$(printf '%s\n%s\n%s\n' "$CUR" "$JOB_LINE" "$JOB_CMD" | sed '/^$/N;/^\n$/D')"
printf '%s\n' "$NEW" | crontab -

echo "Installed Athena-SDA daily cron job:"
echo "  schedule : $TIME UTC (cronie CRON_TZ)"
echo "  command  : $JOB_CMD"
echo "  logs     : $ROOT/data/daily/logs/cron.log"
echo ""
echo "Verify with: bash scripts/install_daily_cron.sh --status"
echo "Remove with: bash scripts/install_daily_cron.sh --uninstall"
