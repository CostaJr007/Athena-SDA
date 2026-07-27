# Athena-SDA

**Space Domain Awareness (SDA) Copilot** — orbital intelligence combining **real data (TLE + space weather)**, a **mathematical noise framework**, **machine learning** (Isolation Forest + XGBoost), and a **copilot** that explains precomputed scores to prioritize attention and validate lead-time before open-source reports.

| | |
|--|--|
| **Challenge** | IBM SkillsBuild AI Builders — *Advance Space Exploration with AI* |
| **Focus** | Military-first SDA (protect assets, monitor suspects) — COP/intelligence spirit, not a generic civil tracker |
| **Repo** | [github.com/CostaJr007/Athena-SDA](https://github.com/CostaJr007/Athena-SDA) |
| **Watchlist** | 24 NORADs (7 asset · 11 suspect · 6 baseline) |
| **Training history** | **~12.5 years** (2014-01-01 → 2026-07-25) |

> Session handoff: [`docs/SESSION_HANDOFF.md`](docs/SESSION_HANDOFF.md)  
> Full ML report: [`docs/RELATORIO_COMPLETO_ML_ATHENA_SDA.md`](docs/RELATORIO_COMPLETO_ML_ATHENA_SDA.md)  
> Walk-forward pre-report: [`docs/RELATORIO_WALKFORWARD_PRE_REPORT_ML_NOVO.md`](docs/RELATORIO_WALKFORWARD_PRE_REPORT_ML_NOVO.md)

---

## 1. Overview

Athena-SDA answers three operational questions:

1. **Did this object’s orbital series change anomalously** relative to its past (and space weather at the time)?  
2. **Does proximity to a protected asset** (geometry / cointegration) raise priority?  
3. **Does mathematical noise rise before** public report anchors (walk-forward past-only)?

The 3D globe is the **showcase**. The technical argument is **quant + ML + real data**.

```
Public sources (TLE + GFZ)
        │
        ▼
20-epoch window → features (Kepler + math + space weather + pairs)
        │
        ├─► Isolation Forest (baseline = PAST series) → anomaly_score
        └─► XGBoost / Fuzzy / Kelly / pair attention → risk board
                    │
                    ▼
         Bob explains precomputed scores
         Walk-forward validates lead-time vs open-source reports
```

**Daily protocol:** train “normal” only with the **series through yesterday**; **today’s data** is only compared (no day leakage into training). See [`docs/PROTOCOLO_DETECCAO_DIARIA.md`](docs/PROTOCOLO_DETECCAO_DIARIA.md).

---

## 2. Data — volumes, sources, Git

### Idea

The seed **downloads** a large TLE catalog (multi-GB Hugging Face cache) and **persists only the watchlist** (tens of MB in the repo).

| Resource | Approx size | On GitHub? | Role |
|----------|-------------|------------|------|
| HF cache `space-track-tle-history` | ~15 GB | No | Raw multi-year download |
| Filtered TLE parquet | ~13 MB | Yes | Training/scoring base (~250k epochs) |
| Space weather daily | ~0.1 MB | Yes | F10.7, Ap, Kp |
| ML models | ~5 MB | Yes | IF, XGB, RKHS |
| Alerts + walk-forward | ~1 MB | Yes | Daily score + WF |
| **Useful total in repo** | **~20–25 MB** | Yes | Demo-ready clone |

### Coverage

| Metric | Value |
|--------|--------|
| TLE range | **2014-01-01 → 2026-07-25** (~12.56 years) |
| Satellites | **24** NORADs |
| Epochs | **~249,558** |
| Roles | 7 **asset** · 11 **suspect** · 6 **baseline** |

### Sources

| Layer | Source |
|-------|--------|
| Historical TLE | Hugging Face `juliensimon/space-track-tle-history` (watchlist-filtered) |
| Daily TLE | CelesTrak GP by `CATNR` |
| Space weather | GFZ Potsdam (Kp, Ap, F10.7, SN) |
| Validation events | Open-source report anchors (Gunter, CSIS, press) |

```bash
python scripts/run_anomaly_monitor.py seed-history --hf --start-year 2014
python scripts/run_anomaly_monitor.py seed-space-weather --force --start-year 2014
python scripts/run_anomaly_monitor.py status
```

---

## 3. Machine learning

| Model | Input | Output |
|-------|--------|--------|
| **Isolation Forest (monitor)** | 34 features | anomaly_score vs past baseline |
| **XGBoost** | 38 features | NORMAL / ANOMALOUS / SUSPECT / HOSTILE (+ proba) — heuristic labels |
| **RKHS reference** | feature subvector | typicality support |
| **Fuzzy Mamdani** | anomaly, dist, TLE age… | linguistic calibration |
| **Kelly** | proba × severity | attention budget |
| **Pair score** | dist + cointegration | pair_risk; attention = 0.45·anom + 0.55·pair |

Serious validation: walk-forward hit **5/5** interest vs **0/3** placebos (ML with space weather).

---

## 4. Mathematical framework

Each tool produces a **feature** (or auxiliary score). Isolation Forest learns the **joint distribution** of these signals in the past.

| Theory | Role in SDA |
|--------|-------------|
| Shannon entropy | Disorder of altitude change |
| Kolmogorov proxy | Complex control compresses poorly |
| Hurst (R/S) | Persistent low thrust vs mean reversion |
| L1-CUSUM | When the series broke |
| ADF | Non-stationarity support |
| Mandelbrot tail | Rare impulses |
| RKHS spectral anomaly | Typicality in feature space |
| Proximity + cointegration | RPO / shadowing |
| F10.7 / Ap / Kp | Drag vs maneuver context |

Detail: `docs/references/fundamentacao_matematica.md` (PT historical docs may remain; code/UI in English).

---

## 5. Inference pipeline

```
TLE history + daily CelesTrak + GFZ SW
 → data quality → features
 → pairs (dist/coint) + IF past-only
 → XGB + Fuzzy + Kelly
 → attention + risk board JSON
 → Bob · globe UI · walk-forward
```

---

## 6. Walk-forward (pre-report)

At each `asof`, IF trains only on windows ending before `asof − holdout` and scores the target.

| Result (current ML + SW) | Interest | Placebo |
|--------------------------|----------|---------|
| Hit score ≥ 0.50 | **100%** (5/5) | **0%** (0/3) |
| Mean lead-time first hit | **~201 days** | — |

```bash
python scripts/run_walkforward.py run
python scripts/run_walkforward.py summary
```

---

## 7. Install and run

```bash
cd Athena-SDA
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # optional WATSONX_*, SPACETRACK_*
```

**Never** commit `.env` or tokens.

### Daily ops

```bash
python scripts/run_anomaly_monitor.py run-daily
PYTHONPATH=. python scripts/run_quant_report.py --all
bash scripts/sync_frontend_data.sh
python scripts/run_anomaly_monitor.py status
```

### Dashboard and frontend

```bash
streamlit run app.py
cd src/frontend && npm install && npm run dev
# http://127.0.0.1:3000 — Mission board + quant reports + Catalog focus
```

Board contract: [`docs/SCHEMA_RISK_REPORT.md`](docs/SCHEMA_RISK_REPORT.md).  
Quant HTML: `public/reports/quant_<norad>_latest.html` (new tab from UI).

---

## 8. Repository layout

```
Athena-SDA/
├── app.py
├── scripts/          # monitor, walkforward, quant report, sync
├── src/              # engine, models, monitor, pair_score, quant_report, frontend/
├── models/           # IF, XGB, RKHS
├── data/             # history, SW, catalog, alerts, reports
├── docs/             # ML reports and handoff
└── requirements.txt
```

---

## 9. Scientific honesty (pitch)

| We claim | We do not claim |
|----------|-----------------|
| TLE and weather are real public data | That XGB “proves” classified hostility |
| Math + IF detect **regime deviation** | That accuracy ~95% = espionage detection |
| Walk-forward shows noise **before** open-source reports | An intention oracle |
| HF cache is multi-GB; repo holds the filtered store | That Git “lost” the download |

**Recommended sentence:**  
> “We download multi-year TLE history (cache ~15 GB), filter 24 objects of interest (~250k epochs, 2014–2026), inject GFZ weather, extract a mathematical noise vector, and train Isolation Forest on the series past. We validate lead-time on documented cases (Luch, Shiyan) with placebos.”

---

## 10. Security

- Secrets only in `.env` / environment  
- `.gitignore` blocks `.env`, `node_modules`, caches, large duplicates  

---

## 11. Data citation

- **GFZ** Kp/Ap/F10.7: cite Matzka et al. / GFZ terms (CC BY 4.0 for published indices).  
- **TLE**: public catalogs (CelesTrak / Space-Track mirrors); use per provider terms.  

---

*Athena-SDA — quant + ML + real data for Space Domain Awareness.*
