"""
Orbital geometry helpers for Athena-SDA.

Provides SMA from mean motion, approximate ECI positions from
Keplerian elements, and minimum inter-satellite distances for
proximity / RPO analysis (no full SGP4 required for demo fidelity).
"""
from __future__ import annotations

from typing import Iterable, Mapping, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

from src.config import MU_EARTH_KM3_S2, R_EARTH_KM


def sma_from_mean_motion(mean_motion_rev_per_day: float) -> float:
    """Third Kepler law: a = (mu / n^2)^(1/3) with n in rad/s."""
    n = float(mean_motion_rev_per_day) * (2.0 * np.pi / 86400.0)
    if n <= 0:
        return float("nan")
    return float((MU_EARTH_KM3_S2 / (n ** 2)) ** (1.0 / 3.0))


def mean_motion_from_sma(sma_km: float) -> float:
    period = 2.0 * np.pi * np.sqrt((sma_km ** 3) / MU_EARTH_KM3_S2)
    return float(86400.0 / period)


def keplerian_to_eci(
    sma_km: float,
    inclination_deg: float,
    raan_deg: float,
    true_anomaly_deg: float = 0.0,
    eccentricity: float = 0.0,
) -> np.ndarray:
    """
    Approximate ECI position (km) for a near-circular orbit.
    True anomaly used as polar angle in orbital plane.
    """
    # Radius for elliptical orbit (approx)
    nu = np.radians(true_anomaly_deg)
    if eccentricity < 1e-8:
        r = sma_km
    else:
        r = sma_km * (1 - eccentricity ** 2) / (1 + eccentricity * np.cos(nu))

    x_orb = r * np.cos(nu)
    y_orb = r * np.sin(nu)
    z_orb = 0.0

    inc = np.radians(inclination_deg)
    raan = np.radians(raan_deg)

    # R3(raan) * R1(inc) applied to orbital-plane coords
    cos_o, sin_o = np.cos(raan), np.sin(raan)
    cos_i, sin_i = np.cos(inc), np.sin(inc)

    x = cos_o * x_orb - sin_o * cos_i * y_orb
    y = sin_o * x_orb + cos_o * cos_i * y_orb
    z = sin_i * y_orb
    return np.array([x, y, z], dtype=float)


def position_series_from_history(history_df: pd.DataFrame, n_samples: int = 24) -> np.ndarray:
    """
    Sample approximate 3D positions along the latest orbital state.
    Uses last-row elements and spreads true anomaly over 0..360°.
    """
    last = history_df.iloc[-1]
    sma = float(last["semi_major_axis_km"])
    inc = float(last["inclination_deg"])
    raan = float(last.get("raan_deg", 0.0))
    ecc = float(last.get("eccentricity", 0.0))

    # If multi-day history, also use evolving SMA for trajectory cloud
    if len(history_df) >= 5:
        idxs = np.linspace(0, len(history_df) - 1, min(n_samples, len(history_df))).astype(int)
        positions = []
        for i, idx in enumerate(idxs):
            row = history_df.iloc[idx]
            nu = (i / max(len(idxs) - 1, 1)) * 360.0
            positions.append(
                keplerian_to_eci(
                    float(row["semi_major_axis_km"]),
                    float(row["inclination_deg"]),
                    float(row.get("raan_deg", raan)),
                    true_anomaly_deg=nu,
                    eccentricity=float(row.get("eccentricity", ecc)),
                )
            )
        return np.asarray(positions)

    thetas = np.linspace(0, 360, n_samples, endpoint=False)
    return np.stack([keplerian_to_eci(sma, inc, raan, t, ecc) for t in thetas])


def approximate_relative_distance_km(
    sma_a: float,
    inc_a: float,
    raan_a: float,
    sma_b: float,
    inc_b: float,
    raan_b: float,
    samples: int = 36,
) -> float:
    """
    Minimum approximate distance (km) between two circular orbits
    sampled over true anomaly grid (coarse RPO proxy).
    """
    min_d = float("inf")
    for i in range(samples):
        nu_a = (360.0 / samples) * i
        for j in range(0, samples, 2):  # coarser on B for speed
            nu_b = (360.0 / samples) * j
            pa = keplerian_to_eci(sma_a, inc_a, raan_a, nu_a)
            pb = keplerian_to_eci(sma_b, inc_b, raan_b, nu_b)
            d = float(np.linalg.norm(pa - pb))
            if d < min_d:
                min_d = d
    # Soft lower bound: |sma difference| is a floor for coplanar case
    floor = abs(sma_a - sma_b)
    return float(max(min_d, floor * 0.5))


def min_distance_to_assets(
    sat_history: pd.DataFrame,
    asset_histories: Mapping[int, pd.DataFrame],
    cap_km: float = 500.0,
) -> Tuple[float, Optional[int]]:
    """
    Minimum approximate distance from sat to any high-value asset.
    Returns (distance_km, closest_asset_id).
    """
    if not asset_histories:
        return cap_km, None

    last = sat_history.iloc[-1]
    sma_a = float(last["semi_major_axis_km"])
    inc_a = float(last["inclination_deg"])
    raan_a = float(last.get("raan_deg", 0.0))

    best_d = cap_km
    best_id = None
    for asset_id, hist in asset_histories.items():
        lb = hist.iloc[-1]
        d = approximate_relative_distance_km(
            sma_a, inc_a, raan_a,
            float(lb["semi_major_axis_km"]),
            float(lb["inclination_deg"]),
            float(lb.get("raan_deg", 0.0)),
        )
        # Also use SMA-series offset when shadowing (same plane)
        sma_offset = abs(
            float(sat_history["semi_major_axis_km"].iloc[-1])
            - float(hist["semi_major_axis_km"].iloc[-1])
        )
        # If cointegrated-style same inclination, trust SMA offset more
        if abs(inc_a - float(lb["inclination_deg"])) < 2.0:
            d = min(d, max(sma_offset, 1.0))
        if d < best_d:
            best_d = d
            best_id = asset_id
    return float(min(best_d, cap_km)), best_id


def orbit_class_from_sma(sma_km: float) -> str:
    alt = sma_km - R_EARTH_KM
    if alt < 2000:
        return "LEO"
    if alt < 35000:
        return "MEO"
    return "GEO"
