#!/usr/bin/env python3
"""
Athena-SDA — continuous validation & drift health check.

Reads the latest risk report / anomalies and the model registry, then emits a
machine-readable `data/alerts/validation_health.json` answering:

  - What exact model produced today's scores? (provenance)
  - Did the score distribution drift vs the previous day?
  - Is the hard threshold still sane vs the observed p95 (calibration)?

Optionally re-runs the walk-forward A+B paper validation (`--run-paper`) to
guard against silent regressions after refactors.

Usage:
    python scripts/run_continuous_validation.py
    python scripts/run_continuous_validation.py --run-paper
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import ALERTS_DIR, MODELS_DIR  # noqa: E402


def _load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _score_stats(alerts: list) -> dict:
    scores = [float(a.get("anomaly_score") or 0.0) for a in alerts if a.get("anomaly_score") is not None]
    n = len(scores)
    if not n:
        return {"n_scored": 0, "mean": None, "p95": None, "max": None}
    s = sorted(scores)
    return {
        "n_scored": n,
        "mean": round(sum(s) / n, 4),
        "p95": round(s[int(0.95 * (n - 1))], 4),
        "max": round(s[-1], 4),
    }


def _prev_day_path(day: str) -> Path:
    try:
        d = datetime.strptime(day, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except Exception:
        return ALERTS_DIR / "anomalies_none.json"
    return ALERTS_DIR / f"anomalies_{(d - timedelta(days=1)).strftime('%Y-%m-%d')}.json"


def main() -> int:
    parser = argparse.ArgumentParser(description="Continuous validation & drift health check")
    parser.add_argument("--run-paper", action="store_true", help="Re-run the A+B paper validation")
    args = parser.parse_args()

    report = _load_json(ALERTS_DIR / "risk_report_latest.json")
    anomalies = _load_json(ALERTS_DIR / "anomalies_latest.json")
    registry = _load_json(MODELS_DIR / "registry.json")
    meta = _load_json(MODELS_DIR / "anomaly_monitor_meta.json")

    alerts = anomalies.get("alerts") or []
    day = anomalies.get("day") or report.get("day") or datetime.now(timezone.utc).strftime("%Y-%m-%d")

    stats = _score_stats(alerts)
    prev = _load_json(_prev_day_path(day))
    prev_alerts = prev.get("alerts") or []
    prev_stats = _score_stats(prev_alerts)

    drift = {
        "prev_day_available": bool(prev_alerts),
        "mean_delta": None,
        "p95_delta": None,
        "new_military_detections": None,
    }
    if prev_alerts:
        if stats["mean"] is not None and prev_stats["mean"] is not None:
            drift["mean_delta"] = round(stats["mean"] - prev_stats["mean"], 4)
        if stats["p95"] is not None and prev_stats["p95"] is not None:
            drift["p95_delta"] = round(stats["p95"] - prev_stats["p95"], 4)
        prev_detect = {a.get("norad_id") for a in prev_alerts if a.get("is_military_detection")}
        cur_detect = {a.get("norad_id") for a in alerts if a.get("is_military_detection")}
        drift["new_military_detections"] = sorted(int(x) for x in (cur_detect - prev_detect) if x is not None)

    # Calibration sanity: recommended hard threshold vs observed p95.
    threshold = float(
        meta.get("recommended_anomaly_threshold")
        or (report.get("summary") or {}).get("threshold")
        or 0.50
    )
    calibration = {
        "threshold": threshold,
        "observed_p95": stats["p95"],
        "p95_exceeds_threshold": bool(stats["p95"] is not None and stats["p95"] > threshold),
        "note": (
            "p95 below threshold => fewer hard hits (threshold may be too strict / distribution quieter). "
            "p95 far above threshold => more alerts (threshold may be too loose). "
            "Re-run train-baseline + paper validation before changing the hard cut."
        ),
    }

    monitor_if = (registry.get("models") or {}).get("monitor_if") or {}
    health = {
        "schema": "athena.validation_health.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "day": day,
        "provenance": {
            "registry_updated": registry.get("updated"),
            "monitor_if_hash": monitor_if.get("feature_schema_hash"),
            "monitor_if_registered_at": monitor_if.get("registered_at"),
            "monitor_trained_at": meta.get("trained_at"),
            "monitor_versioned_model": meta.get("versioned_model"),
        },
        "score_stats": stats,
        "drift": drift,
        "calibration": calibration,
        "paper_validation": None,
    }

    if args.run_paper:
        try:
            res = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "run_paper_validation.py"), "--threshold", str(threshold)],
                capture_output=True,
                text=True,
                timeout=1800,
                cwd=str(ROOT),
            )
            health["paper_validation"] = {
                "exit_code": res.returncode,
                "ok": res.returncode == 0,
                "tail": (res.stdout or res.stderr or "")[-800:],
            }
        except Exception as exc:  # pragma: no cover - subprocess guard
            health["paper_validation"] = {"error": str(exc)}

    out = ALERTS_DIR / "validation_health.json"
    out.write_text(json.dumps(health, indent=2, default=str), encoding="utf-8")
    print(json.dumps(health, indent=2, default=str))
    print(f"\nWrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
