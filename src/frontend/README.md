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
| **Left dock** | Threat Board + **Route Cross** + catalog layers |
| **Right dock** | Selected object telemetry / fusion notes + Bob copilot shell |
| Top | Brand, UTC clock, search, **Cross** toggle |
| Bottom | Time controller (sim speed) |

Docks can be toggled with **Board** / **Intel** buttons.

### Route Cross (two-orbit compare)

1. Click **Cross** (top bar) or enable **Route cross** in the left dock.
2. Fill **slot A** and **slot B** by clicking sats on the globe, search, or “Selected → A/B”.
3. The globe draws both full orbits (cyan / magenta) and yellow markers:
   - **Orbit-path proximity** — closest points between the two rings (geometry)
   - **Time-synced TCA** — minimum range in the next ~3 hours (same sim clock)
4. Yellow line connects the geometric closest pair.

## Stack

- Vite + React + TypeScript + Tailwind
- Three.js globe engine
- CelesTrak TLE feeds (+ offline snapshots in `public/data/`)
- Athena demo catalog: `src/lib/athena-tracks.ts`

## Data from the Python pipeline

The UI reads the latest ML artifacts copied from `data/alerts/` into `public/data/`:

```bash
# Linux
bash scripts/sync_frontend_data.sh
# Windows
powershell scripts/sync_frontend_data.ps1
```

- `risk_report_latest.json` — mission board rows (threat colors, anomaly scores, pair risk, data quality)
- `anomalies_latest.json` / `proximity_latest.json` — alert lists
- `walkforward_summary.json` — PoC summary (Open PoC for judges panel)
- `reports/` — quant HTML per object + `walkforward_poc.html`

Run the sync again after `python scripts/run_anomaly_monitor.py run-daily`.

## Next integrations

1. Wire Bob chat to `src/bob.py` / watsonx (currently local template briefing)
2. Live TLE ingestion per watchlist NORAD (currently offline snapshots)
