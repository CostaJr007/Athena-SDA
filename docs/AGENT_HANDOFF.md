# Athena-SDA — Handoff Instructions for another AI

> Continuity document. Goal: let an autonomous AI agent **analyze the project
> and continue the work** without the context of the previous session.
> Read this file **before** touching the code.

## 1. What the project is

**Athena-SDA** — a *military-first* Space Domain Awareness (SDA) copilot.
It turns public TLE (Two-Line Elements) history + space weather (GFZ
F10.7/Ap/Kp) into **quantitative orbital noise analysis** and **micro-anomaly
detection** over a curated watchlist (24 NORADs: asset/suspect/baseline).

Pipeline: `TLE → quantitative features (engine) → past-only Isolation Forest →
priority (XGB/Dempster-Shafer/pairs) → risk report JSON → mission board
(React/Three.js)`.

Declared inspiration: **Palantir Gotham/Foundry** — object-centric, link graph,
typed ontology, schema contracts, lineage/provenance, an LLM that explains but
**does not recompute** scores.

## 2. Current state (what has been done)

Next round (ops + S6 closed + T1–T9 slices):

- Real cron (marker as *trailing* comment, not a prefix that commented out the job).
- `run_daily_ingest.sh` exits 1 if any stage fails; sync via `.py`.
- UI consumes `investigation.v1`; ACK calls the FSM (`POST /api/alert-state`).
- Pc/TCA extras in `src/conjunction.py` (do not rewrite `pair_risk`).
- `Document` type, cited RAG in Bob/Granite, what-if, watchlist API, compose.

Completed in the previous round:

- **S0 bugs fixed** in `src/anomaly_monitor.py`:
  - versioned snapshot `isolation_forest_monitor_<date>.joblib` (previously
    used an undefined `meta_out` + `re` without import → never worked);
  - `resolve_thresholds()` de-`None`'d the `--threshold` default (`None` broke
    `estimate_anomaly_onset` with `float(None)`).
- **Logging** (`src/logging_setup.py`) + conversion of silent `except: pass`
  in critical paths.
- **Tests**: 37 pytest tests in `tests/` + CI in `.github/workflows/ci.yml`.
- **Packaging**: `pyproject.toml`, `requirements-dev.txt`, `Dockerfile`,
  `.dockerignore`.
- **Hygiene**: `scripts/sync_frontend_data.py` (replaces `.ps1`/`.sh`) +
  `.gitignore` for regenerable artifacts.
- **Product (S6)**: alert lifecycle workflow and provenance/lineage in
  `src/object_layer.py`; continuous validation harness in
  `scripts/run_continuous_validation.py`.

## 3. How to check project health

```bash
cd /run/media/adeilsoncosta/Novo\ volume/Athena-SDA   # adjust the real path

# Tests (fast, no network)
python -m pytest -q                 # expected: 61+ passed

# Quant core smoke test
python scripts/smoke_test.py        # expected: SMOKE OK

# Compilation
python -m py_compile src/*.py scripts/*.py

# Frontend (typecheck + build)
cd src/frontend && npm run build    # expected: success (known chunk warning)

# Daily pipeline (requires data in data/history)
python scripts/run_anomaly_monitor.py status
python scripts/run_anomaly_monitor.py run-daily --skip-if-fresh
python scripts/run_continuous_validation.py
python scripts/compat_refresh.py     # pc/tca + investigation.v1 + UI sync
python scripts/sync_frontend_data.py --quiet
```

## 4. File map (what matters)

