# Complete Mathematical Framework — Athena-SDA

This document is the engineering and modeling reference for **Athena-SDA**, unifying 16 statistical, mathematical, and economic theories for orbital anomaly detection, very-low-thrust maneuver identification, and spy-satellite detection (proximity and shadowing).

---

## 1. Shannon Entropy (Orbital Predictability)
* **Theory:** Claude Shannon (1948)
* **Objective:** Quantify disorder or uncertainty in semi-major axis (\(a\)) behavior.

### Mathematical Formulation
Given a time series of daily semi-major-axis variations \(\Delta a_t = a_t - a_{t-1}\), discretize those values into \(N\) histogram bins to approximate the empirical probability distribution \(P(x_i)\). Shannon entropy is:

$$H(X) = -\sum_{i=1}^{N} P(x_i) \log_2 P(x_i)$$

### Physical Justification (SDA)
* **Passive Keplerian orbit:** The satellite decays only under gravity and regular atmospheric drag. \(\Delta a_t\) is highly concentrated in few bins. \(H(X) \to 0\) (high order / predictability).
* **Orbit with active maneuvers:** Daily altitude variations are erratically distributed due to occasional burns. \(H(X) > 1.8\) (high disorder / chaos).

### Python Implementation
```python
import numpy as np
from scipy.stats import entropy

def shannon_entropy_sma(sma_series, bins=10):
    if len(sma_series) < 2:
        return 0.0
    diffs = np.diff(sma_series)
    hist, _ = np.histogram(diffs, bins=bins)
    probs = hist / np.sum(hist)
    # Remove zero probabilities
    probs = probs[probs > 0]
    return entropy(probs, base=2)
```

---

## 2. Kolmogorov Complexity (Algorithmic Control Detection)
* **Theory:** Andrey Kolmogorov (1965)
* **Objective:** Assess whether the orbital trajectory is described by simple physical laws or by a dynamic guidance-control algorithm.

### Mathematical Formulation
Kolmogorov complexity \(K(s)\) is the size of the shortest program \(p\) that produces string \(s\) on a Universal Turing Machine. Because \(K(s)\) is undecidable, a lossless compressor (e.g. `zlib`) is used as an upper-bound proxy:

$$K_{\text{proxy}}(s) = \frac{\text{Len}(\text{Compress}(s))}{\text{Len}(s)}$$

### Physical Justification (SDA)
* **Natural drift:** The trajectory is described by simple propagation physics (low information flow). The discretized motion-direction representation compresses well (\(K_{\text{proxy}} \to 0\)).
* **Evasive maneuvers or RPO:** The satellite executes frequent sensor-driven micro-corrections, creating a pseudo-random state chain that resists compression (\(K_{\text{proxy}} \to 1\)).

### Python Implementation
```python
import zlib

def kolmogorov_complexity_proxy(sma_series):
    if len(sma_series) < 2:
        return 0.0
    diffs = np.diff(sma_series)
    # Encode the series as tokens: U (Up), D (Down), S (Stable)
    threshold = 0.05  # 50 meters
    tokens = []
    for d in diffs:
        if d > threshold:
            tokens.append("U")
        elif d < -threshold:
            tokens.append("D")
        else:
            tokens.append("S")
    
    s = "".join(tokens).encode('utf-8')
    if len(s) == 0:
        return 0.0
    compressed = zlib.compress(s)
    return len(compressed) / len(s)
```

---

## 3. Hurst Exponent (Long-Memory and R/S)
* **Theory:** Harold Edwin Hurst (1951)
* **Objective:** Identify whether orbital motion has an active long-term trend (low-thrust electric propulsion).

### Mathematical Formulation
Rescaled Range (R/S) analysis divides the cumulative range of mean-detrended amplitude by the standard deviation over windows of size \(n\):

$$E \left[ \frac{R(n)}{S(n)} \right] = C \cdot n^H$$

