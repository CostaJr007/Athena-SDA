#!/usr/bin/env python3
"""
SPLID benchmark adapter — Satellite Pattern-of-Life Identification Dataset
(MIT ARCLab Prize 2024). Evaluates Athena-SDA's corrected change-point
features against the official node-detection metric (F2, ±6 time indices).

Dataset (public, no registration):
  - Dropbox: https://www.dropbox.com/scl/fo/jt5h1f82iycjb8elybmlz/h?rlkey=bjcmny486ddf7m0j7b9uok9ww&dl=0
    (~4.5 GB zip; CSV per object, 15 ephemeris columns, 2-hour grid, ~2184 rows)
  - Paper: Siew et al. 2025, J. Astronautical Sciences 72:41, doi 10.1007/s40295-025-00515-5
  - Devkit: https://github.com/ARCLab-MIT/splid-devkit (MIT license)

Labels: ObjectID, TimeIndex, Direction (EW/NS), Node (SS/ES/ID/AD/IK), Type (NK/CK/EK/HK).
Metric: F2 over node detections; match within tolerance ±6 indices (=12h) on
Direction+Node+Type; ES nodes dropped from scoring.

Usage:
  python scripts/run_splid_benchmark.py --data-dir data/splid --download
  python scripts/run_splid_benchmark.py --data-dir data/splid --limit 50
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SPLID_URL = (
    "https://www.dropbox.com/scl/fo/jt5h1f82iycjb8elybmlz/h?rlkey=bjcmny486ddf7m0j7b9uok9ww&dl=1"
)
# Official tolerance: ±6 time indices at 2 h resolution = 12 h
TOLERANCE = 6
EPHEMERIS_COLS = [
    "Eccentricity", "Semimajor Axis (m)", "Inclination (deg)", "RAAN (deg)",
    "Argument of Periapsis (deg)", "True Anomaly (deg)", "Latitude (deg)",
    "Longitude (deg)", "Altitude (m)", "X (m)", "Y (m)", "Z (m)",
    "Vx (m/s)", "Vy (m/s)", "Vz (m/s)",
]


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------
def download_splid(data_dir: Path) -> Path:
    """Download + unzip SPLID (~4.5 GB) if not present. Returns extracted dir."""
    import zipfile

    data_dir.mkdir(parents=True, exist_ok=True)
    zip_path = data_dir / "SPLID.zip"
    if not zip_path.exists():
        print(f"Downloading SPLID (~4.5 GB) from Dropbox…")
        import urllib.request

        urllib.request.urlretrieve(SPLID_URL, zip_path)
    extracted = data_dir / "SPLID"
    if not extracted.exists() or not any(extracted.rglob("*.csv")):
        print("Extracting SPLID.zip…")
        with zipfile.ZipFile(zip_path) as z:
            z.extractall(data_dir)
    return extracted


def find_object_csvs(root: Path) -> List[Path]:
    """All per-object ephemeris CSVs (one per ObjectID)."""
    if not root.exists():
        return []
    return sorted(p for p in root.rglob("*.csv") if "label" not in p.name.lower())


def load_object(path: Path) -> Dict[str, Any]:
    """CSV -> {object_id, time_index (0..n-1), sma_km, incl, raw df}."""
    import pandas as pd

    df = pd.read_csv(path)
    # column names can vary ("Semimajor Axis (m)" vs "SMA (m)")
    sma_col = next((c for c in df.columns if "semimajor" in c.lower() or c == "SMA (m)"), None)
    inc_col = next((c for c in df.columns if "inclination" in c.lower()), None)
    if sma_col is None or inc_col is None:
        return {"object_id": path.stem, "skip": "missing ephemeris columns"}
    sma_km = df[sma_col].astype(float).values / 1000.0  # m -> km (matches pipeline)
    incl = df[inc_col].astype(float).values
    return {
        "object_id": path.stem,
        "n": len(sma_km),
        "sma_km": sma_km,
        "incl_deg": incl,
        "skip": None,
    }


def load_labels(root: Path) -> Dict[str, pd.DataFrame]:
    """All *label*.csv files -> {object_id: label df}."""
    import pandas as pd

    out: Dict[str, pd.DataFrame] = {}
    for p in root.rglob("*.csv"):
        if "label" not in p.name.lower():
            continue
        try:
            df = pd.read_csv(p)
        except Exception:
            continue
        if "ObjectID" not in df.columns and "TimeIndex" not in df.columns:
            continue
        for oid, g in df.groupby("ObjectID"):
            out[str(oid)] = g
    return out


# ---------------------------------------------------------------------------
# Detection (Athena-SDA corrected change-point features)
# ---------------------------------------------------------------------------
def detect_nodes(
    sma_km: Sequence[float],
    incl_deg: Sequence[float],
    *,
    min_gap: int = 8,
    cusum_h: float = 3.0,
) -> List[Dict[str, Any]]:
    """
    Node candidates via BOCPD + Page CUSUM on the SMA series.

    Returns list of {time_index, direction:'EW', node:'IK' or 'ID', type}.
    Direction/Node/Type are coarse labels (SMA responds to EW drift; ID/IK are
    the maneuver-mode transitions we can localize). A refinement pass can
    classify Type via feature context.
    """
    import numpy as np

    from src.engine import calculate_bocpd, count_regime_changes

    s = np.asarray(sma_km, dtype=float)
    if len(s) < 30:
        return []

    prob, _ = calculate_bocpd(s, hazard=1.0 / 40.0)
    n_regimes = int(count_regime_changes(s, h_sigma=cusum_h))

    # candidate indices: local maxima of |ΔSMA| with a refractory gap
    d = np.abs(np.diff(s))
    med = float(np.median(d))
    thr = max(med * 4.0, 1e-6)
    candidates: List[int] = []
    last = -min_gap
    for i in range(1, len(d)):
        if d[i] >= thr and (i - last) >= min_gap:
            candidates.append(i)
            last = i

    nodes = [
        {
            "time_index": int(i),
            "direction": "EW",
            "node": "IK" if d[max(0, i - 1) : i + 2].mean() > thr else "ID",
            "type": "NK",
        }
        for i in candidates[: min(len(candidates), max(1, n_regimes + 1))]
    ]
    return nodes


# ---------------------------------------------------------------------------
# Evaluation (official F2 metric)
# ---------------------------------------------------------------------------
def evaluate_f2(
    predictions: List[Dict[str, Any]],
    truths: List[Dict[str, Any]],
    tolerance: int = TOLERANCE,
) -> Dict[str, Any]:
    """F2 over node detections; match within tolerance on Direction+Node+Type."""
    tp = 0
    matched = [False] * len(truths)
    for p in predictions:
        for j, t in enumerate(truths):
            if matched[j]:
                continue
            if abs(p["time_index"] - t["time_index"]) <= tolerance:
                if (p.get("direction") == t.get("direction")
                        and p.get("node") == t.get("node")
                        and p.get("type") == t.get("type")):
                    matched[j] = True
                    tp += 1
                    break
    fp = len(predictions) - tp
    fn = len(truths) - tp
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f2 = 5 * precision * recall / (4 * precision + recall) if (4 * precision + recall) else 0.0
    return {"tp": tp, "fp": fp, "fn": fn, "precision": precision, "recall": recall, "f2": f2}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser(description="SPLID benchmark (Athena-SDA features)")
    ap.add_argument("--data-dir", type=Path, default=ROOT / "data" / "splid")
    ap.add_argument("--download", action="store_true", help="download SPLID.zip (~4.5 GB)")
    ap.add_argument("--limit", type=int, default=0, help="max objects to score (0 = all)")
    ap.add_argument("--window-days", type=int, default=30, help="feature context in days")
    args = ap.parse_args()

    data_dir = args.data_dir
    if args.download:
        data_dir = download_splid(data_dir)
    csvs = find_object_csvs(data_dir)
    if not csvs:
        print("No SPLID CSVs found. Use --download (4.5 GB) or point --data-dir at the extracted zip.")
        return 1

    labels = load_labels(data_dir)
    print(f"Objects found: {len(csvs)} · labels files: {len(labels)}")
    print(f"Feature window: {args.window_days} days @ 2 h = {args.window_days * 12} indices")

    results: List[Dict[str, Any]] = []
    skipped = 0
    for i, path in enumerate(csvs):
        if args.limit and i >= args.limit:
            break
        obj = load_object(path)
        if obj.get("skip"):
            skipped += 1
            continue
        truth_rows = labels.get(obj["object_id"])
        truths = (
            [
                {
                    "time_index": int(r["TimeIndex"]),
                    "direction": str(r["Direction"]),
                    "node": str(r["Node"]),
                    "type": str(r["Type"]),
                }
                for _, r in truth_rows.iterrows()
                if str(r.get("Node")) != "ES"
            ]
            if truth_rows is not None
            else []
        )
        preds = detect_nodes(obj["sma_km"], obj["incl_deg"])
        metrics = evaluate_f2(preds, truths)
        results.append({"object_id": obj["object_id"], **metrics, "n_truths": len(truths), "n_preds": len(preds)})

    if not results:
        print("No objects scored.")
        return 1

    # Aggregate (global TP/FP/FN -> macro F2)
    tp = sum(r["tp"] for r in results)
    fp = sum(r["fp"] for r in results)
    fn = sum(r["fn"] for r in results)
    prec = tp / (tp + fp) if (tp + fp) else 0.0
    rec = tp / (tp + fn) if (tp + fn) else 0.0
    f2 = 5 * prec * rec / (4 * prec + rec) if (4 * prec + rec) else 0.0

    out = {
        "objects_scored": len(results),
        "objects_skipped": skipped,
        "total_truth_nodes": tp + fn,
        "total_pred_nodes": tp + fp,
        "tp": tp, "fp": fp, "fn": fn,
        "precision": round(prec, 4),
        "recall": round(rec, 4),
        "f2": round(f2, 4),
        "tolerance_indices": TOLERANCE,
        "note": "F2 over node detections (Direction+Node+Type match, ±6 indices). Coarse Direction/Type labels — refinement pass planned.",
    }
    print(json.dumps(out, indent=2))
    (ROOT / "data" / "alerts" / "splid_benchmark_latest.json").write_text(
        json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print("Saved data/alerts/splid_benchmark_latest.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
