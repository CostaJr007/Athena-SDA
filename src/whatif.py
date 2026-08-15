"""
What-if sandbox: inject a synthetic maneuver and check detector sensitivity.

Does not write back into the live history store. Scores of the production
board stay immutable. This is a sensitivity probe (T6), not a re-score.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

import numpy as np
import pandas as pd

from src.engine import calculate_ewma, calculate_page_cusum, count_regime_changes
from src.utils import generate_mock_tle_history


def inject_sma_impulse(
    hist: pd.DataFrame,
    *,
    delta_km: float = 4.5,
    at_index: Optional[int] = None,
) -> pd.DataFrame:
    """Copy `hist` and add an impulsive SMA jump. Never mutates the input."""
    out = hist.copy()
    if "semi_major_axis_km" not in out.columns or len(out) == 0:
        return out
    idx = at_index if at_index is not None else max(0, len(out) // 2)
    idx = int(np.clip(idx, 0, len(out) - 1))
    sma = out["semi_major_axis_km"].astype(float).to_numpy().copy()
    sma[idx:] = sma[idx:] + float(delta_km)
    out["semi_major_axis_km"] = sma
    return out


def _series_metrics(sma: np.ndarray) -> Dict[str, float]:
    arr = np.asarray(sma, dtype=float)
    return {
        "cusum": float(calculate_page_cusum(arr)),
        "ewma": float(calculate_ewma(arr)),
        "regime_changes": float(count_regime_changes(arr)),
    }


def detect_injected(
    baseline: pd.DataFrame,
    injected: pd.DataFrame,
    *,
    cusum_margin: float = 0.05,
) -> Dict[str, Any]:
    """Compare CUSUM/EWMA before vs after. IF is optional and never required."""
    b = baseline["semi_major_axis_km"].astype(float).values
    a = injected["semi_major_axis_km"].astype(float).values
    before = _series_metrics(b)
    after = _series_metrics(a)
    fired = (
        after["cusum"] > before["cusum"] + cusum_margin
        or after["ewma"] > before["ewma"] + cusum_margin
        or after["regime_changes"] > before["regime_changes"]
    )
    return {
        "fired": bool(fired),
        "before": before,
        "after": after,
        "delta_cusum": round(after["cusum"] - before["cusum"], 4),
        "delta_ewma": round(after["ewma"] - before["ewma"], 4),
        "note": (
            "Sensitivity probe on CUSUM/EWMA/regime_changes. "
            "Does not rewrite Isolation Forest / XGB scores."
        ),
    }


def run_whatif(
    norad_id: int = 9001,
    *,
    delta_km: float = 4.5,
    num_days: int = 40,
    hist: Optional[pd.DataFrame] = None,
    allow_mock: bool = False,
) -> Dict[str, Any]:
    """Inject a burn into a copy of the object's series. Never writes history."""
    source = "provided"
    if hist is None:
        try:
            from src.tle_store import history_as_sat_histories

            loaded = history_as_sat_histories(norad_ids=[int(norad_id)], min_epochs=12)
            hist = loaded.get(int(norad_id))
        except Exception:
            hist = None
        if hist is not None and len(hist) > 0:
            source = "history"
        elif allow_mock or int(norad_id) == 9001:
            hist = generate_mock_tle_history(int(norad_id), num_days=num_days, anomaly_type=None)
            source = "mock"
        else:
            return {
                "norad_id": int(norad_id),
                "delta_km": float(delta_km),
                "injected": False,
                "fired": False,
                "source": "none",
                "error": f"insufficient history for NORAD {int(norad_id)} (need >=12 epochs)",
            }
    injected = inject_sma_impulse(hist, delta_km=delta_km)
    result = detect_injected(hist, injected)
    result.update(
        {
            "norad_id": int(norad_id),
            "delta_km": float(delta_km),
            "n_epochs": int(len(hist)),
            "injected": True,
            "source": source,
        }
    )
    return result
