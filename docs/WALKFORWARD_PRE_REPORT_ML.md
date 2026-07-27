# Walk-Forward Report — Pre-Report Prediction (Current ML Engine)

**Generated:** 2026-07-26T04:57:45 UTC  
**Protocol:** Isolation Forest **past-only training** (3-day holdout) · 14-day step · threshold = 0.50 · hit window ±45 days  
**ML Features:** Current vector with **space weather** (F10.7/Ap/Kp) + math + Kepler · `extract_satellite_features` + `IFOREST_COLUMNS` (34 dimensions)  
**Artifacts:** `data/alerts/walkforward/wf_*.json` · `walkforward_latest.json` · `wf_analysis_new_ml.json`

---

## 1. What This Test Proves (and What it Does Not Prove)

| Claims | Does Not Claim |
|--------|----------------|
| For **public report anchors**, vector noise (IF score) was **elevated prior to / during the report window** for target suspects | That the model had classified intelligence on espionage intent |
| Scientific placebos (TERRA, NOAA-20) **did not** produce a hard hit (score ≥ 0.50 within window) | That XGB accuracy equals ground-truth HOSTILE intent |
| Each fold is trained **strictly without future data** relative to `asof` | That lead-time of 180+ days implies a single maneuver (it reflects sustained anomalous GEO regime) |

**Key Takeaway for Evaluators:**  
> We did not predict the future. We demonstrated that, using **past data only** at each evaluation date, the time series of Luch/Shiyan was **statistically anomalous** months before open-source report publication — whereas civil control satellites in the same timeframe were not.

---

## 2. Global Results (New ML Engine)

| Group | N | Hard Hit (≥0.50 in peak window) | Soft Hit (≥0.45) | Elevated Pre-Peak Noise | Mean Max Anomaly |
|-------|---|----------------------------------|------------------|-------------------------|------------------|
| **Targets of Interest** (Luch-1×3, SY-12, Luch-2) | 5 | **100%** | **100%** | **100%** | **0.603** |
| **Placebo Control** (TERRA 2015/2018, NOAA-20 2023) | 3 | **0%** | 67% (weak soft only) | **0%** | **0.477** |

| Metric | Targets of Interest | Placebo Control |
|--------|---------------------|-----------------|
| Mean Lead-Time (1st hit ≥0.50 before peak) | **~201 days** (median 197) | — |
| Soft Hit Rate | 1.00 | 0.67 |
| Elevated Pre-Peak Noise | **1.00** | **0.00** |

**Interpretation:** The strong discriminator is not a generic soft score (0.45), but **hard hit + elevated pre-peak noise** in target cases vs placebos.

---

## 3. How Noise is Extracted (Theory → Code Function → Signal)

Each fold: 20-epoch window ≤ `asof` → extract features → train IF on windows **&lt; asof − 3d** → `anomaly_score = clip(0.5 − decision_function)`.

| Theory | Code Function | What it Reveals in GEO Inspection |
|--------|---------------|-----------------------------------|
| **Shannon (1948)** | `calculate_shannon_entropy` → `shannon_entropy_sma_30d` | Disorder in \(\Delta a\): maneuvers / irregular station-keeping spread histogram bins |
| **Hurst R/S (1951)** | `calculate_hurst_exponent` → `hurst_exponent_sma` | **Persistence** (\(H \gg 0.5\)): low-thrust / controlled drift (non-Brownian) |
| **Kolmogorov Proxy** | `calculate_kolmogorov_proxy` → `kolmogorov_proxy_7d` | Complexity of U/D/S sequence string (control vs simple Keplerian) |
| **L1-CUSUM** | `calculate_kernel_l1_cusum` → `l1_cusum_sma` | Point in time where the series breaks |
| **Mandelbrot Tail** | `calculate_mandelbrot_tail_anomaly` | Rare tail impulses in \(\Delta a\) |
| **ADF Test** | `calculate_adf_pvalue` | Non-stationarity of the series |
| **ΔSMA / Maneuvers** | `delta_sma_7d_km`, `maneuver_count_30d` | Amplitude and count of orbital shifts |
| **Space Weather (GFZ)** | `space_weather_feature_vector` → `f10_7`, `ap_index` | Contextual drag vs maneuver (secondary in GEO, critical in LEO) |
| **IF Ensemble** | `IsolationForest.decision_function` | Multivariate fusion: “Is this profile rare in past history?” |

