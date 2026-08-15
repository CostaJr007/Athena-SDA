"""Unit tests for the corrected math framework (src/engine.py)."""
from __future__ import annotations

import numpy as np

from src.engine import (
    calculate_dfa_hurst,
    calculate_ewma,
    calculate_lz76_complexity,
    calculate_mandelbrot_tail_anomaly,
    calculate_mmd_typicality,
    calculate_page_cusum,
    calculate_permutation_entropy,
    calculate_ssa_residual,
    count_regime_changes,
    homology_backend,
)


def test_lz76_regular_is_less_complex_than_chaotic() -> None:
    rng = np.random.default_rng(7)
    ramp = 7000.0 + np.arange(30) * 0.5
    chaotic = 7000.0 + np.cumsum(rng.normal(0.0, 0.5, 30))
    assert calculate_lz76_complexity(ramp) < calculate_lz76_complexity(chaotic)


def test_lz76_short_series_is_zero() -> None:
    assert calculate_lz76_complexity(np.array([1.0, 1.01, 1.02])) == 0.0


def test_dfa_neutral_on_short_series() -> None:
    h = calculate_dfa_hurst(np.linspace(0, 1, 8))
    assert abs(h - 0.5) < 1e-9


def test_dfa_activates_at_n30() -> None:
    rng = np.random.default_rng(1)
    h = calculate_dfa_hurst(np.cumsum(rng.normal(0.0, 0.1, 30)))
    assert abs(h - 0.5) > 1e-9


def test_permutation_entropy_in_unit_range() -> None:
    pe = calculate_permutation_entropy(np.linspace(0, 1, 30))
    assert 0.0 <= pe <= 1.0


def test_ssa_residual_finite_and_energy_in_range() -> None:
    resid, energy = calculate_ssa_residual(np.linspace(0, 1, 30))
    assert np.isfinite(resid)
    assert 0.0 <= energy <= 1.0


def test_cusum_and_ewma_separate_maneuver_from_quiet() -> None:
    rng = np.random.default_rng(7)
    quiet = 7000.0 + np.cumsum(rng.normal(0.0, 0.02, 30))
    maneuver = quiet.copy()
    maneuver[18:] += 4.0
    assert calculate_page_cusum(maneuver) > calculate_page_cusum(quiet)
    assert calculate_ewma(maneuver) > calculate_ewma(quiet)
    assert count_regime_changes(maneuver) >= 1


def test_mandelbrot_flat_series_is_zero() -> None:
    assert calculate_mandelbrot_tail_anomaly(np.ones(20)) == 0.0


def test_mmd_ranks_outlier_above_inlier() -> None:
    rng = np.random.default_rng(7)
    ref = rng.normal(0.0, 1.0, (60, 10))
    inlier = ref[0].copy()
    outlier = inlier.copy()
    outlier[0] += 6.0
    typ_in, _ = calculate_mmd_typicality(inlier, ref)
    typ_out, _ = calculate_mmd_typicality(outlier, ref)
    assert typ_out > typ_in


def test_mmd_no_reference_is_neutral() -> None:
    typ, stat = calculate_mmd_typicality(np.zeros(10), None)
    assert typ == 0.5
    assert stat == 0.0


def test_homology_backend_known_value() -> None:
    assert homology_backend() in ("proxy", "ripser")
