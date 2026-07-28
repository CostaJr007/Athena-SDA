# Mathematical Foundation of the Athena-SDA Project

This document details the mathematical framework behind the 14 theories integrated into **Athena-SDA** for orbital anomaly detection, trajectory analysis, and decision-making under uncertainty.

---

## 1. Shannon Entropy (Orbital Information Disorder)
* **Theory:** Claude Shannon (1948)
* **Objective:** Measure disorder and unpredictability in orbital parameter time series.

Shannon entropy for a discrete random variable \(X\) with states \(x_1, ..., x_n\) is defined as:

$$H(X) = -\sum_{i=1}^{n} P(x_i) \log_2 P(x_i)$$

### Application in Satellite Tracking
We analyze variations in Semi-Major Axis (\(a\)) over a rolling 30-day window. Daily variations \(\Delta a_t = a_t - a_{t-1}\) are binned to estimate probabilities \(P(x_i)\).
* **Stable Keplerian Orbit:** Natural perturbation baseline. Probability is concentrated in few bins (\(H(X) \approx 0.2\)).
* **Active Maneuvering:** Intentionally altered altitude spreads variations across multiple bins, elevating entropy (\(H(X) > 1.8\)).

---

## 2. Kolmogorov Complexity Proxy (Algorithmic Intent Detection)
* **Theory:** Andrey Kolmogorov (1965)
* **Objective:** Determine if a trajectory is governed by passive celestial mechanics or an active control algorithm.

The Kolmogorov complexity \(K(s)\) of string \(s\) is the length of the shortest program \(p\) running on a Universal Turing Machine \(U\) that outputs \(s\):

$$K(s) = \min \{ |p| : U(p) = s \}$$

### Application in Satellite Tracking
Since \(K(s)\) is non-computable, lossless compression size (zlib/LZW) serves as an algorithmic complexity proxy:

$$K_{\text{proxy}}(s) = \frac{\text{Size}(\text{Compress}(s))}{\text{Size}(s)}$$

* Natural orbits compress efficiently (\(K_{\text{proxy}} \to 0\)).
* Complex evasive or rendezvous maneuvers yield higher algorithmic entropy (\(K_{\text{proxy}} \to 1\)).

---

## 3. Hurst Exponent (Long-Memory & Rescaled Range R/S Analysis)
* **Theory:** Harold Edwin Hurst (1951)
* **Objective:** Distinguish natural atmospheric drag decay from persistent electric/ion propulsion.

$$E \left[ \frac{R(n)}{S(n)} \right] = C \cdot n^H$$

* **\(H = 0.5\):** Uncorrelated Brownian motion (random walk).
* **\(0.5 < H \le 1.0\):** Persistent time series (long-term memory/trend).
* **\(0 \le H < 0.5\):** Anti-persistent time series (mean-reverting).

---

## 4. Ollivier-Ricci Curvature (Constellation Graph Anomaly Detection)
* **Theory:** Yann Ollivier (2007)
* **Objective:** Detect local deformations in satellite constellations caused by non-cooperative orbital proximity.

$$\kappa(x, y) = 1 - \frac{W_1(m_x, m_y)}{d(x, y)}$$

---

## 5. Persistent Homology (Topological Data Analysis - TDA)
* **Theory:** Herbert Edelsbrunner (2002)
* **Objective:** Detect structural trajectory topological shifts in 3D point cloud embeddings.

Simplicial homology groups \(H_k\):
* **\(H_0\):** Connected components (physical clustering of assets).
* **\(H_1\):** 1D loops/tunnels (circular/elliptical orbital periodicity).

---

## 6. Chern-Simons Proxy (Non-Conservative Force Field Signatures)
* **Theory:** Shiing-Shen Chern, James Harris Simons (1974)
* **Objective:** Detect non-conservative propulsive forces in orbital dynamics.

$$CS = \int_{t_0}^{t_1} (\vec{v} \cdot \vec{\omega}) dt$$

### Application in Tracking
By Liouville's theorem, a purely Hamiltonian flow (satellite under natural gravity) conserves phase-space volume and topology, yielding a constant CS value. If the satellite fires chemical or ion thrusters, it breaks conservative symmetry, causing a peak in the \(CS\) score and indicating an active external force.

---

## 7. Spectral Anomaly in Hilbert Spaces (RKHS)
* **Theory:** David Hilbert (~1900)
* **Objective:** Project orbital trajectories into infinite-dimensional spaces to detect instantaneous distribution changes.

We map the orbital state vector \(x_t \in \mathbb{R}^d\) into a Reproducing Kernel Hilbert Space \(\mathcal{H}_k\) via a feature map \(\Phi(x_t) = k(x_t, \cdot)\), using the Gaussian RBF kernel:

$$k(x, y) = \exp\left(-\gamma \|x - y\|^2\right)$$

Spectral anomaly is measured by computing eigenvalues of the Gram matrix \(K_{ij} = k(x_i, x_j)\) in a rolling window to compute spectral density divergence. A shift in dominant frequencies indicates alteration of orbital harmonic coefficients.

---

## 8. Mamdani Fuzzy Logic (Inference under Uncertainty)
* **Theory:** Lotfi A. Zadeh (1965), Ebrahim Mamdani (1975)
* **Objective:** Combine multiple anomalous features under measurement uncertainty to produce a final classification.

