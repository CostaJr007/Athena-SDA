"""
Athena-SDA quantitative math engine — corrected mathematical framework.

Feature math is anchored to verifiable references (see docs/PROOF_DOSSIER.md):

  - Shannon entropy (Shannon 1948)                — kept, bias-documented
  - LZ76 complexity (Kaspar & Schuster 1987)      — replaces zlib compression
                                                    ratio (was constant on
                                                    short windows)
  - DFA (Peng et al. 1994)                        — replaces biased R/S Hurst;
                                                    applied to drag-detrended
                                                    SMA (first difference)
  - MMD typicality (Gretton et al. 2012)          — replaces 1 - max RBF
                                                    similarity (was saturated)
  - Page CUSUM (Page 1954) + EWMA (Roberts 1959)  — ARL-calibrated; replaces
                                                    the old "kernelized
                                                    L1-CUSUM" (not a CUSUM)
  - Permutation entropy (Bandt & Pompe 2002)      — rank-order complexity,
                                                    robust for n=20-30
  - SSA residual (Broomhead & King 1986;          — low-rank trend removal,
    Golyandina et al. 2001)                         maneuver signal in residual
  - BOCPD (Adams & MacKay 2007)                   — Bayesian regime-change
                                                    probability (novel for TLE)
  - DCCA (Podobnik & Stanley 2008)                — pairwise coupling
  - Hill / Pareto tail (Hill 1975)                — on |ΔSMA| innovations
  - ADF (Dickey & Fuller 1979)                    — on detrended SMA
  - Engle-Granger cointegration (1987)            — on aligned SMA pairs
  - Persistent homology (Edelsbrunner 2002)       — standardized cloud,
                                                    H0 infinite bar included
  - Kelly (1956) / Nadaraya-Watson (1964)         — kept, citation fixed

Removed as decorative or redundant: "Chern-Simons" label (was specific
angular-momentum deviation, redundant with ΔSMA), 1D Ricci proxy (not
Ollivier-Ricci), Łukasiewicz implication (replaced by evidential fusion in
src/evidence.py).

All feature functions are defensive: they never raise and never return NaN.
"""
from __future__ import annotations

import math
from typing import List, Optional, Sequence, Tuple

import numpy as np
from scipy.stats import entropy, t
from sklearn.metrics.pairwise import euclidean_distances, rbf_kernel
from statsmodels.tsa.stattools import adfuller, coint


# ---------------------------------------------------------------------------
# 1. Shannon entropy (Shannon, 1948)
# ---------------------------------------------------------------------------
def calculate_shannon_entropy(sma_series, bins=10):
    """
    Histogram plug-in Shannon entropy of ΔSMA (bits).

    Caveat (documented): with n=20-30 the plug-in estimate is biased low and
    saturates near log2(bins); use `calculate_permutation_entropy` as the
    rank-order complement. Kept as the amplitude-domain measure.
    """
    if len(sma_series) < 2:
        return 0.0
    diffs = np.diff(sma_series)
    hist, _ = np.histogram(diffs, bins=bins)
    probs = hist / np.sum(hist)
    probs = probs[probs > 0]
    return float(entropy(probs, base=2))


# ---------------------------------------------------------------------------
# 2. LZ76 complexity (Kaspar & Schuster, 1987) — replaces zlib proxy
# ---------------------------------------------------------------------------
def _lz76_count(symbols: str) -> int:
    """Kaspar-Schuster LZ76 parsing complexity of a symbol string."""
    n = len(symbols)
    if n == 0:
        return 0
    c, l = 1, 1  # complexity, current substring length
    i, k, k_max = 0, 1, 1
    stop = False
    while not stop:
        if symbols[i + k - 1] == symbols[l + k - 1]:
            k += 1
            if l + k > n:
                c += 1
                stop = True
        else:
            if k > k_max:
                k_max = k
            i += 1
            if i == l:
                c += 1
                l += k_max
                if l + 1 > n:
                    stop = True
                else:
                    i = 0
                    k = 1
                    k_max = 1
            else:
                k = 1
    return c