* **\(H < 0.5\):** Anti-persistent (mean reversion — standard station-keeping).
* **\(H = 0.5\):** Pure random walk (Keplerian white noise).
* **\(H > 0.5\):** Persistent (target-seeking / active orbital transfer behavior).

### Python Implementation
```python
def hurst_exponent(series, max_lag=20):
    n = len(series)
    if n < 10:
        return 0.5
    lags = range(2, min(max_lag, n // 2))
    rs_values = []
    for lag in lags:
        n_segments = n // lag
        rs = []
        for i in range(n_segments):
            segment = series[i * lag : (i + 1) * lag]
            mean = np.mean(segment)
            std = np.std(segment)
            if std == 0:
                continue
            deviations = segment - mean
            cum_dev = np.cumsum(deviations)
            R = np.max(cum_dev) - np.min(cum_dev)
            rs.append(R / std)
        if len(rs) > 0:
            rs_values.append(np.mean(rs))
    if len(rs_values) < 2:
        return 0.5
    H = np.polyfit(np.log(list(lags[:len(rs_values)])), np.log(rs_values), 1)[0]
    return np.clip(H, 0.0, 1.0)
```

---

## 4. Ollivier-Ricci Curvature (Orbital Graph Anomalies)
* **Theory:** Yann Ollivier (2007)
* **Objective:** Detect convergences and spatial distortions in the geometric neighborhood of a constellation.

### Mathematical Formulation
Ricci curvature \(\kappa(x, y)\) between two nodes (satellites) on the geometric graph is computed using the Wasserstein-1 transport distance (\(W_1\)) between neighborhood probability measures:

$$\kappa(x, y) = 1 - \frac{W_1(m_x, m_y)}{d(x, y)}$$

### Physical Justification (SDA)
* **Regular structure:** In stable constellations (e.g. GPS), satellites keep constant distances. Curvature is stable and homogeneous.
* **Hostile approach:** An intruder enters the neighborhood, changing local transport flow atypically so that \(\kappa(x, y)\) takes positive values toward the target.

### Python Implementation
```python
from scipy.stats import wasserstein_distance

def ollivier_ricci_proxy(pos_x, neighbors_x, pos_y, neighbors_y):
    """
    Discrete approximation of Ricci curvature using 1D Wasserstein
    on neighbor distances relative to the central nodes.
    """
    d_xy = np.linalg.norm(pos_x - pos_y)
    if d_xy == 0:
        return 0.0
    
    # Empirical neighborhood measures
    dist_x = np.linalg.norm(neighbors_x - pos_x, axis=1)
    dist_y = np.linalg.norm(neighbors_y - pos_y, axis=1)
    
    w1 = wasserstein_distance(dist_x, dist_y)
    return 1.0 - (w1 / d_xy)
```

---

## 5. Persistent Homology (TDA — Topological Data Analysis)
* **Theory:** Herbert Edelsbrunner (2002)
* **Objective:** Detect long-term structural deformations in 3D point-cloud trajectories.

### Mathematical Formulation
Build the Vietoris–Rips filtration \(VR(P, \epsilon)\) by varying connectivity radius \(\epsilon\) over the satellite’s three-dimensional orbital positions:

$$VR(P, \epsilon) = \{ \sigma \subseteq P : \text{diam}(\sigma) \le \epsilon \}$$

Track the \(H_1\) cycle (1D loops) along the filtration to map its persistence (birth and death).

### Python Implementation
```python
from ripser import ripser

def persistent_homology_features(positions_3d):
    """
    Measure topological persistence (H0 and H1) of a swarm or trajectory.
    """
    if len(positions_3d) < 5:
        return {'h0_persistent': 1, 'h1_persistent': 0}
    
    dgms = ripser(positions_3d, maxdim=1)['dgms']
    h0 = dgms[0]
    h1 = dgms[1]
    
    # Mean H0 (connected components) and H1 (loops) persistence
    h0_pers = np.mean([d[1] - d[0] for d in h0 if np.isfinite(d[1])]) if len(h0) > 0 else 0
    h1_pers = np.mean([d[1] - d[0] for d in h1]) if len(h1) > 0 else 0
    
    return {
        'h0_persistent': h0_pers,
        'h1_persistent': h1_pers
    }
```

