# Schema `athena.risk_report.v1`

Contract between the Python monitor and the tactical frontend.

**Versioning:** keep `schema: "athena.risk_report.v1"` until a breaking board field change.
Related model contracts live in `models/registry.json` (feature schema hash, monitor vs pipeline IF).
Quant validation framing: `docs/FOUNDATION_QUANT_VALIDATION.md`.

| Field | Type | Description |
|-------|------|-------------|
| `schema` | string | Always `athena.risk_report.v1` |
| `generated_at` | ISO datetime | When the score was generated |
| `day` | `YYYY-MM-DD` | Operational day of the snapshot |
| `summary` | object | Aggregate counts |
| `summary.n_scored` | int | Objects on the board |
| `doctrine` | string | `military_first_sda` |
| `summary.n_anomalies` | int | Operational anomaly flags (suspect/asset policy) |
| `summary.n_military_detections` | int | Suspect detections (noise and/or pair) |
| `summary.n_platform_health_flags` | int | Asset regime noise flags |
| `summary.n_pairs` | int | Suspect×asset pairs evaluated |
| `summary.n_pair_elevated` | int | Pairs above attention threshold |
| `summary.threshold` | float | Anomaly threshold used |
| `summary.focus` | string | Doctrine one-liner |
| `board[]` | array | Scored objects |
| `board[].norad_id` | int | NORAD catalog number |
| `board[].object_name` | string | Catalog name |
| `board[].role` | `asset` \| `suspect` \| `baseline` | Watchlist role |
| `board[].anomaly_score` | float | Isolation Forest (clipped 0–1) |
| `board[].attention_score` | float | Fusion ≈ 0.45·anom + 0.55·pair |
| `board[].is_military_detection` | bool | Suspect-focused military alert |
| `board[].is_calibration_object` | bool | Baseline — score only |
| `board[].status` | string | `NOMINAL` / `ANOMALY` / `PAIR_ELEVATED` / `CALIBRATION_BASELINE` / `ASSET_REGIME_NOISE` / `UNRELIABLE_DATA` |
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
# Windows: powershell -File scripts/sync_frontend_data.ps1
# copies data/alerts/*_latest.json and reports/ → src/frontend/public/
```

## Related artifacts

| Artifact | Role |
|----------|------|
| `data/alerts/walkforward_summary.json` | Walk-forward interest vs placebo (past-only) |
| `data/alerts/feature_ablation_latest.json` | Feature-block ablation for IF |
| `models/registry.json` | Versioned micro-models (hot-swap metadata) |
| `models/anomaly_monitor_meta.json` | Monitor IF train meta + homology_mode |

## Bob (LLM post-quant)

Bob **explains** scores and may cite open-source case IDs from `events_walkforward.json`
as *pattern-compatible* analogies. It must **never** rewrite `anomaly_score` / fuzzy threat numbers
(US 2024/0394296-style: quant first, LLM after).