| Path | Role |
|---------|-------|
| `src/config.py` | Feature schema (`FEATURE_COLUMNS`, `IFOREST_COLUMNS`, `XGB_COLUMNS`) and constants |
| `src/engine.py` | Quant feature engine (LZ76, DFA, MMD, CUSUM/EWMA, SSA, BOCPD…) |
| `src/models.py` | `extract_satellite_features`, IF/XGB training, `predict_threat` |
| `src/anomaly_monitor.py` | Daily loop: trains baseline, scores, alerts |
| `src/object_layer.py` | Gotham-lite layer: objects, links, provenance, **alert workflow** |
| `src/doctrine.py` | Role policy (asset/suspect/baseline) and `classify_military_status` |
| `src/evidence.py` | Dempster-Shafer fusion (belief/plausibility/conflict) |
| `src/pair_score.py` | Suspect×asset risk (distance + cointegration/DCCA) |
| `src/bob.py` | LLM copilot (Granite/watsonx) — tool-calling, briefing |
| `src/ontology.json` | Typed ontology (Satellite, Alert, Case, Weather, Evidence) |
| `src/contracts.py` | Schema validation (`risk_report.v1`, `investigation.v1`) |
| `src/tle_store.py` | Epoch store (parquet/CSV) + CelesTrak/HF ingest |
| `scripts/run_anomaly_monitor.py` | Main CLI (argparse) |
| `scripts/run_continuous_validation.py` | Drift/calibration health check |
| `scripts/sync_frontend_data.py` | Syncs artifacts to `src/frontend/public/data` |
| `src/frontend/src/pages/Home.tsx` | **UI monolith** (1,272 lines) |
| `src/frontend/src/lib/globe-engine.ts` | **3D globe monolith** (1,390 lines) |
| `src/frontend/src/workers/propagator.worker.ts` | Orbital propagator (worker) |
| `tests/` | 50+ pytest tests (S0, object layer, conjunction, RAG, what-if, ops) |
| `docs/ROADMAP_ESTRATEGICO.md` | Schedule of what **remains** (tracks T1–T9) |

## 5. What is left (strategic)

See `docs/ROADMAP_ESTRATEGICO.md` for the full schedule. Track summary:

- **T1** Refactor the frontend monolith (`Home.tsx` + `globe-engine.ts`) — **first**, unlocks T2/T8.
- **T2** Multi-hop object-centric graph (search-around) in `InvestigationCanvas`.
- **T3** Operational Pc with 6D ellipsoid (today: Foster + optional Kepler/SGP4 extras; `pair_risk` intact).
- **T4** OSINT ingestion beyond the walk-forward sources (`Document` type already exists).
- **T5** Dense RAG / embeddings (today: token overlap + `path#heading` citation).
- **T6** What-if on real history (today: in-memory sandbox + CLI).
- **T7** Watchlist that retrains the baseline (today: API + editor, JSON persistence).
- **T8** Globe lazy-loading (isolated Three still > 500 kB).
- **T9** Backup/restore and full-stack health (`docker-compose.yml` already brings up board + sidecar).

## 6. Golden rules (DO NOT break)

1. **Scores are immutable.** No UI/LLM code may rewrite `anomaly_score`, XGB classes, or detection. Alert state (`OPEN/ACKNOWLEDGED/...`) is bookkeeping, not analysis.
2. **Past-only.** IF trains only on windows ending before the cutoff (holdout ≥ 1 day). "Today" is scored, never trained.
3. **Normality = baseline + asset.** Suspects **do not** enter IF training. Commercial constellations (Starlink) are excluded.
4. **Bob explains, never recomputes.** The LLM cites the quant; it never generates a new score.
5. **Geometry in features and labels.** If `min_distance_to_military_km`/`cointegration_pvalue` feed XGB, the (weak) labels must use the same signals.

## 7. Environment gotchas (read before assuming)

- The host runs **Python 3.14.6**, but `requirements.txt` pins `pandas<3` and `xgboost<3`; the local environment has `pandas 3.0.3` and `xgboost 3.3.0` (out of range). Use **Python 3.11/3.12** (like CI/Dockerfile) for real reproducibility.
- **`git lfs` is NOT installed.** Models (`*.joblib`) and `*.parquet` are versioned in git — an open hygiene issue.
- **There are many uncommitted WIP files** in the working tree (e.g., `src/object_layer.py`, HUD components, `scripts/run_daily_ingest.sh`). When committing, separate your own new code from pre-existing WIP.
- The frontend uses **Tailwind v3 + React 19 + Vite 7 + Three.js**; the build emits a > 500 kB chunk warning (track T8).
- `--threshold` CLI default is `None` by design; always pass it through `resolve_thresholds()` (never do `float(None)`).

## 8. Where to start

1. Run section 3 to confirm a green baseline.
2. Read `docs/ROADMAP_ESTRATEGICO.md` and pick **track T1** (lowest risk, biggest unlock).
3. Before each change, run `python -m pytest -q` and, if touching the frontend, `npm run build`.
4. Keep the invariants in section 6 and document any new artifact in the README.
