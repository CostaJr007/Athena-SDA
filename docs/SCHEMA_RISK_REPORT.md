# Schema `athena.risk_report.v1`

Contract between the Python monitor and the tactical frontend.

| Field | Type | Description |
|-------|------|-------------|
| `schema` | string | Always `athena.risk_report.v1` |
| `generated_at` | ISO datetime | When the score was generated |
| `day` | `YYYY-MM-DD` | Operational day of the snapshot |
| `summary` | object | Aggregate counts |
| `summary.n_scored` | int | Objects on the board |
| `summary.n_anomalies` | int | `is_anomaly` count |
| `summary.n_pairs` | int | Suspect×asset pairs evaluated |
| `summary.n_pair_elevated` | int | Pairs above attention threshold |
| `summary.threshold` | float | Attention / anomaly threshold used |
| `board[]` | array | Scored objects |
| `board[].norad_id` | int | NORAD catalog number |
| `board[].object_name` | string | Catalog name |
| `board[].role` | `asset` \| `suspect` \| `baseline` | Watchlist role |
| `board[].anomaly_score` | float | Isolation Forest (clipped 0–1) |
| `board[].attention_score` | float | Fusion ≈ 0.45·anom + 0.55·pair |
| `board[].status` | string | `NOMINAL` / `ANOMALY` / `PAIR_ELEVATED` / `UNRELIABLE_DATA` |
| `board[].pair` | object\|null | Best suspect→asset pair if any |
| `board[].features_snapshot` | object | Hurst, Shannon, SW, dist, coint… |
| `board[].data_quality` | object | score, reliable, issues, tle_age_hours |
| `board[].anomaly_onset` | object\|null | Estimate of **when** series noise rose |
| `board[].anomaly_onset.first_elevated_at` | string\|null | First elevated TLE window |
| `board[].anomaly_onset.method` | string | `if_sustained` / `if_first_soft` / `sma_change_fallback` / … |
| `board[].anomaly_onset.sma_change_at` | string\|null | First |SMA−median| / MAD break |
| `board[].anomaly_onset.note` | string | Scientific limit (not intent date) |
| `board[].score_delta_1d` | float\|null | Δ anomaly vs previous day report |
| `top_pairs[]` | array | Top N pairs for the UI board |
| `model` | string | IF monitor path (audit) |
| `train_meta` | object | Last baseline training meta |

## UI threat map (presentation only)

| Condition | UI badge |
|-----------|----------|
| `PAIR_ELEVATED` + pair CRITICAL / att≥0.65 / pair_risk≥0.9 | **HOSTILE** |
| `PAIR_ELEVATED` or pair_risk≥0.55 | **SUSPECT** |
| `is_anomaly` / `ANOMALY` / `UNRELIABLE_DATA` | **ANOMALY** |
| else | **NOMINAL** (+ role color on the globe) |

Implementation: `src/frontend/src/lib/risk-report.ts`.

## Quant HTML reports

```bash
PYTHONPATH=. python scripts/run_quant_report.py --all
# → data/alerts/reports/ and src/frontend/public/reports/
```

## Sync into Vite

```bash
python scripts/run_anomaly_monitor.py run-daily   # optional refresh
bash scripts/sync_frontend_data.sh
# copies data/alerts/*_latest.json and reports/ → src/frontend/public/
```
