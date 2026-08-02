# Athena-SDA

**Space Domain Awareness (SDA) Copilot** — prioritize attention on orbital objects using **real public data**, a **quantitative noise framework**, **machine learning**, and an **AI analyst** that explains scores.

| | |
|--|--|
| **Challenge** | IBM SkillsBuild AI Builders — *Advance Space Exploration with AI* |
| **Focus** | **Military-first SDA**: protect **assets** · detect noise on **suspects** · **baseline** = normality for IF only |
| **Repo** | [github.com/CostaJr007/Athena-SDA](https://github.com/CostaJr007/Athena-SDA) |
| **Watchlist** | 24 NORADs (7 **asset** · 11 **suspect** · 6 **baseline**) |
| **History** | **~12.5 years** of TLEs (2014-01-01 → 2026-07-27) · ~250k epochs |
| **ML doctrine** | IF trains on **baseline+asset**; scores **suspects** for persistent micro-trajectory noise; XGB/pairs = **priority**, not proof |
| **Validation** | **Claims A+B** (paper): military GEO cases **5/5** hard hits vs civil EO **0/7**; Mann–Whitney p≈0.001; reports = anchors not forecast |
| **Paper pack** | [`docs/paper/METHODS_AND_CLAIMS.md`](docs/paper/METHODS_AND_CLAIMS.md) · [`RESULTS_TABLES.md`](docs/paper/RESULTS_TABLES.md) · `python scripts/run_paper_validation.py` |

### For judges — open these first

| Resource | What you get in 2 minutes |
|----------|---------------------------|
| **[Walk-forward PoC HTML](src/frontend/public/reports/walkforward_poc.html)** | Story: noise **before** public reports (Luch, Shiyan) + placebos + math in plain language |
| **This README** | Methodology: what noise is, how each model fits, what we claim / do not claim |
| **Mission board UI** | `cd src/frontend && npm run dev` → link **Open PoC for judges** |
| Deeper docs | [FULL_ML_REPORT](docs/FULL_ML_REPORT_ATHENA_SDA.md) · [WALKFORWARD_PRE_REPORT](docs/WALKFORWARD_PRE_REPORT_ML.md) · [CASE REPORT](docs/WALKFORWARD_DETECTION_CASE_REPORT.md) |

---

## 1. The problem in one minute

There are tens of thousands of objects in Earth orbit. Human operators cannot watch all of them equally.

Some satellites change how they fly — relocating in GEO, irregular station-keeping, persistent micro-maneuvers, or “following” another object. Public catalogs (TLE) exist, but raw tables are not **attention intelligence**.

**Athena-SDA** turns public orbits + public space weather into:

1. A **noise / normality score** (“has this object left its statistical baseline?”) — continuous monitor  
2. A **priority tier** (XGBoost weak labels + fuzzy + proximity — **operational ranking**, not scientific proof)  
3. An **explanation** for the operator (Bob copilot + quant HTML reports)  
4. **Case studies** on open-source report windows: how Hurst / Shannon / CUSUM / IF scores behave on known atypical regimes (walk-forward, past-only) vs placebos  

The 3D globe is the **demo** (extra tracks may decorate the scene). The **models and proof** target the **military watchlist**: quant noise + Isolation Forest + multi-year TLE + military case studies vs civil EO baselines. See [`docs/FOUNDATION_QUANT_VALIDATION.md`](docs/FOUNDATION_QUANT_VALIDATION.md).

---

## 2. What we mean by “noise” and “anomaly” (plain language)

### Everyday analogy

Think of each satellite as a patient with a **vital-signs chart** (altitude / orbital size over time).

| Medical idea | Athena idea |
|--------------|-------------|
| Blood pressure series | Semi-major axis (SMA) / orbital elements over weeks |
| “Is today’s chart weird **for this patient**?” | Isolation Forest vs **that object’s past** |
| “Triage color: green / yellow / red” | NORMAL → ANOMALOUS → SUSPECT → HOSTILE (XGBoost + fuzzy) |
| “Is the patient near a critical ward?” | Distance + cointegration vs protected **assets** |
| “Did labs go bad **before** the hospital wrote the report?” | Walk-forward vs open-source report anchors |

### Precise definitions (still readable)

| Term | Meaning in Athena |
|------|-------------------|
| **Noise** | Structure in the orbital time series that is **not** quiet Keplerian coasting: irregular Δaltitude, persistent drift, complex control patterns, rare jumps, non-stationarity. We measure it with several **math features** (below), not with one magic number. |
| **Anomaly score** | A number in **[0, 1]** from Isolation Forest: how **isolated / rare** the current feature vector is compared with the object’s **past** windows (plus space-weather context). Higher = more anomalous **regime**. |
| **Regime change** | The joint profile of features no longer looks like “normal life” for that object (maneuvers, inspection-like control, busy GEO station-keeping). |
| **Pair / shadowing risk** | Separate channel: geometry (distance) + **cointegration** of two altitude series (do they “move together”?). Used for **priority**, not as the walk-forward hit criterion. |
| **Hard hit (validation)** | In walk-forward: `anomaly_score ≥ 0.50` near a **public report date**. |

**We do not claim** that “anomaly = proven hostile intent.”  
**We claim** that the series left its statistical baseline — often **before** open reporting.

---

## 3. Methodology at a glance (for any reader)

```
┌─────────────────────────────────────────────────────────────────┐
│  A. DATA                                                        │
│     Public TLE history + daily CelesTrak + GFZ F10.7/Ap/Kp      │
└────────────────────────────┬────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  B. WINDOW                                                      │
│     Last ~20 epochs for one NORAD → time series of SMA, etc.    │
└────────────────────────────┬────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  C. QUANT NOISE VECTOR (features)                               │
│     Kepler + math toolkit + space weather + (optional) pairs    │
│     “Describe the noise” — no learning yet                      │
└────────────────────────────┬────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  D. LEARNED MODELS                                              │
│     Isolation Forest → anomaly_score  (rarity vs past)          │
│     XGBoost → class + probabilities (operational tier)        │
└────────────────────────────┬────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  E. DECISION LAYERS (not heavy ML training)                     │
│     Fuzzy rules · pair_risk · Kelly attention · data quality    │
└────────────────────────────┬────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  F. OUTPUT                                                      │
│     Risk board JSON · quant HTML · globe · Bob briefing         │
│     Walk-forward: prove noise rose before public report anchors │
└─────────────────────────────────────────────────────────────────┘
```

**Daily rule (no cheating):** the baseline for “normal” is trained on the series **up to yesterday** (or `asof − holdout` in walk-forward). **Today’s** window is only **compared**, never mixed into that day’s training labels as future knowledge.

---

## 4. Quantitative noise framework (mathematical toolbox)

Almost every tool in `src/engine.py` becomes a **number in the feature vector**.  
Those numbers are the **language** the ML models speak.

### 4.1 How to read this table

- **Plain meaning** — for non-specialists  
- **What it catches in orbit** — SDA intuition  
- **Goes into ML?** — Isolation Forest / XGBoost

| Tool | Plain meaning | Orbital intuition | IF | XGB |
|------|---------------|-------------------|----|-----|
| **Shannon entropy** | How *messy* are altitude steps? | Irregular burns / chaotic SK spread the histogram | ✓ | ✓ |
| **Kolmogorov proxy** | Is the up/down pattern hard to compress? | Active control → complex string of moves | ✓ | ✓ |
| **Hurst (R/S)** | Does the series keep drifting one way? | H ≫ 0.5 → persistent low-thrust / controlled drift | ✓ | ✓ |
| **L1-CUSUM** | Did the series *break* recently? | Structural change / maneuver onset | ✓ | ✓ |
| **Mandelbrot tail** | Are there rare extreme jumps? | Impulsive ΔV-like spikes | ✓ | ✓ |
| **ADF test** | Is the series non-stationary? | Ongoing maneuver / non-mean-reverting regime | ✓ | ✓ |
| **ΔSMA / maneuver count** | How far / how often did altitude move? | Slot relocation, busy GEO ops | ✓ | ✓ |
| **RKHS spectral anomaly** | Is this feature mix typical vs a normal reference cloud? | Multivariate “weirdness” support | ✓ | ✓ |
| **Ricci (Ollivier proxy)** | Local geometric “curvature” along the track | Convergence / neighborhood distortion | ✓ | ✓ |
| **Persistent homology H0/H1** | Topology of the position cloud | Closed orbit vs escape-like shape (proxy) | ✓ | ✓ |
| **Chern–Simons proxy** | Break of angular-momentum conservation signature | Non-Keplerian / propulsion-like force | ✓ | ✓ |
| **Williams score** | Static context (country / purpose / orbit class) | Prior interest, not dynamics | ✓ | ✓ |
| **Space weather** (F10.7, Ap, Kp…) | Is the Sun “stormy”? | Separate **drag** (esp. LEO) from intentional change | ✓ | ✓ |
| **Distance to asset** | How close to a protected satellite? | RPO / conjunction priority | — | ✓ |
| **Cointegration** | Do two altitude series move together? | Shadowing / escort pattern | — | ✓ |
| **Łukasiewicz implication** | Soft logical consistency (fuzzy implication) | Rule-like support signal | — | ✓ |
| **anomaly_score** (from IF) | How rare is the full profile? | Main **noise** output | — | ✓ (input) |

**Isolation Forest** deliberately **excludes** distance / cointegration / Łukasiewicz so it measures **“this object’s own series noise”**, not “who it is next to.”  
**XGBoost** **includes** geometry + cointegration + the IF score for **operational triage**.

Deeper math write-up: [`docs/references/mathematical_foundation.md`](docs/references/mathematical_foundation.md).

### 4.2 One formula judges can remember

\[
\text{anomaly\_score} = \mathrm{clip}\bigl(0.5 - \mathrm{IF.decision\_function}(x),\, 0,\, 1\bigr)
\]

- \(x\) = feature vector of the current window  
- IF is fit only on **past** windows of that object (and related history under the daily protocol)  
- Higher score ⇒ current \(x\) is more **isolated** (anomalous) in feature space  

Walk-forward **hard hit**: \(\text{anomaly\_score} \ge 0.50\) near a public report date \(t_{\text{peak}}\).

---

## 5. How each model / layer fits (architecture for judges)

Nothing is random decoration. Each block has a **job**.

| Layer | Type | Job | Answers the question… |
|-------|------|-----|------------------------|
| **Feature engine** (`engine.py`) | Formulas (not “trained”) | Turn a TLE window into a **noise profile** | “What kind of weird is this?” |
| **Isolation Forest** | Unsupervised ML | Learn “normal” joint patterns in the **past**; score rarity | “Is this rare **for this object**?” |
| **XGBoost** | Supervised ML | Map profile + geometry → 4 tiers with probabilities | “What **priority class** under our doctrine?” |
| **Labels for XGB** | Heuristic rules | Weak labels (proximity + Hurst + coint + ΔSMA…) | Training targets — **not** classified ground truth |
| **Fuzzy Mamdani** | Rule system | Soft calibration under TLE age / distance uncertainty | “How confident is the linguistic threat?” |
| **Pair score** | Geometry + cointegration | `pair_risk` for suspect↔asset | “Is there a **relationship** to a protected asset?” |
| **Attention fusion** | Weighted blend | ≈ `0.45·anomaly + 0.55·pair_risk` | “What should the operator look at first?” |
| **Kelly** | Allocation formula | Sensor / analyst **attention budget** | “How much attention to spend?” |
| **Data quality** | Checks | Stale TLE, gaps, absurd jumps → `UNRELIABLE_DATA` | “Is the alert even trustworthy?” |
| **Bob (Granite / local)** | LLM or template | Explains **precomputed** scores in natural language | “Tell me **why** in operator language” |
| **Walk-forward** | Validation protocol | Replay history past-only vs open reports + placebos | “Did noise rise **before** public stories?” |

### XGBoost classes (operational tiers)

| Class | Intuition (doctrine, not court evidence) |
|-------|------------------------------------------|
| **NORMAL** | Profile consistent with quiet ops / benign context |
| **ANOMALOUS** | Series noise / break without strong hostile geometry |
| **SUSPECT** | Elevated dynamics and/or mid-range approach / pursuit cues |
| **HOSTILE** | Strong geometry (very close) **and** active dynamics / shadowing cues |

**Important for judges:** XGBoost **accuracy ~95%** on the test set means “agrees with our heuristic labels,” **not** “95% proof of real-world espionage.”  
The **scientific validation story** for pre-report detection is the **Isolation Forest walk-forward**, not XGB accuracy.

---

## 6. End-to-end quant pipeline (daily ops)

```
1. Ingest     TLE history store + today’s CelesTrak + GFZ weather
2. Quality    TLE age, gaps, SMA jumps → reliability flag
3. Features   extract_satellite_features() → full noise vector
4. Pairs      distance + cointegration for suspect×asset
5. IF         past-only baseline → anomaly_score
6. XGB        class + proba (uses anomaly + geometry + math + weather)
7. Fuzzy      linguistic calibration
8. Fuse       final tier + threat level for UI
9. Attention  0.45·anom + 0.55·pair  (+ Kelly)
10. Publish   risk_report JSON · quant HTML · optional Bob
```

Code map:

| Concern | Path |
|---------|------|
| Math features | `src/engine.py` |
| Feature extract + IF/XGB train/predict | `src/models.py` |
| Daily monitor | `src/anomaly_monitor.py` · `scripts/run_anomaly_monitor.py` |
| Pairs | `src/pair_score.py` |
| Walk-forward | `src/walkforward.py` · `scripts/run_walkforward.py` |
| Quant HTML | `src/quant_report.py` |
| Board schema | `docs/SCHEMA_RISK_REPORT.md` |
| Frontend | `src/frontend/` |

---

## 7. Walk-forward validation (proof of concept)

**What we claim:** continuous **normality → deviation → alert** using quant features + Isolation Forest.  
**What open-source reports are:** *case-study anchors* to show how Hurst / Shannon / CUSUM / IF scores look on known atypical regimes (GEO relocation, RPO-like activity) — **not** labels the model is trained to “predict”.

**Protocol**

1. Pick an open-source episode (e.g. Olymp-K near Intelsat — Gunter / CSIS).  
2. For each date `asof` on a 14-day grid, train IF **only** on windows ending before `asof − 3 days` (past-only).  
3. Score the window at `asof`.  
4. Compare **interest** vs **placebo** distributions (mean max score, pre-peak mean, `noise_ramp`, `first_fold_hit`).  
5. Hard hit ≥ 0.50 near `t_peak` is a **secondary** flag; if `first_fold_hit` and `noise_ramp ≈ 0`, the honest reading is **persistent elevated regime**, not “ramp discovered just before the news”.

**Results (expanded panel v3, thr=0.50, past-only IF)**

| Group | N | Hard hit | Mean max | Note |
|-------|---|----------|----------|------|
| **GEO interest** (Luch×3 + SY-12 + Luch-2) | 5 | **5/5** | **~0.60** | persistent elevated regime |
| **Civil EO placebos** (TERRA, AQUA, Landsat, NOAA…) | 7 | **0/7** | **~0.46** | quiet controls |
| Full interest (incl. SY-7, Yaogan-29) | 7 | 5/7 | ~0.56 | LEO recon not always hard-hit |
| Full placebos (incl. Starlink, GPS) | 9 | 2/9 | ~0.48 | constellation/GNSS can look “noisy” |

**Honest takeaway:** separation is strong for **GEO Luch/SY-12 vs civil EO**. Active constellation / GNSS placebos can hard-hit (station-keeping) — report them, don’t hide them. `noise_ramp` mean ≈ 0 ⇒ **level**, not ramp forecast.

**Metrics in JSON** (`data/alerts/walkforward/`): `noise_ramp`, `first_fold_hit`, `p95_max_anomaly_placebo`, `subgroup_geo_interest_vs_civil_eo_placebo`, unique NORAD counts.

**Architecture (Palantir-inspired, not a patent claim)**

- Micro-models versioned in `models/registry.json` (monitor IF ≠ pipeline IF — hot-swap pattern).  
- DAG: Data → Features (math quant) → IF score → priority head (XGB weak labels) → LLM explains (Bob does not rewrite scores).  
- XGBoost accuracy is **weak-label agreement only** — scientific validation is IF + walk-forward + placebos.

Interactive write-up: [`src/frontend/public/reports/walkforward_poc.html`](src/frontend/public/reports/walkforward_poc.html)  
Case-by-case markdown: [`docs/WALKFORWARD_DETECTION_CASE_REPORT.md`](docs/WALKFORWARD_DETECTION_CASE_REPORT.md)

```bash
python scripts/smoke_test.py
python scripts/run_anomaly_monitor.py train-baseline
python -c "from src.models import train_and_save_models; train_and_save_models()"
python scripts/run_walkforward.py run
python scripts/run_walkforward.py summary
```

---

## 8. Data — what is real, what is in Git

| Resource | Approx size | On GitHub? | Role |
|----------|-------------|------------|------|
| HF cache `space-track-tle-history` | ~15 GB | No | Raw multi-year download |
| Filtered TLE parquet (watchlist) | ~13 MB | Yes | Training / scoring base |
| Space weather daily | ~0.1 MB | Yes | F10.7, Ap, Kp |
| ML models (IF, XGB, RKHS) | ~5 MB | Yes | Inference |
| Alerts + walk-forward + quant HTML | ~1–2 MB | Yes | Demo outputs |

| Layer | Source |
|-------|--------|
| Historical TLE | Hugging Face `juliensimon/space-track-tle-history` (filtered) |
| Daily TLE | CelesTrak GP by `CATNR` |
| Space weather | GFZ Potsdam |
| Validation anchors | Open reports (Gunter, CSIS, AMOS/SWF, press) |

```bash
python scripts/run_anomaly_monitor.py seed-history --hf --start-year 2014
python scripts/run_anomaly_monitor.py seed-space-weather --force --start-year 2014
python scripts/run_anomaly_monitor.py status
```

---

## 9. Install and run

```bash
cd Athena-SDA
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # optional: WATSONX_*, SPACETRACK_*
```

**Never** commit `.env` or API tokens.

### Daily scoring

```bash
python scripts/run_anomaly_monitor.py run-daily
PYTHONPATH=. python scripts/run_quant_report.py --all
bash scripts/sync_frontend_data.sh   # Windows: powershell scripts/sync_frontend_data.ps1
python scripts/run_anomaly_monitor.py status
```

### UI

```bash
# Tactical globe + mission board (the only UI)
cd src/frontend && npm install && npm run dev
# http://127.0.0.1:3000
# Mission board → “Open PoC for judges” → walkforward_poc.html
```

---

## 10. Repository layout

```
Athena-SDA/
├── README.md                 ← you are here (methodology for judges)
├── requirements.txt
├── scripts/                  ← monitor, walkforward, quant, data sync, ingest
├── src/
│   ├── engine.py             ← mathematical noise toolbox
│   ├── models.py             ← features + IF + XGB
│   ├── anomaly_monitor.py    ← daily past-only scoring
│   ├── walkforward.py        ← pre-report validation
│   ├── pair_score.py         ← distance + cointegration
│   ├── quant_report.py       ← per-object HTML
│   ├── bob.py                ← copilot explanations
│   └── frontend/             ← React globe + mission board (the UI)
│       └── public/reports/   ← quant_*.html + walkforward_poc.html
├── models/                   ← isolation_forest*.joblib, xgboost_model.joblib
├── data/                     ← history, weather, catalog, alerts
└── docs/                     ← deep reports, schema, case studies
```

---

## 11. What we claim vs what we do not claim

| We claim | We do **not** claim |
|----------|---------------------|
| TLE and GFZ weather are **real public** data | Classified ground-truth of hostile intent |
| Math features describe **orbital noise / regime** | That any single theory “proves espionage” |
| IF detects **deviation from that object’s past** | That XGB accuracy ~95% = real-world hostility detection |
| Walk-forward: noise often **before** open reports (5/5 vs 0/3 placebos) | An intention oracle or future TCA predictor |
| Multi-object features support **priority** (RPO / shadowing) | Full SGP4 conjunction replacement |

**Recommended jury sentence**

> “We filter multi-year public TLEs for 24 objects, build a quantitative noise vector (information theory, persistence, change detection, geometry, space weather), train Isolation Forest only on the past, and show that documented GEO inspection cases were statistically loud months before open-source reports — while civil placebos on the same calendars were not. XGBoost and fuzzy layers turn that noise plus proximity into an operator priority board; Bob explains the scores.”

---

## 12. Security and citation

- Secrets only in `.env` / environment variables  
- `.gitignore` blocks `.env`, `node_modules`, large caches, local backups  

**Cite appropriately**

- **GFZ** Kp/Ap/F10.7 — Matzka et al. / GFZ terms (CC BY 4.0 for published indices)  
- **TLE** — CelesTrak / Space-Track (or mirrors) per provider terms  
- **Open reports** — Gunter, CSIS, AMOS/SWF, Breaking Defense, etc., as narrative anchors only  

---

*Athena-SDA — quantitative orbital noise + ML + real data for Space Domain Awareness.*
