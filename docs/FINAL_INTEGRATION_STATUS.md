# Final integration status — Athena-SDA

**Branch:** `main`  
**Language:** English (docs, paper, watchlist, UI copy)

## Stack closed loop

```
TLE history + GFZ weather
  → quant features (engine/models)
  → Isolation Forest (baseline+asset normality, past-only)
  → doctrine alerts (suspect detection / asset health / baseline calibration)
  → pairs + XGB priority
  → data/alerts/*_latest.json + investigation_latest.json
  → scripts/sync_frontend_data.py
  → src/frontend/public/data/*
  → React mission board (risk_report.v1)
```

## Backend

| Component | Status |
|-----------|--------|
| Military doctrine IF train | Done (`src/doctrine.py`) |
| Multi-scale DFA / Shannon / LZ76 / Page CUSUM | Done |
| Space weather in IF | Done (GFZ) |
| Calibration thr | Done (`src/calibration.py`) |
| Registry | Done (`models/registry.json`) |
| Walk-forward Claims A+B | Done (GEO 5/5 vs EO 0/7) |
| Paper pack + LaTeX + figures | Done (`docs/paper/`) |

## Frontend

| Component | Status |
|-----------|--------|
| Loads `risk_report_latest.json` | Done |
| Board scores / pairs / DQ | Done |
| Doctrine badges (`mil detect`, calibration) | Done |
| Summary mil detections + doctrine label | Done |
| Multi-scale keys typed in features_snapshot | Done |
| Walk-forward PoC panel | Done (in-HUD + `walkforward_poc.html`) |
| Object graph + quant fingerprint | Done (investigation canvas, `G`) |
| Command palette | Done (`Ctrl+K`) |
| Globe | Live CelesTrak TLE + SGP4; conjunction lab TCA (~3 h) |

## Daily refresh

```bash
python scripts/run_anomaly_monitor.py run-daily
python scripts/sync_frontend_data.py
# or the full orchestrator: bash scripts/run_daily_ingest.sh
cd src/frontend && npm run dev
```

## Paper

```bash
python scripts/run_paper_validation.py --threshold 0.50
python scripts/plot_prepeak_curves.py
cd docs/paper && pdflatex athena_sda_article.tex
```

## Compatibility verdict

**Operational FE↔BE contract is complete** for the mission board (`athena.risk_report.v1` + sync).  
**Scientific proof pack is complete** for demo and paper draft.  
Globe remains a visualization layer; quant truth is the risk report + walk-forward artifacts.

Graph Ask uses **Groq** (LLM) + **Tavily** (public web cites) via `/api/explain`.
Without those keys the same panel walks the graph locally. Scores stay immutable.
