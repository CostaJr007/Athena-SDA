"""Feature-schema invariants (extract_satellite_features + IFOREST_COLUMNS)."""
from __future__ import annotations

from src.config import FEATURE_COLUMNS, IFOREST_COLUMNS
from src.models import extract_satellite_features
from src.utils import generate_mock_tle_history

LEGACY_FEATURES = [
    "kolmogorov_proxy_7d",
    "hurst_exponent_sma",
    "l1_cusum_sma",
    "spectral_anomaly_rkhs",
    "chern_simons_proxy",
    "ricci_mean",
    "williams_threat",
    "lukasiewicz_implication",
    "maneuver_count_30d",
]


def test_features_cover_iforest_columns() -> None:
    df = generate_mock_tle_history(9001, num_days=60, anomaly_type=None)
    feats = extract_satellite_features(
        df.iloc[-40:],
        country="US",
        purpose="scientific",
        orbit_class="LEO",
        min_distance_to_military_km=400.0,
    )
    for c in IFOREST_COLUMNS:
        assert c in feats, f"missing IF feature {c}"


def test_mmd_excluded_from_iforest_columns() -> None:
    assert "mmd_typicality" not in IFOREST_COLUMNS
    assert "mmd_stat" not in IFOREST_COLUMNS


def test_no_legacy_features_remain() -> None:
    df = generate_mock_tle_history(9002, num_days=60, anomaly_type=None)
    feats = extract_satellite_features(
        df.iloc[-40:],
        country="US",
        purpose="scientific",
        orbit_class="LEO",
    )
    for bad in LEGACY_FEATURES:
        assert bad not in feats, f"legacy feature still present: {bad}"


def test_feature_columns_ordering_is_fixed() -> None:
    assert FEATURE_COLUMNS == list(dict.fromkeys(FEATURE_COLUMNS))  # no duplicates
    assert set(IFOREST_COLUMNS).issubset(set(FEATURE_COLUMNS))
