# Athena-SDA — Military-first quant foundation

**Purpose:** technical anchor for judges / operators / **paper draft** — *what the models detect*, *how they are trained*, and *what is proven*.

## Claims A + B (article-ready)

| Claim | Statement |
|-------|-----------|
| **A** | Past-only quant + IF → **elevated scores** on military-interest cases tied to open-source report anchors |
| **B** | Civil EO placebos under the **same protocol** → **lower scores / near-zero hard hits** |

**Together:** algorithm detects **noise regimes co-occurring with documented atypical military-interest behavior** vs quiet controls — not classified intent, not media-date prediction.

- Methods: `docs/paper/METHODS_AND_CLAIMS.md`  
- Tables: `docs/paper/RESULTS_TABLES.md`  
- JSON: `data/alerts/paper_validation_latest.json`  
- Run: `python scripts/run_paper_validation.py --run-wf`

## Mission (doctrine)

Athena-SDA is a **military-first Space Domain Awareness copilot**, not a consumer sky tracker.

| Role | Meaning | ML role |
|------|---------|---------|
| **asset** | High-value platforms to **protect** | Secondary IF normality anchor; platform-health flags; pair priority target |
| **suspect** | Military interest (SIGINT / recon / dual-use / experimental) | **Primary detection** of persistent micro-trajectory noise |
| **baseline** | Quiet civil EO/meteo | **IF normality training** only — not a threat narrative |

Decorative globe tracks (e.g. commercial constellations for UI) are **not** the training objective.

## Palantir-inspired architecture (not a patent claim)

```
Data (TLE + GFZ)
  → Quant features (engine.py: Hurst, Shannon, CUSUM, Kolmogorov, …)
  → Isolation Forest Inference (past-only, normality = baseline+asset)
  → Priority (XGB weak labels + fuzzy + suspect×asset pair_risk + Kelly)
  → LLM Bob (explains; never rewrites scores)
  → Ontology board (asset | suspect | baseline)
```

Micro-models are versioned in `models/registry.json` (hot-swap metadata).

## What “noise” means (military quant)

**Persistent micro-trajectory / regime noise** on a suspect:

- sustained control (high Hurst)
- irregular ΔSMA / maneuver cadence
- high Shannon / Kolmogorov complexity of altitude changes
- CUSUM structural breaks
- optional cointegration + proximity to protected **assets** (priority channel)

We claim **statistical deviation from normality**, not classified hostile intent.

## Training protocol (remodeled)

| Model | Trained on | Used for |
|-------|------------|----------|
| **Monitor IF** | Past windows of **baseline + asset** only | Daily normality score |
| **Pipeline IF** | History store (train split), weak-label normals | Priority pipeline anomaly |
| **XGBoost** | Weak doctrine labels + temporal purge | Priority tier 0–3 only |
| **Pairs** | suspect × asset | Attention when geometry + coint elevated |

**Key rule:** suspects are **scored** against a baseline they did **not** define. That preserves military detection signal (Luch-class control is not absorbed into “normal”).

## Daily military alert policy

1. Compute `anomaly_score` for all watchlist objects.  
2. **Suspect** + (outlier | relevant Δscore | elevated pair) → `is_military_detection`.  
3. **Asset** + outlier → platform health flag (protect).  
4. **Baseline** → calibration only (`CALIBRATION_BASELINE`), never threat escalate.  
5. Bob may cite open-source cases as *pattern compatible with {source}* — scores immutable.

## Validation (case studies)

Public report anchors (Luch, SY-12, …) are **case studies** for how quant features behave — not forecast targets.

| Subgroup (honest headline) | Hard hit @0.50 | Reading |
|----------------------------|----------------|---------|
| GEO military interest (Luch / SY-12 / Luch-2) | **5/5** | elevated persistent regime |
| Civil EO placebos | **0/7** | quiet controls |
| Active constellation placebos | may hard-hit | station-keeping — not the product focus |

Metrics: `noise_ramp`, `first_fold_hit`, `pre_peak_mean`, `subgroup_geo_interest_vs_civil_eo_placebo`, unique NORADs.

## Mathematical feature blocks

See `src/engine.py` and README §4. Homology uses **proxy** mode by default (`homology_mode` in train meta). RKHS is **excluded** from IF (diagnostic only).

## Reproduce

```bash
python scripts/smoke_test.py
python scripts/run_anomaly_monitor.py train-baseline --holdout-days 1
python -c "from src.models import train_and_save_models; train_and_save_models()"
python scripts/run_anomaly_monitor.py score
python scripts/run_walkforward.py run --threshold 0.50
python scripts/run_feature_ablation.py
powershell -File scripts/sync_frontend_data.ps1
```

## What we do **not** claim

- Classified intent / “espionage detector”  
- Forecast of media dates  
- XGBoost accuracy as SDA proof  
- Generic monitoring of all commercial LEO  

---

*Athena-SDA · military-first quant noise + ML for SDA attention.*
