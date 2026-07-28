# Data Engineering & Architectural Workplan Study

**Athena-SDA** · Technical Specification & Data Volume Planning  
**Scope:** Data ingestion volumes, feature extraction pipeline, model training workflows.

---

## 1. Data Ingestion Architecture & Sizing

| Category | Volume / Specification |
|----------|------------------------|
| **ML Target Scope** | **Watchlist ~24 NORADs** (asset/suspect/baseline) |
| **Ingestion Target** | Streamed / filtered orbital TLE history + space weather |
| **Filtered Storage Footprint** | **~20–25 MB** total repository data size (~250k epochs) |
| **Raw Hugging Face Cache** | ~15 GB raw multi-year cache (`space-track-tle-history`) |

### 1.2 Short answer on volume

> For watchlist ML we **do not need multiple gigabytes**.  
> We need on the order of **0.05–0.3 GB** of useful data.  
> The “full” HF dataset is **~12 GB**, but that is the **universe**; our slice is **filtered**.

### 1.3 Three ingestion modes (pick 1 as default)

| Mode | How | Download | When to use |
|------|-----|----------|-------------|
| **A — Filtered streaming (default)** | `load_dataset(..., streaming=True)` + keep `norad_id ∈ watchlist` + `year≥2024` | Low (kept only + stream overhead) | Athena default |
| **B — Per-year parquet + local filter** | Download `tle_2024.parquet`, `tle_2025.parquet`, … and filter | ~0.5–3+ GB if several years | If stream is slow/unstable |
| **C — CATNR / Space-Track daily only** | CelesTrak CATNR (already done) + optional Space-Track API | MB | Daily ops, not 2y baseline |

**Closed default: A for historical seed; CelesTrak CATNR for daily.**

---

## 2. Where to Fetch Data (Open-Source Source Map)

### 2.1 Primary (use)

| # | Source | URL / ID | Auth | Role in Athena |
|---|--------|----------|------|----------------|
| 1 | **Hugging Face TLE history** | `juliensimon/space-track-tle-history` | No (CC-BY-4.0) | Filtered 2y watchlist seed |
| 2 | **CelesTrak GP** | `celestrak.org/NORAD/elements/gp.php?CATNR=` / `GROUP=` | No | Daily ingest |
| 3 | **Athena catalog** | `data/catalog/watchlist.json` | Local | Who enters the ML |
| 4 | **HF constellation latest** | `juliensimon/constellation-tle-latest` | No | “Today” backup if CelesTrak fails |

### 2.2 Secondary (optional / enrichment)

| Source | Auth | Use |
|--------|------|-----|
| **Space-Track.org** API (GP, GP_History) | Free account | Official history if HF incomplete for a NORAD |
| **HF space-track-satcat** | No | Object metadata (country, type) |
| **UCS Satellite Database** | Public (CSV/site) | civil/military purpose (Williams/ontology context) |
| **NOAA space weather** (F10.7, Ap) | Public | Drag context (phase 2, does not block ML v1) |
| **N2YO** | Free-tier API key | Point real-time (not training) |

### 2.3 What **not** to download for ML v1

- Full daily `GROUP=active` catalog “to train the whole sky”
- Full 12 GB HF without filter
- SAR/EO imagery (out of scope for this TLE/SDA quant hackathon)
- Commercial high-rate ephemeris (expensive / unnecessary for feature demo)

### 2.4 Canonical on-disk layout (after ingestion)

```
data/
├── catalog/
│   ├── watchlist.json           # ontology (small)
│   └── events_walkforward.json  # anchors (final validation only)
├── history/
│   ├── epochs.parquet           # CANONICAL train/score (~tens of MB)
│   ├── epochs.csv
│   └── seed_progress.json       # stream progress
├── daily/
│   └── tle_YYYY-MM-DD.csv       # day audit (KB–MB)
├── features/
│   └── train_windows_*.csv      # IF windows
└── alerts/
    ├── anomalies_latest.json    # operations
    └── walkforward_*.json       # post-train / validation only
models/
├── isolation_forest_monitor.joblib
├── anomaly_monitor_meta.json
└── xgboost_model.joblib
```

