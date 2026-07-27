#!/usr/bin/env python3
"""Generate quantitative HTML rationale reports from risk_report_latest.json."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> None:
    p = argparse.ArgumentParser(description="Athena quant threat rationale HTML")
    p.add_argument(
        "norad",
        nargs="?",
        type=int,
        help="NORAD id (omit with --all)",
    )
    p.add_argument("--all", action="store_true", help="Generate for full board + index")
    p.add_argument(
        "--risk",
        type=Path,
        default=None,
        help="Path to risk_report JSON (default: data/alerts/risk_report_latest.json)",
    )
    args = p.parse_args()

    from src.quant_report import write_all_quant_reports, write_quant_report

    if args.all or args.norad is None:
        paths = write_all_quant_reports(risk_path=args.risk, also_public=True)
        print(f"Wrote {len(paths)} quant reports + index")
        print("  data/alerts/reports/index.html")
        print("  src/frontend/public/reports/index.html")
        return

    out = write_quant_report(int(args.norad), risk_path=args.risk, also_public=True)
    print(f"Wrote {out}")
    print(f"  public: src/frontend/public/reports/quant_{args.norad}_latest.html")


if __name__ == "__main__":
    main()
