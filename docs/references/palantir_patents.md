# Technical Reference: Palantir Technologies Patents (verified 2026-08)

This document compiles the Palantir patent publications used as **architectural
inspiration** for Athena-SDA, with **verified citations** (checked against
Google Patents / Justia / WIPO, 2026-08-10). Palantir patents are inspiration
only — Athena-SDA is an independent implementation on public TLE data and does
not claim affiliation with Palantir Technologies.

> ⚠️ **Citation status:** US 2023/0050870 A1 and US 2024/0394296 A1 are
> **published applications (A1, pending)**, not granted patents. Cite them as
> "U.S. Patent Application Publication".

---

## 1. US 2023/0050870 A1 — AI Meta-Constellation (pending application)

* **Verified:** Palantir Technologies Inc. Inventors: Andrew Elder, Anand
  Gupta, Daniel Cervelli, Robert Imig, Tess Druckenmiller. Priority 2021-08-11;
  published 2023-02-16. Family: WO2023018811A1, EP4384910A1.
* **What it claims (plain language):** request decomposition into tasks →
  selection of edge devices (e.g., satellites) by capability/eligibility →
  edge execution with model activation per monitoring parameters → insight-
  first result transmission. The specification describes the DMP (development
  & management platform, ground) ↔ AIP (AI inference platform, edge) split,
  **micro-model hot-swapping** without breaking outputs, **insight-first
  downlink** (compressed results, not raw data), orthorectification and
  georegistration, low-SWaP edge compute (Jetson-class), and explicit
  "space situational awareness" as a use case.

### Architectural takeaways applied in Athena-SDA
- **Micro-model orchestration bus:** monitor IF / pipeline IF / XGB / evidence
  fusion behind stable interfaces (model registry), so models can be swapped
  per day without touching the sensor/ingest plumbing.
- **Hot-swap versioning:** every `train-baseline` writes a dated snapshot
  (`isolation_forest_monitor_{YYYYMMDD}.joblib`) — the DMP re-fit → AIP score
  loop applied to daily operations (walk-forward analogy).
- **Insight-first downlink:** alerts are compact JSON (risk_report v1), not
  raw TLE dumps.

---

## 2. US 2024/0394296 A1 — ML + LLM-assisted geospatial analysis (pending)

* **Verified:** **Official title is "Machine learning and language model-
  assisted geospatial data analysis and visualization"** (the project's older
  paraphrase "…using machine learning models and language models" was not the
  official title). Palantir. Inventors: Nikhil Nainani, Gabriel Seite, Sameer
  Zaheer, Elena Haddad, Dudon Wai. Published 2024-11-28.
* **Domain caveat:** the application is specifically about **renewable-energy
  site prospecting** (wind/solar capacity and feasibility scoring of land
  parcels). It is NOT a military geospatial patent — frame it as "LLM-assisted
  quantitative geospatial analysis".
* **What it actually claims (corrected framing):** (1) a first ML model scores
  candidate areas/parcels, (2) a **score-threshold filter** cuts the set, (3)
  an **LLM writes a human-readable description** of each survivor, (4) a
  **second ML model scores that text** into a numeric result. Key pattern:
  *cheap quant pre-screen → LLM describes → ML scores the description* — the
  LLM never produces the decision score itself.

### Architectural takeaways applied in Athena-SDA
- **Funnel of coarse→fine:** quant features → IF → threshold → XGB → LLM
  (Bob) describes → final recommendation is a separate deterministic layer.
- **LLM-as-explainer, ML-as-scorer:** Bob generates the briefing but never
  rewrites anomaly scores; a `bob_decision_score` (when present) is a separate
  output from the quant score.
- **LLM plugin/data-access pattern:** Bob retrieves context through typed
  accessors (case-study citations, feature snapshots) rather than free-form
  data access.

---

## 3. US 12,450,265 B2 — Processing and displaying time-related geospatial data

* **Verified:** **Official title is "Systems and methods for processing and
  displaying time-related geospatial data"** (granted 2025-10-21, Active).
  Palantir. Inventors: Peter Wilczynski, Daniel Zangri. Continuation
  US20260093718A1 (2025-10-01).
* **What it claims:** 3D spatiotemporal tiles (two spatial dims + a temporal
  dimension with variable width 1s…1yr); **constant-size tiles across zoom
  levels** via trajectory simplification (Ramer–Douglas–Peucker, Visvalingam–
  Whyatt); interactive spatial+temporal zoom over streamed and historical data
  without latency.

### Architectural takeaways applied in Athena-SDA
- **Temporal epoch store** (`data/history/epochs.parquet`) as the (X, Y, T)
  backbone.
- **Walk-forward event replay** in the UI: anomaly_score(t) curve scrubbed over
  time with event annotations = the "temporal tile" case view.
