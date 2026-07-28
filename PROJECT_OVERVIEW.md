# ATHENA-SDA — Project Document

> **Hackathon:** AI Builders Challenge
> **Theme:** Advance Space Exploration with AI
> **Team:** Athena-SDA
> **Stack:** Python + XGBoost + IBM Granite / Bob + Streamlit + React 3D Globe

---

## 1. WHAT IS ATHENA-SDA?

### Elevator Pitch (30 seconds)

> *"There are over 30,000 objects in Earth's orbit. Human operators cannot monitor all of them manually. Athena-SDA uses machine learning to classify every object by threat tier, combined with IBM Bob as an AI intelligence analyst that explains, prioritizes, and recommends actions in natural language — acting as a space-domain intelligence copilot."*

### Real-World Challenge

| Fact | Consequence |
|------|-------------|
| ~30,000 tracked objects (active satellites + debris) | Impossible to monitor manually |
| Non-cooperative military satellites perform stealth maneuvers | Space operators require pattern detection |
| Public space catalogs (Space-Track/CelesTrak) are raw data | Raw data exists, operational intelligence does not |
| Legacy tracking systems issue alerts | Legacy tools do not **explain, prioritize, or recommend** actions |

### Solution Architecture

A 3-layer intelligence system:

```
LAYER 1 — ML Engine (Perception):   Classifies 30,000 objects into 🟢🟡🟠🔴 tiers
LAYER 2 — Bob Analyst (Reasoning): Explains operational alerts in natural language
LAYER 3 — Dashboard (Interface):    3D Globe + Risk Cards + Bob Analyst Chat
```

---

## 2. FOUNDATIONAL RESEARCH & PATENTS

### 30+ Frontier Patents Mapped

| Source | Count | Highlights |
|--------|-------|------------|
| 🟣 **Palantir Technologies** | 8 patents | AI Meta-Constellation, Sensor Fusion, **LLM + Geospatial**, Ontology Map |
| 🇺🇸 **Lockheed Martin** | 4 patents | Deep NN for satellite tracking, Missile detection, Decoy discrimination |
| 🇺🇸 **Raytheon / GD / L3Harris** | 6 patents | GAN SAR, RL tracking, Military crypto, Phased array |
| 🇨🇳 **China CAST / CASC** | 10 patents | Active orbital defense, Pursuit-evasion, Anti-deception |

### 5 Anchor Patents (Architectural Extraction)

| Patent | Key Concept Extracted |
|--------|-----------------------|
| **US 2023/0050870 A1** (Palantir) | DMP+AIP Architecture: task decomposition → sensor selection → micro-models → insight-first downlink |
| **US 12,450,265 B2** (Palantir) | 3D Tiles (X,Y,T) + RDP algorithm: simplifying time series for rapid visualization |
| **US 12,657,514 B2** (Palantir) | Data API + Inference API + Dynamic DAG: reconfigurable model pipeline |
| **US 2024/0394296 A1** (Palantir) | **4-Stage LLM + GIS:** physical filter → quantitative ML → descriptive LLM → classifier LLM |
| **US 12,374,011 B2** (Palantir) | Ontology + UTF Grid + interactive histograms: geospatial intelligence objects |

---

## 3. DATA ARCHITECTURE

### Primary Source: TLE Data (Space-Track / CelesTrak)

**What is TLE (Two-Line Element):** Standardized format describing satellite orbital elements. Two 69-character lines contain inclination, eccentricity, mean motion, right ascension, and altitude parameters.

**Data Ingest:**
- TLE records for watchlist objects (~250k epochs, 2014–2026)
- **Space Weather (GFZ Potsdam / NOAA):** F10.7 solar flux and geomagnetic Kp/Ap indices
- **UCS Satellite Database & SATCAT:** Country of origin, mission purpose, launch dates

```
TLE Time Series ──▶ Feature Extractor ──▶ ML Training Dataset
                        │
                        ├── semi_major_axis_km
                        ├── eccentricity
                        ├── inclination_deg
                        ├── delta_sma_7d
                        ├── delta_inc_30d
                        ├── maneuver_count_30d
                        ├── min_distance_to_military_km
                        └── country_purpose (military / civil)
```

---

## 4. HOW IT WORKS

