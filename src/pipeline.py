"""
Athena-SDA processing DAG (Data API → Inference API style).

Stages:
  1. Catalog load (synthetic demo constellation + optional real seeds)
  2. Feature extraction (math framework)
  3. Proximity / cointegration context
  4. Isolation Forest + XGBoost
  5. Fuzzy calibration
  6. Kelly resource allocation
"""
from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional, Tuple

import numpy as np
import pandas as pd

from src.config import PURPOSE_SEVERITY
from src.engine import (
    calculate_cointegration_pvalue,
    calculate_kelly_allocation,
    calculate_lukasiewicz_implication,
)
from src.fuzzy import fuzzy_inference_threat
from src.models import extract_satellite_features, predict_threat
from src.orbital import min_distance_to_assets, orbit_class_from_sma
from src.utils import generate_mock_tle_history, generate_shadowing_pair


def _protected_asset_ids() -> set:
    try:
        from src.catalog import asset_ids

        ids = asset_ids()
        if ids:
            return set(ids)
    except Exception:
        pass
    from src.config import MILITARY_ASSET_IDS

    return set(MILITARY_ASSET_IDS)


def build_demo_constellation() -> Dict[int, Dict[str, Any]]:
    """
    Curated multi-threat demo catalog for the tactical dashboard.
    Includes normals, impulsive, low-thrust, and a shadowing pair.
    """
    objects: Dict[int, Dict[str, Any]] = {}

    normal_sats = [
        {"id": 1001, "name": "GPS-BIIRM-1", "country": "US", "purpose": "Navigation", "orbit": "MEO"},
        {"id": 1002, "name": "STARLINK-4291", "country": "US", "purpose": "Commercial", "orbit": "LEO"},
        {"id": 1003, "name": "BRASILSAT-B4", "country": "BR", "purpose": "Telecom", "orbit": "GEO"},
        {"id": 1004, "name": "COSMOS-2491", "country": "RU", "purpose": "Scientific", "orbit": "LEO"},
        {"id": 1005, "name": "BEIDOU-G3", "country": "CN", "purpose": "Navigation", "orbit": "MEO"},
        {"id": 1006, "name": "AMAZONIA-1", "country": "BR", "purpose": "Earth Obs", "orbit": "LEO"},
        {"id": 1007, "name": "EUTELSAT-36B", "country": "FR", "purpose": "Telecom", "orbit": "GEO"},
        {"id": 1008, "name": "SENTINEL-2A", "country": "EU", "purpose": "Earth Obs", "orbit": "LEO"},
        {"id": 1009, "name": "INMARSAT-4F1", "country": "UK", "purpose": "Telecom", "orbit": "GEO"},
        {"id": 1010, "name": "GSAT-18", "country": "IN", "purpose": "Telecom", "orbit": "GEO"},
        {"id": 1011, "name": "NOAA-20", "country": "US", "purpose": "Earth Obs", "orbit": "LEO"},
        {"id": 1012, "name": "TERRA", "country": "US", "purpose": "Scientific", "orbit": "LEO"},
    ]
    for s in normal_sats:
        df = generate_mock_tle_history(s["id"], num_days=30, anomaly_type=None)
        objects[s["id"]] = {"metadata": s, "history": df}

    for s in [
        {"id": 2001, "name": "COSMOS-2561", "country": "RU", "purpose": "Military", "orbit": "LEO"},
        {"id": 2002, "name": "SJ-21_DEBRIS", "country": "CN", "purpose": "Debris removal", "orbit": "GEO"},
    ]:
        df = generate_mock_tle_history(s["id"], num_days=30, anomaly_type="impulsive_maneuver")
        objects[s["id"]] = {"metadata": s, "history": df}

    for s in [
        {"id": 3001, "name": "SHIYAN-12", "country": "CN", "purpose": "Scientific", "orbit": "LEO"},
        {"id": 3002, "name": "LUCH-5X", "country": "RU", "purpose": "sigint", "orbit": "GEO"},
    ]:
        df = generate_mock_tle_history(s["id"], num_days=30, anomaly_type="low_thrust_disguised")
        objects[s["id"]] = {"metadata": s, "history": df}

    # Shadowing pair: Yaogan tails USSF milsat
    target_meta = {"id": 4001, "name": "USSF-22988 (MILSAT)", "country": "US", "purpose": "military", "orbit": "LEO"}
    spy_meta = {"id": 44231, "name": "YAOGAN-31 (SPYSAT)", "country": "CN", "purpose": "sigint", "orbit": "LEO"}
    df_t, df_s = generate_shadowing_pair(4001, 44231, num_days=30)
    objects[4001] = {"metadata": target_meta, "history": df_t}
    objects[44231] = {"metadata": spy_meta, "history": df_s}

    return objects