def calculate_lz76_complexity(series, threshold: Optional[float] = None) -> float:
    """
    Normalized LZ76 complexity of the tokenized ΔSMA series.

    Tokens U/D/S are derived from a robust threshold (0.6745*MAD, sigma-
    equivalent, floored) instead of the old fixed 20 m — the fixed threshold
    made the zlib feature constant on synthetic data and near-constant on
    real data. Returns the complexity rate c(n)*log2(n)/n (0 = regular,
    >= 1 = high complexity).
    """
    d = np.diff(np.asarray(series, dtype=float))
    if len(d) < 8:
        return 0.0
    if threshold is None:
        mad = float(np.median(np.abs(d - np.median(d))))
        threshold = max(0.6745 * mad, 1e-6)
    tokens = ["U" if v > threshold else ("D" if v < -threshold else "S") for v in d]
    s = "".join(tokens)
    n = len(s)
    c = _lz76_count(s)
    rate = c * np.log2(n) / n if n > 1 else 0.0
    return float(np.clip(rate, 0.0, 2.0))


# ---------------------------------------------------------------------------
# 3. Detrended Fluctuation Analysis (Peng et al., 1994) — replaces R/S Hurst
# ---------------------------------------------------------------------------
def calculate_dfa_hurst(series, min_scale: int = 4, max_scale_frac: float = 0.25) -> float:
    """
    DFA scaling exponent alpha on drag-detrended SMA (first difference).

    alpha > 0.5: persistent (long-memory control / low-thrust behavior);
    alpha ~ 0.5: white-noise-like (passive coast);
    alpha < 0.5: anti-persistent (mean-reverting station-keeping).

    Applying DFA to the differenced series removes the secular drag trend
    (Hu et al. 2001: trends inflate R/S/DFA exponents) and avoids the
    positive small-sample bias of the old R/S estimator at n=20-30.
    """
    s = np.asarray(series, dtype=float)
    if len(s) < 12:
        return 0.5
    d = np.diff(s)
    if len(d) < 8:
        return 0.5
    y = np.cumsum(d - np.mean(d))
    n = len(y)
    max_s = int(n * max_scale_frac)
    scales = [sc for sc in range(min_scale, max_s + 1)]
    if len(scales) < 3:
        return 0.5
    Fs: List[float] = []
    used: List[int] = []
    for sc in scales:
        n_seg = n // sc
        if n_seg < 2:
            continue
        f2 = 0.0
        for v in range(n_seg):
            seg = y[v * sc : (v + 1) * sc]
            x = np.arange(sc, dtype=float)
            p = np.polyfit(x, seg, 1)
            f2 += float(np.sum((seg - np.polyval(p, x)) ** 2))
        f2 /= n_seg * sc
        Fs.append(np.sqrt(f2))
        used.append(sc)
    if len(Fs) < 3:
        return 0.5
    alpha = float(np.polyfit(np.log(np.asarray(used, dtype=float)), np.log(np.asarray(Fs, dtype=float)), 1)[0])
    return float(np.clip(alpha, 0.0, 1.0))


# ---------------------------------------------------------------------------
# 4. Persistent homology (Edelsbrunner et al., 2002) — standardized cloud
# ---------------------------------------------------------------------------
def homology_backend() -> str:
    """Canonical topology backend label for artifacts (proxy is default/reproducible)."""
    try:
        import ripser  # noqa: F401

        return "ripser"
    except Exception:
        return "proxy"