**Operational Trigger:** Isolation Forest operating on the complete multivariate vector.  
**Explanatory Attribution:** Hurst + Shannon + ΔSMA (+ Kolmogorov) during high-scoring folds.

---

## 4. Cases of Interest (Public Reports)

### 4.1 Luch / Olymp-K 1 — Intelsat Episode 1 (mid-2015)

| Field | Value |
|-------|-------|
| **Event ID** | `luch1_intelsat_mid2015` |
| **NORAD ID** | 40258 — LUCH (OLYMP-K 1) |
| **Public Anchor (t_peak)** | **2015-04-15** (Intelsat 7/901 colocation ~Apr 2015, Gunter) |
| **WF Window** | 2014-10-01 → 2015-08-01 |
| **Hit / Soft Hit** | **True / True** |
| **Lead-Time (1st score ≥0.50)** | **182 days** → 1st hit on **2014-10-15** |
| **Max Anomaly** | **0.646** @ 2014-10-15 |
| **Elevated Pre-Peak** | **True** |

---

### 4.2 Luch / Olymp-K 1 — Intelsat 905 Season (2015)

| Field | Value |
|-------|-------|
| **Event ID** | `luch1_intelsat_2015` |
| **t_peak** | **2015-09-15** (Intelsat 905 proximity ~24.5°W, Gunter/CSIS) |
| **Hit / Soft Hit** | **True / True** |
| **Lead-Time** | **243 days** → 1st hit **2015-01-15** |
| **Max Anomaly** | **0.599** |
| **Elevated Pre-Peak** | **True** |

---

### 4.3 Luch / Olymp-K 1 — Athena-Fidus (2018)

| Field | Value |
|-------|-------|
| **Event ID** | `luch1_athena_fidus_2018` |
| **t_peak** | **2018-09-01** (Public concern regarding Athena-Fidus / French MoD) |
| **Hit / Soft Hit** | **True / True** |
| **Lead-Time** | **229 days** → 1st hard hit **2018-01-15** |
| **Max Anomaly** | **0.627** @ 2018-11-05 |
| **Elevated Pre-Peak** | **True** |

---

### 4.4 Shiyan-12 01 — GEO RPO 2021–22

| Field | Value |
|-------|-------|
| **Event ID** | `sy12_geo_rpo_2021_22` |
| **NORAD ID** | 50321 — SHIYAN-12 01 |
| **t_peak** | **2022-06-15** (GEO RPO reported by AMOS / SWF) |
| **Hit / Soft Hit** | **True / True** |
| **Lead-Time** | **154 days** → 1st hit **2022-01-12** |
| **Max Anomaly** | **0.573** @ 2022-08-24 |
| **Elevated Pre-Peak** | **True** |

---

### 4.5 Luch-5X / Olymp-K 2 — Trailing 2023

| Field | Value |
|-------|-------|
| **Event ID** | `luch2_trailing_2023` |
| **NORAD ID** | 55841 — LUCH-5X (OLYMP-K 2) |
| **t_peak** | **2023-10-15** (Breaking Defense Oct 2023 — trailing Western assets) |
| **Hit / Soft Hit** | **True / True** |
| **Lead-Time** | **197 days** → 1st hit **2023-04-01** |
| **Max Anomaly** | **0.569** @ 2023-09-02 |
| **Elevated Pre-Peak** | **True** |

---

## 5. Placebo Controls (Same Calendar, Baseline Satellites)

