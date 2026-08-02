# Athena-SDA

**Military-first Space Domain Awareness (SDA) copilot** — quantitative **orbital noise analysis**, **micro-anomaly detection**, and **operational alerts** on a curated watchlist of high-value assets and military-interest platforms.

| | |
|--|--|
| **Challenge** | IBM SkillsBuild AI Builders — *Advance Space Exploration with AI* |
| **Mission** | Analyze TLE time series + space weather; detect elevated noise / micro-trajectory regimes; prioritize attention on **suspects** vs protected **assets** |
| **Repo** | [github.com/CostaJr007/Athena-SDA](https://github.com/CostaJr007/Athena-SDA) |
| **Watchlist** | 24 NORADs (7 **asset** · 11 **suspect** · 6 **baseline**) |
| **History** | ~12.5 years of TLEs (2014-01-01 → 2026-07-27) · ~250k epochs |
| **Space weather** | GFZ F10.7 / Ap / Kp + geomagnetic storm flag |
| **Validation** | Claims **A+B**: GEO interest **5/5** hard hits vs civil EO **0/7** · gap ~0.19 · Mann–Whitney *p*≈0.001 |

---

### Start here

| Resource | Content |
|----------|---------|
| **[LaTeX paper](docs/paper/athena_sda_article.tex)** | Full methods, math, Claims A+B, figures, glossary |
| **[Methods & claims](docs/paper/METHODS_AND_CLAIMS.md)** | Formal validation design |
| **[Results tables](docs/paper/RESULTS_TABLES.md)** | Headline metrics + per-event table |
| **[Figures](docs/paper/figures/)** | Pre-peak IF score curves (asof vs \(t_{\mathrm{peak}}\)) |
| **[Limitations](docs/paper/LIMITATIONS.md)** | Sample size, TLE noise, orbit-class scope |
| **[Foundation](docs/FOUNDATION_QUANT_VALIDATION.md)** | Doctrine + what is validated |
| **[Walk-forward PoC HTML](src/frontend/public/reports/walkforward_poc.html)** | Demo narrative for judges |
| **Mission board UI** | `cd src/frontend && npm run dev` |

```bash
python scripts/run_paper_validation.py --threshold 0.50
python scripts/plot_prepeak_curves.py
```

---

## 1. What Athena-SDA does

Operators cannot watch the entire catalog equally. Athena-SDA focuses a **military-first watchlist** and turns **public TLE history** + **GFZ space weather** into:

1. **Quantitative noise features** — Shannon, multi-scale Hurst, CUSUM, Kolmogorov proxy, ADF, ΔSMA, topology proxies, solar/geomagnetic context  
2. **Anomaly score** — Isolation Forest past-only, trained on **baseline + asset** normality  
3. **Alerts** — elevated score and/or day-over-day shift on **suspects** (and platform-health flags on assets)  
4. **Priority** — XGBoost weak labels, fuzzy calibration, suspect×asset pair risk, Kelly attention  
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
| **Micro-trajectory / persistence** | Multi-scale Hurst & Shannon, CUSUM, ΔSMA, maneuver proxies |
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
Priority: XGB + fuzzy + pair_risk + Kelly + data quality
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

| Block | Examples | Role in analysis |
|-------|----------|------------------|
| Keplerian | SMA, ecc, inc, RAAN, \(n\) | Geometry |
| Deltas / activity | ΔSMA 7d/30d, maneuver count | Relocation / active ops |
| Persistence | Hurst full/short, \(\Delta H\), Shannon full/short | Micro-trajectory / sustained control |
| Complexity / breaks | Kolmogorov proxy, L1-CUSUM, ADF, Mandelbrot tail | Pattern complexity, regime change |
| Topology proxies | Chern–Simons, Ricci, H0/H1 (proxy mode) | Structural support features |
| **Space weather (GFZ)** | F10.7, Ap, Kp, 7d deltas, geomagnetic_storm | Solar/geomagnetic context for LEO drag vs maneuver |
| Pairs (not in IF) | min distance, cointegration | Shadowing / proximity priority |

**IF** measures series noise. **Pairs / XGB** rank operational attention.

---

## 5. Models

| Layer | Function |
|-------|----------|
| Feature engine (`engine.py`) | Deterministic math → noise vector |
| Monitor Isolation Forest | Normality = baseline+asset; daily anomaly scores |
| Pipeline Isolation Forest | Separate artifact for priority stack |
| XGBoost | Weak-label priority tiers (operational) |
| Fuzzy / Kelly / DQ | Soft calibration, attention budget, reliability |
| Pair score | Suspect×asset relationship risk |
| Bob | Natural-language briefing from computed scores |
| Registry | `models/registry.json` — versioned micro-models |

---

## 6. Validation (Claims A + B)

| Claim | Statement | GEO headline result |
|-------|-----------|---------------------|
| **A** | Interest cases at open-source anchors show elevated past-only IF scores / hard hits | **5/5** hard · mean max **~0.65** |
| **B** | Civil EO placebos under the same protocol stay lower | **0/7** hard · mean max **~0.46** · p95 **~0.50** |
| Separation | Interest scores stochastically higher | Gap **~0.19** · Mann–Whitney **p≈0.001** |

Open-source reports (Gunter, CSIS, SWF, press) supply **event windows** \(t_{\mathrm{peak}}\) for evaluation. Expanded LEO/MEO interest panels are reported separately (hard-hit rate lower; GEO remains the headline panel).

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
python scripts/run_anomaly_monitor.py seed-history --hf --start-year 2014
python scripts/run_anomaly_monitor.py seed-space-weather --force --start-year 2014
python scripts/run_anomaly_monitor.py run-daily
powershell -File scripts/sync_frontend_data.ps1
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

---

## 10. Repository layout

```
Athena-SDA/
├── README.md
├── requirements.txt
├── scripts/                 # monitor, walkforward, paper validation, plots, sync
├── src/
│   ├── engine.py            # quantitative math
│   ├── space_weather.py     # GFZ indices
│   ├── models.py            # features + IF/XGB
│   ├── doctrine.py          # military roles
│   ├── calibration.py       # threshold from normality quantiles
│   ├── anomaly_monitor.py   # daily scoring
│   ├── walkforward.py
│   ├── pair_score.py
│   ├── bob.py
│   └── frontend/            # React mission board + globe
├── models/
├── data/
└── docs/paper/              # article, figures, claims, limitations
```

---

## 11. Security and citation

- Secrets only in `.env`  
- **GFZ** Kp/Ap/F10.7 — Matzka et al. / GFZ terms  
- **TLE** — CelesTrak / Space-Track / HF mirrors per provider terms  
- **Open reports** — Gunter, CSIS, AMOS/SWF, press as evaluation anchors  

---

*Athena-SDA — quantitative orbital noise analysis and micro-anomaly alerts for military-first SDA.*