### Complete Pipeline Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                       ATHENA-SDA ENGINE                         │
│                                                                 │
│ ① DATA INGEST                                                   │
│   CelesTrak ──▶ Raw TLE History                                 │
│   GFZ Potsdam ─▶ Space Weather (F10.7, Ap, Kp)                   │
│   UCS Database ▶ Purpose & Ownership Catalog                     │
│                         │                                       │
│                         ▼                                       │
│ ② FEATURE EXTRACTOR                                             │
│   TLE → 34 Orbital + Topological + Space Weather Features        │
│   + Multi-Year Historical Baseline                              │
│                         │                                       │
│                         ▼                                       │
│ ③ ANOMALY DETECTOR (Isolation Forest)                           │
│   "Is this object deviating from its historical baseline?"       │
│   Output: anomaly_score (0.0 = normal, 1.0 = highly anomalous)   │
│                         │                                       │
│                         ▼                                       │
│ ④ THREAT CLASSIFIER (XGBoost + Fuzzy Mamdani + Kelly)           │
│   "What is the operational risk level?"                         │
│   Output: 🟢NORMAL | 🟡ANOMALOUS | 🟠SUSPECT | 🔴HOSTILE          │
│                         │                                       │
│                         ▼                                       │
│ ⑤ BOB ANALYST (IBM Granite Copilot)                             │
│   4-Stage LLM + GIS Pipeline (Palantir Patent US 2024/0394296):  │
│   Stage 1: Filters relevant alerts (eliminates false positives) │
│   Stage 2: ML Engine → quantitative score                       │
│   Stage 3: IBM Granite → contextual qualitative description      │
│   Stage 4: IBM Granite → final classification & recommendation  │
│                         │                                       │
│                         ▼                                       │
│ ⑥ DASHBOARD & FRONTEND                                          │
│   🌍 3D Interactive Globe with Orbital Traces                    │
│   📊 Prioritized Risk Cards                                     │
│   💬 Intelligence Analyst Chat (Briefing & Q&A)                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 5. MACHINE LEARNING ENGINE

| Component | Model | Type | Input | Output |
|-----------|-------|------|-------|--------|
| Anomaly Detector | Isolation Forest | Unsupervised | 34 noise & Kepler features | anomaly_score (0–1) |
| Threat Classifier | XGBoost | Supervised | 38 features + anomaly_score | 🟢🟡🟠🔴 Tiers |
| Risk Calibration | Mamdani Fuzzy | Rule Engine | Distance, Cointegration, Anomaly | Operational Risk |

### Example Feature Vector

```python
features = {
    "semi_major_axis_km": 6878.0,
    "eccentricity": 0.001,              # how circular the orbit is
    "inclination_deg": 51.6,            # angle relative to the equator
    "raan_deg": 150.1,                  # orbital plane orientation
    "arg_perigee_deg": 100.1,           # ellipse orientation
    "mean_anomaly_deg": 260.5,          # position on the orbit
    "mean_motion_rev_per_day": 15.5,    # revolutions per day

    # Temporal variations (detect maneuvers)
    "delta_sma_7d_km": 0.15,           # altitude change over 7 days
    "delta_sma_30d_km": 0.45,          # change over 30 days
    "delta_inc_30d_deg": 0.02,         # inclination change
    "delta_ecc_30d": 0.0001,           # eccentricity change

    # Event counts
    "maneuver_count_7d": 0,            # maneuvers in the week
    "maneuver_count_30d": 1,           # maneuvers in the month

    # Military asset proximity
    "min_distance_to_military_km": 450.0,  # distance to nearest military sat
    "military_nearby_count": 3,            # military sats within 500 km
}
```

### How We Label (Simulated Ground Truth)

We do not have access to real threat classifications (classified). We create rules based on **public military doctrine**:

```python
def label_object(features):
    """
    Space Domain Awareness doctrine rules:
    - Maneuver >2km in 7 days + near military = SUSPECT
    - Maneuver >5km or approach <10km = HOSTILE
    - Multiple maneuvers without motivation = SUSPECT
    """
    if features["min_distance_to_military_km"] < 10:
        return "HOSTILE"
    if features["delta_sma_7d_km"] > 5.0:
        return "HOSTILE"
    if (features["delta_sma_7d_km"] > 2.0 and
        features["min_distance_to_military_km"] < 50):
        return "SUSPECT"
    if features["maneuver_count_30d"] >= 3:
        return "SUSPECT"
    if features["delta_sma_7d_km"] > 1.0:
        return "ANOMALOUS"
    return "NORMAL"
```

### Dataset

