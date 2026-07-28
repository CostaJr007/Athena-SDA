# Full ML Report — Machine Learning, Databases, Mathematics & Weighting  
## Athena-SDA (Space Domain Awareness)

**Version:** 2026-07-26  
**Scope:** Architecture of the machine learning pipeline, data provenance, orbital noise detection methodology, space weather and relative geometry weighting, and explicit boundaries.

---

## 0. Executive Summary

Athena-SDA **does not predict the future** and **does not invent space tracking data**. It operates as follows:

1. **Ingests real TLE data** from public objects (military-first watchlist, 24 NORAD IDs).  
2. **Extracts a mathematical noise vector** (Shannon, Hurst, Kolmogorov proxy, CUSUM, Mandelbrot tail, ADF, RKHS, topology, etc.) over sliding windows of each satellite's time series.  
3. **Injects real space weather metrics** (F10.7, Ap, Kp, SN + rolling 7d) into the feature vector at window timestamps to distinguish solar drag from intentional maneuvers.  
4. **Trains Isolation Forest on past series history** (holdout: today's data is excluded from the baseline).  
5. **Evaluates the latest window** against the past baseline → yields `anomaly_score`.  
6. **Weights operational attention** using suspect×asset pairs (distance + cointegration) and, in parallel, classifies using XGBoost + Mamdani Fuzzy + Kelly Criterion (doctrine layer, weak labels).  
7. **Validates lead-time** via walk-forward analysis against open-source report anchors (e.g. Luch/Olymp-K), without look-ahead leakage.

| Statement for Evaluation | Status |
|--------------------------|--------|
| Orbital data is authentic | **Yes** (TLE history + CelesTrak) |
| Solar/geomagnetic weather is authentic | **Yes** (GFZ Potsdam + NOAA optional) |
| Anomaly detection = series deviation | **Yes** (IF past-train / present-score) |
| HOSTILE labels = ground-truth intelligence | **No** — heuristic / operational doctrine |
| Engine core derived from IBM noise paper | **No** (see §11) |

---

## 1. Machine Learning Pipeline Architecture

```
┌──────────────────────────────────────────────────────────────────────────┐
│  DATA SOURCES                                                            │
│  TLE history (HF space-track mirror) + Daily CelesTrak CATNR             │
│  Space weather GFZ (F10.7/Ap/Kp/SN) ± NOAA F10.7                         │
│  Catalog watchlist (roles: asset / suspect / baseline)                   │
└────────────────────────────┬─────────────────────────────────────────────┘
                             ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  20-EPOCH WINDOW per satellite (Keplerian time series)                   │
│  extract_satellite_features()                                            │
│    • Kepler + Δa/Δi + maneuver counts (CUSUM spikes)                     │
│    • Math: Shannon, Kolmogorov, Hurst, Mandelbrot, ADF, L1-CUSUM…        │
│    • Geometry: distance to assets, cointegration, Łukasiewicz            │
│    • Space weather at window timestamp (12 features)                     │
└────────────────────────────┬─────────────────────────────────────────────┘
                             ▼
        ┌────────────────────┴────────────────────┐
        ▼                                         ▼
 Isolation Forest (34-dim)                 XGBoost (38-dim)
  baseline = PAST series                    + anomaly_score
  score = LATEST window                     classes 0–3 (weak labels)
  anomaly_score ∈ [0,1]                     asymmetric weights HOSTILE↑
        │                                         │
        └────────────────────┬────────────────────┘
                             ▼
              Suspect×Asset Pairs + Fuzzy Mamdani + Kelly Criterion
              attention = 0.45·anom + 0.55·pair_risk
              DQ gate: Stale TLE → UNRELIABLE (does not escalate to HOSTILE)
                             ▼
              Alerts JSON/CSV + risk board + walk-forward validation
```

**Design Principle (Math-First):**  
Machine Learning does **not** train directly on raw TLE parameters. It learns the **joint distribution of noise feature vectors** extracted by the mathematical engine from real TLE series. Isolation Forest computes: *“Does this current window conform to the historical baseline of this series and space weather environment?”*

---

## 2. Databases — Provenance and Size

### 2.1 Orbit (TLE / elements)

| Item | Value |
|------|--------|
| Store | `data/history/epochs.parquet` (+ CSV) |
| Volume | **~249,558** epochs |
| Objects | **24** NORADs (watchlist) |
| Interval | **2014-01-01 → 2026-07-25** (UTC) |
| Fields | `norad_id`, `timestamp`, SMA, e, i, RAAN, n, bstar, `tle_age_hours`, `source` |

**Provenance chain:**

1. **Historical seed** — Hugging Face dataset  
   `juliensimon/space-track-tle-history`  
   (annual parquets filtered by watchlist; progress in `data/history/seed_progress.json`).  
   Nature: public TLE repository in the style of **Space-Track / 18 SPCS** (research mirror, not the classified API).

2. **Daily ingest** — **CelesTrak** GP by `CATNR`  
   `https://celestrak.org/NORAD/elements/gp.php?CATNR=…&FORMAT=csv`  
   Appends to the right of the series (“today’s” data).

3. **Catalog** — `data/catalog/watchlist.json`  
   NORADs validated on CelesTrak GP; roles **asset / suspect / baseline** are **project doctrine**, not an official threat label.

**Physics:** SMA ~6,650–42,500 km, mean motion ~1–16 rev/day — consistent with real LEO→GEO, not mock series.

### 2.2 Space weather (solar / geomagnetic)

| Item | Value |
|------|--------|
| Store | `data/space_weather/daily.parquet` |
| Volume | **~4,589** days (slice 2014–2026; GFZ archive goes back to 1932) |
| Primary source | **GFZ Potsdam** — `Kp_ap_Ap_SN_F107_since_1932.txt` |
| Auxiliary source | **NOAA SWPC** JSON F10.7 (recent refresh) |
| Module | `src/space_weather.py` |

Daily indices: F10.7 obs/adj, Ap, mean Kp, sunspot number + 7-day rolling features.

### 2.3 Validation events (not training labels)

`data/catalog/events_walkforward.json` — anchors from **open-source reports** (Gunter, CSIS, press) for Luch/Olymp-K, Shiyan, placebos (e.g. TERRA).  
Used only in **walk-forward**, never as XGBoost training `y_true`.

### 2.4 What does **not** count as ground truth

| Artifact | Nature |
|----------|--------|
| Labels NORMAL…HOSTILE | Heuristics in `label_features_for_threat` |
| Watchlist roles | Athena operational prioritization |
| XGB accuracy ~95% | Consistency with the heuristic, **not** espionage ground truth |
| Synthetic (`generate_mock_tle_history`) | Fallback / rare boost; current training = **`history_store`** |

---

## 3. Feature Vector — Size and Composition

### 3.1 Dimensions

| Set | Dimension | Content |
|-----|-----------|---------|
| `FEATURE_COLUMNS` | **37** | Kepler + math + SW + multi-object |
| `IFOREST_COLUMNS` | **34** | 37 − {dist, coint, Łukasiewicz} |
| `XGB_COLUMNS` | **38** | 37 + `anomaly_score` |
| Space weather | **12** | ~35% of IF — weather is first-class |

### 3.2 Vector blocks

**A. Instantaneous Kepler (5)**  
`semi_major_axis_km`, `eccentricity`, `inclination_deg`, `raan_deg`, `mean_motion_rev_per_day`

**B. Temporal dynamics (4)**  
`delta_sma_7d_km`, `delta_sma_30d_km`, `delta_inc_30d_deg`, `maneuver_count_30d`  
(maneuvers ≈ L1-CUSUM peaks in sub-windows)

**C. Mathematical noise engine (12)**  
Shannon, Kolmogorov proxy, Hurst, Mandelbrot tail, ADF p-value, Williams threat, L1-CUSUM, spectral RKHS, Chern–Simons proxy, Ricci mean, H0/H1 persistence, `tle_age_hours`

**D. Space weather (12)** — see §6  
`f10_7`, `f10_7_adj`, `ap_index`, `kp_mean`, `sunspot_number`, rolling 7d, `geomagnetic_storm`, `space_weather_available`

**E. Multi-object / “routes” (3)** — XGB only in full training  
`min_distance_to_military_km`, `cointegration_pvalue`, `lukasiewicz_implication`

---

## 4. Mathematical Models — How Noise Is Described

Implementation: `src/engine.py`. Foundation: `docs/references/mathematical_foundation.md` and `docs/references/full_mathematical_framework.md`.

### 4.1 Why “noise” rather than “position”

TLE is already a filtered/published state. The tactical signal of interest is a **regime change** in the series: maneuver, shadowing, atypical station-keeping, or drag. Each proxy responds to a **type** of noise:

| Proxy | Idea | Orbital interpretation |
|-------|------|------------------------|
| **Shannon entropy** (1948) | Disorder of \(\Delta a\) in bins | Maneuver/control spreads \(\Delta a\); stable Kepler concentrates |
| **Kolmogorov proxy** (1965) | zlib compression of U/D/S tokens | “Simple” trajectory compresses; complex control resists |
| **Hurst** R/S (1951) | Long-range persistence | \(H>0.5\): trend (low thrust); \(H\approx0.5\): noise; \(H<0.5\): reversion (SK) |
| **Kernelized L1-CUSUM** | When the series breaks | Localizes *regime change* in time |
| **Mandelbrot (tail)** | Extremes / power laws | Rare jumps vs Gaussian noise |
| **ADF** | Stationarity | Break in stationarity ⇒ process changed |
| **Spectral RKHS** | RBF kernel distance vs reference | Anomaly in embedded feature space |
| **Ricci (Ollivier proxy)** | Local curvature between neighborhoods | Geometric tactical approximation |
| **Homology H0/H1** | Topology of the 3D cloud | Closed orbit vs escape/spiral |
| **Chern–Simons proxy** | Helicity \(\mathbf{v}\cdot\boldsymbol{\omega}\) | Non-conservative force (propulsion) |
| **Engle–Granger cointegration** | Coupling of two SMAs | Shadowing / pair pursuit |
| **Łukasiewicz** | Fuzzy implication \(p\to q\) | Logic of “if close then threat…” |

### 4.2 Layered noise detection (not a single number)

1. **Description** — math features turn the window into a “noise profile”.  
2. **Distribution** — Isolation Forest learns the envelope of **historically normal** profiles.  
3. **Current point** — latest window becomes `anomaly_score = clip(0.5 − decision_function)`.  
4. **Temporal relevance** — \(\Delta\) score vs yesterday’s report (day-to-day change).  
5. **Route geometry** — pair_risk (distance + coint) raises attention even if IF is only “medium”.  
6. **Weather** — SW in the vector + soft-suppress of HOSTILE under storm with light \(\Delta a\).  
7. **DQ** — stale/gap/absurd TLE jump ⇒ `UNRELIABLE_DATA` (catalog noise ≠ tactics).

### 4.3 Daily protocol (series vs today)

```
SERIES up to D−holdout  ──train──►  IF baseline  (= normal + historical weather)
LATEST window (D0)      ──score──►  anomaly_score
Δ vs yesterday          ──filter─►  CHANGE_RELEVANT if jump is relevant
```

- `holdout_days=1` (default): **yesterday and the past train; today only compares.**  
- **Hybrid** sampling: half long series + half recent tip (coverage ~2014→2026 on last monitor train).  
- Doc: `docs/DAILY_DETECTION_PROTOCOL.md`.

---

## 5. Machine Learning Models

### 5.1 Isolation Forest (primary “noise vs normal” channel)

| Aspect | Main pipeline | Daily monitor |
|--------|---------------|---------------|
| File | `models/isolation_forest.joblib` | `isolation_forest_monitor.joblib` |
| Features | 34 (IFOREST) | 34 (IFOREST) |
| Contamination | 0.08 | 0.08 |
| Estimators | 200 | 200 |
| Training | ~960 history_store windows | ~1440 hybrid windows, cutoff D−1 |
| Score | `clip(0.5 − decision_function)` | same |

**Idea:** isolate rare points in feature space without needing a HOSTILE label.  
“Normal” includes Keplerian variation **and** solar climates already seen in the past.

### 5.2 XGBoost (operational classification layer)

| Aspect | Value |
|--------|--------|
| Classes | 0 NORMAL, 1 ANOMALOUS, 2 SUSPECT, 3 HOSTILE |
| Features | 38 (vector + anomaly_score) |
| Hyperparameters | 140 trees, depth 5, lr 0.08, multi:softprob |
| Sample weights | {0:1, 1:1.5, 2:3, 3:5} — HOSTILE errors cost more |
| Labels | `label_features_for_threat` (dist, Δa, Hurst, coint, anomaly, **weather**) |
| Internal metrics (last train) | acc ≈ 0.95, macro-F1 ≈ 0.87, logloss ≈ 0.15 |
| Training source | **`history_store`** (not full synthetic) |

**Explicit limitation:** test-set metrics measure agreement with the **heuristic**, not classified ground truth. For evaluation, the honest detection channel is **IF + walk-forward**, not XGB accuracy.

### 5.3 Fuzzy Mamdani + Kelly

- **Fuzzy** (`src/fuzzy.py`): fuses distance, anomaly, purpose into a linguistic score (NORMAL…HOSTILE), with clamp and 0.5 fallback if no rule fires.  
- **Kelly** (`engine.calculate_kelly_allocation`): allocates “attention/analysis budget” \(f^* \propto\) probability × purpose severity.

### 5.4 Pairs and “routes” (operational geometry)

`src/pair_score.py` + `src/orbital.py`:

- Approximate minimum distance suspect→asset (Kepler proxy, **not** full SGP4 TCA).  
- Cointegration of aligned SMAs (`merge_asof` / tails).  
- `pair_risk` fuses geometry + temporal coupling.  
- **Final attention:**  
  \[
  \text{attention} = 0.45\cdot\text{anomaly\_score} + 0.55\cdot\text{pair\_risk}
  \]
- Strong CRITICAL / ELEVATED pair can mark `PAIR_ELEVATED` even if IF alone does not pass thr 0.55.

This is the **route/proximity vs series noise** weighting.

---

## 6. Weighting Solar Weather vs Orbit / Routes

### 6.1 Why solar enters the same vector

LEO drag rises with **F10.7** and **Ap/Kp** storms. Without SW, \(\Delta a\) + Shannon + CUSUM under a storm look like a maneuver. With SW, IF sees the **same \(\Delta a\) under different climates** and learns regimes.

### 6.2 The 12 solar/geomagnetic features

| Feature | Role in implicit weighting |
|---------|----------------------------|
| `f10_7`, `f10_7_adj` | Solar activity level (thermospheric density) |
| `ap_index`, `kp_mean` | Geomagnetic storm of the day |
| `sunspot_number` | Cycle context |
| `*_delta_7d`, `*_mean_7d`, `ap_max_7d` | Recent dynamics (not only a snapshot) |
| `geomagnetic_storm` | Flag Ap_max_7d ≥ 30 |
| `space_weather_available` | 1 = real weather; 0 = quiet defaults |

Lookup: **UTC date of the window** (`reference_time` in walk-forward; now in live).

### 6.3 **Explicit** weighting in labels (doctrine)

In `label_features_for_threat`:

- If `geomagnetic_storm` or Ap≥30 or F10.7≥180 (**high_drag_climate**):  
  - Δa thresholds for HOSTILE/SUSPECT/ANOMALOUS **rise**;  
  - light Δa + far from assets → tends to **NORMAL** (drag).  
- Critical geometry (dist < 25 km + coint / anomaly) **can still** be HOSTILE — weather does not “absolve” obvious RPO.

### 6.4 **Implicit** weighting in IF/XGB

There is no manual weight “30% solar / 70% Kepler”. Models **learn** importances from data. The design ensures:

- IF **includes** SW (weather is part of normal);  
- IF **excludes** dist/coint (so baseline is not “always near = anomalous” without multi-object context);  
- XGB **includes** SW + geometry + anomaly (full operational classification).

### 6.5 Attention fusion diagram

```
anomaly_score (series + math + SW)     pair_risk (route/proximity)
              0.45                              0.55
                 \                              /
                  \_____ attention_score ______/
                              |
              + DQ gate + status (ANOMALY / PAIR_ELEVATED / CHANGE_RELEVANT)
                              |
                         risk board / Kelly
```

---

## 7. How Training Was Done (Numbers)

### 7.1 IF + XGB pipeline (`train_and_save_models`)

1. Load history store → 20-epoch windows, step 5, last ~40/sat.  
2. Inject catalog country/purpose, dist to assets, coint, **day SW**.  
3. Weak labels; if almost no HOSTILE, light synthetic threat boost (last run: **did not** dilute — history sufficed).  
4. Fit IF on “normal” windows; produce unified `anomaly_score`.  
5. Light relabel with anomaly; fit XGB with class weights.  
6. Save `models/*.joblib` + `training_metrics.json`.

**Last state:** n_samples=960, n_features=38, `training_source=history_store`.

### 7.2 Monitor (`train-baseline` + `score`)

1. Cutoff = now − 1 day.  
2. Hybrid sample on the series → IF.  
3. Score only latest window; Δ vs `anomalies_{yesterday}.json`.  
4. Pairs + report `data/alerts/anomalies_YYYY-MM-DD.json`.

**Last state:** 1440 windows, window_end coverage **2014-01-04 → 2026-07-25**.

### 7.3 Walk-forward (`src/walkforward.py`)

At each `asof` along an event:

- IF trained **only** on windows ending < asof − holdout;  
- score the target;  
- hit if score is elevated **before** the report `t_peak`;  
- placebos (e.g. TERRA) control generic false positives.

This answers “did we detect noise **before** the report?” without contaminating training.

---

## 8. End-to-End Detection Flow (Conceptual Example)

1. **Series** for YAOGAN-29 with thousands of real TLEs 2014–2026.  
2. **Baseline** learns Shannon/Hurst/Δa profiles under various F10.7/Ap.  
3. **Today** a new CelesTrak TLE arrives → latest 20-epoch window.  
4. Features: if Δa rises **with** high Ap, SW contextualizes; if Δa rises **with** quiet weather and high Hurst, IF raises score.  
5. **Pair** vs COSMO-SkyMed: low dist + coint → high pair_risk.  
6. **attention** rises; status may be ANOMALY or PAIR_ELEVATED.  
7. Analyst sees the board — not “courtroom proof”, but **SDA priority grounded in public data**.

---

## 9. What Is Simulated and What Is Not (Transparency)

| Component | Real? |
|-----------|-------|
| TLE history + daily | **Real** (public sources) |
| F10.7 / Ap / Kp | **Real** (GFZ) |
| Math features | **Derived** from real data (not invented) |
| IF anomaly | **Model** trained on real data |
| XGB labels | **Heuristic** |
| Watchlist roles | **Doctrine** |
| Mock TLE | Only if history missing (not the current path) |
| Pair distance | **Proxy** (not official TCA) |

---

## 10. How to Present to Judges (Short Script)

> “We use real public orbital elements (Space-Track-style history + CelesTrak) and solar/geomagnetic indices from GFZ.  
> We transform each series window into a mathematical noise vector (Shannon, Hurst, CUSUM, etc.) **plus** that day’s weather.  
> Isolation Forest learns normal **in the past**; today’s point is compared — not re-trained on the same day.  
> Asset proximity (routes) and solar weather enter attention weighting and drag-vs-maneuver rules.  
> We do not claim classified ground-truth of hostile intent: we claim **deviation detection grounded in real data** and walk-forward validation on open-source cases such as Luch.”

---

## 11. IBM Studies, Noise, and What Was (or Was Not) Researched

### 11.1 Direct answers

| Question | Answer |
|----------|--------|
| Was the Athena engine **implemented from** IBM noise papers? | **No.** |
| Was IBM mentioned in project planning? | **Yes, as an optional theoretical reinforcement item** (block 0.6 in the data/ML organigram), **not as the code base.** |
| Was a deep review of IBM orbital-noise literature done in this session? | **Not as a design axis.** A **targeted mapping** of IBM’s open-source SSA work was done (below). |
| Is there IBM work **relevant** to SDA/ML? | **Yes** — Space Tech SSA line (with Moriba Jah / UT Austin), open-source `IBM/spacetech-ssa`. |

### 11.2 What IBM has in SSA (external context)

- Open-source project **IBM Space Tech – SSA** (`ibm.github.io/spacetech-ssa`, GitHub `IBM/spacetech-ssa`): ML playground for LEO SSA (ASO trajectory prediction, conjunctions, etc.), historically partnered with Moriba Jah research.  
- Typical IBM SSA focus: **predict where objects are / will be**, conjunctions, experimental ML pipeline — **not** Athena’s math-first stack (Shannon–Hurst–CUSUM–RKHS–TDA).  
- Open-source SSA + KubeSat announcements (~2020) to “democratize” space tech.

### 11.3 Where Athena’s theoretical foundation **came from**

| Line | Origin in the project |
|------|------------------------|
| Shannon, Kolmogorov, Hurst, Mandelbrot, CUSUM, ADF, cointegration | Classical literature + `docs/references/mathematical_foundation.md` |
| RKHS / Ricci / homology / Chern–Simons proxies | Project quant framework (implementable proxies, not IBM papers) |
| Multi-stage / COP / DAG architecture | **Palantir** inspiration (patents mapped in `docs/references/palantir_patents.md`) — **not** a Palantir product |
| Generic SSA + ML | State of the art (SSA/ML surveys, anomaly detection practice) |
| IBM | Listed as **optional future bibliography** in the organigram; **not** a founding citation of `engine.py` |

### 11.4 Recommended academic honesty

If a judge asks “did you use IBM’s studies?”:

> “We know the IBM Space Tech SSA line (open-source focused on LEO trajectory prediction).  
> Our core is **different**: information/stochastic/topology features on real TLE series + past-train Isolation Forest, with GFZ weather and geometric pairs.  
> IBM SSA and Athena are **complementary**, not the same paper reimplemented.  
> IBM/quant/fractal papers were in the theoretical reinforcement backlog (item 0.6), not on the critical implementation path.”

### 11.5 If you want to approach IBM later (optional)

- Benchmark prediction/orbital error in the spacetech-ssa style vs our **change** detector.  
- Cite Jah / SSA literature on a “state of the art” slide.  
- **Do not** replace the math stack with a black box just because it is IBM.

---

## 12. Key Repository Files

| Area | Path |
|------|------|
| Math features | `src/engine.py` |
| Extract + train + labels | `src/models.py` |
| Feature schema | `src/config.py` |
| Space weather | `src/space_weather.py` |
| Daily monitor | `src/anomaly_monitor.py` |
| Pairs / routes | `src/pair_score.py`, `src/orbital.py` |
| Walk-forward | `src/walkforward.py` |
| TLE store | `src/tle_store.py` |
| Fuzzy / Kelly | `src/fuzzy.py` |
| CLI | `scripts/run_anomaly_monitor.py` |
| Math docs | `docs/references/mathematical_foundation.md` |
| Daily protocol | `docs/DAILY_DETECTION_PROTOCOL.md` |
| Pre-report demo | `docs/PRE_REPORT_PREDICTION_DEMO.md` |
| SW in ML | `docs/references/space_weather_ml.md` |
| This report | `docs/FULL_ML_REPORT_ATHENA_SDA.md` |

---

## 13. Reproduction Commands

```bash
# Weather (GFZ)
python scripts/run_anomaly_monitor.py seed-space-weather --force --start-year 2014

# Baseline on the series (past) + score today
python scripts/run_anomaly_monitor.py train-baseline --holdout-days 1 --sample-mode hybrid
python scripts/run_anomaly_monitor.py score

# Full daily cycle
python scripts/run_anomaly_monitor.py run-daily

# Retrain IF+XGB pipeline
python -c "from src.models import train_and_save_models; train_and_save_models()"

# Walk-forward (pre-report validation)
python scripts/run_walkforward.py
```

---

## 14. Conclusions

1. **Data:** orbital and solar sources are **real and traceable**; doctrine and labels are **explicit and weak**.  
2. **ML:** math-first → IF (noise vs normal on the series) → XGB/fuzzy/Kelly (priority) → pairs (routes).  
3. **Noise:** multi-proxy classical + IF distribution + daily Δ + DQ.  
4. **Solar vs routes:** SW in the vector and in drag labels; routes via pair_risk with weight 0.55 on attention.  
5. **IBM:** relevant in the open-source SSA ecosystem, **not** the implemented foundation of Athena’s noise engine; optional theoretical backlog.  
6. **For judges:** sell **deviation detection on public data**, not “space warfare accuracy”.

---

*Document generated for the Athena-SDA project. Suitable for pitch, repository, and session handoff.*
