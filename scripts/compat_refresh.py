#!/usr/bin/env python3
"""Refresh back/front artifacts so the mission board matches the latest contracts.

  python scripts/compat_refresh.py

- Enriches risk_report_latest.json with pc/tca (does not rewrite pair_risk)
- Rematerializes investigation.v1
- Syncs into src/frontend/public/data
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import subprocess

from src.conjunction import enrich_risk_report  # noqa: E402
from src.config import ALERTS_DIR  # noqa: E402
from src.object_layer import write_investigation  # noqa: E402


def _write(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


def main() -> int:
    report_path = ALERTS_DIR / "risk_report_latest.json"
    if not report_path.exists():
        print("no risk_report_latest.json — skip pair enrich")
    else:
        report = json.loads(report_path.read_text(encoding="utf-8"))
        report = enrich_risk_report(report)
        _write(report_path, report)
        day = report.get("day")
        if day:
            dated = ALERTS_DIR / f"risk_report_{day}.json"
            _write(dated, report)
        n = sum(1 for p in (report.get("top_pairs") or []) if p.get("pc") is not None)
        print(f"risk_report enriched · {n} top_pairs with pc/tca")

    path = write_investigation()
    print(f"investigation.v1 → {path}")

    return subprocess.call(
        [sys.executable, str(ROOT / "scripts" / "sync_frontend_data.py"), "--quiet"]
    )


if __name__ == "__main__":
    raise SystemExit(main())
