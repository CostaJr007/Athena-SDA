#!/usr/bin/env python3
"""Rebuild walkforward_latest/summary from per-event wf_*.json files."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.tle_store import ALERTS_DIR
from src.walkforward import WF_DIR, _summarize, load_events


def main() -> int:
    events = []
    for e in load_events():
        eid = e.get("id")
        fp = WF_DIR / f"wf_{eid}.json"
        if fp.exists():
            events.append(json.loads(fp.read_text(encoding="utf-8")))
    if not events:
        print("No per-event wf_*.json found")
        return 1
    summary = _summarize(events, anomaly_threshold=0.5)
    compact = {
        "generated_at": None,
        "params": {"anomaly_threshold": 0.5, "note": "rebuilt from per-event files"},
        "summary": summary,
        "events": [
            {
                "event_id": r.get("event_id"),
                "type": r.get("type"),
                "t_peak": r.get("t_peak"),
                "metrics": r.get("metrics"),
                "n_folds": r.get("n_folds"),
                "sources": r.get("sources"),
            }
            for r in events
        ],
    }
    latest = WF_DIR / "walkforward_latest.json"
    if latest.exists():
        old = json.loads(latest.read_text(encoding="utf-8"))
        compact["generated_at"] = old.get("generated_at")
        compact["params"] = old.get("params") or compact["params"]
    latest.write_text(json.dumps(compact, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    (ALERTS_DIR / "walkforward_summary.json").write_text(
        json.dumps(compact, indent=2, ensure_ascii=False, default=str), encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))
    print(f"Wrote {latest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
