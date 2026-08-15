#!/usr/bin/env python3
"""
Cross-platform sync of the latest ML alert artifacts into the frontend
public/ folder (replaces sync_frontend_data.ps1 + sync_frontend_data.sh).

Usage:
    python scripts/sync_frontend_data.py [--quiet]

Mirrors the file set the mission board reads from src/frontend/public/data:
  - risk_report_latest.json, anomalies_latest.json, proximity_latest.json
  - walkforward_summary.json, feature_ablation_latest.json
  - paper_validation_latest.json, investigation_latest.json
  - walkforward/wf_*.json (event replay curves)
  - reports/*.html (quant HTML reports)
"""
from __future__ import annotations

import argparse
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "alerts"
DST = ROOT / "src" / "frontend" / "public" / "data"

JSON_FILES = [
    "risk_report_latest.json",
    "anomalies_latest.json",
    "proximity_latest.json",
    "walkforward_summary.json",
    "feature_ablation_latest.json",
    "paper_validation_latest.json",
    "investigation_latest.json",
    "alert_state.json",
]


def copy_file(src: Path, dst_dir: Path, quiet: bool) -> None:
    dst_dir.mkdir(parents=True, exist_ok=True)
    if src.is_file():
        shutil.copy2(src, dst_dir / src.name)
        if not quiet:
            print(f"  + {src.name}")
    elif not quiet:
        print(f"  - missing {src.name} (skipped)")


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync ML artifacts into frontend public/")
    parser.add_argument("--quiet", action="store_true", help="Suppress per-file output")
    args = parser.parse_args()

    print(f"Sync frontend data -> {DST}")
    for name in JSON_FILES:
        copy_file(SRC / name, DST, args.quiet)

    # Walk-forward per-event curves (event replay UI)
    wf_src = SRC / "walkforward"
    if wf_src.is_dir():
        wf_dst = DST / "walkforward"
        wf_dst.mkdir(parents=True, exist_ok=True)
        curves = sorted(wf_src.glob("wf_*.json"))
        for c in curves:
            shutil.copy2(c, wf_dst / c.name)
        if not args.quiet:
            print(f"  + walkforward/ ({len(curves)} event curves)")

    # Quant HTML reports
    rdir = SRC / "reports"
    if rdir.is_dir():
        rdst = ROOT / "src" / "frontend" / "public" / "reports"
        rdst.mkdir(parents=True, exist_ok=True)
        reports = sorted(rdir.glob("*"))
        n = 0
        for r in reports:
            if r.is_file():
                shutil.copy2(r, rdst / r.name)
                n += 1
        if not args.quiet:
            print(f"  + reports/ ({n} files)")

    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