def _military_histories(all_sats: Mapping[int, Dict[str, Any]]) -> Dict[int, pd.DataFrame]:
    """Assets considered protected (military) for proximity sensing."""
    protected = _protected_asset_ids()
    out = {}
    for sid, sat in all_sats.items():
        meta = sat["metadata"]
        purpose = str(meta.get("purpose", "")).lower()
        if sid in protected or purpose in ("military",) and meta.get("country") in ("US", "UK", "FR", "CA"):
            # Don't use adversary milsats as "protected assets"
            if meta.get("country") in ("US", "UK", "FR", "CA", "EU", "IT", "DE", "INTL"):
                out[sid] = sat["history"]
    # Always include explicit catalog assets when present in the constellation
    for mid in protected:
        if mid in all_sats:
            out[mid] = all_sats[mid]["history"]
    return out


def process_constellation(
    all_sats: Mapping[int, Dict[str, Any]],
    iforest,
    xgb_model,
    rkhs_ref,
) -> List[Dict[str, Any]]:
    """
    Run the full inference DAG for every object in the constellation.
    """
    mil_hist = _military_histories(all_sats)
    processed: List[Dict[str, Any]] = []

    # Precompute cointegration of known shadowing candidate against assets
    for sat_id, sat_data in all_sats.items():
        hist = sat_data["history"]
        meta = sat_data["metadata"]
        purpose = str(meta.get("purpose", "unknown"))
        country = str(meta.get("country", "UNKNOWN"))
        orbit = str(meta.get("orbit", orbit_class_from_sma(float(hist["semi_major_axis_km"].iloc[-1]))))

        # Proximity: exclude self from assets
        assets = {k: v for k, v in mil_hist.items() if k != sat_id}
        min_dist, closest_asset = min_distance_to_assets(hist, assets, cap_km=500.0)

        # Cointegration vs closest military asset (shadowing detector)
        coint_p = 1.0
        if closest_asset is not None and closest_asset in all_sats:
            coint_p = calculate_cointegration_pvalue(
                hist["semi_major_axis_km"].values,
                all_sats[closest_asset]["history"]["semi_major_axis_km"].values,
            )

        # Łukasiewicz: IF cointegrated THEN high Hurst persistence should hold
        # (filled after features for p/q; placeholder now, refined below)
        luk = 1.0

        feats = extract_satellite_features(
            hist.iloc[-20:] if len(hist) >= 20 else hist,
            reference_matrix=rkhs_ref,
            country=country,
            purpose=purpose,
            orbit_class=orbit,
            min_distance_to_military_km=min_dist,
            cointegration_pvalue=coint_p,
            lukasiewicz_implication=luk,
        )

        p_val = 1.0 if coint_p < 0.05 else 0.0
        q_val = 1.0 if feats["hurst_exponent_sma"] > 0.65 else 0.0
        luk = calculate_lukasiewicz_implication(p_val, q_val)
        feats["lukasiewicz_implication"] = luk
        feats["min_distance_to_military_km"] = min_dist
        feats["cointegration_pvalue"] = coint_p

        ml = predict_threat(iforest, xgb_model, feats)
        feats = ml["features"]

        # Fuzzy calibration blends ML anomaly with physics/context
        fuzzy_res = fuzzy_inference_threat(feats, min_dist)

        # Fuse XGBoost class with fuzzy level for final classification
        final_class, final_threat, final_conf = fuse_xgb_fuzzy(
            ml["xgb_class"],
            ml["xgb_confidence"],
            ml["xgb_proba"],
            fuzzy_res,
            min_dist_mil=min_dist,
        )

        severity = PURPOSE_SEVERITY.get(purpose.lower(), 25.0) / 100.0
        # Kelly uses threat probability and severity odds
        kelly = calculate_kelly_allocation(final_threat, max(severity * 4.0, 0.5))
        # Also surface threat * severity as operational allocation %
        kelly_ops = float(np.clip(final_threat * severity, 0.0, 1.0))
        kelly_final = float(max(kelly, kelly_ops * 0.5))

        # Infer likely target name for UI
        target_name = None
        if closest_asset is not None and closest_asset in all_sats:
            target_name = all_sats[closest_asset]["metadata"]["name"]
        if final_class in ("HOSTILE", "HOSTIL", "SUSPECT", "SUSPEITO") and min_dist < 100:
            if target_name is None:
                target_name = "High-value military asset"

        processed.append({
            "id": sat_id,
            "name": meta["name"],
            "country": country,
            "purpose": purpose,
            "orbit": orbit,
            "threat_level": final_threat,
            "classification": final_class,
            "confidence": final_conf,
            "ambiguity": float(1.0 - final_conf),
            "kelly_allocation": kelly_final,
            "features": feats,
            "min_dist_mil": min_dist,
            "closest_asset_id": closest_asset,
            "closest_asset_name": target_name,
            "xgb_class": ml["xgb_class"],
            "xgb_confidence": ml["xgb_confidence"],
            "xgb_proba": ml["xgb_proba"],
            "anomaly_score": ml["anomaly_score"],
            "fuzzy_classification": fuzzy_res["classification"],
            "cointegration_pvalue": coint_p,
            "lukasiewicz_implication": luk,
        })

    return processed


