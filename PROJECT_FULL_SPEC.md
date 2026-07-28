# ATHENA-SDA — Master Project Specification

> **Challenge:** AI Builders Challenge
> **Theme:** Advance Space Exploration with AI
> **Stack:** Python + XGBoost + Isolation Forest + Fuzzy Logic + IBM Granite / Bob + Streamlit + React 3D Globe
> **Last Update:** 2026-07-26

---

## TABLE OF CONTENTS

1. [Project Overview](#1-project-overview)
2. [Patent Foundation (30+ patents)](#2-patent-foundation)
3. [Real Orbital Data](#3-real-orbital-data)
4. [System Architecture](#4-system-architecture)
5. [Machine Learning Pipeline](#5-machine-learning-pipeline)
6. [Mathematical Framework](#6-mathematical-framework)
7. [Bob — Intelligence Analyst Copilot](#7-bob--intelligence-analyst-copilot)
8. [Dashboard & User Interface](#8-dashboard--user-interface)
9. [Demonstration Scenarios](#9-demonstration-scenarios)
10. [Pitch Metrics](#10-pitch-metrics)

---

## 1. PROJECT OVERVIEW

### Concept

**Athena-SDA** is a **Space Domain Awareness (SDA)** copilot combining machine learning, fuzzy logic, information theory, and IBM Granite/Bob to monitor orbital assets, classify threats, and generate natural language tactical intelligence briefings.

### Challenge Statement

Human operators cannot manually track thousands of objects. Legacy systems output raw alerts without **explaining, prioritizing, or recommending actions**.

### 3-Layer Solution Architecture

```
LAYER 1 — ML + Math Engine (Perception): Filter thousands of objects → ~15 daily priority alerts
LAYER 2 — Bob / Granite (Reasoning):    Explain, contextualize, and recommend operational actions
LAYER 3 — Dashboard & Globe (UI):       Interactive 3D globe + risk cards + copilot chat
```

### Core Metric

> **From 30,000 objects to 15 actionable operational decisions per day.**

---

## 2. PATENT FOUNDATION

### Anchor Patents (Architectural Extraction)

| Patent | Organization | Key Insight Extracted |
|--------|--------------|-----------------------|
| US 2023/0050870 A1 | Palantir | DMP+AIP: mission breakdown → sensor selection → micro-models → insight-first downlink |
| US 12,450,265 B2 | Palantir | 3D Tiles (X,Y,T) + RDP: simplifying time series |
| US 12,657,514 B2 | Palantir | Data API + Inference API + Dynamic Model DAG |
| US 2024/0394296 A1 | Palantir | **4-Stage LLM + GIS Architecture** |
| US 12,374,011 B2 | Palantir | Ontology + UTF Grid + interactive histograms |

### Supporting Patent Landscape

| Source | Count | Highlights |
|--------|-------|------------|
| Palantir Technologies | 8 patents | Meta-Constellation, Sensor Fusion, LLM+Geospatial, Ontology Map |
| Lockheed Martin | 4 patents | Deep NN for satellite tracking, Missile detection, Decoy discrimination |
| Raytheon / GD / L3Harris | 6 patents | GAN SAR, RL tracking, Military Crypto, Phased Array |
| China CAST / CASC | 10+ patents | Active orbital defense, Pursuit-evasion, Anti-deception |

---

## 3. REAL ORBITAL DATA

### Primary Data Ingestion

| Source | Payload | Access | Cost |
|--------|---------|--------|------|
| CelesTrak.org | TLE orbital elements | Public API | Free |
| Space-Track.org | Official US Space Force TLEs | REST API | Free |
| UCS Satellite Database | Mission purpose & ownership | CSV Dataset | Free |
| GFZ Potsdam / NOAA | Space weather (F10.7, Ap, Kp) | REST API | Free |

---

## 4. SYSTEM ARCHITECTURE

```
┌─────────────────────────────────────────────────────────────────┐
│                       ATHENA-SDA                              │
│                                                                  │
│ ① DATA INGEST                                                    │
│   CelesTrak TLE ──── NOAA Space Weather ──── UCS Database        │
│                         │                                        │
│                         ▼                                        │
│ ② FEATURE EXTRACTOR (20+ features)                               │
│   Shannon Entropy │ Kolmogorov │ Hurst │ Mandelbrot │ Ricci     │
│   Homology │ Chern-Simons proxy │ Fuzzy │ Hilbert/RKHS           │
│                         │                                        │
│                         ▼                                        │
│ ③ ANOMALY DETECTOR (Isolation Forest)                            │
│   "Is this object behaving differently from normal?"             │
│                         │                                        │
│                         ▼                                        │
│ ④ THREAT CLASSIFIER (XGBoost)                                    │
│   🟢 NORMAL | 🟡 ANOMALOUS | 🟠 SUSPECT | 🔴 HOSTILE             │
│                         │                                        │
│              (only 🟠🔴 alerts proceed)                          │
│                         │                                        │
│                         ▼                                        │
│ ⑤ FUZZY INFERENCE (skfuzzy)                                      │
│   Handles uncertainty: stale TLE, decision boundaries            │
│   Output: threat_level + confidence + ambiguity                  │
│                         │                                        │
│                         ▼                                        │
│ ⑥ BOB ANALYST (IBM Granite + Tool Calling)                       │
│   4-stage LLM+Geospatial pipeline (Palantir US 2024/0394296)     │
│   Contextualize → Explain → Prioritize → Recommend               │
│                         │                                        │
│                         ▼                                        │
│ ⑦ DASHBOARD (Streamlit)                                          │
│   3D Globe │ Threat cards │ Bob chat │ Histograms                │
└─────────────────────────────────────────────────────────────────┘
```

---

## 5. MACHINE LEARNING PIPELINE

### Features (20+ per object)

```python
features = {
    # Instantaneous orbital parameters (7)
    "semi_major_axis_km": 6878.0,
    "eccentricity": 0.001,
    "inclination_deg": 51.6,
    "raan_deg": 150.1,
    "arg_perigee_deg": 100.1,
    "mean_anomaly_deg": 260.5,
    "mean_motion_rev_per_day": 15.5,

    # Temporal variations (4)
    "delta_sma_7d_km": 0.15,
    "delta_sma_30d_km": 0.45,
    "delta_inc_30d_deg": 0.02,
    "maneuver_count_30d": 1,

    # Advanced mathematics (9+)
    # (implemented in Section 6)
    "shannon_entropy_sma_30d": ...,
    "kolmogorov_proxy_7d": ...,
    "hurst_exponent_sma": ...,
    "mandelbrot_tail_score": ...,
    "ricci_mean": ...,
    "ricci_delta_7d": ...,
    "persistent_h0_count": ...,
    "chern_simons_proxy": ...,
    "spectral_anomaly_rkhs": ...,

    # Context (2)
    "intrinsic_threat_value": ...,  # Williams (1938)
    "tle_age_hours": 12,
}
```

### Models

| Model | Algorithm | Type | Output |
|-------|-----------|------|--------|
| Anomaly Detector | Isolation Forest | Unsupervised | anomaly_score (0-1) |
| Threat Classifier | XGBoost | Supervised | 🟢🟡🟠🔴 |
| Fuzzy Inference | skfuzzy (Mamdani) | Rule-based | threat_level + confidence |
| Kelly Allocator | Kelly Criterion | Decision | resource_allocation |

### Labels (Simulated Ground Truth)

Based on public military Space Domain Awareness doctrine:

- `min_distance_to_military_km < 10` → HOSTILE
- `delta_sma_7d > 5.0 km` → HOSTILE
- `delta_sma_7d > 2.0 AND min_dist < 50` → SUSPECT
- `maneuver_count_30d >= 3` → SUSPECT
- `delta_sma_7d > 1.0` → ANOMALOUS
- Otherwise → NORMAL

---

## 6. MATHEMATICAL FRAMEWORK

### Complete Matrix: 14 Applied Theories

| # | Theory | Author/Year | Feature | Type |
|---|--------|-------------|---------|------|
| 1 | Intrinsic Value | Williams (1938) | `intrinsic_threat_value` | Static |
| 2 | Kernel Regression | Lo et al. (2000) | `kernel_typicality_score` | Non-parametric |
| 3 | Kernel L1 CUSUM | — | `l1_cusum_sma` | Robust sequential |
| 4 | Heavy Tails | Mandelbrot (1963) | `mandelbrot_tail_score` | Distributional |
| 5 | Long Memory R/S | Hurst (1951) | `hurst_exponent` | Temporal |
| 6 | Shannon Entropy | Shannon (1948) | `entropy_sma_30d` | Informational |
| 7 | Kolmogorov Complexity | Kolmogorov (1965) | `kolmogorov_proxy_7d` | Algorithmic |
| 8 | Persistent Homology | Edelsbrunner (2002) | `h0_persistent`, `h1_persistent` | Topological |
| 9 | Ricci Curvature | Ollivier (2007) | `ricci_mean`, `ricci_delta` | Geometric |
| 10 | Chern-Simons (proxy) | Chern-Simons (1974) | `topological_violation` | Topological |
| 11 | Fuzzy Sets | Zadeh (1965) | `fuzzy_threat`, `fuzzy_confidence` | Logic |
| 12 | Łukasiewicz Logic | Łukasiewicz (1920) | `lukasiewicz_implication` | Logic |
| 13 | Kelly Criterion | Kelly (1956) | `kelly_allocation` | Decision |
| 14 | Hilbert/RKHS | Hilbert (~1900) | `spectral_anomaly` | Geometric |

### Application Order (Basic to Advanced)

```
PHASE 1 (MVP):      Basic orbital features → XGBoost
PHASE 2 (Advanced): Shannon + Kolmogorov + Hurst
PHASE 3 (Expert):   Mandelbrot + Ricci + Homology + Chern-Simons
PHASE 4 (Decision): Fuzzy + Kelly + Hilbert/RKHS
```

### Implementation Status by Theory

| Status | Theories |
|--------|----------|
| ✅ Direct implementation (5–20 lines) | Shannon, Kolmogorov, Hurst, Mandelbrot, Zadeh, Łukasiewicz, Kelly, Williams, Lo, Hilbert |
| ⚠️ Approximation required | Ollivier-Ricci, Persistent Homology (sample), Chern-Simons (proxy) |
| ❌ Conceptual only | Exact Chern-Simons (out of scope) |

---

## 7. BOB — THE INTELLIGENCE COPILOT

### What Bob Does (Based on Palantir Patent US 2024/0394296 A1)

4-stage LLM + Geospatial pipeline:

| Stage | What It Does | Example |
|-------|--------------|---------|
| **1. Filter** | Removes false positives, irrelevant objects | "Of 15 alerts, 12 are routine maintenance. 3 require analysis." |
| **2. Quantitative** | XGBoost produces numeric score | threat_score = 0.87 |
| **3. Descriptive** | Granite generates contextual description | "Object #44231 (Yaogan-31, China). 3 maneuvers in 24h. ΔSMA: +2.3, -1.1, +0.8 km." |
| **4. Classifier** | Granite classifies and recommends | "🟠 SUSPECT. Confidence: 87%. Recommend optical tasking + notify USSF." |

### Tool Calling (APIs Bob Queries)

```
get_object_history(norad_id)     → 12 months of TLE
get_close_approaches(norad_id)   → Approaches <50km in 48h
get_space_weather()              → F10.7, Ap index
get_object_metadata(norad_id)    → Country, purpose, launch
get_similar_events(norad_id)     → Similar historical events
```

### Example Generated Briefing

```
🚨 SDA BRIEFING — 2026-07-14 04:52 UTC

OBJECT: #44231 (Yaogan-31, China)
CLASSIFICATION: 🟠 SUSPECT
FUZZY CONFIDENCE: 87% | AMBIGUITY: 13%

ANALYSIS:
- 3 orbital maneuvers in 24h (ΔSMA: +2.3, -1.1, +0.8 km)
- Shannon entropy: 2.1 (chaotic — normal is 0.3)
- Hurst exponent: 0.78 (strongly persistent)
- Ricci curvature: -0.45 (neighborhood divergence)
- Approached US military satellite #22988: 15.2 km
- TLE is 12h old (precision ±100m)

RECOMMENDED ACTION (Kelly allocation: 42% of resources):
1. 🔴 Notify USSF SDA cell
2. 📡 Request optical tasking (next overpass: 06:30 UTC)
3. 📊 Monitor 24h with 10 km threshold
4. 📋 Generate report for JSpOC
```

---

## 8. DASHBOARD AND INTERFACE

### Layout

```
┌──────────────────────────────────────────────────────────┐
│  ATHENA-SDA                           🟢 29,947 🟡 35│
│  Space Domain Awareness Copilot           🟠 12  🔴 3   │
├────────────────────┬─────────────────────────────────────┤
│                    │  🚨 ACTIVE ALERTS (Kelly ranked)   │
│   🌍 3D GLOBE      │  🔴 42% — Object #44231 (Yaogan-31)│
│   • 30k objects    │  🟠 28% — Object #52901             │
│   • Colored by     │  🟠 15% — Object #67012             │
│     classification │  ...                                  │
│   • Trajectories   │                                      │
│   • Hover = info   │  📊 HISTOGRAMS                       │
│                    │  [By country] [By class] [By orbit]  │
├────────────────────┴─────────────────────────────────────┤
│  💬 BOB CHAT                                          │
│  Bob: 15 alerts in the last 24h. 3 priority.         │
│  Operator: Detail #44231                             │
│  Bob: Yaogan-31, China. 3 maneuvers. Suspect pattern.│
│  [_________________________________________________] │
└──────────────────────────────────────────────────────────┘
```

### Technologies

- **Streamlit** — dashboard framework
- **Plotly/Cesium** — 3D globe
- **Folium** — 2D map (fallback)
- **Altair/Plotly** — interactive histograms

---

## 9. DEMONSTRATION SCENARIOS

### Primary Scenario: Orbital Reconnaissance Alert

```
1. Day's TLEs are ingested (10 seconds)
2. ML processes 30,000 objects:
   - 29,947 🟢 NORMAL
   - 35 🟡 ANOMALOUS
   - 12 🟠 SUSPECT
   - 3 🔴 HOSTILE
3. Bob analyzes the 15 🟠🔴 alerts (5 seconds each)
4. Dashboard shows:
   - #44231 (Yaogan-31, China): 🔴 HOSTILE — approached US MILSAT
   - #67012 (anomalous debris): 🟠 SUSPECT — unexplained maneuvers
   - #88001 (Cosmos-2560, Russia): 🟠 SUSPECT — orbit change
5. Operator asks: "Bob, has #44231 done this before?"
6. Bob: "Yes. Similar pattern in March/2024 over the Pacific."
```

### Secondary Scenario: False Positive with Stale TLE

```
1. Object #52901: TLE with 96h age
2. Fuzzy detects high uncertainty (ambiguity: 49%)
3. Bob: "Low confidence (51%). Stale TLE.
         I do not recommend escalation. Await update."
```

---

## 10. IMPLEMENTATION ROADMAP

### Phases

```
PHASE 0 (30min)  ▸ Setup: IBM Cloud + watsonx.ai + repository
PHASE 1 (2h)     ▸ Download TLE Space-Track/CelesTrak + UCS DB
PHASE 2 (2h)     ▸ Feature Extractor: basic orbital features (7)
PHASE 3 (2h)     ▸ Train: Isolation Forest + XGBoost (MVP)
PHASE 4 (2h)     ▸ Advanced features: Shannon + Kolmogorov + Hurst + Mandelbrot
PHASE 5 (2h)     ▸ Expert features: Ricci + Homology + Chern-Simons proxy
PHASE 6 (2h)     ▸ Fuzzy Inference System + Kelly Allocator
PHASE 7 (2h)     ▸ Bob Integration: Granite + Tool Calling + Prompt Engineering
PHASE 8 (2h)     ▸ Streamlit Dashboard: 3D globe + cards + chat
PHASE 9 (1h30)   ▸ Polish + Pitch Deck + Rehearsal
```

### Priority

| Priority | What | Why |
|----------|------|-----|
| 🔴 MUST | Basic features + XGBoost + Bob + Dashboard | Functional MVP |
| 🟡 SHOULD | Shannon + Kolmogorov + Hurst + Fuzzy | Mathematical differentiator |
| 🟢 NICE | Ricci + Homology + Chern-Simons + Kelly | Academic excellence |

---

## 11. PITCH METRICS

| Metric | Value | How to Measure |
|--------|-------|----------------|
| Objects monitored | 30,000+ | Space-Track catalog |
| Features per object | 20+ | Extraction pipeline |
| Cognitive reduction | From 30,000 to ~15 alerts/day | ML + Fuzzy filter |
| Classifier precision | >85% | Cross-validation |
| Bob analysis time | <5s per alert | Timestamp |
| Applied mathematical theories | 14 | Documented |
| Patents referenced | 30+ | Mapped |
| Real market | $6.9B SDA + $30B Space Force | Market reports |
| Real contractors | Palantir + Pentagon | Market proof |

---

## APPENDIX: Complete References

### Patents
See document `docs/references/palantir_patents.md` for the mapped patent list.

### Mathematical Theories
- Shannon, C.E. (1948). *A Mathematical Theory of Communication*. Bell System Technical Journal.
- Kolmogorov, A.N. (1965). *Three approaches to the quantitative definition of information*. Problems of Information Transmission.
- Hurst, H.E. (1951). *Long-term storage capacity of reservoirs*. Transactions of ASCE.
- Mandelbrot, B. (1963). *The variation of certain speculative prices*. Journal of Business.
- Zadeh, L.A. (1965). *Fuzzy sets*. Information and Control.
- Ollivier, Y. (2007). *Ricci curvature of Markov chains on metric spaces*. Journal of Functional Analysis.
- Edelsbrunner, H. et al. (2002). *Topological persistence and simplification*. Discrete & Computational Geometry.
- Kelly, J.L. (1956). *A new interpretation of information rate*. Bell System Technical Journal.
- Williams, J.B. (1938). *The Theory of Investment Value*. Harvard University Press.
- Lo, A.W. et al. (2000). *Foundations of technical analysis*. Journal of Finance.

### Data
- CelesTrak: https://celestrak.org
- Space-Track: https://www.space-track.org
- UCS Satellite Database: https://www.ucsusa.org/resources/satellite-database
- NOAA Space Weather: https://www.swpc.noaa.gov

### IBM Tools
- watsonx.ai: https://www.ibm.com/watsonx
- Granite Models: https://huggingface.co/ibm-granite
- IBM Cloud: https://cloud.ibm.com

---

*Document generated as the master reference for the Athena-SDA project.*
*Hackathon AI Builders Challenge — August 2025*
