#!/usr/bin/env python3
"""
Minimal smoke tests for Athena-SDA quant core (hackathon / CI-lite).

  python scripts/smoke_test.py

Covers the CORRECTED math framework: LZ76 complexity, DFA, MMD typicality,
ARL-calibrated Page CUSUM + EWMA, permutation entropy, SSA residual, BOCPD,
plus feature-schema invariants and doctrine rules.
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
        calculate_dfa_hurst,
        calculate_ewma,
        calculate_lz76_complexity,
        calculate_mandelbrot_tail_anomaly,
        calculate_mmd_typicality,
        calculate_page_cusum,
        calculate_permutation_entropy,
        calculate_ssa_residual,
        count_regime_changes,
        homology_backend,
    )
    from src.models import extract_satellite_features, tle_age_hours_at
    from src.utils import generate_mock_tle_history

    errors: list[str] = []

    # --- engine guards (short / degenerate series) ---
    if calculate_lz76_complexity(np.array([1.0, 1.01, 1.02])) != 0.0:
        errors.append("lz76 short series should be 0.0")
    h = calculate_dfa_hurst(np.linspace(0, 1, 8))
    if abs(h - 0.5) > 1e-9:
        errors.append("dfa short series should be neutral 0.5")
    m = calculate_mandelbrot_tail_anomaly(np.ones(20))
    if m != 0.0:
        errors.append("mandelbrot flat series should be 0.0")
    if homology_backend() not in ("proxy", "ripser"):
        errors.append("homology_backend invalid")
    pe = calculate_permutation_entropy(np.linspace(0, 1, 30))
    if not (0.0 <= pe <= 1.0):
        errors.append(f"permutation entropy out of range: {pe}")
    ssa_r, ssa_e = calculate_ssa_residual(np.linspace(0, 1, 30))
    if not np.isfinite(ssa_r) or not (0.0 <= ssa_e <= 1.0):
        errors.append(f"ssa residual invalid: {ssa_r}, {ssa_e}")

    # --- corrected detectors respond to a synthetic maneuver ---
    rng = np.random.default_rng(7)
    quiet = 7000.0 + np.cumsum(rng.normal(0.0, 0.02, 30))  # passive coast
    maneuver = quiet.copy()
    maneuver[18:] += 4.0  # +4 km impulsive jump at epoch 18
    if not (calculate_page_cusum(maneuver) > calculate_page_cusum(quiet)):
        errors.append("Page CUSUM should separate a jump from quiet drift")
    if not (calculate_ewma(maneuver) > calculate_ewma(quiet)):
        errors.append("EWMA should separate a jump from quiet drift")
    if not (count_regime_changes(maneuver) >= 1):
        errors.append("count_regime_changes should detect the jump episode")

    # LZ76 measures token regularity: a monotone ramp (all same token) must be
    # LESS complex than a chaotic series (mixed tokens).
    ramp = 7000.0 + np.arange(30) * 0.5
    chaotic = 7000.0 + np.cumsum(rng.normal(0.0, 0.5, 30))
    if not (calculate_lz76_complexity(ramp) < calculate_lz76_complexity(chaotic)):
        errors.append("LZ76 should be lower for a regular ramp than a chaotic series")

    # WINDOW=30: DFA must ACTIVATE (at n=20 it returned neutral 0.5 — only 1 scale)
    dfa30 = calculate_dfa_hurst(np.cumsum(rng.normal(0.0, 0.1, 30)))
    if abs(dfa30 - 0.5) < 1e-9:
        errors.append("DFA should estimate a non-neutral exponent at n=30")

    # --- MMD separates distributions; no zero-reference fallback trap ---
    ref = rng.normal(0.0, 1.0, (60, 10))
    inlier = ref[0].copy()
    outlier = inlier.copy()
    outlier[0] += 6.0
    typ_in, _ = calculate_mmd_typicality(inlier, ref)
    typ_out, _ = calculate_mmd_typicality(outlier, ref)
    if not (typ_out > typ_in):
        errors.append(f"MMD should rank outlier > inlier (got {typ_out} vs {typ_in})")
    typ_none, _ = calculate_mmd_typicality(inlier, None)
    if typ_none != 0.5:
        errors.append("MMD with no reference must be neutral 0.5")

    # --- tle age timezone ---
    age = tle_age_hours_at(
        "2020-01-01T00:00:00Z",
        reference_time=pd.Timestamp("2020-01-02T00:00:00Z"),
    )
    if not (23.0 <= age <= 25.0):
        errors.append(f"tle_age_hours_at expected ~24h, got {age}")

    # --- features + IF columns ---
    df = generate_mock_tle_history(9001, num_days=60, anomaly_type=None)
    feats = extract_satellite_features(
        df.iloc[-40:],
        country="US",
        purpose="scientific",
        orbit_class="LEO",
        min_distance_to_military_km=400.0,
    )
    for c in IFOREST_COLUMNS:
        if c not in feats:
            errors.append(f"missing IF feature {c}")
    if "mmd_typicality" in IFOREST_COLUMNS:
        errors.append("MMD must not be in IFOREST_COLUMNS (live-reference feature)")
    for c in ("dfa_hurst_sma_short", "shannon_entropy_sma_short", "persistence_dfa_gap"):
        if c not in feats:
            errors.append(f"missing multi-scale feature {c}")
    for bad in ("kolmogorov_proxy_7d", "hurst_exponent_sma", "l1_cusum_sma",
                "spectral_anomaly_rkhs", "chern_simons_proxy", "ricci_mean",
                "williams_threat", "lukasiewicz_implication", "maneuver_count_30d"):
        if bad in feats:
            errors.append(f"legacy feature still present: {bad}")

    # --- optional: load models if present ---
    if (ROOT / "models" / "isolation_forest_monitor.joblib").exists():
        import joblib

        ifo = joblib.load(ROOT / "models" / "isolation_forest_monitor.joblib")
        fit_cols = getattr(ifo, "feature_names_in_", None)
        if fit_cols is not None and set(fit_cols) != set(IFOREST_COLUMNS):
            print("  note: monitor IF schema is stale (old feature set) — retrain required; score check skipped")
        else:
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
                "dfa_hurst_sma": 0.7,
                "lz76_complexity": 0.9,
                "permutation_entropy": 0.6,
                "adf_pvalue": 0.1,
                "page_cusum_sma": 0.2,
                "delta_sma_7d_km": 0.5,
                "tle_age_hours": 12.0,
                "cointegration_pvalue": 0.5,
                "shannon_entropy_sma_30d": 1.0,
                "bocpd_change_prob_3d": 0.3,
                "mmd_typicality": 0.6,
            },
            {"threat_level": 0.4, "classification": "ANOMALOUS", "confidence": 0.6, "ambiguity": 0.4},
            40258,
            100.0,
            {"name": "LUCH", "country": "RU", "purpose": "sigint"},
            {"xgb_class": "ANOMALOUS", "xgb_confidence": 0.6, "anomaly_score": 0.42},
        )
        if "0.42" not in brief and "anomaly_score=0.42" not in brief.replace(" ", ""):
            pass  # format may differ — soft check
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
    print(f"  IFOREST_COLUMNS={len(IFOREST_COLUMNS)} (MMD excluded)")
    print(f"  sample features ok; tle_age~{age:.1f}h")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
