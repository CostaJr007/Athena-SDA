"""
ML models for Athena-SDA: feature extraction, labeling, train, load, predict.

Pipeline (Palantir-inspired DAG):
  Features → Isolation Forest (anomaly) → XGBoost (threat class) → Fuzzy (calibration)
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional, Tuple

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.metrics import classification_report, log_loss
from sklearn.model_selection import train_test_split
from xgboost import XGBClassifier

from src.config import (
    CLASS_NAMES,
    FEATURE_COLUMNS,
    IFOREST_COLUMNS,
    MIN_WINDOW,
    MODELS_DIR,
    XGB_COLUMNS,
)
from src.engine import (
    calculate_adf_pvalue,
    calculate_bocpd,
    calculate_dfa_hurst,
    calculate_ewma,
    calculate_lz76_complexity,
    calculate_mandelbrot_tail_anomaly,
    calculate_mmd_typicality,
    calculate_page_cusum,
    calculate_permutation_entropy,
    calculate_persistent_homology,
    calculate_shannon_entropy,
    calculate_ssa_residual,
    calculate_static_threat,
    complexity_entropy_c,
    count_regime_changes,
    homology_backend,
)
from src.innovation import lkf_innovation_score
from src.orbital import position_series_from_history
from src.utils import generate_mock_tle_history, generate_shadowing_pair

MODELS_DIR_STR = str(MODELS_DIR)

# Canonical English class names for metrics (weak labels — not ground truth)
METRIC_CLASS_NAMES = {
    0: "NORMAL",
    1: "ANOMALOUS",
    2: "SUSPECT",
    3: "HOSTILE",
}


def tle_age_hours_at(
    epoch_ts,
    *,
    reference_time: Optional[pd.Timestamp] = None,
    fallback: float = 12.0,
) -> float:
    """
    TLE age in hours relative to reference_time (walk-forward asof / window end)
    or UTC now for live inference. Never uses a frozen parquet placeholder alone
    when a real epoch timestamp is available.
    """
    if epoch_ts is None or (isinstance(epoch_ts, float) and np.isnan(epoch_ts)):
        return float(fallback)
    try:
        ep = pd.Timestamp(epoch_ts)
        if ep.tzinfo is None:
            ep = ep.tz_localize("UTC")
        else:
            ep = ep.tz_convert("UTC")
    except Exception:
        return float(fallback)

    ref = reference_time
    if ref is None:
        ref = pd.Timestamp.now(tz="UTC")
    else:
        ref = pd.Timestamp(ref)
        if ref.tzinfo is None:
            ref = ref.tz_localize("UTC")
        else:
            ref = ref.tz_convert("UTC")

    age = float((ref - ep).total_seconds() / 3600.0)
    return float(max(0.0, age))


def extract_satellite_features(
    history_df: pd.DataFrame,
    reference_matrix: Optional[np.ndarray] = None,
    country: str = "UNKNOWN",
    purpose: str = "unknown",
    orbit_class: str = "LEO",
    min_distance_to_military_km: float = 500.0,
    cointegration_pvalue: float = 1.0,
    reference_time: Optional[pd.Timestamp] = None,
) -> Dict[str, float]:
    """
    Extract the unified feature vector for the last epoch in history_df.
    Includes the full math framework used by Athena-SDA.

    reference_time: clock for tle_age_hours. Use window end / walk-forward asof
    for historical scoring; omit (None) for live inference (= now UTC).
    """
    history_df = history_df.ffill().bfill()
    if len(history_df) < MIN_WINDOW:
        raise ValueError(f"Insufficient history (minimum {MIN_WINDOW} epochs) for mathematical features.")

    last_row = history_df.iloc[-1]
    sma = float(last_row["semi_major_axis_km"])
    ecc = float(last_row["eccentricity"])
    inc = float(last_row["inclination_deg"])
    raan = float(last_row.get("raan_deg", 0.0))
    mean_motion = float(last_row["mean_motion_rev_per_day"])
    if "timestamp" in last_row.index and pd.notnull(last_row["timestamp"]):
        tle_age = tle_age_hours_at(
            last_row["timestamp"],
            reference_time=reference_time,
            fallback=float(last_row.get("tle_age_hours", 12.0) or 12.0),
        )
        sw_when = reference_time if reference_time is not None else last_row["timestamp"]
    else:
        tle_age = float(last_row.get("tle_age_hours", 12.0) or 12.0)
        sw_when = reference_time

    # Space weather at epoch/asof — F10.7 / Ap / Kp (drag vs maneuver)
    try:
        from src.space_weather import space_weather_feature_vector

        sw_feats = space_weather_feature_vector(sw_when, auto_seed=False)
    except Exception:
        sw_feats = {
            "f10_7": 120.0,
            "f10_7_adj": 120.0,
            "ap_index": 8.0,
            "kp_mean": 2.0,
            "sunspot_number": 50.0,
            "f10_7_delta_7d": 0.0,
            "f10_7_mean_7d": 120.0,
            "ap_mean_7d": 8.0,
            "ap_max_7d": 8.0,
            "ap_delta_7d": 0.0,
            "geomagnetic_storm": 0.0,
            "space_weather_available": 0.0,
        }

    sma_series = history_df["semi_major_axis_km"].values.astype(float)

    delta_sma_7d = float(sma - history_df["semi_major_axis_km"].iloc[-7]) if len(history_df) >= 7 else 0.0
    delta_sma_30d = float(sma - history_df["semi_major_axis_km"].iloc[0])
    delta_inc_30d = float(inc - history_df["inclination_deg"].iloc[0])

    # Distinct maneuver-episode count (two-sided Page CUSUM + refractory window).
    # Fixes the old loop that counted every threshold crossing (up to 8x per
    # single maneuver).
    regime_changes = count_regime_changes(sma_series)

    shannon = calculate_shannon_entropy(sma_series)
    # Multi-scale persistence: short window (~recent tip) vs full window
    n_short = min(12, max(8, len(sma_series) // 2))
    sma_short = sma_series[-n_short:]
    shannon_short = calculate_shannon_entropy(sma_short)
    # Corrected framework: LZ76 complexity (not zlib ratio), DFA (not R/S),
    # permutation entropy + complexity-entropy plane, ARL-calibrated
    # Page CUSUM + EWMA, SSA residual, BOCPD run-length posterior.
    lz76 = calculate_lz76_complexity(sma_series)
    perm_entropy = calculate_permutation_entropy(sma_series)
    c_js = complexity_entropy_c(sma_series)
    dfa = calculate_dfa_hurst(sma_series)
    dfa_short = calculate_dfa_hurst(sma_short)
    # Gap > 0: full window more persistent than recent tip (sustained control memory)
    persistence_dfa_gap = float(np.clip(dfa - dfa_short, -1.0, 1.0))
    mandelbrot = calculate_mandelbrot_tail_anomaly(sma_series)
    adf = calculate_adf_pvalue(sma_series)
    static_threat = calculate_static_threat(country, purpose, orbit_class, inc)
    cusum = calculate_page_cusum(sma_series)
    ewma = calculate_ewma(sma_series)
    bocpd_prob, bocpd_ll = calculate_bocpd(sma_series)
    ssa_resid, ssa_energy = calculate_ssa_residual(sma_series)
    # Linear Kalman Filter innovation score (Zollo & Weigel 2023 — best
    # published TLE maneuver method: KF on SMA + normalized innovation eps).
    innovation_score, innovation_eps = lkf_innovation_score(sma_series)

    # Homology on trajectory cloud (standardized inside the engine)
    pos_cloud = position_series_from_history(history_df, n_samples=min(24, len(history_df)))
    h0_pers, h1_pers = calculate_persistent_homology(pos_cloud)

    # MMD typicality vs the normality reference (1 - permutation p-value).
    # Fixes the old 1 - max RBF similarity, which saturated for normal vectors
    # and returned 1.0 on the zero-reference fallback (now neutral 0.5).
    mmd_feature_subset = np.array(
        [sma, ecc, inc, raan, mean_motion, delta_sma_7d, shannon, lz76, dfa, adf],
        dtype=float,
    )
    mmd_typicality, mmd_stat = calculate_mmd_typicality(mmd_feature_subset, reference_matrix)

    return {
        "semi_major_axis_km": sma,
        "eccentricity": ecc,
        "inclination_deg": inc,
        "raan_deg": raan,
        "mean_motion_rev_per_day": mean_motion,
        "delta_sma_7d_km": delta_sma_7d,
        "delta_sma_30d_km": delta_sma_30d,
        "delta_inc_30d_deg": delta_inc_30d,
        "regime_changes_30d": float(regime_changes),
        "shannon_entropy_sma_30d": shannon,
        "shannon_entropy_sma_short": float(shannon_short),
        "lz76_complexity": lz76,
        "permutation_entropy": float(perm_entropy),
        "complexity_entropy_c": float(c_js),
        "dfa_hurst_sma": dfa,
        "dfa_hurst_sma_short": float(dfa_short),
        "persistence_dfa_gap": float(persistence_dfa_gap),
        "mandelbrot_tail_score": mandelbrot,
        "adf_pvalue": adf,
        "static_threat": static_threat,
        "page_cusum_sma": cusum,
        "ewma_sma": ewma,
        "bocpd_change_prob_3d": bocpd_prob,
        "bocpd_pred_ll": bocpd_ll,
        "innovation_score": innovation_score,
        "innovation_max_eps": innovation_eps,
        "ssa_residual_last": ssa_resid,
        "ssa_energy_ratio": ssa_energy,
        "mmd_typicality": mmd_typicality,
        "mmd_stat": mmd_stat,
        "h0_persistent": float(h0_pers),
        "h1_persistent": float(h1_pers),
        "tle_age_hours": tle_age,
        "f10_7": float(sw_feats.get("f10_7", 120.0)),
        "f10_7_adj": float(sw_feats.get("f10_7_adj", 120.0)),
        "ap_index": float(sw_feats.get("ap_index", 8.0)),
        "kp_mean": float(sw_feats.get("kp_mean", 2.0)),
        "sunspot_number": float(sw_feats.get("sunspot_number", 50.0)),
        "f10_7_delta_7d": float(sw_feats.get("f10_7_delta_7d", 0.0)),
        "f10_7_mean_7d": float(sw_feats.get("f10_7_mean_7d", 120.0)),
        "ap_mean_7d": float(sw_feats.get("ap_mean_7d", 8.0)),
        "ap_max_7d": float(sw_feats.get("ap_max_7d", 8.0)),
        "ap_delta_7d": float(sw_feats.get("ap_delta_7d", 0.0)),
        "geomagnetic_storm": float(sw_feats.get("geomagnetic_storm", 0.0)),
        "space_weather_available": float(sw_feats.get("space_weather_available", 0.0)),
        "min_distance_to_military_km": float(min_distance_to_military_km),
        "cointegration_pvalue": float(cointegration_pvalue),
        "dcca_rho": 0.0,
    }


def label_features_for_threat(features: Dict[str, float], min_dist_mil: Optional[float] = None) -> int:
    """
    Doctrine-based weak labels for supervised training (public SDA heuristics).
    0=NORMAL, 1=ANOMALOUS, 2=SUSPECT, 3=HOSTILE

    Geometry (dist / coint) is first-class — coherent with statistical audit:
    labels that use proximity must match features seen by XGBoost.
    Conservative so passive drag does not flood SUSPECT.
    """
    dist = features.get("min_distance_to_military_km", min_dist_mil if min_dist_mil is not None else 500.0)
    delta = abs(features.get("delta_sma_7d_km", 0.0))
    dfa = features.get("dfa_hurst_sma", 0.5)
    lz76 = features.get("lz76_complexity", 0.0)
    cusum = features.get("page_cusum_sma", 0.0)
    coint = features.get("cointegration_pvalue", 1.0)
    regime_changes = features.get("regime_changes_30d", 0)
    shannon = features.get("shannon_entropy_sma_30d", 0.0)
    anomaly = features.get("anomaly_score", 0.0)

    # Space weather context: strong geomag / high F10.7 inflate LEO drag Δa
    # Soft-suppress HOSTILE when stormy + mild delta (favor drag over maneuver)
    storm = float(features.get("geomagnetic_storm", 0.0) or 0.0) >= 0.5
    ap = float(features.get("ap_index", 8.0) or 8.0)
    f107 = float(features.get("f10_7", 120.0) or 120.0)
    high_drag_climate = storm or ap >= 30.0 or f107 >= 180.0

    # HOSTILE: critical RPO geometry + active Δ / shadowing
    # Under high drag climate, require stronger Δ or cointegration for HOSTILE
    hostile_delta_thr = 3.0 if high_drag_climate else 2.0
    if dist < 25.0 and (delta > hostile_delta_thr or dfa > 0.6 or coint < 0.05 or anomaly > 0.55):
        if not (high_drag_climate and delta <= 2.5 and coint >= 0.05 and dist >= 15.0):
            return 3
    if delta > (5.0 if high_drag_climate else 4.0) and dist < 80.0:
        return 3
    if coint < 0.05 and dist < 40.0 and dfa > 0.55:
        return 3

    # SUSPECT: mid-range approach, multi-episode maneuvering, or cointegrated pursuit
    if dist < 150.0 and (delta > 1.0 or dfa > 0.7 or coint < 0.08):
        return 2
    if delta > (2.5 if high_drag_climate else 2.0) and dist < 200.0:
        return 2
    if dfa > 0.65 and lz76 > 0.9 and dist < 250.0:
        return 2
    if regime_changes >= 2 and dist < 120.0:
        return 2
    if coint < 0.05 and dist < 80.0:
        return 2
    if dfa > 0.7 and shannon > 1.5 and delta > 1.0:
        return 2

    # ANOMALOUS: structural break without hostile geometry
    # Mild Δ under storm → more often NORMAL (natural drag), not ANOMALOUS
    if high_drag_climate and delta < 1.2 and dist > 150.0 and cusum < 0.9:
        return 0
    if cusum >= 0.7 and delta > 0.8:
        return 1
    if delta > (2.0 if high_drag_climate else 1.5):
        return 1
    if regime_changes >= 2 and delta > 0.5:
        return 1
    if anomaly > 0.55 and dist > 200.0:
        return 1

    return 0


def features_to_frame(feats: Dict[str, float], columns: List[str]) -> pd.DataFrame:
    row = {c: float(feats.get(c, 0.0)) for c in columns}
    return pd.DataFrame([row], columns=columns)


def predict_threat(
    iforest: IsolationForest,
    xgb: XGBClassifier,
    feats: Dict[str, float],
) -> Dict[str, Any]:
    """
    Full quantitative stage: Isolation Forest anomaly + XGBoost class probabilities.
    """
    # Align to training feature sets
    if_row = features_to_frame(feats, IFOREST_COLUMNS)
    # IsolationForest may have been trained on IFOREST_COLUMNS or older schema
    try:
        raw_score = float(iforest.decision_function(if_row)[0])
    except Exception:
        # Fallback: only shared columns
        common = [c for c in IFOREST_COLUMNS if c in getattr(iforest, "feature_names_in_", IFOREST_COLUMNS)]
        if not common:
            common = IFOREST_COLUMNS[: min(19, len(IFOREST_COLUMNS))]
        raw_score = float(iforest.decision_function(if_row[common] if hasattr(iforest, "feature_names_in_") else if_row)[0])

    anomaly_score = float(np.clip(0.5 - raw_score, 0.0, 1.0))
    feats = dict(feats)
    feats["anomaly_score"] = anomaly_score

    xgb_row = features_to_frame(feats, XGB_COLUMNS)
    try:
        proba = xgb.predict_proba(xgb_row)[0]
        class_id = int(np.argmax(proba))
    except Exception:
        # Older model with different columns — use intersection
        model_cols = list(getattr(xgb, "feature_names_in_", XGB_COLUMNS))
        aligned = pd.DataFrame([{c: feats.get(c, 0.0) for c in model_cols}])
        proba = xgb.predict_proba(aligned)[0]
        class_id = int(np.argmax(proba))

    return {
        "anomaly_score": anomaly_score,
        "xgb_class_id": class_id,
        "xgb_class": CLASS_NAMES.get(class_id, "NORMAL"),
        "xgb_proba": {CLASS_NAMES.get(i, str(i)): float(p) for i, p in enumerate(proba)},
        "xgb_confidence": float(np.max(proba)),
        "features": feats,
    }


def _build_synthetic_training_set() -> Tuple[pd.DataFrame, np.ndarray]:
    data_rows: List[Dict[str, float]] = []
    labels: List[int] = []

    # Normals (majority class — far from assets)
    for norad_id in range(1000, 1080):
        df = generate_mock_tle_history(norad_id, num_days=60, anomaly_type=None)
        for end_idx in range(MIN_WINDOW, len(df) + 1, 2):
            sub = df.iloc[end_idx - MIN_WINDOW : end_idx]
            feats = extract_satellite_features(
                sub, country="US", purpose="commercial", orbit_class="LEO",
                min_distance_to_military_km=float(np.random.uniform(200, 500)),
            )
            data_rows.append(feats)
            labels.append(label_features_for_threat(feats))

    # Impulsive maneuvers (mix of near/far assets)
    for norad_id in range(2000, 2040):
        df = generate_mock_tle_history(norad_id, num_days=60, anomaly_type="impulsive_maneuver")
        dist = float(np.random.choice([12.0, 40.0, 90.0, 300.0]))
        for end_idx in range(MIN_WINDOW, len(df) + 1, 2):
            sub = df.iloc[end_idx - MIN_WINDOW : end_idx]
            feats = extract_satellite_features(
                sub, country="RU", purpose="military", orbit_class="LEO",
                min_distance_to_military_km=dist,
            )
            data_rows.append(feats)
            labels.append(label_features_for_threat(feats))

    # Low-thrust disguised
    for norad_id in range(3000, 3040):
        df = generate_mock_tle_history(norad_id, num_days=60, anomaly_type="low_thrust_disguised")
        dist = float(np.random.choice([8.0, 25.0, 80.0, 250.0]))
        for end_idx in range(MIN_WINDOW, len(df) + 1, 2):
            sub = df.iloc[end_idx - MIN_WINDOW : end_idx]
            feats = extract_satellite_features(
                sub, country="CN", purpose="military", orbit_class="LEO",
                min_distance_to_military_km=dist,
            )
            data_rows.append(feats)
            labels.append(label_features_for_threat(feats))

    # Shadowing pairs (cointegration signal) — minority but critical
    for seed in range(12):
        t_id, s_id = 4000 + seed, 5000 + seed
        df_t, df_s = generate_shadowing_pair(t_id, s_id, num_days=60)
        for end_idx in range(MIN_WINDOW, len(df_s) + 1, 3):
            sub = df_s.iloc[end_idx - MIN_WINDOW : end_idx]
            sub_t = df_t.iloc[end_idx - MIN_WINDOW : end_idx]
            from src.engine import calculate_cointegration_pvalue

            coint = calculate_cointegration_pvalue(
                sub["semi_major_axis_km"].values,
                sub_t["semi_major_axis_km"].values,
            )
            dist = float(abs(sub["semi_major_axis_km"].iloc[-1] - sub_t["semi_major_axis_km"].iloc[-1]))
            feats = extract_satellite_features(
                sub, country="CN", purpose="sigint", orbit_class="LEO",
                min_distance_to_military_km=max(dist, 5.0),
                cointegration_pvalue=coint,
            )
            data_rows.append(feats)
            labels.append(label_features_for_threat(feats))

    return pd.DataFrame(data_rows), np.array(labels)


def _try_load_history_store_training(
    max_windows_per_sat: int = 40,
    step: int = 5,
) -> Optional[Tuple[pd.DataFrame, np.ndarray]]:
    """
    Preferred real training source: data/history/epochs (HF seed + daily).
    Injects catalog country/purpose and approximate min_distance to assets
    so XGBoost sees the same geometry used in labels (statistical alignment).
    """
    try:
        from src.tle_store import history_as_sat_histories, load_history
        from src.orbital import min_distance_to_assets
        from src.engine import calculate_cointegration_pvalue
    except Exception:
        return None

    hist_all = load_history()
    if len(hist_all) < 100:
        return None

    hists = history_as_sat_histories(min_epochs=MIN_WINDOW)
    if len(hists) < 4:
        return None

    # Catalog meta
    try:
        from src.catalog import asset_ids, get_meta, baseline_ids

        assets = set(asset_ids())
        baselines = set(baseline_ids())
    except Exception:
        assets, baselines = set(), set()
        def get_meta(nid: int) -> Dict[str, Any]:
            return {"country": "UNKNOWN", "purpose": "unknown", "orbit_class": "LEO", "role": "unknown"}

    asset_h = {i: h for i, h in hists.items() if i in assets} if assets else {}
    # If no assets tagged, use nothing for dist (500 default)

    data_rows: List[Dict[str, float]] = []
    labels: List[int] = []

    for sid, hist in hists.items():
        meta = get_meta(int(sid))
        country = str(meta.get("country") or "UNKNOWN")
        purpose = str(meta.get("purpose") or "unknown")
        orbit = str(meta.get("orbit_class") or "LEO")
        role = str(meta.get("role") or "unknown")

        h = hist.sort_values("timestamp").reset_index(drop=True)
        ends = list(range(MIN_WINDOW, len(h) + 1, step))[-max_windows_per_sat:]
        others = {k: v for k, v in asset_h.items() if k != int(sid)}

        for e in ends:
            sub = h.iloc[e - 20 : e]
            dist = 500.0
            coint = 1.0
            if others:
                try:
                    dist, closest = min_distance_to_assets(sub, others, cap_km=2000.0)
                    if closest is not None and closest in hists:
                        n = min(60, len(sub), len(hists[closest]))
                        coint = calculate_cointegration_pvalue(
                            sub["semi_major_axis_km"].astype(float).values[-n:],
                            hists[closest]["semi_major_axis_km"].astype(float).values[-n:],
                        )
                except Exception:
                    pass
            # Baseline assets far from "self-threat"
            if role == "baseline":
                dist = max(float(dist), 300.0)
            try:
                win_end = pd.to_datetime(sub["timestamp"].iloc[-1], utc=True, errors="coerce")
                feats = extract_satellite_features(
                    sub,
                    country=country,
                    purpose=purpose,
                    orbit_class=orbit,
                    min_distance_to_military_km=float(dist),
                    cointegration_pvalue=float(coint),
                    reference_time=win_end if pd.notnull(win_end) else None,
                )
                # Placeholder anomaly; refined after IF fit
                feats["anomaly_score"] = 0.0
                # Temporal metadata for purge split (dropped before model fit)
                feats["_window_end"] = str(win_end) if pd.notnull(win_end) else None
                feats["_norad_id"] = int(sid)
                lab = label_features_for_threat(feats)
                data_rows.append(feats)
                labels.append(lab)
            except Exception:
                continue

    if len(data_rows) < 80:
        return None
    print(f"History store training: {len(data_rows)} windows from {len(hists)} sats")
    return pd.DataFrame(data_rows), np.array(labels)


def _temporal_purge_split(
    times: pd.Series,
    sat_ids: pd.Series,
    y: np.ndarray,
    *,
    test_frac: float = 0.2,
    purge_days: int = 14,
) -> Tuple[np.ndarray, np.ndarray, str]:
    """
    Temporal train/test with purge gap to reduce leakage from overlapping windows.
    Falls back to random stratified split if timestamps are unusable.
    """
    t = pd.to_datetime(times, utc=True, errors="coerce")
    if t.notna().sum() < max(40, int(0.5 * len(t))):
        idx = np.arange(len(y))
        try:
            tr, te = train_test_split(idx, test_size=test_frac, random_state=42, stratify=y)
        except ValueError:
            tr, te = train_test_split(idx, test_size=test_frac, random_state=42)
        return np.asarray(tr), np.asarray(te), "random_fallback"

    order = np.argsort(t.values)
    cut_i = int(len(order) * (1.0 - test_frac))
    cut_i = min(max(cut_i, 10), len(order) - 10)
    cut_time = pd.Timestamp(t.values[order[cut_i]])
    if cut_time.tzinfo is None:
        cut_time = cut_time.tz_localize("UTC")
    purge = pd.Timedelta(days=purge_days)
    train_mask = t < (cut_time - purge)
    test_mask = t >= cut_time
    train_idx = np.where(train_mask.values)[0]
    test_idx = np.where(test_mask.values)[0]
    if len(train_idx) < 30 or len(test_idx) < 10:
        idx = np.arange(len(y))
        try:
            tr, te = train_test_split(idx, test_size=test_frac, random_state=42, stratify=y)
        except ValueError:
            tr, te = train_test_split(idx, test_size=test_frac, random_state=42)
        return np.asarray(tr), np.asarray(te), "random_fallback_small"
    return train_idx, test_idx, f"temporal_purge_{purge_days}d"


def _try_load_real_training() -> Optional[Tuple[pd.DataFrame, np.ndarray]]:
    """Legacy CSV path; prefer history store when present."""
    store = _try_load_history_store_training()
    if store is not None:
        return store

    candidates = [
        MODELS_DIR.parent / "data" / "real_tle_history_2024_2026.csv",
        MODELS_DIR.parent / "data" / "real_celestrak_active.csv",
    ]
    path = next((p for p in candidates if p.exists()), None)
    if path is None:
        return None

    try:
        df_real = pd.read_csv(path)
    except Exception:
        return None

    cols = {c.upper(): c for c in df_real.columns}
    if "NORAD_CAT_ID" in cols or "NORAD_CAT_ID" in df_real.columns:
        id_col = "NORAD_CAT_ID" if "NORAD_CAT_ID" in df_real.columns else cols.get("NORAD_CAT_ID")
        epoch_col = "EPOCH" if "EPOCH" in df_real.columns else None
        mm_col = "MEAN_MOTION" if "MEAN_MOTION" in df_real.columns else None
        if not all([id_col, epoch_col, mm_col]):
            return None

        mu = 398600.4418
        n_rad_s = df_real[mm_col] * (2 * np.pi / 86400.0)
        df_real = df_real.copy()
        df_real["semi_major_axis_km"] = (mu / (n_rad_s ** 2)) ** (1.0 / 3.0)
        df_real["inclination_deg"] = df_real["INCLINATION"]
        df_real["eccentricity"] = df_real["ECCENTRICITY"]
        df_real["raan_deg"] = df_real["RA_OF_ASC_NODE"] if "RA_OF_ASC_NODE" in df_real.columns else 0.0
        df_real["mean_motion_rev_per_day"] = df_real[mm_col]
        df_real["tle_age_hours"] = 12.0
        df_real["timestamp"] = pd.to_datetime(df_real[epoch_col], errors="coerce")
        df_real = df_real.dropna(subset=["timestamp"])
        df_real.sort_values(by=[id_col, "timestamp"], inplace=True)

        data_rows, labels = [], []
        for sat_id, group in df_real.groupby(id_col):
            if len(group) < MIN_WINDOW + 5:
                continue
            obj_name = str(group["OBJECT_NAME"].iloc[0]) if "OBJECT_NAME" in group.columns else "UNKNOWN"
            c = "US" if any(x in obj_name.upper() for x in ("USA", "STARLINK", "ISS", "NAVSTAR")) else (
                "CN" if "YAOGAN" in obj_name.upper() or "BEIDOU" in obj_name.upper() else (
                    "RU" if "COSMOS" in obj_name.upper() else "UNKNOWN"
                )
            )
            p = "military" if c in ("CN", "RU") or "USA" in obj_name.upper() else "scientific"
            for end_idx in range(MIN_WINDOW, min(len(group), 140), 4):
                sub = group.iloc[end_idx - MIN_WINDOW : end_idx]
                o_class = "LEO" if sub["semi_major_axis_km"].iloc[-1] < 8000 else "MEO"
                dist = 500.0
                try:
                    feats = extract_satellite_features(
                        sub, country=c, purpose=p, orbit_class=o_class,
                        min_distance_to_military_km=dist,
                    )
                    data_rows.append(feats)
                    labels.append(label_features_for_threat(feats))
                except Exception:
                    continue
        if len(data_rows) < 50:
            return None
        print(f"Dados reais (CSV legado): {len(data_rows)} janelas de {path.name}")
        return pd.DataFrame(data_rows), np.array(labels)
    return None


def _synth_threat_boost() -> Tuple[pd.DataFrame, np.ndarray]:
    """
    Small synthetic set ONLY for rare HOSTIL/SUSPEITO geometry — not full sky.
    Used when real history is almost all NORMAL (prevents drowning real data in synthetic data).
    """
    data_rows: List[Dict[str, float]] = []
    labels: List[int] = []
    # Impulsive near-asset
    for norad_id in range(2000, 2015):
        df = generate_mock_tle_history(norad_id, num_days=60, anomaly_type="impulsive_maneuver")
        dist = float(np.random.choice([8.0, 18.0, 40.0]))
        for end_idx in range(MIN_WINDOW, len(df) + 1, 3):
            sub = df.iloc[end_idx - MIN_WINDOW : end_idx]
            feats = extract_satellite_features(
                sub, country="RU", purpose="military", orbit_class="LEO",
                min_distance_to_military_km=dist,
            )
            data_rows.append(feats)
            labels.append(label_features_for_threat(feats))
    # Low-thrust near
    for norad_id in range(3000, 3012):
        df = generate_mock_tle_history(norad_id, num_days=60, anomaly_type="low_thrust_disguised")
        dist = float(np.random.choice([12.0, 30.0, 70.0]))
        for end_idx in range(MIN_WINDOW, len(df) + 1, 3):
            sub = df.iloc[end_idx - MIN_WINDOW : end_idx]
            feats = extract_satellite_features(
                sub, country="CN", purpose="military", orbit_class="LEO",
                min_distance_to_military_km=dist,
            )
            data_rows.append(feats)
            labels.append(label_features_for_threat(feats))
    # Shadowing
    for seed in range(8):
        t_id, s_id = 4000 + seed, 5000 + seed
        df_t, df_s = generate_shadowing_pair(t_id, s_id, num_days=60)
        for end_idx in range(MIN_WINDOW, len(df_s) + 1, 4):
            sub = df_s.iloc[end_idx - MIN_WINDOW : end_idx]
            sub_t = df_t.iloc[end_idx - MIN_WINDOW : end_idx]
            from src.engine import calculate_cointegration_pvalue

            coint = calculate_cointegration_pvalue(
                sub["semi_major_axis_km"].values,
                sub_t["semi_major_axis_km"].values,
            )
            dist = float(abs(sub["semi_major_axis_km"].iloc[-1] - sub_t["semi_major_axis_km"].iloc[-1]))
            feats = extract_satellite_features(
                sub, country="CN", purpose="sigint", orbit_class="LEO",
                min_distance_to_military_km=max(dist, 5.0),
                cointegration_pvalue=coint,
            )
            data_rows.append(feats)
            labels.append(label_features_for_threat(feats))
    return pd.DataFrame(data_rows), np.array(labels)


def train_and_save_models(
    use_real_if_available: bool = True,
    *,
    augment_threats: bool = True,
) -> Dict[str, Any]:
    """
    Train Isolation Forest + XGBoost.

    Priority (Statistical Baseline Alignment):
      1) history store (watchlist real TLE)
      2) light synthetic boost for rare HOSTIL/SUSPEITO only
      3) full synthetic fallback if no real data
    """
    real = _try_load_real_training() if use_real_if_available else None
    source = "synthetic"
    if real is not None:
        X_df, y = real
        source = "history_store"
        # Only boost minority threat classes if almost no HOSTILE/SUSPECT
        n_hot = int(sum((y == 2) | (y == 3)))
        if augment_threats and n_hot < max(30, int(0.05 * len(y))):
            boost_X, boost_y = _synth_threat_boost()
            X_df = pd.concat([X_df, boost_X], ignore_index=True)
            y = np.concatenate([y, boost_y])
            source = "history_store+threat_boost"
            print(f"Light synthetic threat boost: +{len(boost_y)} windows (rare HOSTILE/SUSPECT in real data).")
        else:
            print("Training predominantly on real history data.")
    else:
        print("Generating synthetic training dataset (SDA scenarios)...")
        X_df, y = _build_synthetic_training_set()

    # Temporal metadata (optional) for purge split — not model features
    if "_window_end" not in X_df.columns:
        X_df["_window_end"] = None
    if "_norad_id" not in X_df.columns:
        X_df["_norad_id"] = -1
    times = X_df["_window_end"]
    sat_ids = X_df["_norad_id"]
    drop_meta = [c for c in ("_window_end", "_norad_id") if c in X_df.columns]
    if drop_meta:
        X_df = X_df.drop(columns=drop_meta)

    # Ensure all feature columns exist
    for col in FEATURE_COLUMNS:
        if col not in X_df.columns:
            X_df[col] = 0.0
    X_df = X_df[FEATURE_COLUMNS].astype(float).replace([np.inf, -np.inf], 0.0).fillna(0.0)

    print(f"Dataset: {X_df.shape[0]} samples, {X_df.shape[1]} features. source={source}")
    print(
        f"Classes: Normal={sum(y==0)}, Anomalous={sum(y==1)}, "
        f"Suspect={sum(y==2)}, Hostile={sum(y==3)}"
    )

    os.makedirs(MODELS_DIR_STR, exist_ok=True)

    # Temporal train/test with purge (reduces leakage from overlapping windows)
    train_idx, test_idx, split_mode = _temporal_purge_split(times, sat_ids, y, test_frac=0.2, purge_days=14)
    print(f"Split mode: {split_mode}  train={len(train_idx)} test={len(test_idx)}")

    # --- Isolation Forest: prefer baseline/asset NORADs as normality (military doctrine) ---
    print("Training Isolation Forest (priority pipeline; separate from monitor IF)...")
    X_if = X_df[IFOREST_COLUMNS]
    y_train_tmp = y[train_idx]
    # Prefer weak-label NORMAL windows on train; further bias to baseline/asset if meta present
    normal_mask = y_train_tmp == 0
    X_normal = X_if.iloc[train_idx][normal_mask]
    if len(X_normal) < 30:
        X_normal = X_if.iloc[train_idx]
    contam = 0.06 if source.startswith("history") else 0.1
    iforest = IsolationForest(
        n_estimators=200,
        contamination=contam,
        random_state=42,
        n_jobs=-1,
    )
    iforest.fit(X_normal)

    # Unified anomaly score: clip(0.5 - raw)
    raw_scores = iforest.decision_function(X_if)
    X_full = X_df.copy()
    X_full["anomaly_score"] = np.clip(0.5 - raw_scores, 0.0, 1.0)
    y_relabel = np.array(
        [
            label_features_for_threat(
                {**X_full.iloc[i].to_dict(), "anomaly_score": float(X_full.iloc[i]["anomaly_score"])}
            )
            for i in range(len(X_full))
        ]
    )
    if len(np.unique(y_relabel)) >= 2:
        y = y_relabel

    X_xgb = X_full[XGB_COLUMNS]
    X_train, X_test = X_xgb.iloc[train_idx], X_xgb.iloc[test_idx]
    y_train, y_test = y[train_idx], y[test_idx]

    class_w = {0: 1.0, 1: 1.5, 2: 3.0, 3: 5.0}
    sw_train = np.array([class_w.get(int(yi), 1.0) for yi in y_train])

    print("Training XGBoost priority head (weak labels; not scientific proof)...")
    xgb = XGBClassifier(
        n_estimators=140,
        max_depth=5,
        learning_rate=0.08,
        objective="multi:softprob",
        num_class=4,
        subsample=0.9,
        colsample_bytree=0.9,
        random_state=42,
        eval_metric="mlogloss",
    )
    xgb.fit(X_train, y_train, sample_weight=sw_train)

    proba_test = xgb.predict_proba(X_test)
    pred_test = np.argmax(proba_test, axis=1)
    try:
        ll = float(log_loss(y_test, proba_test, labels=[0, 1, 2, 3]))
        if not np.isfinite(ll):
            ll = None
    except Exception:
        ll = None
    report = classification_report(
        y_test,
        pred_test,
        labels=[0, 1, 2, 3],
        target_names=[METRIC_CLASS_NAMES[i] for i in range(4)],
        output_dict=True,
        zero_division=0,
    )
    metrics = {
        "n_samples": int(len(X_df)),
        "n_features": int(X_xgb.shape[1]),
        "training_source": source,
        "iforest_contamination": contam,
        "anomaly_score_formula": "clip(0.5 - decision_function)",
        "sample_weights": class_w,
        "split_mode": split_mode,
        "purge_days": 14,
        "log_loss_test": ll,
        "accuracy_test": float(report.get("accuracy", 0.0)),
        "macro_f1": float(report.get("macro avg", {}).get("f1-score", 0.0)),
        "class_distribution": {METRIC_CLASS_NAMES[i]: int(sum(y == i)) for i in range(4)},
        "classification_report": report,
        "feature_columns": list(XGB_COLUMNS),
        "iforest_columns": list(IFOREST_COLUMNS),
        "homology_mode": homology_backend(),
        "role": "priority_head_weak_labels",
        "doctrine": "military_first_sda",
        "disclaimer": (
            "XGBoost is an operational priority head (weak labels), NOT military ground truth. "
            "Detection of persistent micro-trajectory noise is Isolation Forest vs normality anchors "
            "(baseline+asset). Validation: walk-forward on military interest cases vs civil EO controls."
        ),
        "statistically_coherent_fixes": [
            "history_store_primary_training",
            "geometry_in_features_and_labels",
            "unified_anomaly_score",
            "temporal_purge_split",
            "if_fit_on_train_only",
            "rkhs_excluded_from_iforest",
            "monitor_if_not_overwritten",
            "military_baseline_train_suspect_score",
            "asymmetric_class_weights",
        ],
    }
    ll_s = f"{ll:.4f}" if ll is not None else "n/a"
    print(
        f"Test accuracy={metrics['accuracy_test']:.3f}  log_loss={ll_s}  "
        f"macro_F1={metrics['macro_f1']:.3f}  (weak-label agreement only)"
    )

    if_path = os.path.join(MODELS_DIR_STR, "isolation_forest.joblib")
    xgb_path = os.path.join(MODELS_DIR_STR, "xgboost_model.joblib")
    joblib.dump(iforest, if_path)
    joblib.dump(xgb, xgb_path)

    # MMD reference: normal subset of core features (diagnostic / optional)
    rkhs_cols = [
        "semi_major_axis_km", "eccentricity", "inclination_deg", "raan_deg",
        "mean_motion_rev_per_day", "delta_sma_7d_km", "shannon_entropy_sma_30d",
        "lz76_complexity", "dfa_hurst_sma", "adf_pvalue",
    ]
    normal_subset = X_df[y == 0][rkhs_cols].values
    if len(normal_subset) == 0:
        normal_subset = X_df[rkhs_cols].values[:50]
    rkhs_path = os.path.join(MODELS_DIR_STR, "rkhs_reference.joblib")
    joblib.dump(normal_subset, rkhs_path)

    try:
        from src.model_registry import register_model

        register_model(
            "pipeline_if",
            path=if_path,
            feature_columns=IFOREST_COLUMNS,
            extra={
                "n_samples": metrics["n_samples"],
                "contamination": contam,
                "split_mode": split_mode,
                "homology_mode": metrics["homology_mode"],
                "role": "priority_pipeline_if",
            },
        )
        register_model(
            "xgboost",
            path=xgb_path,
            feature_columns=XGB_COLUMNS,
            extra={
                "accuracy_test_weak_labels": metrics["accuracy_test"],
                "macro_f1": metrics["macro_f1"],
                "split_mode": split_mode,
                "disclaimer": metrics["disclaimer"],
            },
        )
        register_model(
            "rkhs_reference",
            path=rkhs_path,
            feature_columns=rkhs_cols,
            extra={"n_rows": int(len(normal_subset))},
        )
    except Exception as exc:
        print(f"Warning: registry update failed: {exc}")

    metrics_path = os.path.join(MODELS_DIR_STR, "training_metrics.json")
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2, ensure_ascii=False)
    print(f"Models and metrics saved to {MODELS_DIR_STR}")
    return metrics


def load_models() -> Tuple[IsolationForest, XGBClassifier, np.ndarray, Dict[str, Any]]:
    """Load models; auto-train if missing."""
    iforest_path = os.path.join(MODELS_DIR_STR, "isolation_forest.joblib")
    xgb_path = os.path.join(MODELS_DIR_STR, "xgboost_model.joblib")
    rkhs_path = os.path.join(MODELS_DIR_STR, "rkhs_reference.joblib")
    metrics_path = os.path.join(MODELS_DIR_STR, "training_metrics.json")

    if not (os.path.exists(iforest_path) and os.path.exists(xgb_path) and os.path.exists(rkhs_path)):
        print("Models not found. Training automatically...")
        train_and_save_models()

    iforest = joblib.load(iforest_path)
    xgb = joblib.load(xgb_path)
    rkhs_ref = joblib.load(rkhs_path)
    metrics: Dict[str, Any] = {}
    if os.path.exists(metrics_path):
        with open(metrics_path, encoding="utf-8") as f:
            metrics = json.load(f)
    return iforest, xgb, rkhs_ref, metrics