def calculate_persistent_homology(positions_3d):
    """
    H0/H1 Vietoris-Rips persistence of a standardized trajectory cloud.

    Fixes vs the old version: (a) the cloud is centered and scaled before
    ripser so persistence is scale-free across windows; (b) the H0 infinite
    bar (global component) is included via the maximum finite bar, not
    dropped; (c) n < 12 returns neutral constants (small clouds have no
    statistical content — Fasy et al. 2014).
    """
    positions_3d = np.asarray(positions_3d, dtype=float)
    if len(positions_3d) < 12:
        return 1.0, 0.0

    # Standardize cloud: centroid at origin, scale by RMS radius
    centroid = positions_3d.mean(axis=0)
    cloud = positions_3d - centroid
    scale = float(np.linalg.norm(cloud, axis=1).mean())
    if scale < 1e-12:
        return 1.0, 0.0
    cloud = cloud / scale

    use_ripser = os_env_ripser()
    if use_ripser:
        try:
            from ripser import ripser

            dgms = ripser(cloud, maxdim=1)["dgms"]
            h0 = dgms[0]
            h1 = dgms[1]
            pers0 = [d[1] - d[0] for d in h0]
            finite = [p for p in pers0 if np.isfinite(p)]
            max_finite = max(finite) if finite else 1.0
            pers0 = [p if np.isfinite(p) else max_finite * 1.5 for p in pers0]
            h0_pers = float(np.mean(pers0)) if pers0 else 1.0
            h1_pers = float(np.mean([d[1] - d[0] for d in h1])) if len(h1) > 0 else 0.0
            return h0_pers, float(np.clip(h1_pers, 0.0, 5.0))
        except Exception:
            pass

    # Canonical proxy (deterministic, no ripser): scale-normalized pairwise
    # distance percentiles as cheap H0/H1 persistence proxies.
    from scipy.spatial.distance import pdist

    d = pdist(cloud)
    if len(d) == 0:
        return 1.0, 0.0
    h0_pers = float(np.percentile(d, 10))
    h1_pers = float(np.clip(np.percentile(d, 75) - np.percentile(d, 25), 0.0, 5.0))
    return h0_pers, h1_pers


def os_env_ripser() -> bool:
    import os

    return os.environ.get("ATHENA_USE_RIPSER", "").strip() in ("1", "true", "True")


# ---------------------------------------------------------------------------
# 5. MMD typicality (Gretton et al., 2012) — replaces 1 - max RBF similarity
# ---------------------------------------------------------------------------
def calculate_mmd_typicality(
    features_vector,
    reference_matrix,
    gamma: Optional[float] = None,
    n_perm: int = 200,
    seed: int = 42,
) -> Tuple[float, float]:
    """
    Maximum Mean Discrepancy two-sample typicality score.

    Returns (typicality, mmd_stat): typicality = 1 - permutation p-value
    (high = anomalous distribution vs the reference normality set), and
    mmd_stat = raw unbiased MMD². Features are z-scored against the
    reference; gamma uses the median pairwise-distance heuristic. The
    permutation test is distribution-free and exactly valid at any sample
    size — fixing the old `1 - max k` heuristic, which saturated at ~1 for
    normal vectors and returned 1.0 on the zero-reference fallback.
    """
    if reference_matrix is None or len(reference_matrix) < 3:
        return 0.5, 0.0
    ref = np.asarray(reference_matrix, dtype=float)
    x = np.asarray(features_vector, dtype=float).reshape(1, -1)
    if x.shape[1] != ref.shape[1]:
        return 0.5, 0.0
    mu = ref.mean(axis=0)
    sd = ref.std(axis=0)
    sd[sd < 1e-12] = 1.0
    ref = (ref - mu) / sd
    x = (x - mu) / sd

    if gamma is None:
        D2 = euclidean_distances(ref, ref) ** 2
        med = float(np.median(D2[D2 > 0])) if np.any(D2 > 0) else 1.0
        gamma = 1.0 / max(med, 1e-12)

    def _mmd2(a, b):
        kaa = float(np.mean(rbf_kernel(a, a, gamma=gamma)))
        kbb = float(np.mean(rbf_kernel(b, b, gamma=gamma)))
        kab = float(np.mean(rbf_kernel(a, b, gamma=gamma)))
        return kaa + kbb - 2.0 * kab

    mmd2 = _mmd2(x, ref)
    pool = np.vstack([ref, x])
    n_ref = len(ref)
    rng = np.random.default_rng(seed)
    count = 1
    for _ in range(n_perm):
        perm = rng.permutation(len(pool))
        a = pool[perm[:n_ref]]
        b = pool[perm[n_ref:]]
        if _mmd2(a, b) >= mmd2:
            count += 1
    p_value = count / (n_perm + 1)
    return float(np.clip(1.0 - p_value, 0.0, 1.0)), float(max(mmd2, 0.0))


