"""
Offline change-point detection for maneuver-candidate auto-labeling.

Primary backend: `ruptures` PELT (Killick, Fearnhead & Eckley 2012,
doi 10.1080/01621459.2012.737745) when installed; fallback: binary
segmentation with an F-statistic cost on the SMA series (no external
dependency). Used to (a) count distinct maneuver episodes and (b) generate
weak training labels for the priority models instead of ad-hoc thresholds.
"""
from __future__ import annotations

from typing import List, Sequence

import numpy as np


def _f_stat_cost(series: np.ndarray) -> float:
    """Variance cost (negative log-likelihood of iid normal) for a segment."""
    s = np.asarray(series, dtype=float)
    if len(s) < 2:
        return 0.0
    var = float(np.var(s))
    if var <= 0:
        return 0.0
    return len(s) * np.log(var)


def _binary_segmentation(series: np.ndarray, min_size: int = 5, pen: float = 8.0) -> List[int]:
    """Recursive binary segmentation maximizing the between-segment F contrast."""
    s = np.asarray(series, dtype=float)
    n = len(s)
    bkps: List[int] = []

    def _best_split(start: int, end: int) -> int:
        if end - start < 2 * min_size:
            return -1
        best_i, best_f = -1, -1.0
        for i in range(start + min_size, end - min_size + 1):
            left = s[start:i]
            right = s[i:end]
            v_pooled = float(np.var(np.concatenate([left, right])))
            if v_pooled <= 1e-15:
                continue
            f = (len(left) * (float(np.mean(left)) - float(np.mean(s[start:end]))) ** 2
                 + len(right) * (float(np.mean(right)) - float(np.mean(s[start:end]))) ** 2) / v_pooled
            if f > best_f:
                best_f, best_i = f, i
        return best_i

    stack = [(0, n)]
    while stack:
        start, end = stack.pop()
        if end - start < 2 * min_size:
            continue
        i = _best_split(start, end)
        if i < 0:
            continue
        # penalize small gains; keep split only if F is meaningful
        if _f_stat_cost(s[start:end]) - (_f_stat_cost(s[start:i]) + _f_stat_cost(s[i:end])) >= pen:
            bkps.append(i)
            stack.append((start, i))
            stack.append((i, end))
    return sorted(bkps)


def detect_changepoints(sma_series: Sequence[float], pen: float = 10.0, min_size: int = 5) -> List[int]:
    """
    Detect maneuver-candidate change-point indices in an SMA series.

    Prefers ruptures PELT (rbf cost); falls back to binary segmentation.
    Returns sorted indices (0-based, exclusive segment boundaries).
    """
    s = np.asarray(sma_series, dtype=float)
    if len(s) < 2 * min_size:
        return []
    try:
        import ruptures  # type: ignore

        algo = ruptures.Pelt(model="rbf", min_size=min_size).fit(s.reshape(-1, 1))
        bkps = algo.predict(pen=pen)
        return [int(b) for b in bkps if 0 < b < len(s)]
    except Exception:
        return _binary_segmentation(s, min_size=min_size, pen=pen)


def count_changepoints(sma_series: Sequence[float], pen: float = 10.0, min_size: int = 5) -> int:
    """Count distinct change-point episodes in an SMA series (auto-label count)."""
    return len(detect_changepoints(sma_series, pen=pen, min_size=min_size))