We use trapezoidal and triangular membership functions \(\mu_A(x) \in [0, 1]\) to translate continuous variables into linguistic terms:
* **Inputs:** `Maneuver Magnitude` (\(\Delta SMA\)), `Target Proximity` (\(Dist\)), `TLE Age` (\(Age\)).
* **Fuzzy Rules:**
  $$\text{IF } \Delta SMA \text{ is HIGH } \text{ AND } \text{ Proximity is CLOSE } \text{ AND } \text{ TLE Age is NEW } \rightarrow \text{ Threat is RED (HOSTILE)}$$

### Inference Mechanism
1. **Fuzzification:** Compute membership degrees \(\mu_i(x)\) for inputs.
2. **Fuzzy Operator (AND):** Use minimum \(\mu_{A \cap B}(x) = \min(\mu_A(x), \mu_B(x))\).
3. **Defuzzification:** Compute the centroid of the aggregated area from Mamdani rules to obtain the crisp numeric value:
   $$z^* = \frac{\int z \cdot \mu_C(z) dz}{\int \mu_C(z) dz}$$

---

## 9. Łukasiewicz Logic (Logical Hypothesis Validation)
* **Theory:** Jan Łukasiewicz (1920)
* **Objective:** Evaluate logical consistency of threat assumptions operating on fractional truth values \(v(A) \in [0, 1]\).

The Łukasiewicz implication \(I(p, q)\) is defined as:

$$v(p \rightarrow q) = \min(1, 1 - v(p) + v(q))$$

We use this to compute consistency of complex SDA premises. For example:
* If \(p\) = *"Object maneuvered"* (\(v(p) = 0.85\) via Hurst) and \(q\) = *"Object is active/controlled"* (\(v(q) = 0.90\) via Kolmogorov).
* The truth of the implication \(v(p \rightarrow q)\) is \(\min(1, 1 - 0.85 + 0.90) = 1.0\), validating the logical integrity of the controlled-maneuver hypothesis.

---

## 10. Kelly Criterion (Search Resource Prioritization)
* **Theory:** John Larry Kelly, Jr. (1956)
* **Objective:** Optimize allocation of ground sensor time (radars and telescopes) for tracking priority targets.

The ideal resource fraction \(f^*\) to allocate to a given threat is:

$$f^* = \frac{b \cdot p - q}{b}$$

Where:
* \(f^*\) is the fraction of ground sensor processing/time capacity to allocate.
* \(p\) is the threat probability (from XGBoost + Fuzzy).
* \(q = 1 - p\) is the probability the object is benign.
* \(b\) represents the relative criticality of the threatened target satellite (strategic-loss odds).

This prevents wasting critical tracking resources on high-uncertainty false alarms.

---

## 11. Williams Intrinsic Value (Vulnerability Weighting)
* **Theory:** John Burr Williams (1938)
* **Objective:** Weight the strategic relevance of satellites in space based on residual future utility.

We adapt the classic discounted-dividend formula to compute the *Strategic Intrinsic Value* \(V\) of a target satellite under monitoring:

$$V = \sum_{t=1}^{T} \frac{U_t}{(1 + r)^t}$$

Where:
* \(U_t\) is the utility/importance index of the satellite at time \(t\) (military, communications, GPS).
* \(r\) is the annual technological obsolescence or orbital decay rate.
* \(T\) is the remaining expected useful life of the satellite.

---

## 12. Kernel Regression (Trajectory Smoothing)
* **Theory:** Andrew W. Lo, Harry Mamaysky, A. Craig MacKinlay (2000)
* **Objective:** Remove noise and secondary harmonic fluctuations from orbital telemetry series.

We estimate a smoothed version of the orbit \(m(t)\) from noisy measurements \(Y_i\) using the Nadaraya–Watson estimator:

$$\hat{m}(t) = \frac{\sum_{i=1}^n K_h(t - t_i) Y_i}{\sum_{i=1}^n K_h(t - t_i)}$$

Where \(K_h(u) = \frac{1}{h} K\left(\frac{u}{h}\right)\) is a Gaussian kernel of bandwidth \(h\) that filters spurious frequencies, isolating the true orbital transition curve.

---

## 13. Kernelized L1-CUSUM Algorithm (Maneuver Onset Detection)
* **Objective:** Detect the exact onset of a very-low-thrust maneuver.

We monitor a cumulative sum in Hilbert space to detect structural breaks in the temporal distribution of orbital elements:

$$S_k = \max\left(0, S_{k-1} + \ln \frac{p_{\theta_1}(\Phi(x_k))}{p_{\theta_0}(\Phi(x_k))}\right)$$

When the statistic \(S_k\) exceeds a critical threshold \(h_{\text{thr}}\), we determine that a change-point occurred and mark the immediate onset of active satellite propulsion ignition.

---

## 14. Heavy-Tail Distribution Theory (Noise Discrimination)
* **Theory:** Benoit Mandelbrot (1963)
* **Objective:** Differentiate natural orbital perturbations from artificial disturbances based on the weight of the error distribution tails.

We analyze whether orbital acceleration variations follow a Lévy Alpha-Stable distribution with tail parameter \(\alpha \in (0, 2]\):

$$P(X > x) \sim x^{-\alpha} \quad (x \to \infty)$$

* **\(\alpha = 2\) (Normal distribution):** Indicates orbital fluctuations generated by the sum of natural micro-impacts (thermal drag, stable solar winds).
* **\(\alpha < 1.5\) (Mandelbrot heavy tails):** Indicates isolated extreme peaks incompatible with normal stochastic phenomena, characterizing high-energy thruster firings over short timescales.

---

*Athena-SDA Mathematical Framework Reference Standard.*