- **Orbit decimation (RDP)** in the propagation worker (optional) so long
  histories stay smooth at any temporal zoom.

---

## 4. US 12,657,514 B2 — AI inference platform and sensor correlation

* **Verified:** Grant confirmed via **Justia** (Patent 12657514) and PCT family
  member **WO2023114386A1** (PCT/US2022/052991, priority 2021-12-17). Palantir.
  Inventors: Robert Imig, Steven Fackler, Ian Peters, Mark Elliot, Joseph
  Ellis, Andres Felipe Orozco, Akash Jain. Application publication
  US 2023/0196201 A1 (2023-06-22). EP family: EP4433963A1.
* **What it claims:** access models + sensor info → **select models and sensors
  per processing request** → build **model pipelines** (sequential/parallel)
  → deploy to edge. Spec details: **Data API** (sensor adapters), **Inference
  API** (dynamically configurable model registry), **Open API** (downstream
  consumers); **latency budgets** per processor (fixed frame-rate guarantees);
  model push without dropping sensor connections; sensor fusion.

### Architectural takeaways applied in Athena-SDA
- **Data API** = `src/tle_store` (canonical epoch store).
- **Inference API** = `models/registry.json` (micro-model registry).
- **Open API** = `schemas/risk_report.v1.schema.json` (typed contract,
  validated at write time via `src/contracts.py`).
- **Pipeline semantics** = features → IF → XGB → evidence fusion, auditable
  and reproducible per fold.

---

## 5. US 12,374,011 B2 — Interactive data object map

* **Verified:** Granted 2025-07-29, Active. Palantir. **Inventor list
  correction: Dan Cervelli, Cai GoGwilt, Bobby Prochnow** (the project's older
  draft listed "Lauren Shearer, Anand Gupta" — incorrect). Continuation
  US20250329089A1 (2025-10-23). Priority family root 2013-05-07.
* **What it claims:** interactive map of data objects with metadata; on
  selection, objects are organized into **histograms by metadata category**;
  selecting histogram bars **cross-filters the map** and regenerates
  sub-histograms; **client-side UTF grid** per map tile enables instant
  hover/highlight without server round-trips.

### Architectural takeaways applied in Athena-SDA
- **Ontology object model** (`src/ontology.json`): typed Satellite / Alert /
  Sensor / TaskingOrder objects with property and link types (OSDK-style).
- **Cross-filter histograms** on the mission board: filter by role × country ×
  orbit class → board rows and globe layers update together.
- **Instant picking/hover** on the globe (CPU picking over visible objects,
  precomputed geometry) mirrors the UTF-grid interaction idea.

---

## Corrected citation block (paste-ready)

1. A. Elder, A. Gupta, D. Cervelli, R. Imig, T. Druckenmiller, "Systems and
   methods for AI meta-constellation," **U.S. Patent Application Publication
   US 2023/0050870 A1** (filed 2022-08-10, published 2023-02-16), Palantir
   Technologies Inc. https://patents.google.com/patent/US20230050870A1/en
2. N. Nainani, G. Seite, S. Zaheer, E. Haddad, D. Wai, "Machine learning and
   language model-assisted geospatial data analysis and visualization," **US
   2024/0394296 A1** (published 2024-11-28), Palantir.
   https://patents.google.com/patent/US20240394296A1/en
3. P. Wilczynski, D. Zangri, "Systems and methods for processing and displaying
   time-related geospatial data," **US 12,450,265 B2** (granted 2025-10-21),
   Palantir. https://patents.google.com/patent/US12450265B2/en
4. R. Imig, S. Fackler, I. Peters, M. Elliot, J. Ellis, A. F. Orozco,
   A. Jain, "Systems and methods for AI inference platform and sensor
   correlation," **US 12,657,514 B2** (grant; application US 2023/0196201 A1,
   2023-06-22), Palantir. https://patents.justia.com/patent/12657514
5. D. Cervelli, C. GoGwilt, B. Prochnow, "Interactive data object map,"
   **US 12,374,011 B2** (granted 2025-07-29), Palantir.
   https://patents.google.com/patent/US12374011B2/en

Related family members: WO2023018811A1 · EP4384910A1 (patent 1 family);
WO2023114386A1 · EP4433963A1 (patent 4 family); US20260093718A1 (patent 3
continuation); US20250329089A1 (patent 5 continuation).

---

## Honest-use note

- Patents are **architectural inspiration only**; Athena-SDA does not claim
  affiliation with Palantir Technologies.
- Palantir's commercial SDA activity (Warp Core $110.3M Space Force data
  services; Voyager × Palantir SDA payloads 2026) is **program news, not a
  patent** — cite as news, never as a patent number.
- No separate Palantir patent on orbital-maneuver detection or TLE processing
  exists; the two space-relevant families are patents 1 and 4 above.

*Athena-SDA Patent Research Reference — citations verified 2026-08-10.*
