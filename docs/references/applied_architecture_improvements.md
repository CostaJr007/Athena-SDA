# Applied Architecture & Model Improvements

**Date:** 2026-07-26  
**Scope:** Summary of mathematical, ML engine, and data pipeline optimizations applied during architectural audits.

## Applied Optimizations

| Audit Item | Implementation in Athena-SDA |
|------------|------------------------------|
| **Real TLE Training Baseline** | `train_and_save_models` prioritizes real historical series from `data/history/epochs` over synthetic data. |
| **Controlled Synthetic Augmentation** | Synthetic maneuvers are restricted to minimal threat-boosting only when positive class samples are scarce. |
| **Geometry Alignment** | Distance to protected assets + cointegration are embedded in feature extraction and `label_features_for_threat`. |
| **Unified Anomaly Metric** | `clip(0.5 - decision_function)` applied uniformly across training, prediction, and operational monitoring. |
| **Asymmetric Risk Cost** | Weighted loss applied in XGBoost: NORMAL = 1 → HOSTILE = 5 to penalize false negatives. |
| **Isolation Forest Contamination** | Calibrated to 0.08 on real historical time series data. |
| **Pre-Report Backtesting** | Walk-forward validation with `pre_peak_noise` detection, relative pairs, and placebo control satellites. |
| **Real Satellite Metadata** | Country of origin and mission purpose integrated into threat scoring; training ingest uses catalog metadata. |
| **Fuzzy Boundary Safety** | Universe inputs in `fuzzy.py` clipped to valid domains; fallback set to neutral 0.5 risk score. |
| **Short Series Kolmogorov Proxy** | Edge-case handling added in `engine.py`: series length &lt; 10 returns 0 with zlib compression fallback. |
| **Cointegration Alignment** | `pair_score._align_series` uses `merge_asof` with ±12h timestamp tolerance. |
| **TLE Age Calculation** | Refactored to `tle_age_hours_at(reference_time)`; walk-forward passes exact `asof`, live mode passes `now`. |
| **Data Quality Gate** | Recomputes TLE age against reference time dynamically to eliminate stale data leakage. |

## Out-of-Scope / Future Enhancements

- Full SGP4 UKF state estimation  
- Deep Neural Networks / Transformer-based trajectory prediction  
- Full Riemannian Ricci Wasserstein metric over 32 dimensions  

## Walk-Forward Validation Rationale

Each fold trains the Isolation Forest **strictly on historical windows** (`window_end < asof - holdout`). Scores along the timeline up to `t_peak` evaluate whether orbital noise/deviation increases **prior** to open-source report publication.