---

## 3. What Enters the ML (Method Reminder)

```
TLE (history) 
  → MATH features (Shannon, Hurst, CUSUM, Kolmogorov, fractal/Mandelbrot, …)
  → Isolation Forest = “deviates from normal?”
  → XGB/Fuzzy/Kelly = class + uncertainty + priority
  → [FINAL] walk-forward on reports = lead-time test
```

- **Noise that deviates from normal** = core  
- **Walk-forward** = validation stage **after** training, not the training itself  

---

## 4. Organigram of Work

### 4.1 Phase view (macro)

```
┌──────────────────────────────────────────────────────────────────────────┐
│                         ATHENA-SDA — TIMELINE                            │
└──────────────────────────────────────────────────────────────────────────┘

 PHASE 0         PHASE 1          PHASE 2           PHASE 3          PHASE 4
 STUDY           DATA             FEATURES+ML       DAILY OPS        VALIDATION
 (now)           SEED             TRAIN             LOOP             FINAL
    │               │                 │                 │                │
    ▼               ▼                 ▼                 ▼                ▼
 Close          HF stream         Math vector       ingest CATNR     Walk-forward
 volumes        + CelesTrak       IF on past        score latest     vs reports
 sources        history store     meta + joblib     alerts JSON      lead-time
 organigram     coverage 24       (no walkfwd)      (pairs later)    (test only)
```

### 4.2 Detailed organigram (WBS)

```
ATHENA-SDA
│
├── 0. GOVERNANCE AND STUDY                    [CLOSE / IN PROGRESS]
│   ├── 0.1 Military-first scope (watchlist 24)
│   ├── 0.2 Data volume and sources (this doc)
│   ├── 0.3 Math = features; ML = deviation from normal
│   ├── 0.4 Walk-forward only at the end
│   ├── 0.5 Patent map → modules
│   └── 0.6 (next) IBM/quant/fractal papers → theoretical reinforcement
│
├── 1. DATA                                    [NEXT WORK BLOCK]
│   ├── 1.1 deps: datasets, pyarrow, (optional polars)
│   ├── 1.2 seed-history --hf filtered streaming watchlist ≥2024
│   ├── 1.3 seed_progress.json (scanned / kept / by_norad)
│   ├── 1.4 ingest-daily CelesTrak CATNR (24/24)
│   ├── 1.5 status: depth ≥20 epochs on ≥18 sats
│   └── 1.6 (opt) download year parquet if stream fails
│
├── 2. MATHEMATICAL FEATURES                   [QUANT CORE]
│   ├── 2.1 engine: Shannon, Kolmogorov, Hurst, CUSUM, ADF, Mandelbrot…
│   ├── 2.2 DQ gate (catalog noise ≠ tactical anomaly)
│   ├── 2.3 sliding windows (WINDOW=20)
│   └── 2.4 features/train_windows_*.csv audit
│
├── 3. ML — DEVIATION FROM NORMAL              [TRAINING]
│   ├── 3.1 Isolation Forest on the PAST (holdout 1–7d)
│   ├── 3.2 meta: n_windows, n_sats, cutoff, score_p95
│   ├── 3.3 XGBoost threat (weak labels / fuse)
│   ├── 3.4 Fuzzy + Kelly
│   └── 3.5 DO NOT include walk-forward in the training loop
│
├── 4. PAIRS (RPO/shadowing narrative)         [AFTER 3 STABLE]
│   ├── 4.1 suspect × asset: distance / TCA
│   ├── 4.2 series cointegration
│   └── 4.3 proximity_*.json
│
├── 5. DAILY OPERATIONS                        [LOOP]
│   ├── 5.1 ingest-daily
│   ├── 5.2 optional retrain (hot-swap baseline — patent 070)
│   ├── 5.3 score → anomalies_latest.json
│   └── 5.4 Bob only explains (post-quant — patent 296)
│
├── 6. FINAL VALIDATION                        [AFTER TRAINING]
│   ├── 6.1 events_walkforward.json (public anchors)
│   ├── 6.2 expanding window: pre-report series score
│   ├── 6.3 Hit@event, lead-time, FPR baseline metrics
│   └── 6.4 report: math features that fired
│
├── 7. PRODUCT / UI                            [AFTER STABLE JSON]
│   ├── 7.1 risk_report_latest.json contract
│   ├── 7.2 board + globe by role/threat
│   └── 7.3 (opt) event replay panel
│
└── 8. DOCS / PITCH
    ├── 8.1 patents + math + RPO cases
    ├── 8.2 volumes and scale honesty
    └── 8.3 (opt) IBM/Simons/fractal bib
```

