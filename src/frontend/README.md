# ATHENA-SDA Frontend

Tactical Space Domain Awareness console: live globe + TLE propagation + mission board + conjunction lab.

Engine: Three.js / satellite.js (SGP4). Chrome UI is Athena-branded (black panels, emerald accents) — not a consumer “tracker” skin.

## Run

```bash
cd src/frontend
npm install
npm run dev
```

Open http://localhost:3000

## Layout

| Zone | Content |
|------|---------|
| Center | 3D Earth + live TLE propagation (Three.js + satellite.js) |
| **Investigation (G)** | Object graph (Satellite → Asset / Alert / Case) + **quant fingerprint** |
| **Left dock** | Threat Board + histogram cross-filters + **Route Cross** |
| **Right dock** | Telemetry · fusion · compact fingerprint · Bob |
| Top | Brand, **Claims A+B seal**, UTC clock, search, Graph / PoC |
| Bottom | Time controller (sim speed) |
| **Ctrl+K** | Command palette — jump to object, filter, or surface |

Docks toggle with **Board** / **Intel**. Keyboard: `Ctrl+K` palette · `G` investigate · `P` proof · `/` search · `B`/`I`/`C` docks.

The investigation canvas is the product signature: a typed ontology graph plus a cited noise fingerprint (LZ76, DFA, Shannon, CUSUM, EWMA, BOCPD, DS belief). Open it with **Graph** or `G` after selecting an object — the app does not start with it open.

### Conjunction lab (two-orbit compare)

1. Click **Conj** (top bar) or enable **Conjunction lab** in the left dock.
2. Fill **slot A** and **slot B** by clicking sats on the globe, search, or “Sel → A/B”.
3. The globe draws both full orbits (teal / orange) and amber markers:
   - **Orbit-path proximity** — closest points between the two rings (geometry)
   - **Time-synced TCA** — minimum range in the next ~3 hours (same sim clock)
4. Amber line connects the geometric closest pair.

## Stack

- Vite + React + TypeScript + Tailwind
- Three.js globe engine
- CelesTrak TLE feeds (+ offline snapshots in `public/data/`)
- Catalog layers: `src/lib/satellites.ts`

## Data from the Python pipeline

The UI reads the latest ML artifacts copied from `data/alerts/` into `public/data/`:

```bash
# Cross-platform (canonical)
python scripts/sync_frontend_data.py
```

- `risk_report_latest.json` — mission board rows (threat colors, anomaly scores, pair risk, data quality)
- `paper_validation_latest.json` — Claims A+B headline (GEO 5/5 · EO 0/7 · p)
- `anomalies_latest.json` / `proximity_latest.json` — alert lists
- `walkforward_summary.json` + `walkforward/wf_*.json` — PoC replay curves
- `reports/` — quant HTML per object + `walkforward_poc.html`

Run the sync again after `python scripts/run_anomaly_monitor.py run-daily`.

## IBM Granite (ontology + graph)

The investigation canvas calls IBM Granite on watsonx.ai to explain typed
objects and links. The model runs **server-side** — not in the browser, not Bob.

```bash
# from repo root (optional keys in .env)
python scripts/serve_granite_explain.py
# Vite proxies /api/explain → http://127.0.0.1:8787
```

Without `WATSONX_APIKEY` + `WATSONX_PROJECT_ID` the sidecar still answers
with a local ontology walk (scores stay immutable).
