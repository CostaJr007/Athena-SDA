"""Regression tests for the `--threshold None` onset bug (src/anomaly_monitor.py).

Before the fix, score_latest() called `float(anomaly_threshold)` with the CLI
default of None, raising TypeError and silently disabling anomaly-onset
estimation. `resolve_thresholds` now centralizes and de-Nones the value.
"""
from __future__ import annotations

from src.anomaly_monitor import resolve_thresholds


def test_none_threshold_falls_back_to_default() -> None:
    thr_global, thr_elevated = resolve_thresholds(None, {})
    assert thr_global == 0.50
    assert 0.45 <= thr_elevated <= 0.50


def test_explicit_threshold_is_preserved() -> None:
    thr_global, thr_elevated = resolve_thresholds(0.55, {})
    assert thr_global == 0.55
    assert 0.45 <= thr_elevated <= 0.55


def test_cli_threshold_overrides_meta() -> None:
    meta = {"recommended_anomaly_threshold": 0.60}
    thr_global, _ = resolve_thresholds(0.55, meta)
    assert thr_global == 0.55


def test_meta_recommended_used_when_cli_is_none() -> None:
    meta = {"recommended_anomaly_threshold": 0.60}
    thr_global, _ = resolve_thresholds(None, meta)
    assert thr_global == 0.60


def test_calibration_p90_drives_elevated() -> None:
    meta = {"calibration": {"global": {"recommended_thr": 0.50, "p90": 0.42}}}
    _, thr_elevated = resolve_thresholds(None, meta)
    assert thr_elevated == 0.42


def test_never_returns_none() -> None:
    for arg, meta in [(None, {}), (0.55, {}), (None, {"score_p95": 0.6})]:
        thr_global, thr_elevated = resolve_thresholds(arg, meta)
        assert isinstance(thr_global, float)
        assert isinstance(thr_elevated, float)
        assert 0.0 < thr_global <= 1.0
        assert 0.0 < thr_elevated <= 1.0
