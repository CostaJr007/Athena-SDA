"""
Threshold calibration for military-first anomaly detection (paper A+B).

Claim-friendly rule:
  - Fit IF on normality anchors (baseline+asset).
  - Set hard threshold from empirical distribution of scores on those anchors
    (global p95 / p99), optionally stratified by orbit_class.
  - A detection is "hard" if score >= thr; report interest vs placebo separation.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

import numpy as np


def summarize_score_distribution(scores: Sequence[float]) -> Dict[str, Any]:
    arr = np.asarray([float(s) for s in scores if s is not None and np.isfinite(s)], dtype=float)
    if len(arr) == 0:
        return {
            "n": 0,
            "mean": None,
            "std": None,
            "p50": None,
            "p90": None,
            "p95": None,
            "p99": None,
            "max": None,
        }
    return {
        "n": int(len(arr)),
        "mean": float(np.mean(arr)),
        "std": float(np.std(arr)),
        "p50": float(np.percentile(arr, 50)),
        "p90": float(np.percentile(arr, 90)),
        "p95": float(np.percentile(arr, 95)),
        "p99": float(np.percentile(arr, 99)),
        "max": float(np.max(arr)),
    }


def recommended_threshold(
    score_dist: Dict[str, Any],
    *,
    floor: float = 0.50,
    use: str = "p95",
) -> float:
    """
    Hard threshold for paper/ops: max(floor, empirical quantile of normality scores).
    Default floor 0.50 keeps legacy hard-hit definition when baseline p95 is lower.
    """
    q = score_dist.get(use)
    if q is None or not np.isfinite(q):
        return float(floor)
    return float(max(floor, float(q)))


def build_calibration_table(
    scores: Sequence[float],
    orbit_classes: Optional[Sequence[str]] = None,
    *,
    floor: float = 0.50,
) -> Dict[str, Any]:
    """
    Global + per-orbit calibration from normality-anchor scores (train windows).
    """
    global_dist = summarize_score_distribution(scores)
    thr_global = recommended_threshold(global_dist, floor=floor, use="p95")
    by_orbit: Dict[str, Any] = {}
    if orbit_classes is not None and len(orbit_classes) == len(scores):
        buckets: Dict[str, List[float]] = {}
        for s, oc in zip(scores, orbit_classes):
            key = str(oc or "UNK").upper()
            if key not in ("LEO", "MEO", "GEO"):
                # coarse bucket from unknown
                key = "LEO"
            buckets.setdefault(key, []).append(float(s))
        for oc, sc in buckets.items():
            d = summarize_score_distribution(sc)
            by_orbit[oc] = {
                **d,
                "recommended_thr": recommended_threshold(d, floor=floor, use="p95"),
            }

    return {
        "method": "empirical_normality_anchor_quantiles",
        "floor": floor,
        "global": {**global_dist, "recommended_thr": thr_global},
        "by_orbit": by_orbit,
        "paper_note": (
            "Hard hit if anomaly_score >= thr. thr = max(0.50, p95 of IF scores on "
            "baseline+asset training windows). Per-orbit thr used when available."
        ),
    }


def threshold_for_orbit(calibration: Dict[str, Any], orbit_class: str, default: float = 0.50) -> float:
    oc = str(orbit_class or "LEO").upper()
    by = (calibration or {}).get("by_orbit") or {}
    if oc in by and by[oc].get("recommended_thr") is not None:
        return float(by[oc]["recommended_thr"])
    g = (calibration or {}).get("global") or {}
    if g.get("recommended_thr") is not None:
        return float(g["recommended_thr"])
    return float(default)


def mann_whitney_interest_vs_placebo(
    interest_scores: Sequence[float],
    placebo_scores: Sequence[float],
) -> Dict[str, Any]:
    """Two-sided Mann–Whitney U on max (or pre-peak) scores — paper separation test."""
    a = np.asarray([float(x) for x in interest_scores if x is not None], dtype=float)
    b = np.asarray([float(x) for x in placebo_scores if x is not None], dtype=float)
    out: Dict[str, Any] = {
        "n_interest": int(len(a)),
        "n_placebo": int(len(b)),
        "mean_interest": float(np.mean(a)) if len(a) else None,
        "mean_placebo": float(np.mean(b)) if len(b) else None,
        "u_statistic": None,
        "p_value": None,
        "effect_note": None,
    }
    if len(a) < 2 or len(b) < 2:
        out["effect_note"] = "insufficient_n_for_mw"
        return out
    try:
        from scipy.stats import mannwhitneyu

        # alternative greater: interest scores stochastically larger
        res = mannwhitneyu(a, b, alternative="greater")
        out["u_statistic"] = float(res.statistic)
        out["p_value"] = float(res.pvalue)
        out["effect_note"] = (
            "H1: interest scores > placebo (one-sided). "
            "Small n: interpret p-value cautiously; report effect sizes (means/gaps)."
        )
    except Exception as e:
        out["effect_note"] = f"mw_failed:{e}"
    return out