---

## 6. Chern–Simons Proxy (Non-Conservation of the Orbital Field)
* **Theory:** Chern–Simons (1974)
* **Objective:** Measure the action of non-conservative propulsive forces (chemical or ion).

### Mathematical Formulation
Specific angular momentum \(\vec{h} = \vec{r} \times \vec{v}\) is conserved for a pure Keplerian orbit (conservative gravitational field). Perturbation of angular momentum is used as a Chern–Simons topological proxy:

$$\text{CS}_{\text{proxy}} = \frac{\max \|\vec{h}_t - \vec{h}_0\|}{\|\vec{h}_0\|}$$

### Python Implementation
```python
def chern_simons_angular_momentum(positions, velocities):
    if len(positions) < 2:
        return 0.0
    # Specific angular momentum h = r x v
    h_vectors = np.cross(positions, velocities)
    h0 = h_vectors[0]
    norm_h0 = np.linalg.norm(h0)
    if norm_h0 == 0:
        return 0.0
    # Maximum deviation from baseline
    diffs = np.linalg.norm(h_vectors - h0, axis=1)
    return np.max(diffs) / norm_h0
```

---

## 7. Spectral Anomaly in Hilbert Space (RKHS)
* **Theory:** David Hilbert (~1900)
* **Objective:** Detect orbital distribution changes by mapping features into infinite dimensions.

### Mathematical Formulation
Use the Gaussian RBF kernel \(k(x, y) = \exp(-\gamma \|x - y\|^2)\) to compute feature similarity in Hilbert space and evaluate the similarity norm against a stable reference set:

$$\text{Anomaly} = 1.0 - \max_j k(x, x_{\text{ref}, j})$$

### Python Implementation
```python
from sklearn.metrics.pairwise import rbf_kernel

def spectral_anomaly_rkhs(features_vector, reference_matrix, gamma=0.1):
    if reference_matrix.shape[0] == 0:
        return 1.0
    x = features_vector.reshape(1, -1)
    sims = rbf_kernel(x, reference_matrix, gamma=gamma)
    return 1.0 - np.max(sims)
```

---

## 8. Mamdani Fuzzy Logic (Inference under Uncertainty)
* **Theory:** Lotfi A. Zadeh (1965)
* **Objective:** Aggregate multiple ML scores and mathematical features under measurement uncertainty.

### Mathematical Formulation
Given continuous input \(x\), compute membership \(\mu_A(x) \in [0, 1]\). Inference rules are aggregated and the crisp output is defuzzified by centroid:

$$z^* = \frac{\int z \cdot \mu_C(z) dz}{\int \mu_C(z) dz}$$

### Python Implementation
```python
import skfuzzy as fuzz
from skfuzzy import control as ctrl

# Basic fuzzy control system setup
anomaly = ctrl.Antecedent(np.arange(0, 1.01, 0.01), 'anomaly')
anomaly['low'] = fuzz.trapmf(anomaly.universe, [0, 0, 0.3, 0.5])
anomaly['medium'] = fuzz.trimf(anomaly.universe, [0.3, 0.5, 0.7])
anomaly['high']  = fuzz.trapmf(anomaly.universe, [0.5, 0.7, 1.0, 1.0])

# Variables and rules are initialized in the fuzzy.py module
```

---

## 9. Łukasiewicz Logic (Logical Validation of Theses)
* **Theory:** Jan Łukasiewicz (1920)
* **Objective:** Check consistency of continuous aerospace hypotheses (e.g. “Satellite A behaves anomalously implies it is performing RPO”).

### Mathematical Formulation
Truth of the Łukasiewicz implication \(I(p, q)\) operates on continuous logical values in \([0, 1]\):

$$v(p \rightarrow q) = \min(1, 1 - v(p) + v(q))$$

### Python Implementation
```python
def lukasiewicz_implication(val_p, val_q):
    return min(1.0, 1.0 - val_p + val_q)
```