### 4.3 Block dependencies

```
[0 Study] ──► [1 Data] ──► [2 Features] ──► [3 ML train]
                                                  │
                          ┌───────────────────────┼───────────────────────┐
                          ▼                       ▼                       ▼
                     [4 Pairs]              [5 Daily]              [6 Walk-forward FINAL]
                          │                       │                       │
                          └───────────────────────┴───────────────────────┘
                                              │
                                              ▼
                                         [7 UI + 8 Pitch]
```

**Critical blocker:** without **1.5** (history depth), **3** and **6** are not reliable.

### 4.4 “Ready to start work” checklist (gate)

| Gate | Criterion |
|------|-----------|
| G0 | Volume/source/organigram study accepted (this doc) |
| G1 | `datasets` + `pyarrow` installed |
| G2 | HF seed: ≥18/24 sats with ≥20 epochs; range ~2024→today |
| G3 | `train-baseline` n_sats≥15, reasonable n_windows (hundreds+) |
| G4 | `score` produces `anomalies_latest` with role/country |
| G5 | (later) walk-forward on ≥1 event covered by the data |

---

## 5. Target Commands (When Execution Starts)

```bash
# deps
pip install datasets pyarrow

# seed (default A — filtered streaming; max-rows avoids runaway)
python scripts/run_anomaly_monitor.py seed-history --hf --start-year 2024 --max-rows 30000

# coverage
python scripts/run_anomaly_monitor.py status
python scripts/run_anomaly_monitor.py catalog -v

# daily
python scripts/run_anomaly_monitor.py ingest-daily --source celestrak

# train + score (ML core)
python scripts/run_anomaly_monitor.py train-baseline --holdout-days 1
python scripts/run_anomaly_monitor.py score

# walk-forward: ONLY afterward — scripts/run_walkforward.py
```

---

## 6. Effort Estimate (Order of Magnitude)

| Phase | Work | Dependency |
|-------|------|------------|
| 1 Data | 1 session (stream may take tens of min) | network + pip |
| 2–3 Features+ML | 1 session if history ok | G2 |
| 4 Pairs | 1 session | G3 |
| 5 Daily | minutes | G3 |
| 6 Walk-forward | 1 session + anchors with data | G3 + history covering event period |
| 7 UI contract | 1 session | G4 |

---

## 7. Direct Answers

| Question | Answer |
|----------|--------|
| How many GB for ML? | **Useful: ~0.05–0.3 GB.** Reserve **1 GB** slack. **Not** 12 GB. |
| Does HF have 12 GB? | Yes for the **full archive**. We use **filter/stream** of the watchlist. |
| Where? | HF `space-track-tle-history` + CelesTrak CATNR (+ optional Space-Track). |
| Does walk-forward need extra data? | Same history; only reprocesses over time. Report disk: MB. |
| Organigram? | Section 4 — phases 0→8; start work at **Phase 1** after G0 acceptance. |

---

## 8. Next Step After Accepting This Study

1. Install deps and run **filtered HF seed**  
2. Confirm **status** (depth)  
3. **train-baseline + score**  
4. Only then pairs and, **last**, walk-forward  

IBM/quant/fractal papers: block **0.6** in parallel with Phase 1 (theory), without blocking download.

---
*Athena-SDA Data Engineering Reference.*