# ---------------------------------------------------------------------------
# 6. Kelly criterion (Kelly, 1956) — half-Kelly, standard damping (Thorp)
# ---------------------------------------------------------------------------
def calculate_kelly_allocation(threat_prob, severity_multiplier):
    """Growth-optimal attention fraction, half-Kelly damped."""
    p = float(threat_prob)
    b = float(severity_multiplier)
    q = 1.0 - p
    if b <= 0:
        return 0.0
    f_star = (p * b - q) / b
    return float(max(0.0, f_star * 0.5))


# ---------------------------------------------------------------------------
# 7. Static threat heuristic (doctrine, TVA-style — NOT a mathematical model)
# ---------------------------------------------------------------------------
def calculate_static_threat(country, purpose, orbit_class, inclination):
    """
    Doctrine-based static threat heuristic (asset criticality index).

    Renamed from "Williams intrinsic value": the original name misattributed
    a financial dividend-discount model (Williams 1938). These weights are a
    doctrine choice (joint targeting / asset criticality, JP 3-60 style) —
    country and mission weights are configurable policy, not mathematics.
    """
    score = 0.0
    adversaries = ["CN", "RU", "KP", "IR"]
    if country in adversaries:
        score += 0.35
    elif country not in ["US", "UK", "FR", "CA", "DE"]:
        score += 0.1

    military_purposes = ["military", "sigint", "asat_test", "reconnaissance"]
    if purpose in military_purposes:
        score += 0.45
    elif purpose in ["commercial", "scientific"]:
        score += 0.05

    if orbit_class == "LEO" and inclination > 55:
        score += 0.2

    return float(np.clip(score, 0.0, 1.0))


# ---------------------------------------------------------------------------
# 8. Nadaraya-Watson kernel smoothing (Nadaraya 1964; Watson 1964)
# ---------------------------------------------------------------------------
def calculate_kernel_smoothing(time_indices, values, bandwidth=1.5):
    """
    Nadaraya-Watson estimator with Gaussian kernel (Nadaraya 1964; Watson 1964;
    Wand & Jones 1995). Bandwidth is a hyper-parameter; prefer applying to
    residuals (x - smoothed) so the maneuver signal is not masked.
    """
    n = len(values)
    smoothed = np.zeros(n)
    for i, t in enumerate(time_indices):
        diffs = (t - time_indices) / bandwidth
        weights = np.exp(-0.5 * diffs**2)
        sum_w = np.sum(weights)
        smoothed[i] = np.sum(weights * values) / sum_w if sum_w > 0 else values[i]
    return smoothed


# ---------------------------------------------------------------------------
# 9. Page CUSUM (Page 1954) + EWMA (Roberts 1959), ARL-calibrated
# ---------------------------------------------------------------------------
def _robust_standardized_innovations(series, sigma_floor_km: float = 0.05):
    """
    Two-sided standardized ΔSMA; trailing baseline excludes last point.

    sigma_floor_km floors the robust scale at the TLE SMA noise floor
    (~50 m): without it, a tight core MAD makes any real variation an
    extreme z-score and the CUSUM/EWMA saturate at 1.0 for every object.
    Empirically (2026-08 real history): floor 0.05 km keeps ISS-style
    regular station-keeping visible while quiet objects stay ~0.
    """
    d = np.diff(np.asarray(series, dtype=float))
    if len(d) < 8:
        return np.array([]), 0.0
    base = d[:-1]
    med = float(np.median(base))
    mad = float(np.median(np.abs(base - med)))
    sigma = 1.4826 * mad
    if sigma < 1e-12:
        sigma = max(float(np.std(base)), 1e-9)
    sigma = max(sigma, float(sigma_floor_km))
    return (d - med) / sigma, sigma


