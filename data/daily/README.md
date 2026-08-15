# `data/daily/` — daily TLE ingestion store

Organized landing zone for the daily TLE pipeline. Produced by
[`scripts/run_daily_ingest.sh`](../../scripts/run_daily_ingest.sh) (and the
lower-level `python scripts/run_anomaly_monitor.py ingest-daily`).

## Layout

| Path | Contents |
|------|----------|
| `tle_YYYY-MM-DD.csv` | Raw daily TLE/GP snapshot for the watchlist (one row per epoch) |
| `tle_YYYY-MM-DD.meta.json` | Snapshot metadata: `day`, `n_rows`, `n_sats`, `saved_at` |
| `logs/run_YYYY-MM-DD.log` | Full pipeline output for that day's run (keeps last 30) |
| `logs/cron.log` | Crontab redirect (concatenated runs; `run_*.log` is the structured view) |
| `last_run.json` | Manifest of the most recent run: per-stage `status` / `exit_code` / `seconds` and `overall` |

## Notes

- **Idempotent**: `run_daily_ingest.sh` calls `ingest-daily --skip-if-fresh`, so
  a re-run on the same day skips the network fetch (use `--force` to re-fetch).
- Raw snapshots here are **inputs**; the canonical queryable history lives in
  `../history/epochs.parquet` (merged by `src/tle_store.append_epochs`).
- `../tle/` is a **legacy empty folder** (gitignored) — do not write new data there.
