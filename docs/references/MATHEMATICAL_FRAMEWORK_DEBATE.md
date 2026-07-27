# Architectural & Mathematical Verification Guide — Athena-SDA

**Document Purpose:**  
This technical dossier provides an architectural evaluation framework and open questions for peer review, verifying the mathematical design of Athena-SDA against aerospace standards and threat-detection domain requirements.

---

## Technical Context & Architectural Audit

**System Overview:**  
Athena-SDA is a Space Domain Awareness (SDA) intelligence framework inspired by modern defense intelligence architectures (Palantir Patent US 2024/0394296 A1). Its primary objective is detecting non-cooperative orbital behaviors, rendezvous and proximity operations (RPO), and stealth maneuvers.

**Pipeline Architecture:**
1. **Data Ingestion:** Historical TLE (Two-Line Element) time series extracted over sliding 20-epoch windows.
2. **Mathematical Engine (26 Features):** Computes Keplerian deltas alongside complex mathematical proxies: Shannon Entropy, Kolmogorov Proxy Complexity, Hurst Exponent, L1-CUSUM, Mandelbrot Tail Anomaly, Engle-Granger Cointegration (satellite pairs), Ricci Curvature proxy, Persistent Homology (H0/H1), RKHS Spectral Anomaly, and Łukasiewicz Fuzzy Logic.
3. **ML Pipeline:**
   - **Phase 1 (Unsupervised Anomaly Monitor):** `IsolationForest` (trained strictly on past baseline windows) generates `anomaly_score`.
   - **Phase 2 (Supervised Classifier):** `XGBoost` (classes: Normal, Anomalous, Suspect, Hostile) consumes features + `anomaly_score`, applying asymmetric cost-weighting (false negatives on Hostile weighted 5x).
   - **Phase 3 (Operational Doctrine Calibration):** Mamdani Fuzzy engine adjusts risk scores based on operational proximity rules and data quality gates.
4. **Validation:** Out-of-time *Walk-Forward* validation over multi-year real TLE histories (~250k epochs) and open-source event anchors.

---

### Core Review Axes

#### Axis 1: Mathematical Framework & Topology Robustness
1. **Short Series Phase Space Topology:** Evaluating Persistent Homology (H0/H1) and Ricci curvature proxy stability over 20-epoch sliding windows vs sensor noise.
2. **Engle-Granger Cointegration for Shadowing:** Verifying that orbital decay non-stationarity is properly decoupled from true cointegration during relative proximity inspection.

#### Axis 2: Machine Learning Pipeline Integrity
1. **Multi-Stage Cascade (IF → XGB → Fuzzy):** Assessing model generalization, monotonic constraints, and preventing overfitting on historical time series.
2. **Walk-Forward Holdout Protocol:** Strict temporal separation preventing look-ahead data leakage during training folds.

#### Axis 3: Space Weather & Atmospheric Drag Decoupling
1. **Solar Weather Integration:** Distinguishing solar flux (F10.7 / geomagnetic Kp index) atmospheric expansion drag from propulsive satellite maneuvers.

#### Axis 4: Relative Geometries & Closest Approach (TCA)
1. **Dynamic RPO Metrics:** Transitioning static orbital ring distances into dynamic SGP4 relative propagation and relative velocity ($\Delta v$) vectors.

