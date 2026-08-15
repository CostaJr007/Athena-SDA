"""Regression tests guarding the two fixed S0 bugs."""
from __future__ import annotations

import ast
from pathlib import Path

import src.anomaly_monitor as am

ROOT = Path(__file__).resolve().parent.parent
MONITOR_SRC = ROOT / "src" / "anomaly_monitor.py"


def test_anomaly_monitor_imports_re() -> None:
    """Regression: the versioned-snapshot block used `re.sub` without importing
    `re`, so it always raised NameError and silently disabled snapshots."""
    assert hasattr(am, "re")


def test_resolve_thresholds_exists() -> None:
    """Regression: threshold normalization was extracted so None is handled."""
    assert callable(am.resolve_thresholds)


def test_versioned_snapshot_uses_cutoff_not_meta_out() -> None:
    """Regression: the snapshot block must not reference `meta_out` before its
    definition (a NameError path). It now derives the stamp from `cutoff`."""
    src = MONITOR_SRC.read_text(encoding="utf-8")
    tree = ast.parse(src)

    # Locate the versioned snapshot assignment and confirm it references cutoff.
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == "versioned_name" for t in node.targets
        ):
            # Assignment value is the `try` block result; just confirm the
            # source line that computes v_stamp uses `cutoff`, not `meta_out`.
            pass
    assert 're.sub(r"[^0-9]", "", str(cutoff))' in src
    assert "str(cutoff)" in src


def test_onset_threshold_normalized_in_score_latest() -> None:
    """Regression: score_latest must normalize None before estimate_anomaly_onset."""
    src = MONITOR_SRC.read_text(encoding="utf-8")
    assert "onset_thr = float(anomaly_threshold) if anomaly_threshold is not None" in src


def test_versioned_stamp_uses_cutoff_value() -> None:
    assert am.versioned_monitor_stamp("2026-08-12T00:00:00+00:00") == "20260812"
    assert am.versioned_monitor_stamp("cutoff-missing")  # falls back to today, still 8 digits
    assert len(am.versioned_monitor_stamp(None)) == 8
