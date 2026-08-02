# Athena-SDA

**Military-first Space Domain Awareness (SDA) copilot** — track **orbital micro-anomalies** (persistent / strange motion regimes) on **suspect** platforms, protect high-value **assets**, and explain scores with quant math + ML + AI.

| | |
|--|--|
| **Challenge** | IBM SkillsBuild AI Builders — *Advance Space Exploration with AI* |
| **Intent** | **Not** predicting the future or “news dates”. **Yes** continuous tracking of micro-anomalies that resemble **strange / inspection-like / shadowing-like** regimes discussed in open sources |
| **Focus** | Protect **assets** · monitor **suspects** · **baseline** = normality for Isolation Forest only |
| **Repo** | [github.com/CostaJr007/Athena-SDA](https://github.com/CostaJr007/Athena-SDA) |
| **Watchlist** | 24 NORADs (7 asset · 11 suspect · 6 baseline) |
| **History** | ~12.5 years TLEs (2014-01-01 → 2026-07-27) · ~250k epochs |
| **Space weather** | **GFZ real** F10.7 / Ap / Kp + storm flag (drag vs maneuver context) |
| **Proof (Claims A+B)** | GEO military cases **5/5** hard hits vs civil EO **0/7** · gap ~0.19 · Mann–Whitney p≈0.001 |

---

### Open these first (judges / paper)

| Resource | What you get |
|----------|----------------|
| **[Paper pack](docs/paper/METHODS_AND_CLAIMS.md)** | Formal claims, methods, preregistered protocol |
| **[RESULTS_TABLES.md](docs/paper/RESULTS_TABLES.md)** | Headline numbers + per-event table |
| **[Figures](docs/paper/figures/)** | Pre-peak IF score curves per event (Luch, SY-12, placebos…) |
| **[LIMITATIONS.md](docs/paper/LIMITATIONS.md)** | Honest limits (small N, level vs ramp, TLE noise) |
| **[FOUNDATION_QUANT_VALIDATION.md](docs/FOUNDATION_QUANT_VALIDATION.md)** | Doctrine + what is proven |
| **[Walk-forward PoC HTML](src/frontend/public/reports/walkforward_poc.html)** | Interactive story for demo |
| **Mission board UI** | `cd src/frontend && npm run dev` → Open PoC for judges |

```bash
# Regenerate proof tables + figures
python scripts/run_paper_validation.py --threshold 0.50
python scripts/plot_prepeak_curves.py
```

---

## 1. What the project does (intent)

There are tens of thousands of objects in orbit. Operators cannot watch all equally.

**Athena-SDA** focuses a **military-first watchlist** and turns public TLE + space weather into:

1. **Noise / anomaly score** — is this object’s recent series statistically rare vs **normality anchors** (baseline + asset)?  
2. **Priority** — XGBoost weak labels + fuzzy + **suspect×asset** pair risk (attention, not scientific proof)  
3. **Explanation** — Bob (LLM or local) + quant HTML; **never rewrites** quant scores  
4. **Validation** — walk-forward past-only on open-source **report anchors** (Gunter, CSIS, SWF…) vs **civil EO placebos**

The 3D globe may show decorative tracks. **Models and proof** target the military watchlist and quant pipeline.

### Intent (one line)

> Continuous tracking of **micro-anomalies** and strange motion regimes on **military-interest** satellites — co-occurring with periods discussed in open reports — **not** future prediction or classified intent proof.

---

## 2. Noise and anomaly (definitions)

| Term | Meaning |
|------|---------|
| **Noise** | Structure in the orbital time series that is not quiet Keplerian coasting: irregular Δaltitude, **persistent** drift, complex control, jumps, non-stationarity |
| **Anomaly score** | \([0,1]\) from Isolation Forest: how rare the current feature vector is vs trained normality (+ space weather) |
| **Micro-trajectory / persistence** | Multi-scale Hurst & Shannon (full vs short window), CUSUM, ΔSMA, maneuver proxies |
| **Pair risk** | Distance + cointegration suspect→asset — **priority** channel, not IF hit criterion |
| **Hard hit (validation)** | `anomaly_score ≥ 0.50` near public \(t_{\text{peak}}\) under past-only walk-forward |

**We do not claim** anomaly = proven espionage.  
**We claim** elevated **quant noise regimes** on interest cases relative to quiet controls, under a locked past-only protocol.

---

## 3. Pipeline (data → quant → detection → priority → explain)

```
Public TLE (history + daily) + GFZ space weather (F10.7 / Ap / Kp / storm)
        ↓
Sliding window (~20+ epochs) → quantitative noise features (engine.py)
        ↓
Isolation Forest (train: baseline+asset only, past-only) → anomaly_score
        ↓
Priority: XGB (weak labels) + fuzzy + pair_risk + Kelly + data quality
        ↓
Board JSON + quant HTML + Bob briefing (scores immutable)
        ↓
Walk-forward / paper validation vs open-source anchors + placebos
```

**Daily rule:** IF normality is trained on windows ending **before** cutoff (e.g. yesterday). Today is **scored only**.

| Role | Doctrine |
|------|----------|
| **baseline** | Civil EO/meteo — **IF normality train**; calibration only on board |
| **asset** | Protect — IF train anchor + platform health / pair target |
| **suspect** | Military interest — **primary detection** of micro-anomaly noise |

---

## 4. Quantitative toolbox + space weather

Features live in `src/engine.py` / `src/models.py` / `src/space_weather.py`.

| Block | Examples | Role |
|-------|----------|------|
| Keplerian | SMA, ecc, inc, RAAN, \(n\) | Geometry |
| Deltas / activity | ΔSMA 7d/30d, maneuver count | Relocation / burns |
| **Persistence (multi-scale)** | Hurst full/short, `persistence_hurst_gap`, Shannon full/short | Micro-trajectory / sustained control |
| Complexity / breaks | Kolmogorov proxy, L1-CUSUM, ADF, Mandelbrot | Pattern + structural change |
| Topology proxies | Chern–Simons, Ricci, H0/H1 (proxy mode) | Structural (approximate) |
| **Space weather (GFZ)** | F10.7, Ap, Kp, 7d deltas, **geomagnetic_storm** | Separate **solar drag** from intentional change |
| Pairs (not in IF) | min distance, cointegration | Shadowing / RPO **priority** |

**IF** excludes distance/coint so it measures **series strangeness**.  
**XGB / pairs** add geometry for **operator priority**.

\[
\text{anomaly\_score} = \mathrm{clip}\bigl(0.5 - \mathrm{IF.decision\_function}(x),\, 0,\, 1\bigr)
\]

Calibrated ops thr: \(\max(0.50,\ p_{95}\) of normality-anchor scores). Paper primary table uses **thr = 0.50**.

---

## 5. Models and layers

| Layer | Job |
|-------|-----|
| Feature engine | Deterministic math → noise vector |
| **Isolation Forest** (monitor) | Normality = baseline+asset; score all; alert doctrine on **suspects** |
| Isolation Forest (pipeline) | Separate joblib for priority stack |
| XGBoost | Weak-label priority tiers (not detection proof) |
| Fuzzy / Kelly / DQ | Calibration, attention budget, reliability |
| Pair score | Suspect×asset relationship risk |
| Bob | Explains scores; may cite open-source cases; **never** changes numbers |
| Registry | `models/registry.json` — versioned micro-models |

**XGBoost accuracy** = agreement with heuristic labels only — **not** proof of real-world hostility.

---

## 6. Proof documentation (what exists)

| Doc | Content |
|-----|---------|
| [`docs/paper/PROTOCOL_PREREGISTRATION.md`](docs/paper/PROTOCOL_PREREGISTRATION.md) | Locked analysis plan (endpoints, thr, inclusions) |
| [`docs/paper/METHODS_AND_CLAIMS.md`](docs/paper/METHODS_AND_CLAIMS.md) | Methods + formal Claims **A** and **B** |
| [`docs/paper/RESULTS_TABLES.md`](docs/paper/RESULTS_TABLES.md) | Results tables after last validation run |
| [`docs/paper/figures/`](docs/paper/figures/) | **Score curves vs asof** with \(t_{\text{peak}}\) line (report anchors) |
| [`docs/paper/LIMITATIONS.md`](docs/paper/LIMITATIONS.md) | Manuscript-ready limitations |
| [`data/alerts/paper_validation_latest.json`](data/alerts/paper_validation_latest.json) | Machine-readable Claims A+B package |
| [`docs/FOUNDATION_QUANT_VALIDATION.md`](docs/FOUNDATION_QUANT_VALIDATION.md) | Doctrine + military training rules |
| [`docs/WALKFORWARD_DETECTION_CASE_REPORT.md`](docs/WALKFORWARD_DETECTION_CASE_REPORT.md) | Case-by-case narrative (Luch, SY-12…) |
| [`docs/FULL_ML_REPORT_ATHENA_SDA.md`](docs/FULL_ML_REPORT_ATHENA_SDA.md) | Long ML report |

### Claims A + B (headline)

| Claim | Meaning | Latest headline result |
|-------|---------|------------------------|
| **A** | Interest (open-source GEO anchors): elevated past-only IF scores / hard hits | **5/5** hard · mean max **~0.65** |
| **B** | Civil EO placebos: lower scores / near-zero hard hits | **0/7** hard · mean max **~0.46** · p95 **~0.50** |
| Separation | Interest > placebo | Gap **~0.19** · Mann–Whitney **p≈0.001** |

**Open-source reports / “news”:** used as **\(t_{\text{peak}}\) anchors** (Gunter, CSIS, SWF, press…).  
Conclusion: quant noise is **elevated in those case windows** relative to placebos — **co-occurrence** with documented atypical regimes — **not** “we predicted the article.”

Expanded unique-NORAD panel (LEO/MEO) is reported honestly: harder hits concentrated on **GEO Luch/SY-12 class** + some cases (e.g. Tianhe assembly); not every LEO recon hard-hits.

---

## 7. Walk-forward protocol (no cheating)

1. Event from `data/catalog/events_walkforward.json` (interest + placebos).  
2. For each `asof` (step 14 d): fit IF only on windows ending before `asof − 3 d` (normality anchors).  
3. Score target at `asof`.  
4. Metrics: hard hit, pre-peak mean/max, `noise_ramp`, `first_fold_hit`, unique NORADs.  
5. If `first_fold_hit` and `noise_ramp ≈ 0` → **persistent elevated regime**, not ramp-to-news.

```bash
python scripts/smoke_test.py
python scripts/run_anomaly_monitor.py train-baseline
python scripts/run_paper_validation.py --run-wf --threshold 0.50
python scripts/plot_prepeak_curves.py
```

---

## 8. Data

| Resource | On GitHub? | Role |
|----------|------------|------|
| Filtered TLE parquet (watchlist) | Yes | Train / score |
| GFZ space weather daily | Yes | F10.7, Ap, Kp, storm |
| Models (IF monitor/pipeline, XGB, registry) | Yes | Inference |
| Alerts + walk-forward + paper JSON + figures | Yes | Demo / proof |
| Full HF TLE cache | No (~15 GB) | Optional re-seed |

```bash
python scripts/run_anomaly_monitor.py seed-history --hf --start-year 2014
python scripts/run_anomaly_monitor.py seed-space-weather --force --start-year 2014
python scripts/run_anomaly_monitor.py run-daily
powershell -File scripts/sync_frontend_data.ps1   # or bash scripts/sync_frontend_data.sh
```

---

## 9. Install and run

```bash
cd Athena-SDA
python -m venv .venv
# Windows: .venv\Scripts\activate
pip install -r requirements.txt
# optional .env: WATSONX_* for Bob live
```

**UI (only frontend):**

```bash
cd src/frontend && npm install && npm run dev
# http://127.0.0.1:3000
```

---

## 10. Repository layout

```
Athena-SDA/
├── README.md
├── requirements.txt
├── scripts/                 # monitor, walkforward, paper validation, figures, sync
├── src/
│   ├── engine.py            # quant math
│   ├── space_weather.py     # GFZ F10.7 / Ap / Kp
│   ├── models.py            # features + IF/XGB
│   ├── doctrine.py          # military roles
│   ├── calibration.py       # thr from normality p95
│   ├── anomaly_monitor.py   # daily score
│   ├── walkforward.py       # past-only validation
│   ├── pair_score.py
│   ├── bob.py
│   ├── model_registry.py
│   └── frontend/            # React mission board + globe
├── models/                  # joblibs + registry.json
├── data/                    # history, weather, catalog, alerts
└── docs/
    ├── paper/               # proof pack (methods, results, figures, limitations)
    ├── FOUNDATION_QUANT_VALIDATION.md
    └── FULL_ML_REPORT_ATHENA_SDA.md
```

---

## 11. Claim vs do-not-claim

| We claim | We do **not** claim |
|----------|---------------------|
| Real public TLE + GFZ weather | Classified hostile intent |
| Quant features describe **orbital noise / micro-anomaly regimes** | That any score alone “proves espionage” |
| IF detects deviation vs **military normality doctrine** | Prediction of future maneuvers or news dates |
| Claims A+B: GEO interest vs civil EO separation under past-only protocol | XGB accuracy = real-world hostility rate |
| Open reports as **anchors** for co-occurrence reading | Full SGP4 TCA replacement |

**Jury / paper sentence**

> We build a quantitative orbital noise vector (persistence, complexity, change detection, geometry, **space weather**) from multi-year public TLEs on a military-first watchlist. Isolation Forest is trained only on baseline/asset normality and scored past-only. Documented GEO inspection/shadowing cases show elevated anomaly scores versus civil EO placebos under the same protocol (Claims A+B). Priority layers and Bob turn scores into operator attention — without rewriting the quant detection.

---

## 12. Security and citation

- Secrets only in `.env` (never commit tokens)  
- **GFZ** Kp/Ap/F10.7 — Matzka et al. / GFZ (CC BY 4.0 where applicable)  
- **TLE** — CelesTrak / Space-Track / HF mirrors per terms  
- **Open reports** — Gunter, CSIS, AMOS/SWF, press: narrative anchors only  

---

*Athena-SDA — military-first quant noise tracking for SDA attention · public data · past-only validation.*
