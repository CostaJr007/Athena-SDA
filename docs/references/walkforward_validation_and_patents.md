# Walk-Forward Historical Validation & Palantir Patent Architecture Reference

**Athena-SDA** · Historical temporal validation of documented maneuvers/RPO · Architecture inspired by public Palantir patent publications.

> **Objective:** Validate that the **Math → ML stack** detects behavioral anomaly signatures *prior to or during* publicly reported event windows — operating strictly without look-ahead leakage.

---

## 1. Core Walk-Forward Methodology (Expanding Window)

```
Timeline →

[===== TRAIN on past only =====] | gap | [SCORE window] | [EVENT documented]
                                 ^                      ^
                            train_cutoff            evaluation_end
```

### Execution Rules:

1. **Strict Holdout:** At each fold \(t\), Isolation Forest (and model calibration) observes data strictly prior to `timestamp < t_cutoff`.
2. **Feature Isolation:** Mathematical features (Shannon, Hurst, CUSUM, cointegration) are computed using time series bounded by the score window — never using future TLE records.
3. **Public Anchors:** Open-source reporting milestones (CSIS/SWF/SpaceNews) define temporal evaluation anchors.
4. **Validation Criteria:** Successful detection is defined by coherent elevation in anomaly scores and mathematical features around event windows relative to placebo controls.

---

## 2. Tested Hypotheses

| ID | Hypothesis | Expected Math Signal | ML / Pair Score |
|----|------------|----------------------|-----------------|
| **H1** | Deliberate maneuver increases altitude disorder | Shannon↑, Kolmogorov↑, CUSUM change-point | anomaly_score↑ |
| **H2** | Low-thrust / persistent drift | Hurst \(> 0.5\) | Anomaly vs passive baseline |
| **H3** | Temporal shadowing / tracking | **Cointegration** p-value↓ between suspect & target | pair_score↑ |
| **H4** | Rendezvous & Proximity Operations (RPO) | Min distance↓, TCA geometry | Fuse + Kelly attention↑ |
| **H5** | Catalog noise / stale data | DQ score↓, TLE age↑ | Gate: do **not** classify as HOSTILE |

---

## 3. Documented Public Anchors for Walk-Forward Validation

