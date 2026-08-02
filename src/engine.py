import numpy as np
import pandas as pd
import zlib
from scipy.stats import entropy, wasserstein_distance, pareto
from sklearn.metrics.pairwise import rbf_kernel
from statsmodels.tsa.stattools import adfuller, coint

def calculate_shannon_entropy(sma_series, bins=10):
    """
    1. Shannon entropy (Shannon, 1948)
    Measures disorder in semi-major-axis variations.
    """
    if len(sma_series) < 2:
        return 0.0
    diffs = np.diff(sma_series)
    hist, _ = np.histogram(diffs, bins=bins)
    probs = hist / np.sum(hist)
    probs = probs[probs > 0]
    return float(entropy(probs, base=2))

def calculate_kolmogorov_proxy(sma_series):
    """
    2. Kolmogorov complexity proxy (Kolmogorov, 1965)
    Uses zlib compression as an estimate of trajectory algorithmic complexity.

    Returns value in [0, 1]; short series (<10 samples) → 0.0 (not "complex").
    """
    if len(sma_series) < 10:
        return 0.0
    diffs = np.diff(sma_series)
    threshold = 0.02  # 20 m discretization
    tokens = []
    for d in diffs:
        if d > threshold:
            tokens.append("U")
        elif d < -threshold:
            tokens.append("D")
        else:
            tokens.append("S")

    s = "".join(tokens).encode("utf-8")
    if len(s) < 10:
        return 0.0
    compressed = zlib.compress(s)
    comp_len = max(len(compressed) - 11, 1)
    return float(np.clip(comp_len / len(s), 0.0, 1.0))

