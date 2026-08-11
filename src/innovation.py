"""
Linear Kalman Filter innovation scoring on the SMA timeline.

Follows Zollo & Weigel 2023, "Comparison of satellite manoeuvre detection
methods based on timeline of orbit elements", Advances in Space Research
(doi 10.1016/j.asr.2023.10.032) — the best-performing published method for
TLE element timelines: a linear Kalman filter on SMA with state
x = [a, a_dot, a_ddot] (constant-acceleration dynamics), then the
normalized innovation squared

    eps_t = y_t' S_t^{-1} y_t

with y_t the measurement innovation and S_t its covariance. Under a correct
model eps ~ chi-square(1); the final score normalizes by the 99.9% quantile
(10.83). Peak-prominence thresholding (scipy find_peaks) is the
literature-validated decision rule (Zollo & Weigel 2023), replacing ad-hoc
sigma thresholds.
"""
from __future__ import annotations

import numpy as np

CHI2_1_Q999 = 10.83  # 99.9% quantile of chi-square with 1 dof


def lkf_innovation_score(
    sma_series,
    dt_days: float = 1.0,
    q_acc_km: float = 1e-4,
    r_meas_km: float = 0.01,
) -> tuple[float, float]:
    """
    Returns (score, max_eps): score = max(eps)/10.83 clipped to [0, 1],
    max_eps = raw maximum normalized innovation squared.

    Process-noise covariance Q is scaled by dt so per-step units are
    km^2 (SMA); measurement noise R ~ (TLE SMA noise)^2 ~ 0.01 km^2.
    Tune q_acc_km / r_meas_km per data regime; defaults match daily TLE.
    """
    y = np.asarray(sma_series, dtype=float)
    n = len(y)
    if n < 10:
        return 0.0, 0.0

    dt = float(dt_days)
    F = np.array([[1.0, dt, 0.5 * dt**2], [0.0, 1.0, dt], [0.0, 0.0, 1.0]])
    H = np.array([[1.0, 0.0, 0.0]])
    Q = float(q_acc_km) * np.array(
        [
            [dt**4 / 4.0, dt**3 / 2.0, dt**2 / 2.0],
            [dt**3 / 2.0, dt**2, dt],
            [dt**2 / 2.0, dt, 1.0],
        ]
    )
    R = np.array([[float(r_meas_km)]])

    x = np.array([y[0], 0.0, 0.0], dtype=float)
    P = np.eye(3) * 1e-2
    eps = np.zeros(n)
    for i in range(1, n):
        x = F @ x
        P = F @ P @ F.T + Q
        yhat = float((H @ x)[0])
        innov = y[i] - yhat
        S = float((H @ P @ H.T + R)[0, 0])
        if S <= 0:
            S = 1e-12
        K = P @ H.T / S
        x = x + K.flatten() * innov
        P = (np.eye(3) - K @ H) @ P
        eps[i] = innov**2 / S

    max_eps = float(np.max(eps))
    score = float(np.clip(max_eps / CHI2_1_Q999, 0.0, 1.0))
    return score, max_eps