def fuse_xgb_fuzzy(
    xgb_class: str,
    xgb_conf: float,
    xgb_proba: Dict[str, float],
    fuzzy_res: Dict[str, Any],
    min_dist_mil: float = 500.0,
) -> Tuple[str, float, float]:
    """
    Combine quantitative XGBoost output with fuzzy Mamdani calibration.

    XGBoost is the primary classifier; fuzzy can raise severity when
    geometry (proximity) supports it, but cannot alone mark HOSTILE if
    the object is far from protected assets and XGB says NORMAL.
    """
    # Canonical English labels (+ legacy PT aliases for old artifacts)
    rank = {
        "NORMAL": 0,
        "ANOMALOUS": 1, "ANÔMALO": 1, "ANOMALO": 1,
        "SUSPECT": 2, "SUSPEITO": 2,
        "HOSTILE": 3, "HOSTIL": 3,
    }
    inv = {0: "NORMAL", 1: "ANOMALOUS", 2: "SUSPECT", 3: "HOSTILE"}

    r_x = rank.get(xgb_class, 0)
    r_f = rank.get(fuzzy_res["classification"], 0)
    near = min_dist_mil < 50.0
    critical = min_dist_mil < 15.0

    def _p(*keys: str) -> float:
        for k in keys:
            if k in xgb_proba:
                return float(xgb_proba[k])
        return 0.0

    threat_x = float(
        _p("HOSTILE", "HOSTIL") * 1.0
        + _p("SUSPECT", "SUSPEITO") * 0.7
        + _p("ANOMALOUS", "ANÔMALO", "ANOMALO") * 0.4
    )
    threat_f = float(fuzzy_res["threat_level"])
    # Weight fuzzy higher only when geometry is tactically relevant
    w_f = 0.55 if near else 0.30
    w_x = 1.0 - w_f
    final_threat = float(np.clip(w_x * threat_x + w_f * threat_f, 0.0, 1.0))

    # Start from XGB; allow fuzzy to escalate by at most +1 when confident
    final_rank = r_x
    if r_f > r_x and fuzzy_res["confidence"] > 0.35:
        if near or r_f <= 2:
            final_rank = min(r_x + 1, r_f)
        # Far + fuzzy HOSTILE alone → cap at ANOMALOUS unless XGB already elevated
        if not near and r_f >= 3 and r_x == 0:
            final_rank = 1

    if critical and (r_x >= 1 or r_f >= 2 or threat_x > 0.3):
        final_rank = max(final_rank, 2)
    if critical and (r_x >= 2 or threat_x > 0.5):
        final_rank = max(final_rank, 3)

    if final_threat >= 0.75 and (near or r_x >= 2):
        final_rank = max(final_rank, 3)
    elif final_threat >= 0.55 and (near or r_x >= 1):
        final_rank = max(final_rank, 2)
    elif final_threat >= 0.35:
        final_rank = max(final_rank, 1)

    final_class = inv.get(final_rank, "NORMAL")
    final_conf = float(np.clip(0.55 * xgb_conf + 0.45 * fuzzy_res["confidence"], 0.0, 1.0))
    return final_class, final_threat, final_conf


def process_to_dataframe(processed: List[Dict[str, Any]]) -> pd.DataFrame:
    rows = []
    for p in processed:
        rows.append({k: v for k, v in p.items() if k != "features"})
    return pd.DataFrame(rows)