| Event | NORAD | Peak | Hit ≥0.50 | Soft Hit | Elevated Pre-Peak | Max Score |
|-------|-------|------|-----------|----------|-------------------|-----------|
| placebo_terra_2015 | 25994 TERRA | 2015-09-15 | **False** | True (weak) | **False** | 0.478 |
| placebo_terra_2018 | 25994 TERRA | 2018-09-01 | **False** | False | **False** | 0.489 |
| placebo_noaa20_2023 | 43013 NOAA-20 | 2023-10-15 | **False** | True (weak) | **False** | 0.463 |

**Methodological Significance:** Placebos share identical solar/geomagnetic space weather (F10.7/Ap) on the calendar. If solar weather alone caused alerts, placebos would produce hard hits. They **did not**. This proves that the orbital profile (Hurst/Shannon/ΔSMA/IF) is the primary discriminator.

---

## 6. Pre-Report Prediction Summary Table

| Public Case | Report Peak | 1st Athena Detection (score ≥ 0.50) | Lead-Time | Primary Contributing Functions | Hit |
|-------------|-------------|--------------------------------------|-----------|--------------------------------|-----|
| Luch Intelsat mid-2015 | 2015-04-15 | 2014-10-15 | **182 days** | **Hurst**, then Shannon + ΔSMA | Yes |
| Luch Intelsat 2015 | 2015-09-15 | 2015-01-15 | **243 days** | **Hurst 0.94**, Shannon↑, Kolmogorov | Yes |
| Luch Athena-Fidus 2018 | 2018-09-01 | 2018-01-15 | **229 days** | **Hurst 0.96**, Shannon, Kolmogorov | Yes |
| SY-12 RPO 2021–22 | 2022-06-15 | 2022-01-12 | **154 days** | Hurst + Shannon + Kolmogorov | Yes |
| Luch-2 Trailing 2023 | 2023-10-15 | 2023-04-01 | **197 days** | **Shannon 2.1** + Hurst | Yes |
| TERRA / NOAA Placebos | (same calendar) | — | — | Scores &lt; 0.50 in window | **No** |

---

## 7. Explicit Boundaries & Limitations

1. **Sustained Lead-Time:** Long lead-times often reflect a satellite operating in an anomalous regime from `t_start`, rather than a single discrete maneuver spike.
2. **CUSUM Sensitivity:** `l1_cusum_sma` is low in certain GEO inspection folds; Shannon, Hurst, and IF provide primary detection strength.
3. **Pair Risk:** Pair risk acts as an operational weighting proxy rather than exact SGP4 TCA.
4. **Space Weather:** Space weather is integrated into feature vectors; its primary role is distinguishing LEO atmospheric drag from maneuvers.

---

## 8. Execution & Reproduction Commands

```bash
python scripts/run_walkforward.py run --step-days 14 --holdout-days 3 --threshold 0.50
python scripts/run_walkforward.py summary
```

| Artifact File | Description |
|---------------|-------------|
| `data/alerts/walkforward/walkforward_latest.json` | Global metrics and summary per event |
| `data/alerts/walkforward/wf_<event>.json` | Full folds and feature vectors per `asof` |
| `data/alerts/walkforward/wf_analysis_new_ml.json` | First hit extraction and feature movers |
| `data/catalog/events_walkforward.json` | Report anchors and open-source references |
| Documentation Report | `docs/WALKFORWARD_PRE_REPORT_ML.md` |

---
*Athena-SDA — Walk-forward validation report.*
s por evento |
| `data/alerts/walkforward/wf_<event>.json` | Folds completos + features por asof |
| `data/alerts/walkforward/wf_analysis_new_ml.json` | Extração 1º hit / movers |
| `data/catalog/events_walkforward.json` | Âncoras e fontes |
| Este relatório | `docs/RELATORIO_WALKFORWARD_PRE_REPORT_ML_NOVO.md` |

---

*Walk-forward executado com o ML pós–space weather / hybrid / protocolo série. Duração ~13,5 min. Exit code 0.*
