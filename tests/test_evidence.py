"""Unit tests for Dempster-Shafer evidence fusion (src/evidence.py)."""
from __future__ import annotations

from src.evidence import fuse_evidence


def test_empty_evidence_is_neutral() -> None:
    out = fuse_evidence([])
    assert out["belief_anomalous"] == 0.0
    assert out["plausibility_anomalous"] == 0.5
    assert out["conflict_K"] == 0.0


def test_fusion_outputs_in_unit_range() -> None:
    out = fuse_evidence([0.9, 0.8, 0.3], tle_age_hours=12.0)
    assert 0.0 <= out["belief_anomalous"] <= 1.0
    assert 0.0 <= out["plausibility_anomalous"] <= 1.0
    assert 0.0 <= out["conflict_K"] <= 1.0


def test_stale_tle_increases_ignorance_not_belief() -> None:
    fresh = fuse_evidence([0.9], tle_age_hours=0.0)
    stale = fuse_evidence([0.9], tle_age_hours=400.0)
    # Ignorance grows with age → plausibility grows, belief stays bounded.
    assert stale["plausibility_anomalous"] >= fresh["plausibility_anomalous"]
    assert stale["belief_anomalous"] <= fresh["belief_anomalous"] + 1e-9


def test_agreement_produces_high_belief() -> None:
    out = fuse_evidence([0.99, 0.99, 0.99], tle_age_hours=0.0)
    assert out["belief_anomalous"] > 0.5
