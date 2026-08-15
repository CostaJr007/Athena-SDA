#!/usr/bin/env python3
"""Index risk_report + walk-forward into athena.investigation.v1.

  python scripts/materialize_investigation.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.object_layer import materialize_investigation, write_investigation  # noqa: E402


def main() -> int:
    bundle = materialize_investigation()
    path = write_investigation(bundle)
    print(f"wrote {path}  objects={len(bundle.get('objects') or [])}  day={bundle.get('day')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
