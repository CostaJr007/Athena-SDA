#!/usr/bin/env python3
"""Inject a synthetic SMA burn and report whether CUSUM/EWMA fire.

  python scripts/run_whatif.py
  python scripts/run_whatif.py --norad 40258 --delta-km 4.5
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.whatif import run_whatif  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(description="Athena-SDA what-if maneuver sandbox")
    p.add_argument("--norad", type=int, default=9001)
    p.add_argument("--delta-km", type=float, default=4.5)
    args = p.parse_args()
    result = run_whatif(args.norad, delta_km=args.delta_km)
    print(json.dumps(result, indent=2))
    return 0 if result.get("fired") else 1


if __name__ == "__main__":
    raise SystemExit(main())
