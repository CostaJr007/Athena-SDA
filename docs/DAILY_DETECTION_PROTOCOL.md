# Daily detection protocol

**Rule:** the **series** trains the “normal”; **today** is only compared.

```
TRAIN (past): windows ending before cutoff (yesterday if holdout_days=1)
SCORE (today): last window of each sat vs that baseline
```

## One-shot (recommended)

```bash
# Full pipeline: space weather → ingest → baseline → score → sync frontend
bash scripts/run_daily_ingest.sh

# Re-fetch today's TLEs even if a snapshot already exists
bash scripts/run_daily_ingest.sh --force

# Skip heavy stages when you only want a refresh
bash scripts/run_daily_ingest.sh --skip-train --skip-score
```

The orchestrator is **idempotent** (ingest skips today if already fetched), logs
to `data/daily/logs/run_YYYY-MM-DD.log`, and writes a per-stage manifest to
`data/daily/last_run.json`.

## Manual (equivalent stages)

```bash
python scripts/run_anomaly_monitor.py seed-space-weather
python scripts/run_anomaly_monitor.py ingest-daily --source celestrak
python scripts/run_anomaly_monitor.py train-baseline --holdout-days 1 --sample-mode hybrid
python scripts/run_anomaly_monitor.py score
bash scripts/sync_frontend_data.sh
# or one-shot (ingest → train → score; no weather/sync):
python scripts/run_anomaly_monitor.py run-daily
```

## Scheduled (cron, Fedora)

```bash
# Install a daily job at 03:15 UTC (idempotent; safe to re-run)
bash scripts/install_daily_cron.sh
# Custom time / uninstall / inspect
bash scripts/install_daily_cron.sh --time 06:30
bash scripts/install_daily_cron.sh --uninstall
bash scripts/install_daily_cron.sh --status
```

The cron entry redirects to `data/daily/logs/cron.log`; the structured per-run
log and manifest remain in `data/daily/`.

Alerts: `data/alerts/anomalies_latest.json` and `risk_report_latest.json`.

Quant HTML rationale: `PYTHONPATH=. python scripts/run_quant_report.py --all`

