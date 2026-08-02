# Athena-SDA — Quantitative foundation and validation

**Purpose:** Technical anchor for judges and paper draft — what the models detect, how they are trained, and what is validated.

## Claims A + B

| Claim | Statement |
|-------|-----------|
| **A** | Past-only quant + Isolation Forest yields elevated scores on military-interest cases at open-source report anchors |
| **B** | Civil EO placebos under the same protocol yield lower scores / near-zero hard hits |

Together: the pipeline detects **elevated noise regimes** on interest cases relative to quiet controls under a locked past-only protocol.

- Methods: `docs/paper/METHODS_AND_CLAIMS.md`  
- Tables: `docs/paper/RESULTS_TABLES.md`  
- LaTeX article: `docs/paper/athena_sda_article.tex`  
- JSON: `data/alerts/paper_validation_latest.json`  
- Run: `python scripts/run_paper_validation.py --run-wf`

## Doctrine

| Role | Meaning | ML role |
|------|---------|---------|
| **asset** | High-value platforms to protect | Secondary IF normality anchor; pair target |
| **suspect** | Military interest (SIGINT / recon / dual-use / experimental) | Primary micro-anomaly / noise detection |
| **baseline** | Quiet civil EO/meteo | IF normality training |

Decorative globe tracks are not the training objective.

## Architecture

```
Data (TLE + GFZ)
  → Quant features (Hurst, Shannon, CUSUM, Kolmogorov, space weather, …)
  → Isolation Forest (past-only; normality = baseline+asset)
  → Priority (XGB weak labels + fuzzy + pair_risk + Kelly)
  → Bob explains scores
  → Ontology board (asset | suspect | baseline)
```

Micro-models: `models/registry.json`.

## Training protocol

| Model | Trained on | Used for |
|-------|------------|----------|
| Monitor IF | Past windows of baseline+asset | Daily normality / anomaly score |
| Pipeline IF | History store (train split) | Priority pipeline anomaly |
| XGBoost | Weak labels + temporal purge | Priority tiers 0–3 |
| Pairs | suspect × asset | Attention when geometry + cointegration elevated |

## Daily alert policy

1. Compute `anomaly_score` for all watchlist objects.  
2. **Suspect** + (outlier | relevant Δscore | elevated pair) → military detection flag.  
3. **Asset** + outlier → platform health flag.  
4. **Baseline** → calibration scores on the board.  
5. Bob cites open-source cases when relevant; scores remain fixed.

## Walk-forward honesty metrics

- `first_fold_hit` — elevated from first scorable fold  
- `noise_ramp` — late − early pre-peak mean  
- `pre_peak_anomaly_mean` / max  
- `p95_max_anomaly_placebo`  
- Unique NORAD counts  

## Reproduce

```bash
python scripts/smoke_test.py
python scripts/run_anomaly_monitor.py train-baseline --holdout-days 1
python -c "from src.models import train_and_save_models; train_and_save_models()"
python scripts/run_feature_ablation.py
python scripts/run_walkforward.py run --threshold 0.50
powershell -File scripts/sync_frontend_data.ps1
```
