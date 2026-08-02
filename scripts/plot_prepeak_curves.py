#!/usr/bin/env python3
"""
Plot pre-peak anomaly score curves for walk-forward events (paper figures).

  python scripts/plot_prepeak_curves.py
  python scripts/plot_prepeak_curves.py --events luch1_intelsat_2015,placebo_terra_2015

Outputs:
  docs/paper/figures/prepeak_<event_id>.png
  docs/paper/figures/prepeak_grid_interest.png
  docs/paper/figures/prepeak_grid_placebo.png
  docs/paper/figures/manifest.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime

from src.walkforward import WF_DIR, load_events

FIG_DIR = ROOT / "docs" / "paper" / "figures"
THR_DEFAULT = 0.50


def _series_from_event(ev: Dict[str, Any]) -> Tuple[Optional[str], List[Tuple[Any, float]], Optional[str]]:
    """Return (norad, [(asof_ts, score), ...], object_name)."""
    metrics = ev.get("metrics") or {}
    if not metrics:
        return None, [], None
    nid = next(iter(metrics.keys()))
    name = (metrics[nid] or {}).get("object_name")
    peak = ev.get("t_peak")
    rows = []
    for f in ev.get("folds") or []:
        asof = f.get("asof")
        t = (f.get("targets") or {}).get(str(nid)) or (f.get("targets") or {}).get(nid)
        if not t or not t.get("ok"):
            continue
        sc = t.get("anomaly_score")
        if sc is None:
            continue
        rows.append((asof, float(sc)))
    return str(nid), rows, name


def _parse_day(s: str):
    return datetime.strptime(str(s)[:10], "%Y-%m-%d")


def plot_one(
    ev: Dict[str, Any],
    *,
    thr: float = THR_DEFAULT,
    out_path: Path,
) -> Optional[Dict[str, Any]]:
    eid = ev.get("event_id") or ev.get("id")
    nid, rows, name = _series_from_event(ev)
    if not rows:
        return None
    peak = ev.get("t_peak")
    t_start = ev.get("t_start")
    is_placebo = str(ev.get("type", "")).startswith("placebo")

    dates = [_parse_day(a) for a, _ in rows]
    scores = [s for _, s in rows]
    peak_dt = _parse_day(peak) if peak else None

    fig, ax = plt.subplots(figsize=(8, 3.6), dpi=140)
    ax.plot(dates, scores, color="#1f77b4" if not is_placebo else "#2ca02c", marker="o", ms=3.5, lw=1.4, label="anomaly_score")
    ax.axhline(thr, color="#d62728", ls="--", lw=1.0, label=f"hard thr={thr:.2f}")
    if peak_dt is not None:
        ax.axvline(peak_dt, color="#ff7f0e", ls="-", lw=1.2, alpha=0.9, label="t_peak (open-source anchor)")
        # shade pre-peak
        pre_x = [d for d in dates if d <= peak_dt]
        pre_y = [s for d, s in zip(dates, scores) if d <= peak_dt]
        if pre_x:
            ax.fill_between(pre_x, pre_y, thr, where=[s >= thr for s in pre_y], color="#1f77b4", alpha=0.15)

    ax.set_ylim(0, 1.02)
    ax.set_ylabel("IF anomaly score")
    ax.set_xlabel("asof (walk-forward fold)")
    title = f"{eid}  ·  NORAD {nid}"
    if name:
        title += f"  ({name})"
    ax.set_title(title, fontsize=10)
    ax.grid(True, alpha=0.3)
    ax.legend(loc="best", fontsize=8)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    fig.autofmt_xdate()
    note = "past-only IF · shaded = pre-peak scores ≥ thr"
    if is_placebo:
        note = "PLACEBO control · " + note
    ax.text(0.01, 0.02, note, transform=ax.transAxes, fontsize=7, color="#444")
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, bbox_inches="tight")
    plt.close(fig)

    pre = [(d, s) for d, s in zip(dates, scores) if peak_dt is None or d <= peak_dt]
    return {
        "event_id": eid,
        "norad_id": nid,
        "object_name": name,
        "is_placebo": is_placebo,
        "t_peak": peak,
        "t_start": t_start,
        "n_folds": len(rows),
        "n_pre_peak_folds": len(pre),
        "max_score": float(max(scores)),
        "pre_peak_mean": float(np.mean([s for _, s in pre])) if pre else None,
        "figure": str(out_path.relative_to(ROOT)).replace("\\", "/"),
    }


def plot_grid(items: List[Dict[str, Any]], title: str, out_path: Path, thr: float) -> None:
    if not items:
        return
    n = len(items)
    cols = 2
    rows = int(np.ceil(n / cols))
    fig, axes = plt.subplots(rows, cols, figsize=(10, 2.8 * rows), dpi=130, squeeze=False)
    for i, it in enumerate(items):
        ax = axes[i // cols][i % cols]
        path = ROOT / it["figure"] if not Path(it["figure"]).is_absolute() else Path(it["figure"])
        # re-load from wf for grid
        eid = it["event_id"]
        wf = WF_DIR / f"wf_{eid}.json"
        if not wf.exists():
            ax.set_visible(False)
            continue
        ev = json.loads(wf.read_text(encoding="utf-8"))
        nid, series, name = _series_from_event(ev)
        if not series:
            ax.set_visible(False)
            continue
        dates = [_parse_day(a) for a, _ in series]
        scores = [s for _, s in series]
        peak = ev.get("t_peak")
        ax.plot(dates, scores, lw=1.2, marker="o", ms=2.5)
        ax.axhline(thr, color="r", ls="--", lw=0.8)
        if peak:
            ax.axvline(_parse_day(peak), color="orange", lw=1.0)
        ax.set_ylim(0, 1.02)
        ax.set_title(f"{eid}", fontsize=8)
        ax.tick_params(labelsize=7)
        ax.grid(True, alpha=0.25)
    # hide unused
    for j in range(n, rows * cols):
        axes[j // cols][j % cols].set_visible(False)
    fig.suptitle(title, fontsize=11)
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, bbox_inches="tight")
    plt.close(fig)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--events", type=str, default=None, help="Comma-separated event ids")
    ap.add_argument("--threshold", type=float, default=THR_DEFAULT)
    args = ap.parse_args()

    want = None
    if args.events:
        want = {x.strip() for x in args.events.split(",") if x.strip()}

    catalog = {e["id"]: e for e in load_events()}
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    metas: List[Dict[str, Any]] = []

    # Prefer all wf_*.json on disk (results), filter by catalog / want
    files = sorted(WF_DIR.glob("wf_*.json"))
    for fp in files:
        eid = fp.stem.replace("wf_", "", 1)
        if eid in ("analysis_new_ml",):
            continue
        if want and eid not in want:
            continue
        try:
            ev = json.loads(fp.read_text(encoding="utf-8"))
        except Exception:
            continue
        # enrich from catalog
        cat = catalog.get(eid) or {}
        if not ev.get("t_peak"):
            ev["t_peak"] = cat.get("t_peak")
        if not ev.get("t_start"):
            ev["t_start"] = cat.get("t_start")
        if not ev.get("type"):
            ev["type"] = cat.get("type")
        meta = plot_one(ev, thr=args.threshold, out_path=FIG_DIR / f"prepeak_{eid}.png")
        if meta:
            metas.append(meta)
            print(f"  figure {meta['figure']}  max={meta['max_score']:.3f}")

    interest = [m for m in metas if not m.get("is_placebo")]
    placebo = [m for m in metas if m.get("is_placebo")]
    plot_grid(interest, "Interest — pre-peak IF score curves", FIG_DIR / "prepeak_grid_interest.png", args.threshold)
    plot_grid(placebo, "Placebo — pre-peak IF score curves", FIG_DIR / "prepeak_grid_placebo.png", args.threshold)

    manifest = {
        "n_figures": len(metas),
        "threshold": args.threshold,
        "figures": metas,
        "grids": [
            "docs/paper/figures/prepeak_grid_interest.png",
            "docs/paper/figures/prepeak_grid_placebo.png",
        ],
    }
    (FIG_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"\nWrote {len(metas)} figures → {FIG_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