def calculate_page_cusum(series, k_sigma: float = 0.5, h_sigma: float = 4.0) -> float:
    """
    Two-sided Page CUSUM on robustly standardized ΔSMA innovations.

    Reference value k=0.5σ and decision interval h=4σ give ARL0 ≈ 365
    observations for iid normal increments (Siegmund 1985 approximation,
    exp(2k(h+1.166))-1 over 2k²; Monte-Carlo checked in smoke_test). The
    trailing baseline excludes the test point so a jump cannot inflate its
    own MAD (the old "kernelized L1-CUSUM" included it and returned 0.0 on
    every mock maneuver). Returns max|S|/h clipped to [0, 1] (1 = alarm).
    """
    z, _ = _robust_standardized_innovations(series)
    if len(z) == 0:
        return 0.0
    s_pos = 0.0
    s_neg = 0.0
    s_max = 0.0
    for v in z:
        s_pos = max(0.0, s_pos + v - k_sigma)
        s_neg = max(0.0, s_neg - v - k_sigma)
        s_max = max(s_max, s_pos, s_neg)
    return float(np.clip(s_max / h_sigma, 0.0, 1.0))


def count_regime_changes(series, k_sigma: float = 0.5, h_sigma: float = 4.0, refractory: int = 5) -> float:
    """
    Distinct change-point episode count via two-sided CUSUM with a refractory
    window. A single maneuver spans several epochs; this counts it once
    (the old maneuver_count loop counted every threshold crossing, up to 8x
    per maneuver). Refractory = min epochs between two distinct detections.
    """
    z, _ = _robust_standardized_innovations(series)
    if len(z) == 0:
        return 0.0
    s_pos = 0.0
    s_neg = 0.0
    count = 0
    last = -refractory
    for i, v in enumerate(z):
        s_pos = max(0.0, s_pos + v - k_sigma)
        s_neg = max(0.0, s_neg - v - k_sigma)
        if (s_pos >= h_sigma or s_neg >= h_sigma) and (i - last) >= refractory:
            count += 1
            last = i
            s_pos = 0.0
            s_neg = 0.0
    return float(count)


def calculate_ewma(series, lam: float = 0.2, L: float = 3.0) -> float:
    """
    EWMA control statistic (Roberts 1959) on standardized ΔSMA.

    EWMA is near-optimal for small persistent shifts — the low-thrust /
    electric-propulsion regime (Lucas & Saccucci 1990). Steady-state control
    limit L·sqrt(lam/(2-lam)). Returns max|z|/CL clipped to [0, 1].
    """
    z, _ = _robust_standardized_innovations(series)
    if len(z) == 0:
        return 0.0
    z_ewma = 0.0
    z_max = 0.0
    for v in z:
        z_ewma = lam * v + (1.0 - lam) * z_ewma
        z_max = max(z_max, abs(z_ewma))
    cl = L * math.sqrt(lam / (2.0 - lam))
    if cl <= 0:
        return 0.0
    return float(np.clip(z_max / cl, 0.0, 1.0))


# ---------------------------------------------------------------------------
# 10. Permutation entropy (Bandt & Pompe 2002) + complexity-entropy plane
# ---------------------------------------------------------------------------
def calculate_permutation_entropy(series, m: int = 3, tau: int = 1) -> float:
    """
    Normalized permutation entropy of ΔSMA ordinal patterns (Bandt & Pompe
    2002). Bin-free and rank-based: robust to TLE amplitude noise and stable
    with n=20-30 (m=3 → 6 patterns). H_norm=1 = maximal disorder.
    """
    d = np.diff(np.asarray(series, dtype=float))
    n = len(d)
    if n < m + (m - 1) * (tau - 1) + 1 or n < m:
        return 0.0
    patterns = []
    span = m * tau
    for i in range(n - span + 1):
        window = d[i : i + span : tau]
        patterns.append(tuple(np.argsort(window)))
    counts: dict = {}
    for p in patterns:
        counts[p] = counts.get(p, 0) + 1
    probs = np.array(list(counts.values()), dtype=float) / len(patterns)
    H = float(-np.sum(probs * np.log2(probs)))
    H_max = math.log2(math.factorial(m))
    if H_max <= 0:
        return 0.0
    return float(np.clip(H / H_max, 0.0, 1.0))