| Parameter | Value |
|-----------|-------|
| Objects analyzed | ~10,000 active satellites + ~5,000 trackable fragments |
| Historical period | 12 months (365 days) |
| Features per record | 15 |
| Total records | ~15,000 objects × 365 days = **~5.5 million** |
| On-disk size | ~200 MB (compressed CSV) |
| Expected distribution | ~95% NORMAL, ~3% ANOMALOUS, ~1.5% SUSPECT, ~0.5% HOSTILE |

### Training on Local Hardware

| Hardware | Isolation Forest Time | XGBoost Time | Total |
|----------|----------------------|--------------|-------|
| Ryzen 9 7900X (CPU 12C/24T) | ~30 seconds | ~3 minutes | **~4 minutes** |
| With ROCm GPU | — | ~1 minute | ~2 minutes |

---

## 6. THE DASHBOARD

### Layout

```
┌──────────────────────────────────────────────────────────┐
│  ATHENA-SDA                           🟢 9,947 🟡 35 │
│  Space Domain Awareness Copilot           🟠 12  🔴 3   │
├────────────────────┬─────────────────────────────────────┤
│                    │  🚨 ACTIVE ALERTS                   │
│                    │                                     │
│                    │  🔴 PRIORITY 1                      │
│   🌍 3D GLOBE      │  ┌─────────────────────────────┐    │
│   (Cesium/Plotly)  │  │ Object #44231               │    │
│                    │  │ 3 maneuvers in 24h          │    │
│   • 15,000 objects │  │ Approach to US #22988       │    │
│     in orbit       │  │ Confidence: 87%             │    │
│   • Colored by     │  │ [View briefing] [Dismiss]   │    │
│     classification │  └─────────────────────────────┘    │
│   • Trajectory     │                                     │
│     lines          │  🟠 PRIORITY 2                      │
│   • Hover = info   │  ┌─────────────────────────────┐    │
│                    │  │ Object #52901               │    │
│                    │  │ Suspect orbital change      │    │
│                    │  │ Confidence: 72%             │    │
│                    │  └─────────────────────────────┘    │
├────────────────────┴─────────────────────────────────────┤
│  💬 BOB CHAT                                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │ Bob: I detected 15 alerts in the last 24h.       │  │
│  │ 3 require immediate attention.                   │  │
│  │                                                  │  │
│  │ Operator: Bob, show the trajectory of #44231     │  │
│  │ for the last 7 days.                             │  │
│  │                                                  │  │
│  │ Bob: Rendering on the globe...                   │  │
│  │ The object performed 3 maneuvers:                │  │
│  │ • 10/07: +2.3 km (suspect)                       │  │
│  │ • 12/07: -1.1 km (suspect)                       │  │
│  │ • 13/07: +0.8 km (suspect)                       │  │
│  │ [Type your question...]                          │  │
│  └──────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────┘
```

---

## 7. PITCH METRICS

| Metric | Value | How to Measure |
|--------|-------|----------------|
| Objects monitored | 15,000+ | Active Space-Track catalog |
| Features per object | 15 | Extracted from TLE |
| Cognitive load reduction | **From 15,000 to 15 alerts/day** | ML filter |
| Classifier precision | >85% (cross-validation) | sklearn metrics |
| Bob analysis time | <5 seconds per alert | From insight to briefing |
| Patents referenced | 30+ | Mapped in the project |
| Real contractors | Palantir + Pentagon ($30B Space Force) | Market proof |

---

## 8. WHY THIS IS REAL

- **Palantir** has an active US Space Force contract for SDA
- **Voyager Space + Palantir** announced a partnership in June 2024 specifically for military space AI
- **China** is patenting active orbital defense (5 patents in 2024–2025)
- **SDA market**: $6.9 billion in 2025, growing
- **Data is public**: Space-Track is maintained by the US Space Force

---

## 9. ONE-PARAGRAPH SUMMARY

Athena-SDA ingests the public orbital catalog of 15,000 objects, extracts 15 orbital and temporal features from each, and uses trained Isolation Forest + XGBoost models to classify behavior into 4 threat tiers. Of the 15,000 objects, only ~15 generate alerts per day. Those alerts feed IBM Bob, which — following the 4-stage architecture of Palantir patent US 2024/0394296 A1 (LLM + Geospatial) — contextualizes each threat with space-weather data and military purpose catalogs, produces a qualitative description, classifies with a confidence level, and recommends tactical actions. Everything is displayed on a dashboard with an interactive 3D globe, prioritized alert cards, and chat with Bob. The project is grounded in 30+ frontier patents (Palantir, Lockheed Martin, Raytheon, China CAST/CASC) published between 2023 and 2026.
