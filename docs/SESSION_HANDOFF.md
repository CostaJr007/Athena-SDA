# Athena-SDA — Session handoff

**Last update:** 2026-07-27  
**Workspace:** project root  
**Repo:** https://github.com/CostaJr007/Athena-SDA  

Use at session start: *“read docs/SESSION_HANDOFF.md and continue”*.

---

## 1. Product focus

| Priority | Content |
|----------|---------|
| **Core** | Quant + ML for anomaly, risk, proximity/shadowing |
| **Narrative** | Military SDA / COP intelligence — not a generic civil tracker |
| **UI** | Globe + board showcase; polish after stable ML JSON |
| **Bob** | Explains scores after quant — does not invent threats |

**One-line pitch:** Military-first watchlist + multi-year TLE + daily inject + Isolation Forest on the past + score today + space weather + pairs + Fuzzy/XGB/Kelly + Bob post-quant + walk-forward pre-report.

---

## 2. Closed decisions

1. Frontend base = Kimi `src/frontend/` (not Lovable backup).
2. Visual: black panels, stars chrome, zinc/white text, emerald accent.
3. Route Cross lab: two sats, orbits + TCA geometric proximity.
4. Small watchlist (~15–25 NORADs): assets + suspects + baseline.
5. Canonical catalog: `data/catalog/watchlist.json` with roles.
6. Prefer CelesTrak **CATNR** ingest.
7. Heavy military UI polish deferred until ML JSON stable.

---

## 3. Implemented

- Catalog + roles wired through tle_store / monitor / pipeline
- History ~12.5 years (2014→), 24 sats, space weather GFZ
- Daily protocol series=past / today=score
- Walk-forward past-only + Gemini-coherent fixes
- Pair score + risk_report v1
- Frontend: Mission board, Track intel, Catalog focus (all/watchlist/military), country flags, quant HTML reports
- Anomaly onset estimate on board

---

## 4. Ops commands

```bash
python scripts/run_anomaly_monitor.py status
python scripts/run_anomaly_monitor.py run-daily
PYTHONPATH=. python scripts/run_quant_report.py --all
bash scripts/sync_frontend_data.sh
cd src/frontend && npm run dev   # http://127.0.0.1:3000
```

---

## 5. Pitfalls

1. High train accuracy on heuristic labels is not espionage proof.
2. Ricci/homology/Chern–Simons are proxies.
3. CelesTrak GROUP=active may 403 — use CATNR.
4. HOSTILE UI badge ≠ confirmed hostile intent.
5. Onset dates are TLE-window estimates.
6. Do not commit `.env` / tokens / `node_modules`.

---

## 6. Next

- Push remote if credentials available
- Optional Bob watsonx
- Optional deeper polish