def complexity_entropy_c(series, m: int = 3, tau: int = 1) -> float:
    """
    Jensen-Shannon complexity (Rosso et al. 2007) of the ordinal pattern
    distribution. C_JS in [0, 1]: high near both extremes (pure noise and
    pure order) separates "coherent low-thrust ramp" from "white noise" that
    share the same entropy. Complements permutation entropy.
    """
    d = np.diff(np.asarray(series, dtype=float))
    n = len(d)
    if n < m + (m - 1) * (tau - 1) + 1 or n < m:
        return 0.0
    patterns = []
    span = m * tau
    for i in range(n - span + 1):
        window = d[i : i + span : tau]
        patterns.append(tuple(np.argsort(window)))
    counts: dict = {}
    for p in patterns:
        counts[p] = counts.get(p, 0) + 1
    probs = np.array(list(counts.values()), dtype=float)
    probs /= probs.sum()
    S = math.factorial(m)
    u = np.full(S, 1.0 / S)
    P = np.zeros(S)
    P[: len(probs)] = probs
    M = 0.5 * (P + u)
    jsd = 0.5 * (_kld(P, M) + _kld(u, M))
    jsd_max = -0.5 * ((S + 1.0) / S * math.log(S + 1.0) + math.log(S) - 2.0 * math.log(2.0 * S))
    if jsd_max <= 0:
        return 0.0
    return float(np.clip(jsd / jsd_max, 0.0, 1.0))


def _kld(p, q) -> float:
    p = np.asarray(p, dtype=float)
    q = np.asarray(q, dtype=float)
    mask = p > 0
    return float(np.sum(p[mask] * np.log(p[mask] / q[mask])))


