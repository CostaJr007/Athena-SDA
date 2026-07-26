#!/usr/bin/env python3
"""
Athena-SDA — walk-forward validation CLI (POST training).

Examples:
  python scripts/run_walkforward.py run
  python scripts/run_walkforward.py run --step-days 21 --threshold 0.50
  python scripts/run_walkforward.py run --events luch2_geo_ops_2024,placebo_terra_2024h2
  python scripts/run_walkforward.py summary
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def cmd_run(args: argparse.Namespace) -> None:
    from src.walkforward import run_all_walkforward

    ids = None
    if args.events:
        ids = [x.strip() for x in args.events.split(",") if x.strip()]

    out = run_all_walkforward(
        event_ids=ids,
        step_days=args.step_days,
        holdout_days=args.holdout_days,
        anomaly_threshold=args.threshold,
        hit_window_days=args.hit_window_days,
    )
    s = out.get("summary") or {}
    print("\n========== WALK-FORWARD SUMMARY ==========")
    print(json.dumps(s, indent=2, ensure_ascii=False))
    print("==========================================")


def cmd_summary(args: argparse.Namespace) -> None:
    from src.tle_store import ALERTS_DIR
    from src.walkforward import WF_DIR

    path = ALERTS_DIR / "walkforward_summary.json"
    if not path.exists():
        path = WF_DIR / "walkforward_latest.json"
    if not path.exists():
        print("No walkforward summary yet. Run: python scripts/run_walkforward.py run")
        return
    data = json.loads(path.read_text(encoding="utf-8"))
    print(json.dumps(data.get("summary") or data, indent=2, ensure_ascii=False))
    print("\nPer event:")
    for e in data.get("events") or []:
        print(f"\n- {e.get('event_id')} ({e.get('type')}) peak={e.get('t_peak')}")
        for nid, m in (e.get("metrics") or {}).items():
            print(
                f"    #{nid} {m.get('object_name')}: hit={m.get('hit_at_event')} "
                f"soft={m.get('soft_hit_at_event')} lead={m.get('lead_time_days')} "
                f"max={m.get('anomaly_score_max')} placebo={m.get('is_placebo')}"
            )


def cmd_list_events(args: argparse.Namespace) -> None:
    from src.walkforward import load_events

    for e in load_events():
        print(
            f"{e.get('id'):30}  type={e.get('type'):20}  "
            f"norads={e.get('norad_ids')}  peak={e.get('t_peak')}"
        )


def main() -> None:
    p = argparse.ArgumentParser(description="Athena-SDA walk-forward validation")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("run", help="Run walk-forward on catalog events")
    s.add_argument("--events", type=str, default=None, help="Comma-separated event ids")
    s.add_argument("--step-days", type=int, default=14)
    s.add_argument("--holdout-days", type=int, default=3)
    s.add_argument("--threshold", type=float, default=0.50, help="Anomaly hit threshold (default 0.50 after calib)")
    s.add_argument("--hit-window-days", type=int, default=45)
    s.set_defaults(func=cmd_run)

    s = sub.add_parser("summary", help="Print last walk-forward summary")
    s.set_defaults(func=cmd_summary)

    s = sub.add_parser("list-events", help="List events_walkforward.json")
    s.set_defaults(func=cmd_list_events)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
