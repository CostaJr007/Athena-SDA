"""Unit tests for military-first doctrine role policy (src/doctrine.py)."""
from __future__ import annotations

from src.doctrine import classify_military_status, doctrine_summary, ids_for_if_training


def test_doctrine_summary_tag() -> None:
    assert doctrine_summary()["doctrine"] == "military_first_sda"


def test_ids_for_if_training_returns_something() -> None:
    assert ids_for_if_training(min_ids=1)


def test_ids_for_if_training_never_expands_to_suspects() -> None:
    ids = ids_for_if_training(available=[40258, 41038, 25544, 25994], min_ids=4)
    from src.catalog import get_meta

    for nid in ids:
        assert get_meta(nid).get("role") in ("asset", "baseline")


def test_baseline_never_escalates() -> None:
    out = classify_military_status(
        role="baseline",
        reliable=True,
        series_outlier=True,
        day_over_day_relevant=True,
    )
    assert out["is_anomaly"] is False
    assert out["is_military_detection"] is False
    assert out["status"] == "CALIBRATION_BASELINE"


def test_unreliable_data_short_circuits() -> None:
    out = classify_military_status(
        role="suspect",
        reliable=False,
        series_outlier=True,
        day_over_day_relevant=False,
    )
    assert out["status"] == "UNRELIABLE_DATA"
    assert out["is_military_detection"] is False


def test_suspect_outlier_is_military_detection() -> None:
    out = classify_military_status(
        role="suspect",
        reliable=True,
        series_outlier=True,
        day_over_day_relevant=False,
    )
    assert out["is_military_detection"] is True
    assert out["is_anomaly"] is True


def test_asset_noise_is_platform_health_not_hostile() -> None:
    out = classify_military_status(
        role="asset",
        reliable=True,
        series_outlier=True,
        day_over_day_relevant=False,
    )
    assert out["is_platform_health_flag"] is True
    assert out["is_military_detection"] is False
    assert out["status"] == "ASSET_REGIME_NOISE"
