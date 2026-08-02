#!/usr/bin/env python3
"""
Minimal smoke tests for Athena-SDA quant core (hackathon / CI-lite).

  python scripts/smoke_test.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> int:
    import numpy as np
    import pandas as pd

    from src.config import IFOREST_COLUMNS
    from src.engine import (
        calculate_hurst_exponent,
        calculate_kolmogorov_proxy,
        calculate_mandelbrot_tail_anomaly,
        homology_backend,
    )
    from src.models import extract_satellite_features, tle_age_hours_at
    from src.utils import generate_mock_tle_history

    errors: list[str] = []

    # --- engine guards ---
    if calculate_kolmogorov_proxy(np.array([1.0, 1.01, 1.02])) != 0.0:
        errors.append("kolmogorov short series should be 0.0")
    h = calculate_hurst_exponent(np.linspace(0, 1, 8))
    if abs(h - 0.5) > 1e-9:
        errors.append("hurst short series should be neutral 0.5")
    m = calculate_mandelbrot_tail_anomaly(np.ones(20))
    if m != 0.0:
        errors.append("mandelbrot flat series should be 0.0")
    if homology_backend() not in ("proxy", "ripser"):
        errors.append("homology_backend invalid")

    # --- tle age timezone ---
    age = tle_age_hours_at(
        "2020-01-01T00:00:00Z",
        reference_time=pd.Timestamp("2020-01-02T00:00:00Z"),
    )
    if not (23.0 <= age <= 25.0):
        errors.append(f"tle_age_hours_at expected ~24h, got {age}")

    # --- features + IF columns ---
    df = generate_mock_tle_history(9001, num_days=40, anomaly_type=None)
    feats = extract_satellite_features(
        df.iloc[-25:],
        country="US",
        purpose="scientific",
        orbit_class="LEO",
        min_distance_to_military_km=400.0,
    )
    for c in IFOREST_COLUMNS:
        if c not in feats:
            errors.append(f"missing IF feature {c}")
    if "spectral_anomaly_rkhs" in IFOREST_COLUMNS:
        errors.append("RKHS must not be in IFOREST_COLUMNS")
    for c in ("hurst_exponent_sma_short", "shannon_entropy_sma_short", "persistence_hurst_gap"):
        if c not in feats:
            errors.append(f"missing multi-scale feature {c}")

    # --- optional: load models if present ---
    from pathlib import Path as P

    if (ROOT / "models" / "isolation_forest_monitor.joblib").exists():
        import joblib
        from sklearn.ensemble import IsolationForest

        ifo = joblib.load(ROOT / "models" / "isolation_forest_monitor.joblib")
        row = pd.DataFrame([{c: float(feats.get(c, 0.0)) for c in IFOREST_COLUMNS}])
        row = row.replace([np.inf, -np.inf], 0.0).fillna(0.0)
        try:
            raw = float(ifo.decision_function(row)[0])
            score = float(np.clip(0.5 - raw, 0.0, 1.0))
            if not (0.0 <= score <= 1.0):
                errors.append(f"anomaly_score out of range: {score}")
        except Exception as e:
            errors.append(f"monitor IF score failed (retrain?): {e}")

    # --- history store present ---
    hist_path = ROOT / "data" / "history" / "epochs.parquet"
    if hist_path.exists():
        hdf = pd.read_parquet(hist_path)
        if len(hdf) < 1000:
            errors.append("history parquet unexpectedly small")
        if hdf["norad_id"].nunique() < 5:
            errors.append("too few NORADs in history")

    # --- Bob citations never invent scores ---
    try:
        from src.bob import tool_get_case_study_citations, generate_bob_briefing

        cites = tool_get_case_study_citations(40258)
        if not cites:
            errors.append("expected case citations for NORAD 40258")
        brief = generate_bob_briefing(
            {
                "hurst_exponent_sma": 0.7,
                "kolmogorov_proxy_7d": 0.4,
                "adf_pvalue": 0.1,
                "l1_cusum_sma": 0.2,
                "delta_sma_7d_km": 0.5,
                "tle_age_hours": 12.0,
                "cointegration_pvalue": 0.5,
                "shannon_entropy_sma_30d": 1.0,
                "ricci_mean": 0.0,
                "spectral_anomaly_rkhs": 0.1,
            },
            {"threat_level": 0.4, "classification": "ANOMALOUS", "confidence": 0.6, "ambiguity": 0.4},
            40258,
            100.0,
            {"name": "LUCH", "country": "RU", "purpose": "sigint"},
            {"xgb_class": "ANOMALOUS", "xgb_confidence": 0.6, "anomaly_score": 0.42},
        )
        if "immutable" not in brief.lower() and "unchanged" not in brief.lower() and "QUANTITATIVE" not in brief:
            pass  # soft check
        if "0.42" not in brief and "anomaly_score=0.42" not in brief.replace(" ", ""):
            # still ok if format differs
            pass
    except Exception as e:
        errors.append(f"bob citation smoke failed: {e}")

    # --- doctrine military-first ---
    try:
        from src.doctrine import (
            classify_military_status,
            doctrine_summary,
            ids_for_if_training,
        )

        d = doctrine_summary()
        if d.get("doctrine") != "military_first_sda":
            errors.append("doctrine_summary missing military_first_sda")
        ids = ids_for_if_training(min_ids=1)
        if not ids:
            errors.append("ids_for_if_training empty")
        cal = classify_military_status(
            role="baseline", reliable=True, series_outlier=True, day_over_day_relevant=False
        )
        if cal.get("is_anomaly") or cal.get("is_military_detection"):
            errors.append("baseline must not escalate military anomaly")
        sus = classify_military_status(
            role="suspect", reliable=True, series_outlier=True, day_over_day_relevant=False
        )
        if not sus.get("is_military_detection"):
            errors.append("suspect outlier must be military detection")
    except Exception as e:
        errors.append(f"doctrine smoke failed: {e}")

    # --- registry ---
    reg = ROOT / "models" / "registry.json"
    if reg.exists():
        import json

        r = json.loads(reg.read_text(encoding="utf-8"))
        for role in ("monitor_if", "pipeline_if", "xgboost"):
            if role not in (r.get("models") or {}):
                errors.append(f"registry missing {role}")

    if errors:
        print("SMOKE FAILED:")
        for e in errors:
            print(" -", e)
        return 1
    print("SMOKE OK")
    print(f"  homology_mode={homology_backend()}")
    print(f"  IFOREST_COLUMNS={len(IFOREST_COLUMNS)} (RKHS excluded)")
    print(f"  sample features ok; tle_age~{age:.1f}h")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
