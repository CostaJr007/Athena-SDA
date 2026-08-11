"""
Athena-SDA configuration: paths, feature schema, threat labels, catalog.
"""
from __future__ import annotations

import os
from pathlib import Path

# Project root (parent of src/)
ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
MODELS_DIR = ROOT / "models"
DOCS_DIR = ROOT / "docs"
# Anomaly monitor stores (created by src/tle_store.py)
HISTORY_DIR = DATA_DIR / "history"
DAILY_DIR = DATA_DIR / "daily"
ALERTS_DIR = DATA_DIR / "alerts"

# Optional .env loading (no crash if python-dotenv missing)
try:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
except ImportError:
    pass

# --- Earth / orbital constants ---
MU_EARTH_KM3_S2 = 398600.4418
R_EARTH_KM = 6371.0

# --- Feature window (epochs per feature vector) ---
# WINDOW=30: ~30 days of daily-cadence TLE; activates DFA/ADF (inert at 20).
# Set to 20 if the longer window regresses validation (re-run paper validation).
MIN_WINDOW = 20

# --- Feature vector used by Isolation Forest + XGBoost (order fixed) ---
# delta_sma_7d/30d are EPOCH-based (rows -7 / row 0 of a 20-epoch window),
# NOT calendar days — documented here to avoid semantic confusion.
FEATURE_COLUMNS = [
    # Instantaneous Keplerian
    "semi_major_axis_km",
    "eccentricity",
    "inclination_deg",
    "raan_deg",
    "mean_motion_rev_per_day",
    # Temporal deltas (epoch-based)
    "delta_sma_7d_km",
    "delta_sma_30d_km",
    "delta_inc_30d_deg",
    "regime_changes_30d",
    # Corrected math framework (see docs/PROOF_DOSSIER.md for citations)
    "shannon_entropy_sma_30d",
    "shannon_entropy_sma_short",
    "lz76_complexity",
    "permutation_entropy",
    "complexity_entropy_c",
    "dfa_hurst_sma",
    "dfa_hurst_sma_short",
    "persistence_dfa_gap",
    "mandelbrot_tail_score",
    "adf_pvalue",
    "static_threat",
    "page_cusum_sma",
    "ewma_sma",
    "bocpd_change_prob_3d",
    "bocpd_pred_ll",
    "innovation_score",
    "innovation_max_eps",
    "ssa_residual_last",
    "ssa_energy_ratio",
    "mmd_typicality",
    "mmd_stat",
    "h0_persistent",
    "h1_persistent",
    "tle_age_hours",
    # Space weather (solar / geomagnetic) — reduce drag-vs-maneuver confusion
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
    "min_distance_to_military_km",
    "cointegration_pvalue",
    "dcca_rho",
]

# Isolation Forest trains WITHOUT multi-object / reference context
# (proximity, cointegration, DCCA) and WITHOUT live-reference features
# (MMD requires a normality reference matrix at prediction time). Space
# weather IS included in IF — part of the "normal climate" background.
IFOREST_COLUMNS = [c for c in FEATURE_COLUMNS if c not in (
    "min_distance_to_military_km",
    "cointegration_pvalue",
    "dcca_rho",
    "mmd_typicality",
    "mmd_stat",
)]

# XGBoost uses full feature set including anomaly_score injected after IF
XGB_COLUMNS = FEATURE_COLUMNS + ["anomaly_score"]

CLASS_NAMES = {
    0: "NORMAL",
    1: "ANOMALOUS",
    2: "SUSPECT",
    3: "HOSTILE",
}
CLASS_TO_ID = {
    "NORMAL": 0,
    "ANOMALOUS": 1,
    "ANÔMALO": 1,
    "ANOMALO": 1,
    "SUSPECT": 2,
    "SUSPEITO": 2,
    "HOSTILE": 3,
    "HOSTIL": 3,
}

# High-value assets treated as "military protected" for proximity.
# Prefer data/catalog/watchlist.json (role=asset); fallback keeps old demo IDs.
def _military_asset_ids() -> set:
    try:
        from src.catalog import asset_ids

        ids = asset_ids()
        if ids:
            return set(ids)
    except Exception:
        pass
    return {25544, 39166, 28874, 28054}  # ISS + GPS + DMSP fallback


MILITARY_ASSET_IDS = _military_asset_ids()

# Default severity weights for Kelly (purpose → severity multiplier)
PURPOSE_SEVERITY = {
    "military": 100.0,
    "sigint": 95.0,
    "reconnaissance": 90.0,
    "asat_test": 100.0,
    "debris removal": 40.0,
    "scientific": 15.0,
    "navigation": 20.0,
    "telecom": 10.0,
    "commercial": 10.0,
    "earth obs": 15.0,
    "unknown": 25.0,
}

# Environment helpers
def env(key: str, default: str = "") -> str:
    return os.environ.get(key, default) or default
