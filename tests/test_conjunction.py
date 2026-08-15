"""Conjunction extras (Pc / TCA) must not rewrite pair_risk."""
from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd

from src.conjunction import estimate_conjunction, foster_pc
from src.utils import generate_mock_tle_history


def test_foster_pc_closer_is_higher() -> None:
    close = foster_pc(1.0, 5.0)
    far = foster_pc(50.0, 5.0)
    assert 0.0 <= close <= 1.0
    assert far < close


def test_enrich_risk_report_does_not_rewrite_pair_risk() -> None:
    from src.conjunction import enrich_risk_report

    a = generate_mock_tle_history(9001, num_days=30, anomaly_type=None)
    b = generate_mock_tle_history(9002, num_days=30, anomaly_type=None)
    a["timestamp"] = pd.date_range("2026-01-01", periods=len(a), freq="D", tz="UTC")
    b["timestamp"] = pd.date_range("2026-01-01", periods=len(b), freq="D", tz="UTC")
    report = {
        "top_pairs": [
            {
                "suspect_norad": 9001,
                "asset_norad": 9002,
                "pair_risk": 0.42,
                "min_distance_km": 120.0,
            }
        ],
        "board": [
            {
                "norad_id": 9001,
                "pair": {"asset_norad": 9002, "pair_risk": 0.42, "min_distance_km": 120.0},
            }
        ],
    }
    # No history store for 9001/9002 — enrich must still keep pair_risk.
    out = enrich_risk_report(report)
    assert out["top_pairs"][0]["pair_risk"] == 0.42
    assert out["board"][0]["pair"]["pair_risk"] == 0.42


def test_estimate_conjunction_adds_fields_without_crash() -> None:
    a = generate_mock_tle_history(9001, num_days=30, anomaly_type=None)
    b = generate_mock_tle_history(9002, num_days=30, anomaly_type=None)
    a["timestamp"] = pd.date_range("2026-01-01", periods=len(a), freq="D", tz="UTC")
    b["timestamp"] = pd.date_range("2026-01-01", periods=len(b), freq="D", tz="UTC")
    now = datetime(2026, 1, 30, tzinfo=timezone.utc)
    conj = estimate_conjunction(a, b, horizon_hours=6, step_seconds=600, now=now)
    assert conj["method"] in ("sgp4", "kepler_circular", "unavailable")
    if conj["method"] != "unavailable":
        assert conj["miss_distance_km"] is not None
        assert conj["pc"] is not None
        assert 0.0 <= float(conj["pc"]) <= 1.0