def calculate_hurst_exponent(series, max_lag=20):
    """
    3. Hurst exponent (Hurst, 1951) via classical R/S analysis.
    H > 0.5: persistent trend (active low-thrust / station-keeping control).
    H < 0.5: mean reversion (quiet coast / noise).
    Requires enough samples and multiple lag scales; otherwise returns 0.5 (neutral).
    """
    series = np.asarray(series, dtype=float)
    n = len(series)
    if n < 20:
        return 0.5
    # Use several lags with enough segments to reduce polyfit bias on tiny lag sets
    max_l = min(max_lag, max(4, n // 4))
    lags = [lag for lag in range(2, max_l + 1) if (n // lag) >= 2]
    if len(lags) < 3:
        return 0.5
    rs_values = []
    used_lags = []
    for lag in lags:
        n_segments = n // lag
        rs = []
        for i in range(n_segments):
            segment = series[i * lag : (i + 1) * lag]
            mean = np.mean(segment)
            std = np.std(segment)
            if std < 1e-12:
                continue
            deviations = segment - mean
            cum_dev = np.cumsum(deviations)
            R = np.max(cum_dev) - np.min(cum_dev)
            rs.append(R / std)
        if len(rs) > 0:
            rs_values.append(np.mean(rs))
            used_lags.append(lag)
    if len(rs_values) < 3:
        return 0.5
    H = np.polyfit(np.log(np.asarray(used_lags, dtype=float)), np.log(np.asarray(rs_values, dtype=float)), 1)[0]
    return float(np.clip(H, 0.0, 1.0))

def calculate_ricci_proxy(pos_x, neighbors_x, pos_y, neighbors_y):
    """
    4. Ollivier-Ricci curvature (Ollivier, 2007)
    Measures neighborhood curvature between two satellites (spatial convergence).
    """
    d_xy = np.linalg.norm(pos_x - pos_y)
    if d_xy == 0:
        return 0.0
    
    # Local mean neighbor distances relative to x and y
    dist_x = np.linalg.norm(neighbors_x - pos_x, axis=1) if len(neighbors_x) > 0 else np.array([0.0])
    dist_y = np.linalg.norm(neighbors_y - pos_y, axis=1) if len(neighbors_y) > 0 else np.array([0.0])
    
    w1 = wasserstein_distance(dist_x, dist_y)
    return float(1.0 - (w1 / d_xy))

def homology_backend() -> str:
    """Canonical topology backend label for artifacts (proxy is default/reproducible)."""
    try:
        import ripser  # noqa: F401
        return "ripser"
    except Exception:
        return "proxy"


def calculate_persistent_homology(positions_3d):
    """
    5. Persistent homology (TDA — Edelsbrunner, 2002)
    Topological structure of a swarm or orbital window.

    Prefer lightweight pairwise-distance proxy for cross-machine determinism
    unless ATHENA_USE_RIPSER=1 and ripser is installed.
    """
    import os
    positions_3d = np.asarray(positions_3d, dtype=float)
    if len(positions_3d) < 5:
        return 1.0, 0.0  # (h0_pers, h1_pers)

    use_ripser = os.environ.get("ATHENA_USE_RIPSER", "").strip() in ("1", "true", "True")
    if use_ripser:
        try:
            from ripser import ripser
            dgms = ripser(positions_3d, maxdim=1)["dgms"]
            h0 = dgms[0]
            h1 = dgms[1]
            h0_pers = np.mean([d[1] - d[0] for d in h0 if np.isfinite(d[1])]) if len(h0) > 0 else 1.0
            h1_pers = np.mean([d[1] - d[0] for d in h1]) if len(h1) > 0 else 0.0
            return float(h0_pers), float(h1_pers)
        except Exception:
            pass

    # Canonical proxy: scale-normalized pairwise distance stats
    from scipy.spatial.distance import pdist
    d = pdist(positions_3d)
    if len(d) == 0:
        return 1.0, 0.0
    scale = max(np.linalg.norm(positions_3d, axis=1).mean(), 1.0)
    d_n = d / scale
    h0_pers = float(np.percentile(d_n, 10))
    h1_pers = float(np.clip(np.percentile(d_n, 75) - np.percentile(d_n, 25), 0.0, 2.0))
    return h0_pers, h1_pers

def calculate_chern_simons_proxy(positions, velocities):
    """
    6. Chern-Simons proxy (Chern-Simons, 1974)
    Measures break of conservation of specific orbital angular momentum.
    """
    if len(positions) < 2:
        return 0.0
    # h = r x v (specific angular momentum)
    h_vectors = np.cross(positions, velocities)
    h0 = h_vectors[0]
    norm_h0 = np.linalg.norm(h0)
    if norm_h0 == 0:
        return 0.0
    diffs = np.linalg.norm(h_vectors - h0, axis=1)
    return float(np.max(diffs) / norm_h0)

def calculate_spectral_anomaly_rkhs(features_vector, reference_matrix, gamma=0.1):
    """
    7. Spectral anomaly in RKHS (David Hilbert)
    Measures typicality of a feature distribution in a reproducing kernel Hilbert space.
    """
    if len(reference_matrix) == 0:
        return 1.0
    x = features_vector.reshape(1, -1)
    sims = rbf_kernel(x, reference_matrix, gamma=gamma)
    return float(1.0 - np.max(sims))

def calculate_lukasiewicz_implication(val_p, val_q):
    """
    9. Łukasiewicz logic (Łukasiewicz, 1920)
    Fuzzy implication for logical thesis validation.
    """
    return float(min(1.0, 1.0 - val_p + val_q))

def calculate_kelly_allocation(threat_prob, severity_multiplier):
    """
    10. Kelly criterion (Kelly, 1956)
    Optimizes sensor-time allocation sizing.
    """
    p = threat_prob
    q = 1.0 - p
    b = severity_multiplier
    if b <= 0:
        return 0.0
    f_star = (p * b - q) / b
    return float(max(0.0, f_star * 0.5))  # Half-Kelly to damp volatility

def calculate_williams_threat(country, purpose, orbit_class, inclination):
    """
    11. Williams intrinsic value (Williams, 1938)
    Scores static strategic vulnerability / threat.
    """
    score = 0.0
    adversaries = ['CN', 'RU', 'KP', 'IR']
    if country in adversaries:
        score += 0.35
    elif country not in ['US', 'UK', 'FR', 'CA', 'DE']:
        score += 0.1
    
    military_purposes = ['military', 'sigint', 'asat_test', 'reconnaissance']
    if purpose in military_purposes:
        score += 0.45
    elif purpose in ['commercial', 'scientific']:
        score += 0.05
    
    # Polar LEO is a classic indicator of military scan orbits
    if orbit_class == 'LEO' and inclination > 55:
        score += 0.2
        
    return float(np.clip(score, 0.0, 1.0))

def calculate_kernel_smoothing(time_indices, values, bandwidth=1.5):
    """
    12. Kernel regression smoothing (Lo et al., 2000)
    Nadaraya-Watson filter with Gaussian kernel to clean orbital noise.
    """
    n = len(values)
    smoothed = np.zeros(n)
    for i, t in enumerate(time_indices):
        diffs = (t - time_indices) / bandwidth
        weights = np.exp(-0.5 * diffs**2)
        sum_w = np.sum(weights)
        smoothed[i] = np.sum(weights * values) / sum_w if sum_w > 0 else values[i]
    return smoothed

def calculate_kernel_l1_cusum(series, window=30, threshold=3.5):
    """
    13. Kernelized L1-CUSUM algorithm
    Detects cumulative structural breaks in orbital variation.
    """
    if len(series) < window:
        return 0.0
    baseline = np.median(series[-window:])
    mad = np.median(np.abs(series[-window:] - baseline))
    if mad == 0:
        mad = 1e-6
    
    current = series[-1]
    z_score = np.abs(current - baseline) / mad
    
    if z_score > 1.0:
        kernel_weight = 0.0
    else:
        kernel_weight = 0.75 * (1 - z_score**2)
        
    cusum = np.sum(kernel_weight * np.abs(np.array(series[-10:]) - baseline)) / mad
    return float(np.clip(cusum / threshold, 0.0, 1.0))

def calculate_mandelbrot_tail_anomaly(series, quantile=90):
    """
    14. Mandelbrot heavy-tail anomalies (Mandelbrot, 1963)
    Uses a Pareto heavy-tail model to detect rare anomalies.
    """
    series = np.asarray(series, dtype=float)
    if len(series) < 15:
        return 0.0
    threshold = float(np.percentile(series, quantile))
    if not np.isfinite(threshold) or abs(threshold) < 1e-15:
        return 0.0
    tail_data = series[series >= threshold]
    if len(tail_data) < 2 or np.all(tail_data == threshold):
        return 0.0

    # Hill estimator for tail alpha — guard div/0 and non-positive ratios
    ratios = tail_data / threshold
    ratios = ratios[ratios > 0]
    if len(ratios) < 2:
        return 0.0
    log_sum = float(np.sum(np.log(ratios)))
    if log_sum < 1e-9:
        return 0.0
    alpha = len(ratios) / log_sum
    current = float(series[-1])
    if current < threshold or threshold <= 0:
        return 0.0
    try:
        p_val = (current / threshold) ** (-alpha)
    except Exception:
        return 0.0
    if not np.isfinite(p_val):
        return 0.0
    return float(np.clip(1.0 - p_val, 0.0, 1.0))

def calculate_adf_pvalue(series):
    """
    15. Augmented Dickey-Fuller unit-root test (ADF)
    p-value > 0.05 -> non-stationary (strong hint of low-thrust maneuvers).
    p-value <= 0.05 -> stationary (passive satellite decaying normally).
    """
    if len(series) < 20:
        return 0.0  # Insufficient data
    try:
        result = adfuller(series, regression='ct')
        p_value = result[1]
        return float(p_value)
    except Exception:
        return 0.5

def calculate_cointegration_pvalue(series_a, series_b):
    """
    16. Engle-Granger cointegration test
    p-value < 0.05 -> cointegrated (pursuit / tactical shadowing supported).
    p-value >= 0.05 -> independent / normal orbits.
    """
    if len(series_a) < 20 or len(series_b) < 20:
        return 1.0
    try:
        _, p_value, _ = coint(series_a, series_b, trend='c')
        return float(p_value)
    except Exception:
        return 1.0
