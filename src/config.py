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

# Optional .env loading (no crash if python-dotenv missing)
try:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
except ImportError:
    pass

# --- Earth / orbital constants ---
MU_EARTH_KM3_S2 = 398600.4418
R_EARTH_KM = 6371.0

# --- Feature vector used by Isolation Forest + XGBoost (order fixed) ---
FEATURE_COLUMNS = [
    # Instantaneous Keplerian
    "semi_major_axis_km",
    "eccentricity",
    "inclination_deg",
    "raan_deg",
    "mean_motion_rev_per_day",
    # Temporal deltas
    "delta_sma_7d_km",
    "delta_sma_30d_km",
    "delta_inc_30d_deg",
    "maneuver_count_30d",
    # Math framework (Shannon → RKHS)
    "shannon_entropy_sma_30d",
    "kolmogorov_proxy_7d",
    "hurst_exponent_sma",
    "mandelbrot_tail_score",
    "adf_pvalue",
    "williams_threat",
    "l1_cusum_sma",
    "spectral_anomaly_rkhs",
    "chern_simons_proxy",
    "ricci_mean",
    "h0_persistent",
    "h1_persistent",
    "tle_age_hours",
    # Context (filled at inference; may be 0 at pure train windows)
    "min_distance_to_military_km",
    "cointegration_pvalue",
    "lukasiewicz_implication",
]

# Isolation Forest trains WITHOUT context/proximity features that require multi-object state
IFOREST_COLUMNS = [c for c in FEATURE_COLUMNS if c not in (
    "min_distance_to_military_km",
    "cointegration_pvalue",
    "lukasiewicz_implication",
)]

# XGBoost uses full feature set including anomaly_score injected after IF
XGB_COLUMNS = FEATURE_COLUMNS + ["anomaly_score"]

CLASS_NAMES = {
    0: "NORMAL",
    1: "ANÔMALO",
    2: "SUSPEITO",
    3: "HOSTIL",
}
CLASS_TO_ID = {v: k for k, v in CLASS_NAMES.items()}

# High-value assets treated as "military protected" for proximity (demo catalog)
MILITARY_ASSET_IDS = {4001, 43941}  # USSF / MILSAT demo targets

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
