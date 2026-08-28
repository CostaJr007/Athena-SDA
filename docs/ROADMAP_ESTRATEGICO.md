# Athena-SDA — Strategic Roadmap (post-Quick-Wins)

> Military scope / Palantir Gotham-Foundry. Quick-wins S0–S4 + S6 (now wired
> into the UI: `investigation.v1` + FSM via sidecar) are in the code.
> Initial T1–T9 slices (extracted hotkeys, code-split, Pc/TCA extras,
> Document, cited RAG, what-if, watchlist API, compose) already exist.
> This document covers what is **still deep**: the globe monolith, rich
> temporal hops, operational Pc with real covariance, dense RAG.

Effort: **S** = small (≤1 week) · **M** = medium (1–2 weeks) · **L** = large (2–4 weeks).

## Track overview

| # | Track | Effort | Depends on | Output |
|---|-------|--------|------------|--------|
| T1 | Frontend monolith refactor | M | — | `Home.tsx`/`globe-engine.ts` split into modules + Vitest |
| T2 | Multi-hop object-centric graph (search-around) | L | T1, `object_layer.py` | 2–3 hop navigation in `InvestigationCanvas` |
| T3 | Conjunction/proximity with covariance (Pc + TCA) | L | — (backend) | `pair_score.py` with SGP4 + covariance ellipsoid |
| T4 | Documents/OSINT as first-class objects (multi-INT) | M | `ontology.json` | `Document` type, open-report ingestion |
| T5 | Bob → analytical copilot with RAG + citation | M | `bob.py`, `docs/` | Multi-turn Q&A with cited sources |
| T6 | What-if / adversary sandbox | S–M | `utils.py`, `EventReplayPanel` | Synthetic maneuver injection + detection |
| T7 | Dynamic watchlist + Space-Track ingest | M | `download_spacetrack.py`, UI | NORAD/role management from the UI |
| T8 | Frontend code-splitting + performance | S | T1 | Chunk < 500 kB, globe lazy-load |
| T9 | Operations & deploy | M | Dockerfile (done) | Compose, persistence, monitoring |

## Schedule (weeks 1–8, 3 parallel tracks)

```
Week     1     2     3     4     5     6     7     8
Track A (frontend/UI)
        [T1 monolith refactor]  [T2 multi-hop graph        ]
                                      [T8 code-split ]
Track B (astrodynamics/backend)
        [T3 SGP4 + covariance                 ]
        [T4 multi-INT documents  ]
Track C (AI/operations)
        [T5 Bob RAG+citation      ]
        [T6 what-if sandbox]
        [T7 dynamic watchlist        ]
        [T9 deploy/compose                          ]
```

## Phase detail

### Phase 1 (Weeks 1–2) — Foundations

**T1 — Frontend monolith refactor (M)**
- Target: `src/frontend/src/pages/Home.tsx` (1,272 lines) and `src/frontend/src/lib/globe-engine.ts` (1,390 lines).
- Plan: extract 3D state/UI into hooks (`useGlobe`, `useSelection`, `useTimeline`), separate the Three.js engine from React rendering, type the contracts with `zod` (already a dependency).
- Exit: clean `npm run build`; HUD components tested with Vitest; no behavior regression.
- **Blocks** T2 and T8.

**T4 — Documents/OSINT as objects (M)**
- Add `Document`/`Intel` types to `src/ontology.json` (Entity/Event/Document categories already foreseen in the docstring).
- Ingest `data/catalog/events_walkforward.json` + open reports (Gunter/CSIS/SWF) as objects linkable to `Case`/`Satellite` via `validatedBy`/`mentions`.
- Exit: `materialize_investigation` emits `Document` objects with provenance; `investigation.v1` schema updated.

### Phase 2 (Weeks 2–4) — Analytical capability

**T3 — SGP4 conjunction with covariance (L)**
- Today `pair_score.py` uses distance + cointegration/DCCA. Upgrade to SGP4 propagation (the frontend already has `propagator.worker.ts` + `satellite.js`; the backend needs `sgp4>=2.22` — currently commented in `requirements.txt`).
- Deliver Pc (collision probability) and TCA (time of closest approach) with a per-pair covariance ellipsoid for suspect→asset.
- Exit: `score_all_pairs` emits `pc`/`tca`/`covariance` per pair; `risk_report.v1.schema.json` updated; regression tests with synthetic pairs.

**T5 — Bob RAG + citation (M)**
- On top of `src/bob.py` (tool-calling already sketched): add a RAG index over `docs/` (proof dossier, paper, references, patents) and multi-turn briefing **with source citation**.
- Invariant to preserve: Bob **explains**, never recomputes scores (declared project principle).
- Exit: briefing answers "what supports this alert?" citing the exact artifact.

### Phase 3 (Weeks 3–6) — Interactivity and ingest

**T2 — Multi-hop graph (L)**
- On top of `src/object_layer.py` (links already exist: `threatens`, `sameAsset`, `samePeak`, `validatedBy`, `weather`, `fusedAs`): 2–3 hop temporal navigation in the `InvestigationCanvas`.
- Search by any entity (NORAD, event, document, operator) with neighborhood visualization.
- Exit: expand-neighbors works; results materialized in `investigation_latest.json`.

**T6 — What-if sandbox (S–M)**
- On top of `src/utils.py` (`generate_mock_tle_history`, `generate_shadowing_pair`) and `EventReplayPanel`: inject a synthetic maneuver into a suspect and check whether the detection (IF + CUSUM/EWMA) fires.
- Exit: CLI/UI demonstrates detection of an injected maneuver → serves as continuous sensitivity validation.

**T7 — Dynamic watchlist (M)**
- On top of `download_spacetrack.py` + `data/catalog/watchlist.json`: UI to add/remove NORAD, reclassify role (asset/suspect/baseline), and schedule ingest (`install_daily_cron.sh`).
- Exit: catalog change persists, retrains the baseline, and reflects on the board without manual JSON editing.

### Phase 4 (Weeks 6–8) — Operations and polish

**T8 — Code-splitting (S)**
- Vite reports a ~985 kB chunk. Use `React.lazy`/`import()` for the globe and heavy panels; `manualChunks` for `three`/`satellite.js`/`recharts`.
- Exit: no chunk > 500 kB; better TTFB.

**T9 — Operations & deploy (M)**
- `docker-compose.yml` (backend pipeline + frontend build), volumes for `data/` and `models/`, healthcheck, backup/restore documentation.
- Exit: `docker compose up` brings up the board + reproducible pipeline.

## Dependency order (summary)

1. **T1** first (unlocks T2 and T8).
2. **T3 and T4** are independent and can run in parallel with T1 (pure backend).
3. **T5, T6, T7** are independent of T1; they only need the quick-wins already done.
4. **T9** last (packages everything).

## Global Definition of Done

- `python -m pytest -q` green; `python scripts/smoke_test.py` green.
- `cd src/frontend && npm run build` green (no chunk warning).
- New artifacts respect the doctrine invariants (immutable scores, past-only, baseline+asset = normality).