---

## 10. Kelly Criterion (Prioritization and Allocation Sizing)
* **Theory:** John Larry Kelly, Jr. (1956)
* **Objective:** Tune sensor scan focus and time (radars/telescopes) toward the highest-value alert satellites.

### Mathematical Formulation
The ideal tracking-time fraction \(f^*\) for a specific object is:

$$f^* = \frac{p \cdot b - q}{b}$$

* **\(p\):** Probability the threat is real (fuzzy confidence \(\times\) threat level).
* **\(q = 1.0 - p\):** Probability of false positive.
* **\(b\):** Target severity (odds multiplier: military=100, civil=5).

### Python Implementation
```python
def kelly_resource_allocation(threat_prob, severity_multiplier):
    p = threat_prob
    q = 1.0 - p
    b = severity_multiplier
    if b <= 0:
        return 0.0
    f_star = (p * b - q) / b
    return max(0.0, f_star * 0.5)  # Half-Kelly for stability
```

---

## 11. Williams Intrinsic Value (Static Heuristic Threat)
* **Theory:** John Burr Williams (1938)
* **Objective:** Evaluate the static geopolitical vulnerability intrinsic to the satellite.

### Mathematical Formulation
Assign a static weight from fixed satellite properties: owner country (allies vs adversaries), orbit type (LEO Polar vs LEO Equatorial), and mission purpose (SIGINT/Reconnaissance vs civil telecommunications).

### Python Implementation
```python
def williams_intrinsic_threat(country, purpose, orbit_class, inclination):
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
    
    # Polar LEO is typical of high-resolution reconnaissance satellites
    if orbit_class == 'LEO' and inclination > 55:
        score += 0.2
        
    return np.clip(score, 0.0, 1.0)
```

---

## 12. Kernel Regression Smoothing (Harmonic Noise Filter)
* **Theory:** Lo et al. (2000)
* **Objective:** Smooth coordinate series to remove secondary harmonic orbital perturbations or point TLE measurement errors.

### Mathematical Formulation
Use the Nadaraya–Watson estimator with Gaussian kernel \(K_h\):

$$\hat{m}(t) = \frac{\sum_{i=1}^{n} K_h(t - t_i) Y_i}{\sum_{i=1}^{n} K_h(t - t_i)}$$

### Python Implementation
```python
def kernel_smoothing_nadaraya_watson(time_indices, values, bandwidth=1.5):
    n = len(values)
    smoothed = np.zeros(n)
    for i, t in enumerate(time_indices):
        diffs = (t - time_indices) / bandwidth
        weights = np.exp(-0.5 * diffs**2)  # Gaussian kernel
        sum_w = np.sum(weights)
        smoothed[i] = np.sum(weights * values) / sum_w if sum_w > 0 else values[i]
    return smoothed
```

---

## 13. Kernelized L1-CUSUM Algorithm
* **Objective:** Detect abrupt structural breaks in orbital variation in a statistically robust way.

### Mathematical Formulation
Use the median and median absolute deviation (MAD) under an Epanechnikov kernel so that isolated outliers do not trigger false maneuver alarms:

$$z_t = \frac{|x_t - \text{median}|}{\text{MAD} + \epsilon}$$

### Python Implementation
```python
def kernel_l1_cusum_robust(series, window=30, threshold=3.5):
    if len(series) < window:
        return 0.0
    baseline = np.median(series[-window:])
    mad = np.median(np.abs(series[-window:] - baseline))
    if mad == 0:
        mad = 1e-6
    
    current = series[-1]
    z_score = np.abs(current - baseline) / mad
    
    # Epanechnikov kernel
    if z_score > 1.0:
        kernel_weight = 0.0
    else:
        kernel_weight = 0.75 * (1 - z_score**2)
        
    cusum = np.sum(kernel_weight * np.abs(np.array(series[-10:]) - baseline)) / mad
    return np.clip(cusum / threshold, 0.0, 1.0)
```

---

