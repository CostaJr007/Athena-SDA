# Daily detection protocol

**Rule:** the **series** trains the “normal”; **today** is only compared.

```
TRAIN (past): windows ending before cutoff (yesterday if holdout_days=1)
SCORE (today): last window of each sat vs that baseline
```

```bash
python scripts/run_anomaly_monitor.py ingest-daily --source celestrak
python scripts/run_anomaly_monitor.py train-baseline --holdout-days 1 --sample-mode hybrid
python scripts/run_anomaly_monitor.py score
# or one-shot:
python scripts/run_anomaly_monitor.py run-daily
```

Alerts: `data/alerts/anomalies_latest.json` and `risk_report_latest.json`.

Quant HTML rationale: `PYTHONPATH=. python scripts/run_quant_report.py --all`
