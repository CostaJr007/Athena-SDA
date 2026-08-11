"""
Evidential fusion layer (Dempster-Shafer theory).

Replaces the decorative Łukasiewicz implication and the hand-coded threat
rules with a principled belief/plausibility combination over the frame
Θ = {NORMAL, ANOMALOUS}, with an ignorance mass driven by data quality
(TLE age): stale data increases ignorance instead of forcing a decision.

References:
  - Dempster 1967, Annals of Mathematical Statistics 38:325
  - Shafer 1976, "A Mathematical Theory of Evidence", Princeton UP
  - Smets & Kennes 1994, "The transferable belief model", AIJ 66:191

Outputs:
  - belief_anomalous  = m({ANOMALOUS})            (lower bound)
  - plausibility_anomalous = m({ANOMALOUS}) + m(Θ) (upper bound)
  - conflict_K         = total conflicting mass (disagreeing detectors)
The conflict K is itself an anomaly indicator: when independent features
disagree strongly, the object state is genuinely ambiguous.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Sequence

import numpy as np

# Frame of discernment: focal elements as bitmasks
_N = 1 << 0  # NORMAL
_A = 1 << 1  # ANOMALOUS
_THETA = _N | _A  # ignorance / full frame

# Focal-set labels for readability
_FOCAL_NAMES = {_N: "normal", _A: "anomalous", _THETA: "ignorance"}


def _mass_from_score(
    score: float,
    base_ignorance: float = 0.30,
    direction: str = "anomalous",
) -> Dict[int, float]:
    """
    Map a [0, 1] feature score into a basic mass assignment.

    direction="anomalous": high score -> m({ANOMALOUS}) grows.
    direction="normal":    high score -> m({NORMAL}) grows (e.g. data quality).
    """
    s = float(np.clip(score, 0.0, 1.0))
    ig = float(np.clip(base_ignorance, 0.0, 0.9))
    known = 1.0 - ig
    if direction == "anomalous":
        return {_N: (1.0 - s) * known, _A: s * known, _THETA: ig}
    return {_N: s * known, _A: (1.0 - s) * known, _THETA: ig}


def _dempster_combine(m1: Dict[int, float], m2: Dict[int, float]) -> Dict[int, float]:
    """Dempster's rule of combination (unnormalized conflict returned via m12[_CONFLICT])."""
    out: Dict[int, float] = {}
    conflict = 0.0
    for f1, v1 in m1.items():
        for f2, v2 in m2.items():
            inter = f1 & f2
            prod = v1 * v2
            if inter == 0:
                conflict += prod
            else:
                out[inter] = out.get(inter, 0.0) + prod
    norm = 1.0 - conflict
    if norm <= 0 or not np.isfinite(norm):
        # total conflict: fall back to full ignorance (Zadeh paradox guard)
        return {_THETA: 1.0}
    return {f: v / norm for f, v in out.items()}


def fuse_evidence(
    feature_scores: Sequence[float],
    *,
    base_ignorance: float = 0.30,
    tle_age_hours: Optional[float] = None,
    directions: Optional[Sequence[str]] = None,
) -> Dict[str, float]:
    """
    Fuse a list of [0, 1] anomaly feature scores into belief / plausibility.

    feature_scores: each is a weak anomaly detector output in [0, 1]
    (anomalous direction). directions: optional per-feature override.
    tle_age_hours: raises ignorance for stale data
    (ignorance = base + clip(age/168h, 0, 0.45)).
    """
    if not feature_scores:
        return {"belief_anomalous": 0.0, "plausibility_anomalous": 0.5, "conflict_K": 0.0}

    ig = base_ignorance
    if tle_age_hours is not None:
        ig = float(np.clip(ig + float(tle_age_hours) / 168.0 * 0.45, 0.0, 0.85))

    dirs = directions or ["anomalous"] * len(feature_scores)
    combined: Optional[Dict[int, float]] = None
    conflicts: List[float] = []
    for s, d in zip(feature_scores, dirs):
        m = _mass_from_score(s, base_ignorance=ig, direction=d)
        if combined is None:
            combined = m
        else:
            combined = _dempster_combine(combined, m)
            # track per-step conflict (K) as normalized conflicting mass
            c = 0.0
            for f1, v1 in m.items():
                for f2, v2 in combined.items():
                    if f1 & f2 == 0:
                        c += v1 * v2
            conflicts.append(c)

    if combined is None:
        return {"belief_anomalous": 0.0, "plausibility_anomalous": 0.5, "conflict_K": 0.0}

    belief = float(combined.get(_A, 0.0))
    plaus = float(combined.get(_A, 0.0) + combined.get(_THETA, 0.0))
    conflict = float(np.mean(conflicts)) if conflicts else 0.0
    return {
        "belief_anomalous": float(np.clip(belief, 0.0, 1.0)),
        "plausibility_anomalous": float(np.clip(plaus, 0.0, 1.0)),
        "conflict_K": float(np.clip(conflict, 0.0, 1.0)),
    }