## 14. Mandelbrot Heavy-Tail Anomalies
* **Theory:** Benoit Mandelbrot (1963)
* **Objective:** Model the tails of orbital variations with heavy-tailed Pareto distributions.

### Mathematical Formulation
Natural orbital variations follow Gaussian distributions, but deliberate maneuvers produce extreme events that violate that assumption. Fit a Pareto distribution to the upper tail:

$$P(X > x) \sim \left( \frac{x_{\text{min}}}{x} \right)^\alpha$$

### Python Implementation
```python
from scipy.stats import pareto

def mandelbrot_tail_anomaly(series, quantile=90):
    if len(series) < 15:
        return 0.0
    threshold = np.percentile(series, quantile)
    tail_data = series[series >= threshold]
    if len(tail_data) < 2 or np.all(tail_data == threshold):
        return 0.0
    
    # Hill estimator for the tail alpha parameter
    alpha = len(tail_data) / np.sum(np.log(tail_data / threshold))
    current = series[-1]
    if current < threshold:
        return 0.0
    
    # P-value under Pareto distribution
    p_val = (current / threshold) ** (-alpha)
    return 1.0 - p_val
```

---

## 15. Augmented Dickey–Fuller Unit-Root Test (ADF)
* **Theory:** David Dickey, Wayne Fuller (1979)
* **Objective:** Detect loss of stationarity in the detrended residual orbital series, flagging the onset of active micro-maneuvers.

### Mathematical Formulation
The ADF test fits a linear regression on the first difference of the orbital series to test for a unit root (\(\gamma = 0\)):

$$\Delta y_t = \alpha + \beta t + \gamma y_{t-1} + \sum_{i=1}^{p} \delta_i \Delta y_{t-i} + \epsilon_t$$

* **Null hypothesis (\(H_0\)):** The series has a unit root (non-stationary — satellite is actively changing orbit).
* **Alternative hypothesis (\(H_1\)):** The series is stationary (satellite only decaying passively).

### Python Implementation
```python
from statsmodels.tsa.stattools import adfuller

def adf_stationarity_pvalue(series):
    """
    Returns the ADF test p-value.
    p-value > 0.05 -> Non-stationary (indication of behavior change / maneuver).
    p-value <= 0.05 -> Stationary (passive / stable Keplerian satellite).
    """
    if len(series) < 20:
        return 0.0  # Insufficient data to test
    try:
        # Run ADF with regression containing constant and trend
        result = adfuller(series, regression='ct')
        p_value = result[1]
        return p_value
    except Exception:
        return 0.5  # On numerical error, return indecision
```

---

## 16. Engle–Granger Cointegration Test (RPO / Shadowing Detection)
* **Theory:** Robert Engle, Clive Granger (1987)
* **Objective:** Detect physical pursuit (shadowing) between two satellites by testing whether the difference of their altitudes is stationary long-term.

### Mathematical Formulation
Given two non-stationary altitude series \(y_{A, t}\) and \(y_{B, t}\) (which decay independently under drag), run ordinary least squares (OLS):

$$y_{A, t} = \beta y_{B, t} + u_t$$

Then test stationarity of the estimated residuals \(\hat{u}_t\) with the ADF test. If \(\hat{u}_t\) is stationary, the series are **cointegrated**, meaning the distance between them is actively and precisely maintained under closed-loop control.

### Python Implementation
```python
from statsmodels.tsa.stattools import coint

def check_orbital_cointegration(series_a, series_b):
    """
    Check whether two satellite trajectories are cointegrated.
    Returns Engle-Granger test p-value.
    p-value < 0.05 -> Cointegrated (Satellite A is actively following / spying on B).
    p-value >= 0.05 -> Not cointegrated (Independent orbits that diverge).
    """
    if len(series_a) < 20 or len(series_b) < 20:
        return 1.0
    try:
        # Test returns test statistic, p-value, and critical values
        score, p_value, _ = coint(series_a, series_b, trend='c')
        return p_value
    except Exception:
        return 1.0
```
