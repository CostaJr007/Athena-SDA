# Athena-SDA

**Military-first Space Domain Awareness (SDA) copilot** — quantitative **orbital noise analysis**, **micro-anomaly detection**, and **operational alerts** on a curated watchlist of high-value assets and military-interest platforms.

| | |
|--|--|
| **Challenge** | IBM SkillsBuild AI Builders — *Advance Space Exploration with AI* (August 2026) |
| **Mission** | Analyze TLE time series + space weather; detect elevated noise / micro-trajectory regimes; prioritize attention on **suspects** vs protected **assets** |
| **Repo** | [github.com/CostaJr007/Athena-SDA](https://github.com/CostaJr007/Athena-SDA) |
| **Watchlist** | 24 NORADs (7 **asset** · 11 **suspect** · 6 **baseline**) |
| **History** | **~12.6 years** longitudinal series (2014-01-01 → 2026-08-12) · **Full ~11-year Solar Cycle** coverage (Cycles 24 & 25) · ~250k epochs |
| **Space weather** | GFZ Potsdam F10.7 / Ap / Kp + NOAA geomagnetic storm flags (physical drag vs maneuver decoupling) |
| **AI Copilot** | **DeepSeek (`deepseek-chat`)** / **IBM Granite (watsonx.ai)** / **Groq** + **Tavily** web context · *Immutable math scores* |
| **Validation** | Claims **A+B** (re-validated 2026-08, corrected framework): GEO interest **5/5** hard hits vs civil EO **0/7** · gap ~0.26 · Mann–Whitney *p*≈0.0013 |

---

**Integration:** Backend risk report ↔ frontend mission board is wired via `athena.risk_report.v1` + `scripts/sync_frontend_data.py` (cross-platform; replaces the old `.ps1`/`.sh` pair). See [`docs/FINAL_INTEGRATION_STATUS.md`](docs/FINAL_INTEGRATION_STATUS.md).

### Start here

| Resource | Content |
|----------|---------|
| **[Proof dossier](docs/PROOF_DOSSIER.md)** | Embasamento por feature (DOI), reprodução, diferencial, limitações |
| **[LaTeX paper](docs/paper/athena_sda_article.tex)** | Full methods, math, Claims A+B, figures, glossary |
| **[Methods & claims](docs/paper/METHODS_AND_CLAIMS.md)** | Formal validation design |
| **[Results tables](docs/paper/RESULTS_TABLES.md)** | Headline metrics + per-event table |
| **[Figures](docs/paper/figures/)** | Pre-peak IF score curves (asof vs \(t_{\mathrm{peak}}\)) |
| **[Limitations](docs/paper/LIMITATIONS.md)** | Sample size, TLE noise, orbit-class scope |
| **[Foundation](docs/FOUNDATION_QUANT_VALIDATION.md)** | Doctrine + what is validated |
| **[Palantir patents (verified)](docs/references/palantir_patents.md)** | Corrected citations + architectural mapping |
| **[Pitch script](docs/PITCH.md)** | 1-minute demo narrative (honest framing) |
| **[Strategic roadmap](docs/ROADMAP_ESTRATEGICO.md)** | Cronograma do que falta (tracks T1–T9) |
| **[Agent handoff](docs/AGENT_HANDOFF.md)** | Instruções para outra IA analisar / continuar |
| **[Walk-forward PoC HTML](src/frontend/public/reports/walkforward_poc.html)** | In-browser demo narrative |
| **Mission board UI** | `cd src/frontend && npm run dev` |

### Hackathon demo (Live Interactive Stack)

AI Copilot with immutable scores: **IBM Granite (`WATSONX_APIKEY` / `ibm/granite-3-8b-instruct`)** / **DeepSeek** (`DEEPSEEK_API_KEY`) / **Groq** (`GROQ_API_KEY`) + **Tavily** web context.
Quant scores and ML anomaly metrics stay immutable.

```powershell
copy .env.example .env
# configure your API keys in .env
python scripts/serve_granite_explain.py
```

Sidecar API: http://127.0.0.1:8787/api/health  
Tactical 3D Board: http://127.0.0.1:3000 — inspect live objects, open ontology graph (`G`), run Conjunction Lab (`C`).

```bash
python scripts/run_paper_validation.py --threshold 0.50
python scripts/plot_prepeak_curves.py
```

---

## 🏆 Hackathon Alignment: IBM SkillsBuild AI Builders

| Hackathon Criterion | Athena-SDA Implementation | Verification / Evidence |
|---------------------|---------------------------|-------------------------|
| **1. Space Exploration & Domain Safety** | Military-first Space Domain Awareness (SDA) monitoring 24 strategic satellites (assets, suspects, baselines). Decouples natural space weather drag (F10.7, Ap, Kp) from covert low-thrust maneuvers and RPO threats. | [`README.md #1-4`](#1-what-athena-sda-does) · [`docs/PROOF_DOSSIER.md`](docs/PROOF_DOSSIER.md) |
| **2. IBM Technology & AI Innovation** | **IBM Granite (`ibm/granite-3-8b-instruct`)** on **watsonx.ai** powers the **Bob Copilot** and sidecar API (`scripts/serve_granite_explain.py`), translating multi-dimensional orbital noise vectors and ontology graphs into natural-language tactical briefings while preserving immutable math scores. | [`src/bob.py`](src/bob.py) · [`src/graph_qa.py`](src/graph_qa.py) · `WATSONX_APIKEY` in `.env` |
| **3. Advanced ML & Deterministic Math** | Multi-model pipeline: LZ76 complexity, DFA, Page CUSUM/EWMA, Kalman innovation (Zollo & Weigel 2023), past-only Isolation Forest, XGBoost weak labeling, Dempster-Shafer evidential fusion, and Kelly attention allocation. | [`src/engine.py`](src/engine.py) · [`src/evidence.py`](src/evidence.py) |
| **4. Architectural Foundation (Palantir-Inspired)** | Implements 5 public patent concepts: micro-model orchestration with daily hot-swapping, LLM-as-explainer / ML-as-scorer, 4D spatiotemporal replay, typed OpenAPI contracts (`risk_report.v1`), and interactive 3D ontology map with cross-filtering. | [`docs/references/palantir_patents.md`](docs/references/palantir_patents.md) |
| **5. Empirical Validation & Reproducibility** | Validated across **12.6 years** of longitudinal TLE data (~250k epochs across Solar Cycles 24 & 25): **5/5 hard hits** on GEO interest cases with 150–240 days lead time vs **0/7** on civil placebos (*p* ≈ 0.0013). 100% automated test suite passing (62/62 tests). | [`docs/paper/`](docs/paper/) · `pytest -q` (62 passed) |

---

## 1. What Athena-SDA does

Operators cannot watch the entire catalog equally. Athena-SDA focuses a **military-first watchlist** and turns **public TLE history** + **GFZ space weather** into:

1. **Quantitative noise features** — LZ76, DFA, Page CUSUM/EWMA (ARL), permutation entropy, SSA, BOCPD, LKF innovation (Zollo & Weigel), MMD typicality, ΔSMA, space weather  
2. **Anomaly score** — Isolation Forest past-only, trained on **baseline + asset** normality  
3. **Alerts** — elevated score and/or day-over-day shift on **suspects** (and platform-health flags on assets)  
4. **Priority** — XGBoost weak labels, Dempster-Shafer evidence fusion, suspect×asset pair risk, Kelly attention  
5. **Explanation** — quant HTML reports + Bob copilot (reads scores; does not recompute them)  
6. **Validation** — walk-forward against open-source report windows and civil EO placebos  

### Watchlist doctrine

| Role | Examples | ML role |
|------|----------|---------|
| **asset** | ISS, GPS, DMSP, allied SAR | IF normality anchor; protect / pair target |
| **suspect** | Luch/Olymp-K, Yaogan, Shiyan, CSS | Primary **noise / micro-anomaly** detection |
| **baseline** | TERRA, AQUA, Landsat, NOAA | IF train only (quiet EO reference) |

Suspects are **not** used to define IF normality. Commercial mega-constellations (e.g. Starlink) are excluded from IF training.

---

## 2. Noise and anomaly (definitions)

| Term | Meaning |
|------|---------|
| **Noise** | Structure in the orbital series beyond quiet Keplerian coasting: irregular Δaltitude, persistent drift, complex control, jumps, non-stationarity |
| **Anomaly score** \(s\in[0,1]\) | How isolated the current feature vector is vs trained normality (Isolation Forest) |
| **Micro-trajectory / persistence** | DFA, permutation entropy, Page CUSUM/EWMA, SSA residual, BOCPD, LKF innovation, ΔSMA |
| **Pair risk** | Distance + cointegration suspect→asset — **priority** channel |
| **Hard hit** | \(s \ge 0.50\) near public \(t_{\mathrm{peak}}\) in past-only walk-forward |

---

## 3. Pipeline

```
Public TLE (history + daily) + GFZ F10.7/Ap/Kp
        ↓
Sliding window → quantitative noise feature vector
        ↓
Isolation Forest (train: baseline+asset, past-only) → anomaly_score
        ↓
Priority: XGB + evidence fusion (DS) + pair_risk + Kelly + data quality
        ↓
Risk board JSON · quant HTML · Bob briefing
        ↓
Walk-forward / paper validation (open-source anchors + placebos)
```

**Past-only rule:** IF is trained only on windows ending before the cutoff (e.g. yesterday). The current window is **scored**, not mixed into that baseline.

\[
s(x)=\mathrm{clip}\bigl(0.5-\mathrm{IF.decision\_function}(x),\,0,\,1\bigr)
\]

---

## 4. Quantitative features and space weather

> **Math framework corrected (2026-08):** every feature maps to a verified
> reference (see [`docs/PROOF_DOSSIER.md`](docs/PROOF_DOSSIER.md)). The old
> zlib "Kolmogorov proxy", biased R/S Hurst, `1−max` RKHS and fake
> "L1-CUSUM" were replaced by LZ76 (Kaspar-Schuster), DFA (Peng 1994),
> MMD typicality (Gretton 2012) and ARL-calibrated Page CUSUM + EWMA.

| Block | Examples | Role in analysis |
|-------|----------|------------------|
| Keplerian | SMA, ecc, inc, RAAN, \(n\) | Geometry |
| Deltas / activity | ΔSMA 7d/30d (epoch-based), regime-change count | Relocation / active ops |
| Persistence | DFA full/short, \(\Delta\alpha\), Shannon full/short, permutation entropy | Micro-trajectory / sustained control |
| Complexity / breaks | LZ76, complexity-entropy \(C\), Page CUSUM, EWMA, BOCPD, ADF, SSA residual, LKF innovation (Zollo & Weigel) | Pattern complexity, regime change |
| Topology / typicality | H0/H1 persistence (proxy mode), MMD typicality | Structural support features |
| Evidence | Dempster-Shafer belief / plausibility / conflict K | Weak-detector fusion with explicit ignorance |
| **Space weather (GFZ)** | F10.7, Ap, Kp, 7d deltas, geomagnetic_storm | Solar/geomagnetic context for LEO drag vs maneuver |
| Pairs (not in IF) | min distance, aligned cointegration, DCCA | Shadowing / proximity priority |

**IF** measures series noise. **Pairs / XGB + evidence fusion** rank operational attention.

---

## 5. Models

| Layer | Function |
|-------|----------|
| Feature engine (`engine.py` + `innovation.py`) | Deterministic math → noise vector (corrected framework) |
| Monitor Isolation Forest | Normality = baseline+asset; daily anomaly scores |
| Pipeline Isolation Forest | Separate artifact for priority stack |
| XGBoost | Weak-label priority tiers (operational) |
| Evidence fusion (`evidence.py`) | Dempster-Shafer belief/plausibility from weak detectors |
| Kelly / DQ | Attention budget, reliability |
| Pair score | Suspect×asset relationship risk (aligned cointegration + DCCA) |
| Bob | Natural-language briefing from computed scores |
| Ontology + contracts | `ontology.json` typed objects · `schemas/risk_report.v1.schema.json` Open API |
| Registry | `models/registry.json` — versioned micro-models (hot-swap per day) |

---

## 6. Validation (Claims A + B)

> **Re-validated 2026-08-10 with the corrected math framework** (LZ76, DFA,
> MMD, ARL CUSUM/EWMA, SSA, BOCPD, LKF innovation). The headline claims are
> **preserved** — and now rest on verified methods (see
> [`docs/PROOF_DOSSIER.md`](docs/PROOF_DOSSIER.md)).

| Claim | Statement | Result (corrected framework) |
|-------|-----------|---------------------|
| **A (GEO headline)** | Interest cases (Luch/SY-12 class) show elevated past-only IF scores / hard hits | **5/5** hard · mean max **0.716** · pre-peak mean 0.637 |
| **A (core panel)** | 11 interest events, 9 unique NORADs (GEO+LEO+MEO) | **7/11** hard · mean max **0.616** |
| **B** | Civil EO placebos under the same protocol stay lower | **0/7** hard · mean max **0.457** · p95 **0.495** |
| Separation (GEO) | Interest scores stochastically higher | Gap **0.260** · Mann–Whitney **p≈0.0013** |
| Separation (core) | Interest vs placebo max scores | Gap 0.160 · Mann–Whitney **p≈0.010** |

Open-source reports (Gunter, CSIS, SWF, press) supply **event windows** \(t_{\mathrm{peak}}\) for evaluation. Expanded LEO/MEO interest panels are reported separately (hard-hit rate lower; GEO remains the headline panel). Honest notes: LEO recon (Yaogan-3/29) misses are expected (TLE noise floor); Shiyan-7 reached 0.55 (below hard threshold 0.50 sustained near peak).

### Paper pack

| Path | Content |
|------|---------|
| [`docs/paper/athena_sda_article.tex`](docs/paper/athena_sda_article.tex) | Full English paper (math, results, **glossary**) |
| [`docs/paper/PROTOCOL_PREREGISTRATION.md`](docs/paper/PROTOCOL_PREREGISTRATION.md) | Locked analysis plan |
| [`docs/paper/METHODS_AND_CLAIMS.md`](docs/paper/METHODS_AND_CLAIMS.md) | Methods text |
| [`docs/paper/RESULTS_TABLES.md`](docs/paper/RESULTS_TABLES.md) | Result tables |
| [`docs/paper/figures/`](docs/paper/figures/) | Pre-peak curves |
| [`docs/paper/LIMITATIONS.md`](docs/paper/LIMITATIONS.md) | Limitations |
| [`data/alerts/paper_validation_latest.json`](data/alerts/paper_validation_latest.json) | Machine-readable A+B package |

```bash
python scripts/smoke_test.py
python scripts/run_anomaly_monitor.py train-baseline
python scripts/run_paper_validation.py --run-wf --threshold 0.50
python scripts/plot_prepeak_curves.py
cd docs/paper && pdflatex athena_sda_article.tex
```

---

## 7. Walk-forward protocol

1. Load events from `data/catalog/events_walkforward.json`.  
2. For each `asof` (14-day step): fit IF on normality windows with end before `asof − 3` days.  
3. Score the target NORAD at `asof`.  
4. Metrics: hard hit, max score, pre-peak mean, `noise_ramp`, `first_fold_hit`, unique NORAD counts.

---

## 8. Data sources

| Resource | In git? | Role |
|----------|---------|------|
| Filtered TLE parquet | Yes | Train / score |
| GFZ space weather daily | Yes | F10.7, Ap, Kp |
| Models + registry | Yes | Inference |
| Alerts, walk-forward, paper JSON, figures | Yes | Demo / proof |
| Full HF TLE cache | No | Optional re-seed |

```bash
# one-time seed
python scripts/run_anomaly_monitor.py seed-history --hf --start-year 2014
python scripts/run_anomaly_monitor.py seed-space-weather --force --start-year 2014

# daily refresh (organized pipeline: weather → ingest → baseline → score → sync)
bash scripts/run_daily_ingest.sh

# optional: schedule it daily at 03:15 UTC (idempotent, reversible)
bash scripts/install_daily_cron.sh
```

---

## 9. Install and run

```bash
cd Athena-SDA
python -m venv .venv
# Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

```bash
cd src/frontend && npm install && npm run dev
# http://127.0.0.1:3000
```

### Developer tooling

```bash
# Run the test suite (pytest) — fast, network-free unit tests
pip install -r requirements-dev.txt
python -m pytest -q

# Continuous validation / drift health check → data/alerts/validation_health.json
python scripts/run_continuous_validation.py            # stats + drift + calibration
python scripts/run_continuous_validation.py --run-paper  # also re-run Claims A+B

# Align risk_report (pc/tca) + investigation.v1 + frontend public/
python scripts/compat_refresh.py

# One-shot sync of ML artifacts into the frontend public/ folder
python scripts/sync_frontend_data.py

# CI (.github/workflows/ci.yml) runs pytest + frontend lint/build on every PR.
# Reproducible image: docker build -t athena-sda .
# Full board + sidecar: docker compose up --build
```

---

## 10. Repository layout

```
Athena-SDA/
├── README.md
├── requirements.txt
├── scripts/                 # monitor, walkforward, paper validation, plots, sync
├── src/
│   ├── engine.py            # corrected math framework (LZ76, DFA, MMD, CUSUM…)
│   ├── innovation.py        # LKF innovation score (Zollo & Weigel 2023)
│   ├── evidence.py          # Dempster-Shafer belief/plausibility fusion
│   ├── changepoint.py       # offline change-point (auto-label)
│   ├── ontology.py/.json    # typed object model (Palantir-inspired)
│   ├── contracts.py         # risk_report.v1 schema validation
│   ├── models.py            # features + IF/XGB
│   ├── space_weather.py     # GFZ indices
│   ├── anomaly_monitor.py   # daily scoring (hot-swap model snapshots)
│   ├── walkforward.py / pair_score.py / bob.py / doctrine.py
│   └── frontend/            # React mission board + globe (cross-filters, replay)
├── schemas/                 # risk_report.v1.schema.json (Open API contract)
├── models/ · data/
└── docs/                    # paper pack · proof dossier · pitch · patents (verified)
```

---

## 11. Security and citation

- Secrets only in `.env`  
- **GFZ** Kp/Ap/F10.7 — Matzka et al. / GFZ terms  
- **TLE** — CelesTrak / Space-Track / HF mirrors per provider terms  
- **Open reports** — Gunter, CSIS, AMOS/SWF, press as evaluation anchors  

---

*Athena-SDA — quantitative orbital noise analysis and micro-anomaly alerts for military-first SDA.*