# ---------------------------------------------------------------------------
# 11. SSA residual (Broomhead & King 1986; Golyandina et al. 2001)
# ---------------------------------------------------------------------------
def calculate_ssa_residual(series, L: int = 12, k: int = 3) -> Tuple[float, float]:
    """
    Singular Spectrum Analysis residual of the SMA series.

    Decomposes SMA into low-rank trend/oscillation + residual via SVD of the
    trajectory matrix; a maneuver makes the trailing point deviate from the
    low-rank "physical drift" reconstruction (the natural fix for the
    underpowered ADF at n=20). Returns (normalized last-point residual,
    spectral energy ratio lambda1/sum(lambda)).
    """
    y = np.asarray(series, dtype=float)
    n = len(y)
    if n < 16:
        return 0.0, 1.0
    L = int(min(L, n // 2))
    K = n - L + 1
    X = np.column_stack([y[i : i + L] for i in range(K)])
    try:
        U, s, Vt = np.linalg.svd(X, full_matrices=False)
    except np.linalg.LinAlgError:
        return 0.0, 1.0

    recon = np.zeros(n)
    for j in range(min(k, len(s))):
        Xj = s[j] * np.outer(U[:, j], Vt[j, :])
        for idx in range(n):
            total = 0.0
            count = 0
            for i2 in range(L):
                j2 = idx - i2
                if 0 <= j2 < K:
                    total += Xj[i2, j2]
                    count += 1
            recon[idx] += total / count if count > 0 else 0.0

    resid = y - recon
    sigma = float(np.std(resid))
    resid_norm = float(abs(resid[-1]) / max(sigma, 1e-9))
    energy = float(np.sum(s**2))
    ratio = float(s[0] ** 2 / max(energy, 1e-12)) if len(s) else 1.0
    return float(np.clip(resid_norm, 0.0, 20.0)), float(np.clip(ratio, 0.0, 1.0))


# ---------------------------------------------------------------------------
# 12. Bayesian Online Changepoint Detection (Adams & MacKay 2007)
# ---------------------------------------------------------------------------
def _t_logpdf(x, mu, kappa, alpha, beta):
    df = 2.0 * alpha
    scale = np.sqrt(beta * (kappa + 1.0) / (kappa * alpha))
    return t.logpdf(x, df=df, loc=mu, scale=scale)


def calculate_bocpd(
    series,
    hazard: float = 1.0 / 30.0,
    mu0: float = 0.0,
    kappa0: float = 1.0,
    alpha0: float = 1.0,
    beta0: float = 1.0,
    max_run: int = 60,
) -> Tuple[float, float]:
    """
    Bayesian Online Changepoint Detection on ΔSMA (Gaussian conjugate
    predictive, unknown mean/variance). Returns
    (prob_change_3d, neg_log_pred_ll): posterior probability of a regime
    change within the last 3 observations, and the negative log predictive
    likelihood of the last observation (both are calibrated uncertainty
    outputs — the run-length posterior is a probabilistic maneuver score).
    No published TLE application found in the literature → novelty claim.
    """
    d = np.diff(np.asarray(series, dtype=float))
    n = len(d)
    if n < 6:
        return 0.0, 0.0
    max_run = int(min(max_run, n))

    R = np.zeros(max_run + 1)
    R[0] = 1.0
    mu = np.full(max_run + 1, mu0)
    kappa = np.full(max_run + 1, kappa0)
    alpha = np.full(max_run + 1, alpha0)
    beta = np.full(max_run + 1, beta0)
    pred_ll_last = 0.0

    for x in d:
        logp = _t_logpdf(x, mu, kappa, alpha, beta)
        p = np.exp(np.clip(logp, -50.0, 0.0))
        pred = float(np.sum(R * p))
        pred_ll_last = -math.log(max(pred, 1e-12))

        grow = R * p * (1.0 - hazard)
        cp = float(np.sum(R * p)) * hazard
        R_new = np.zeros(max_run + 1)
        R_new[0] = cp
        R_new[1:] = grow[:max_run]
        norm = float(R_new.sum())
        if norm <= 0 or not np.isfinite(norm):
            R_new[0] = 1.0
            norm = 1.0
        R = R_new / norm

        # Sufficient-statistics update per run length
        new_mu = np.full(max_run + 1, mu0)
        new_kappa = np.full(max_run + 1, kappa0)
        new_alpha = np.full(max_run + 1, alpha0)
        new_beta = np.full(max_run + 1, beta0)
        new_mu[0] = (kappa0 * mu0 + x) / (kappa0 + 1.0)
        new_kappa[0] = kappa0 + 1.0
        new_alpha[0] = alpha0 + 0.5
        new_beta[0] = beta0 + (kappa0 * (x - mu0) ** 2) / (2.0 * (kappa0 + 1.0))
        for r in range(1, max_run + 1):
            k = kappa[r - 1]
            m = mu[r - 1]
            a = alpha[r - 1]
            b = beta[r - 1]
            new_mu[r] = (k * m + x) / (k + 1.0)
            new_kappa[r] = k + 1.0
            new_alpha[r] = a + 0.5
            new_beta[r] = b + (k * (x - m) ** 2) / (2.0 * (k + 1.0))
        mu, kappa, alpha, beta = new_mu, new_kappa, new_alpha, new_beta

    prob_change_3d = float(np.sum(R[: min(4, max_run + 1)]))
    return float(np.clip(prob_change_3d, 0.0, 1.0)), float(np.clip(pred_ll_last, 0.0, 50.0))


# ---------------------------------------------------------------------------
# 13. Mandelbrot heavy-tail extremeness (Hill 1975) — on |ΔSMA| innovations
# ---------------------------------------------------------------------------
def calculate_mandelbrot_tail_anomaly(series, quantile=85):
    """
    Hill-estimator tail extremeness of |ΔSMA| (Mandelbrot 1963; Hill 1975).

    Fix: applied to innovation magnitudes (|diff|), not raw bounded SMA, so
    the i.i.d. heavy-tail assumption holds; quantile 85 keeps >= 3 tail
    points at n=20 (the old 90th quantile left 2 points with huge bias).
    Returns an extremeness rank in [0, 1] (P(X <= current | X > u)), not a
    calibrated probability — documented as such.
    """
    series = np.asarray(series, dtype=float)
    if len(series) < 15:
        return 0.0
    d = np.abs(np.diff(series))
    if len(d) < 8:
        return 0.0
    threshold = float(np.percentile(d, quantile))
    if not np.isfinite(threshold) or threshold <= 1e-15:
        return 0.0
    tail = d[d >= threshold]
    if len(tail) < 3 or np.all(tail == threshold):
        return 0.0
    ratios = tail / threshold
    ratios = ratios[ratios > 0]
    if len(ratios) < 3:
        return 0.0
    log_sum = float(np.sum(np.log(ratios)))
    if log_sum < 1e-9:
        return 0.0
    alpha = len(ratios) / log_sum
    current = float(d[-1])
    if current < threshold:
        return 0.0
    try:
        p_val = (current / threshold) ** (-alpha)
    except Exception:
        return 0.0
    if not np.isfinite(p_val):
        return 0.0
    return float(np.clip(1.0 - p_val, 0.0, 1.0))


# ---------------------------------------------------------------------------
# 14. ADF unit-root test (Dickey & Fuller 1979) — on detrended SMA
# ---------------------------------------------------------------------------
def calculate_adf_pvalue(series):
    """
    ADF unit-root p-value on drag-detrended SMA (constant regression on the
    linear-trend residual). Documented caveats: at n=20 the test is
    underpowered and size-distorted (DeJong et al. 1992) — use as a
    continuous feature, never as a hard p < 0.05 threshold.
    """
    series = np.asarray(series, dtype=float)
    if len(series) < 20:
        return 0.0
    x = np.arange(len(series), dtype=float)
    p = np.polyfit(x, series, 1)
    resid = series - np.polyval(p, x)
    try:
        result = adfuller(resid, regression="c")
        return float(result[1])
    except Exception:
        return 0.5


# ---------------------------------------------------------------------------
# 15. Engle-Granger cointegration (Engle & Granger 1987)
# ---------------------------------------------------------------------------
def calculate_cointegration_pvalue(series_a, series_b):
    """
    Engle-Granger cointegration p-value between two SMA series.

    Documented caveats: (a) both series must be aligned to common epochs
    (pair_score._align_series does merge_asof ±12h) — raw tails give
    misaligned, meaningless tests; (b) at n=20-30 the test has near-zero
    power — require >= 100 aligned points where possible; (c) control for
    multiple testing across pairs (FDR). NEVER test (SMA, mean_motion) —
    Kepler's third law makes them deterministically coupled (tautology).
    """
    if len(series_a) < 20 or len(series_b) < 20:
        return 1.0
    try:
        _, p_value, _ = coint(series_a, series_b, trend="c")
        return float(p_value)
    except Exception:
        return 1.0


# ---------------------------------------------------------------------------
# 16. DCCA coefficient (Podobnik & Stanley 2008) — pairwise coupling
# ---------------------------------------------------------------------------
def calculate_dcca_rho(series_a, series_b, min_scale: int = 4, max_scale_frac: float = 0.25) -> float:
    """
    Detrended cross-correlation coefficient between two SMA series.

    Robust to nonstationarity (unlike Pearson); strengthens the shadowing
    axis alongside cointegration. Requires equal-length aligned series.
    """
    a = np.asarray(series_a, dtype=float)
    b = np.asarray(series_b, dtype=float)
    if len(a) != len(b) or len(a) < 12:
        return 0.0
    ya = np.cumsum(a - np.mean(a))
    yb = np.cumsum(b - np.mean(b))
    n = len(ya)
    max_s = int(n * max_scale_frac)
    scales = [sc for sc in range(min_scale, max_s + 1)]
    rhos: List[float] = []
    for sc in scales:
        n_seg = n // sc
        if n_seg < 2:
            continue
        f_ab = 0.0
        f_a = 0.0
        f_b = 0.0
        for v in range(n_seg):
            seg_a = ya[v * sc : (v + 1) * sc]
            seg_b = yb[v * sc : (v + 1) * sc]
            x = np.arange(sc, dtype=float)
            pa = np.polyfit(x, seg_a, 1)
            pb = np.polyfit(x, seg_b, 1)
            ra = seg_a - np.polyval(pa, x)
            rb = seg_b - np.polyval(pb, x)
            f_ab += float(np.sum(ra * rb))
            f_a += float(np.sum(ra**2))
            f_b += float(np.sum(rb**2))
        denom = np.sqrt(f_a * f_b) if f_a > 0 and f_b > 0 else 0.0
        if denom > 0:
            rhos.append(f_ab / denom)
    if not rhos:
        return 0.0
    return float(np.clip(float(np.mean(rhos)), -1.0, 1.0))
