#!/usr/bin/env python3
"""
Feature-block ablation for Isolation Forest (honest quant contribution).

Trains IF on past windows with all features, then scores leave-one-block-out
on the same train matrix (proxy for block importance via mean score shift
and separation of high-score vs low-score tails).

Not a substitute for walk-forward; use as supporting evidence that math blocks
carry signal beyond a single ΔSMA rule.

  python scripts/run_feature_ablation.py
  → data/alerts/feature_ablation_latest.json
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import IFOREST_COLUMNS, DATA_DIR, MODELS_DIR
from src.anomaly_monitor import build_feature_windows, WINDOW
from src.tle_store import history_as_sat_histories, ensure_dirs, ALERTS_DIR

# Feature blocks for leave-one-group-out
BLOCKS: Dict[str, List[str]] = {
    "keplerian_level": [
        "semi_major_axis_km",
        "eccentricity",
        "inclination_deg",
        "raan_deg",
        "mean_motion_rev_per_day",
    ],
    "deltas_maneuvers": [
        "delta_sma_7d_km",
        "delta_sma_30d_km",
        "delta_inc_30d_deg",
        "maneuver_count_30d",
    ],
    "complexity_quant": [
        "shannon_entropy_sma_30d",
        "kolmogorov_proxy_7d",
        "hurst_exponent_sma",
        "mandelbrot_tail_score",
        "adf_pvalue",
        "l1_cusum_sma",
    ],
    "topology_proxy": [
        "chern_simons_proxy",
        "ricci_mean",
        "h0_persistent",
        "h1_persistent",
    ],
    "space_weather": [
        "f10_7",
        "f10_7_adj",
        "ap_index",
        "kp_mean",
        "sunspot_number",
        "f10_7_delta_7d",
        "f10_7_mean_7d",
        "ap_mean_7d",
        "ap_max_7d",
        "ap_delta_7d",
        "geomagnetic_storm",
        "space_weather_available",
    ],
    "metadata_context": [
        "williams_threat",
        "tle_age_hours",
    ],
}


def _score(iforest: IsolationForest, X: pd.DataFrame) -> np.ndarray:
    raw = iforest.decision_function(X)
    return np.clip(0.5 - raw, 0.0, 1.0)


def main() -> int:
    ensure_dirs()
    hists = history_as_sat_histories(min_epochs=WINDOW)
    if not hists:
        print("No history — abort")
        return 1

    cutoff = pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=1)
    X, meta = build_feature_windows(
        hists,
        end_before=cutoff,
        step=3,
        max_windows_per_sat=40,
        sample_mode="hybrid",
    )
    if len(X) < 80:
        print(f"Too few windows: {len(X)}")
        return 1

    cols = [c for c in IFOREST_COLUMNS if c in X.columns]
    X = X[cols].astype(float).replace([np.inf, -np.inf], 0.0).fillna(0.0)

    base = IsolationForest(n_estimators=150, contamination=0.08, random_state=42, n_jobs=-1)
    base.fit(X)
    s0 = _score(base, X)
    thr = float(np.percentile(s0, 95))
    high = s0 >= thr
    low = s0 <= float(np.percentile(s0, 50))

    results: List[Dict[str, Any]] = []
    for name, block in BLOCKS.items():
        drop = [c for c in block if c in cols]
        if not drop:
            continue
        keep = [c for c in cols if c not in drop]
        if len(keep) < 5:
            continue
        Xb = X[keep]
        # Zero-out ablated columns (same dim) so we can reuse structure OR retrain on keep
        ifo = IsolationForest(n_estimators=150, contamination=0.08, random_state=42, n_jobs=-1)
        ifo.fit(Xb)
        sb = _score(ifo, Xb)
        # Align comparison: correlation of ranks + mean |Δ| on high-score tail of full model
        # Pad scores by re-scoring full with zeros? Better: compare separation of original high vs low
        mean_high = float(np.mean(sb[high])) if high.any() else None
        mean_low = float(np.mean(sb[low])) if low.any() else None
        sep = (mean_high - mean_low) if mean_high is not None and mean_low is not None else None
        base_sep = float(np.mean(s0[high]) - np.mean(s0[low])) if high.any() and low.any() else None
        results.append(
            {
                "block": name,
                "dropped_features": drop,
                "n_features_kept": len(keep),
                "mean_score_all": float(np.mean(sb)),
                "mean_score_on_full_model_high_tail": mean_high,
                "mean_score_on_full_model_low_half": mean_low,
                "separation_high_minus_low": sep,
                "full_model_separation": base_sep,
                "separation_drop": (base_sep - sep) if sep is not None and base_sep is not None else None,
                "corr_with_full_scores": float(np.corrcoef(s0, sb)[0, 1]) if len(s0) > 2 else None,
            }
        )

    # Simple baseline: only |delta_sma_7d|
    simple_cols = [c for c in ("delta_sma_7d_km", "maneuver_count_30d") if c in cols]
    if simple_cols:
        Xs = X[simple_cols]
        ifs = IsolationForest(n_estimators=100, contamination=0.08, random_state=42)
        ifs.fit(Xs)
        ss = _score(ifs, Xs)
        simple_sep = float(np.mean(ss[high]) - np.mean(ss[low])) if high.any() and low.any() else None
    else:
        simple_sep = None

    out = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "n_windows": int(len(X)),
        "n_features": len(cols),
        "feature_columns": cols,
        "full_model": {
            "score_mean": float(np.mean(s0)),
            "score_p95": float(np.percentile(s0, 95)),
            "separation_high_minus_low": float(np.mean(s0[high]) - np.mean(s0[low]))
            if high.any() and low.any()
            else None,
        },
        "simple_delta_maneuver_baseline_separation": simple_sep,
        "ablation": sorted(
            results,
            key=lambda r: (r.get("separation_drop") is not None, r.get("separation_drop") or 0),
            reverse=True,
        ),
        "interpretation": (
            "Larger separation_drop when removing a block ⇒ that block helped isolate "
            "the full-model high-score tail. complexity_quant (Hurst/Shannon/CUSUM/…) "
            "should matter for persistent micro-maneuver / regime noise. "
            "Compare full_model.separation vs simple_delta_maneuver_baseline_separation."
        ),
    }

    path = ALERTS_DIR / "feature_ablation_latest.json"
    path.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({k: out[k] for k in ("n_windows", "full_model", "simple_delta_maneuver_baseline_separation")}, indent=2))
    print("\nAblation (by separation_drop):")
    for r in out["ablation"]:
        print(
            f"  {r['block']:20} drop={r.get('separation_drop')}  "
            f"corr={r.get('corr_with_full_scores')}  sep={r.get('separation_high_minus_low')}"
        )
    print(f"\nSaved {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