| Event Key | Object(s) | Public Window (approx.) | Type | Target / Context | Key Features |
|-----------|-----------|-------------------------|------|------------------|--------------|
| `luch1_intelsat_2015` | Luch/Olymp-K 1 (#40258) | 2015–2019 GEO maneuvers | GEO Shadowing | Intelsat / Commercial slots | Cointegration + Δlong + CUSUM |
| `luch1_athena_fidus_2018` | Luch-1 | ~2018 | GEO Proximity | Athena-Fidus (FR) | Distance + maneuver count |
| `luch2_geo_2023` | Luch-5X / Olymp-K 2 (#55841) | 2023–2025 | GEO Shadowing | Western GEO assets | Same as Luch-1 |
| `sy12_usa_geo` | SY-12 01/02 (#50321/50322) | 2021–2022+ | GEO RPO | USA orbital objects | Pair distance + TCA |

### Event catalog extensions

Add event **extensions** in the validation JSON (without polluting the operational watchlist if it does not fit).

Target file:

```
data/catalog/events_walkforward.json
```

Suggested schema:

```json
{
  "events": [
    {
      "id": "luch2_geo_2023",
      "norad_ids": [55841],
      "pair_with": null,
      "t_start": "2023-03-12",
      "t_peak": "2023-10-01",
      "t_end": "2024-06-01",
      "type": "shadowing_geo",
      "sources": ["Breaking Defense 2023", "SWF Counterspace"],
      "expected_signals": ["cusum", "shannon", "maneuver_count"]
    }
  ]
}
```

---

## 4. Walk-Forward Protocol (Steps)

### 4.1 Expanding window (recommended for demo)

For each event \(E\) with anchor \(t_{peak}\):

1. **Minimum history:** require ≥ 60–90 days of NORAD epochs (and pair, if any) **before** \(t_{peak}\).
2. **Folds:** every \(step\) days (e.g. 7 or 14):
   - `train_end = t_i - holdout_days` (holdout 1–7 d avoids leakage from the current window)
   - Train IF **only** on feature windows with `window_end < train_end` (prefer baseline + assets + non-event suspects, or full fleet *before* \(t_i\)).
   - Score windows with `window_end ∈ [t_i - W, t_i]`.
3. **Per-fold metrics:**
   - suspect `anomaly_score(t)`
   - Tier A features (Shannon, Hurst, CUSUM, Kolmogorov)
   - if pair: `coint_pvalue`, `min_distance_km`, `tca`
   - `data_quality` (do not count fold if unreliable)
4. **Lead-time:** smallest \(t\) with `anomaly_score ≥ θ` **and** DQ ok, relative to \(t_{peak}\) (days of anticipation).
5. **Control (placebo):** same protocol on civil **baseline** (e.g. TERRA, NOAA-20) in the same epoch — reference false-alarm rate.

### 4.2 Validation metrics (what to report at the hackathon)

| Metric | Definition | Pitch use |
|--------|------------|-----------|
| **Hit@event** | Score ≥ θ in \([t_{peak}-Δ, t_{peak}+Δ]\) | “we detected the documented window” |
| **Lead-time** | days between first stable alert and \(t_{peak}\) | “anticipation relative to the report” |
| **Feature attribution** | which math tools crossed threshold | “not a black box — Shannon/CUSUM/…” |
| **Pair confirmation** | coint/dist confirm single-sat | “shadowing signature, not solo maneuver only” |
| **FPR baseline** | alerts on stable civils in the same fold | honesty / noise |

**Do not sell:** “we detect spies with 99% accuracy”.  
**Sell:** “walk-forward on open-source events; micro-models + math; insight-first alert”.

### 4.3 Where this lives in code (roadmap)

| Module | Role |
|--------|------|
| `data/catalog/events_walkforward.json` | public anchors |
| `src/walkforward.py` | folds, train cutoff, score series |
| `scripts/run_walkforward.py` | CLI: one event or batch |
| `data/alerts/walkforward_{event}.json` | temporal curve + lead-time |
| reuses | `engine.py`, `anomaly_monitor.build_feature_windows`, `catalog` |

Flow:

```
HF history (2y+) → epochs
     → walkforward folds
          → IF fit (past only)     [hot-swappable micro-model per fold]
          → math features + score
          → report vs event anchor
```

---

## 5. Patents → Extract Maximum Value (Technology Map)

We do not copy a Palantir product. We **translate** patented mechanisms into SDA + TLE + math.

### 5.1 Inheritance matrix (maximum coverage)

| Patent | Original mechanism | In Athena (implemented / to extract) | Walk-forward |
|--------|-------------------|--------------------------------------|--------------|
| **US 2023/0050870 A1** Meta-Constellation | DMP (ground) + AIP (edge); **micro-models**; hot-swap; **insight-first** downlink | DMP = train/store (`train-baseline`, joblib); AIP = daily score; micro-models = IF + XGB + Fuzzy + (future) pair scorer; downlink = `anomalies_*.json` not TLE dump | Each fold = **hot-swap** of IF baseline over time (DMP re-fit → AIP score) |
| **US 2024/0394296 A1** LLM + Geospatial | 4 stages: physical filter → quant ML → LLM thesis → score | ① DQ/bounds ② math+IF+XGB ③ Bob description ④ fuse/recommendation | Bob **only** comments folds/events **after** quant; never defines the score |
| **US 12,657,514 B2** Sensor correlation | Data API + Inference API + **DAG** | Data API = canonical `tle_store`; Inference API = `pipeline` / `anomaly_monitor`; fixed auditable DAG features→IF→XGB→Fuzzy→Kelly→(pairs) | Identical DAG in each fold (reproducibility) |
| **US 12,450,265 B2** Time-series geo | Trajectories (X,Y,T); tiles; RDP compression for UI | Kepler+T series in `history/epochs`; UI: SGP4 globe + (roadmap) RDP downsample of orbits on front | `anomaly_score(t)` curve and event trajectory = case “temporal tile” |
| **US 12,374,011 B2** Ontology map | Intelligence objects + filters + histograms | `watchlist.json` roles asset/suspect/baseline; board by role/country/threat | Walk-forward filter by role; lead-time / hits histogram by event type |

### 5.2 Checklist “patent technology → module”

#### Meta-Constellation (070 A1)

- [x] Separate micro-models (IF / XGB / Fuzzy)
- [x] Insight-first (alert JSON, not raw dump)
- [x] Watchlist = “payload/object selection” for the mission
- [ ] Versioned hot-swap: `models/if_baseline_{asof_date}.joblib` per fold/day
- [ ] Model registry (meta: contamination, n_windows, cutoff) — partial in `anomaly_monitor_meta.json`

#### LLM + GIS (296 A1)

- [x] Stage ① Data quality
- [x] Stage ② Quant + ML
- [x] Stage ③ Bob (stub/Granite)
- [ ] Stage ④ **explicit** post-text decision score (only calibrates, does not rewrite quant)
- [ ] Bob prompt ties **walk-forward event citation** when there is a temporal match

#### Sensor correlation / DAG (514 B2)

- [x] Staged pipeline
- [ ] Formal Data API / Inference API interfaces (JSON Schema contracts)
- [ ] **Pair** DAG as optional node when `role=suspect` and assets nearby

#### Time-series geo (265 B2)

- [x] Temporal epoch store
- [x] Front with simulated time / orbits
- [ ] RDP or polyline decimation in globe worker (temporal zoom)
- [ ] Walk-forward event “tile” export (CSV/JSON of the curve)

#### Ontology map (011 B2)

- [x] Roles in catalog
- [ ] Cross filters on board (role × country × anomaly)
- [ ] Alert histogram by class (UI)

### 5.3 Canonical DAG (patents 514 + 296 fused)

```
[Data API] tle_store.epochs
     │
     ▼
[1] DQ filter                    ← 296 stage 1 / 070 quality
     │
     ▼
[2] Feature Extractor (engine)   ← math framework (our differentiator)
     │
     ├──────────────────┐
     ▼                  ▼
[3a] IF micro-model   [3b] Pair micro-model (coint/dist/TCA)
     │                  │
     └────────┬─────────┘
              ▼
[4] XGB threat micro-model
              ▼
[5] Fuzzy calibration
              ▼
[6] Kelly priority               ← insight-first ranking (070)
              ▼
[7] Bob LLM thesis + recs        ← 296 stages 3–4 (post-quant)
              ▼
[8] Ontology board / map         ← 011
```

Walk-forward **repeats 1–6** in each fold; 7–8 only in the final report.

---

## 6. Math + ML + Event (One Line per Tool)

| Tool | Role in walk-forward |
|------|----------------------|
| Shannon \(H(\Delta a)\) | Rises when maneuver “dirties” the series before/during the report |
| Hurst | Pre-event persistence (subtle thrust) |
| CUSUM | Marks *when* the regime broke (natural lead-time) |
| Kolmogorov proxy | Complex control vs “simple” drag |
| ADF | Non-stationarity of the individual series |
| Cointegration | Shadowing (Luch-class) |
| Proximity / TCA | RPO (SY/SJ-class) |
| IF | Aggregates the math vector: “outside past normal” |
| Fuzzy | Penalizes bad TLE in the historical window |
| Kelly | Prioritizes which event/alert “deserves sensor” |
| Bob | Explains fold + cites open source of the event |

---

## 7. Suggested Implementation Order

1. **HF seed** with watchlist (coverage ≥2024; extend years if event requires).  
2. **`events_walkforward.json`** with 2–3 anchors covered by the data (e.g. Luch-2 2023+, SY-12 if TLE exists).  
3. **`src/walkforward.py`**: expanding window + JSON curve export.  
4. **Hit@event + lead-time + placebo baseline metrics**.  
5. **Version micro-models** by `asof` (patent 070 hot-swap).  
6. **JSON Schema** Data/Inference (patent 514).  
7. **Bob** template: “compatible with pattern documented in {source}, scores: …”.  
8. UI: one “Event replay” panel (ontology + time-series 265).

---

## 8. Pitfalls

1. **Sparse TLE** in GEO can delay detection — report temporal resolution.  
2. **Look-ahead:** forbidden to use epochs ≥ cutoff in training or decision features.  
3. **HOSTILE labels** from journalistic report ≠ forensic ground truth.  
4. **Circular accuracy** from old synthetic training does not replace walk-forward.  
5. Patents = **architectural inspiration**; do not claim Palantir affiliation.

---

## 9. Continuity Prompt

```text
Continue Athena-SDA: (1) seed HF if needed; (2) create
data/catalog/events_walkforward.json with Luch/SY anchors;
(3) implement src/walkforward.py expanding-window reusing
engine + anomaly_monitor; (4) report Hit@event and lead-time;
(5) keep DAG and 4 patent stages in the design.
```

---
*Athena-SDA Walk-forward & Patent Architecture Reference.*
