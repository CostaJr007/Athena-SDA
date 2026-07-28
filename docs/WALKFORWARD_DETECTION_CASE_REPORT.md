# Walk-Forward Detection Case Report

**What the model saw before open-source public reports**

| | |
|--|--|
| **Run** | 2026-07-26T04:57:45 UTC |
| **Engine** | Isolation Forest past-only (holdout 3 days) · step 14 days · hit thr = **0.50** · peak window ±45 days |
| **Features** | 34-d IF vector: Kepler + math noise (Hurst, Shannon, Kolmogorov, CUSUM, Mandelbrot, ADF…) + GFZ space weather |
| **Artifacts** | `data/alerts/walkforward/wf_*.json`, `wf_analysis_new_ml.json`, `walkforward_summary.json` |
| **Event anchors** | `data/catalog/events_walkforward.json` |

---

## 0. How to read this report

### Protocol (no future leak)

At each evaluation date `asof`:

1. Build a 20-epoch feature window ending on/before `asof`.
2. Train Isolation Forest **only** on folds ending before `asof − holdout` (past series).
3. Score the current window → `anomaly_score = clip(0.5 − decision_function)`.
4. **Hard hit** = score ≥ 0.50 inside ±45 days of public `t_peak`.
5. **Lead-time** = days from **first hard hit** to `t_peak`.

### What “detection” means here

The model does **not** classify “espionage intent.” It flags that the **multivariate orbital noise profile** is rare relative to that object’s own past — typically:

| Signal | Physical / tactical reading |
|--------|------------------------------|
| **Hurst H ≫ 0.5** | Persistent altitude drift (low-thrust / controlled station-keeping, not pure random walk) |
| **Shannon entropy ↑** | Disordered ΔSMA histogram — irregular burns / SK |
| **Kolmogorov proxy ↑** | Hard-to-compress U/D/S pattern → active control |
| **\|ΔSMA 7d\| large** | Net semi-major-axis shift in a week |
| **maneuver_count_30d** | Count of significant SMA steps in ~30 days |
| **L1-CUSUM** | Localized structural break (often low in GEO inspection folds; IF still fires on joint profile) |
| **F10.7 / Ap** | Space-weather context (drag vs maneuver); placebos share same calendar weather |

### Global scoreboard

| Group | N | Hard hit ≥0.50 | Elevated pre-peak noise | Mean max score | Mean lead-time |
|-------|---|----------------|-------------------------|----------------|----------------|
| **Interest (Luch ×4 + SY-12)** | 5 | **5/5 (100%)** | **5/5** | **0.603** | **~201 days** (median 197) |
| **Placebo (TERRA ×2, NOAA-20)** | 3 | **0/3 (0%)** | **0/3** | **0.477** | — |

---

## 1. Case: Luch-1 / Olymp-K — first Intelsat colocation (mid-2015)

| Field | Value |
|-------|-------|
| **Event ID** | `luch1_intelsat_mid2015` |
| **Object** | NORAD **40258** — LUCH (OLYMP-K 1) |
| **Type** | GEO shadowing / RPO-style espionage pattern |
| **WF window** | 2014-10-01 → 2015-08-01 |
| **Public report culmination (`t_peak`)** | **2015-04-15** |
| **Open-source anchor** | Gunter: first colocation between **Intelsat 7 and 901** ~April 2015 |
| **Hard hit** | **Yes** · soft hit Yes |
| **Lead-time** | **182 days** |
| **First hard detection** | **2014-10-15** · score **0.646** (also global max for this event) |
| **Pre-peak elevated noise** | **Yes** (mean 0.555, max 0.646 over 13 pre-peak folds) |

### Timeline

```
2014-10-01   WF window opens (measure ramp before report)
2014-10-15   ★ FIRST HIT score 0.646  ──────────────── lead 182 d ──┐
2015-01-07   High fold 0.631 (H=0.93, persistent control)            │
2015-03-18   High fold 0.597                                         │
2015-04-15   ══ PUBLIC ANCHOR: Intelsat 7/901 colocation (Gunter) ═══╡ culmination
2015-08-01   WF window closes
```

### Why the model fired (first hit 2014-10-15)

| Feature @ first hit | Value | Interpretation |
|---------------------|-------|----------------|
| `anomaly_score` | **0.646** | Strong isolation vs past baseline |
| `delta_sma_7d_km` | **−72.0 km** | Large week-scale SMA change (GEO slot relocation signature) |
| `hurst_exponent_sma` | **0.796** | Persistent (non-Brownian) altitude dynamics |
| `maneuver_count_30d` | **2** | Multiple SMA steps in month |
| `shannon_entropy_sma_30d` | 0.30 | Lower entropy here; isolation driven more by **ΔSMA + Hurst joint profile** |
| `kolmogorov_proxy_7d` | 0.26 | Mild complexity |
| `l1_cusum_sma` | 0.0 | Break not localized by CUSUM; IF still flags multivariate rarity |
| F10.7 / Ap | 125.8 / 9 | Quiet–moderate; not a storm-driven false alarm |

**Narrative:** Months before the April 2015 open report of Olymp-K sitting between Intelsat 7/901, the series already showed a **large SMA relocation** and **persistent control (Hurst)**. Athena’s IF, trained only on the past of this object, marked the regime as anomalous from **15 Oct 2014**.

---

## 2. Case: Luch-1 / Olymp-K — Intelsat 905 season (2015)

| Field | Value |
|-------|-------|
| **Event ID** | `luch1_intelsat_2015` |
| **Object** | NORAD **40258** — LUCH (OLYMP-K 1) |
| **Type** | GEO shadowing |
| **WF window** | 2015-01-15 → 2016-03-01 |
| **Public report culmination (`t_peak`)** | **2015-09-15** |
| **Open-source anchors** | Gunter: near **Intelsat 905** ~24.4–24.5°W (~Sep 2015); earlier Intelsat 7/901 (~Apr); CSIS *Unusual Behavior in GEO* |
| **Hard hit** | **Yes** |
| **Lead-time** | **243 days** (longest interest lead) |
| **First hard detection** | **2015-01-15** · score **0.537** |
| **Max anomaly** | 0.599 @ 2015-12-31 (post-peak continuation of active GEO regime) |
| **Pre-peak elevated noise** | **Yes** (mean 0.522, max 0.578) |

### Timeline

```
2015-01-15   ★ FIRST HIT score 0.537  ────────────── lead 243 d ──┐
2015-02-12   Fold 0.563 · ΔSMA ≈ +62 km (big weekly shift)        │
2015-04-09   Fold 0.545 · Shannon 2.29                            │
2015-04-23   Fold 0.561 (near first Intelsat episode)             │
2015-07-02   Fold 0.538                                           │
2015-08-27   Pre-peak peak fold 0.578 · Shannon 2.84              │
2015-09-15   ══ PUBLIC ANCHOR: Intelsat 905 proximity reports ════╡ culmination
2015-12-31   Max score in full window 0.599 (sustained regime)
2016-03-01   WF window closes
```

### Why the model fired (first hit 2015-01-15)

| Feature @ first hit | Value | Interpretation |
|---------------------|-------|----------------|
| `anomaly_score` | **0.537** | Above hard threshold |
| `hurst_exponent_sma` | **0.941** | **Very high persistence** → continuous low-thrust / controlled drift |
| `shannon_entropy_sma_30d` | **1.36** | Elevated disorder in ΔSMA |
| `kolmogorov_proxy_7d` | **0.47** | Moderate control complexity |
| `maneuver_count_30d` | **6** | Frequent SMA steps (busy GEO SK / relocation) |
| `delta_sma_7d_km` | +0.54 km | Mild at first hit; later folds show large jumps (e.g. +62 km on 2015-02-12) |
| F10.7 / Ap | 131.4 / 5 | Not storm-dominated |

**Narrative:** From the start of the 2015 window, Olymp-K already looked like a **persistently controlled GEO object with high maneuver cadence**. Public reporting of the Intelsat 905 proximity clustered around **Sep 2015**; Athena had hard-flagged the noise regime **~8 months earlier**.

---

## 3. Case: Luch-1 / Olymp-K — Athena-Fidus concerns (2018)

| Field | Value |
|-------|-------|
| **Event ID** | `luch1_athena_fidus_2018` |
| **Object** | NORAD **40258** — LUCH (OLYMP-K 1) |
| **Type** | GEO shadowing near allied military comms asset |
| **WF window** | 2018-01-01 → 2019-03-01 |
| **Public report culmination (`t_peak`)** | **2018-09-01** |
| **Open-source anchors** | Gunter / open press: proximity concerns re **Athena-Fidus** (FR military communications); French government space-security statements |
| **Hard hit** | **Yes** |
| **Lead-time** | **229 days** |
| **First hard detection** | **2018-01-15** · score **0.524** |
| **Max anomaly** | 0.627 @ 2018-11-05 |
| **Pre-peak elevated noise** | **Yes** |

### Timeline

```
2018-01-15   ★ FIRST HIT score 0.524  ────────────── lead 229 d ──┐
2018-04-23   Fold 0.559 · ΔSMA ≈ −110 km (major slot move)        │
2018-06-18   Fold 0.554                                           │
2018-08-27   Pre-peak peak fold 0.561 · Shannon 2.65              │
2018-09-01   ══ PUBLIC ANCHOR: Athena-Fidus concern window ═══════╡ culmination
2018-11-05   Max score 0.627 (continued post-report activity)
2019-03-01   WF window closes
```

### Why the model fired (first hit 2018-01-15)

| Feature @ first hit | Value | Interpretation |
|---------------------|-------|----------------|
| `anomaly_score` | **0.524** | Hard hit |
| `hurst_exponent_sma` | **0.956** | Extreme persistence (active control signature) |
| `kolmogorov_proxy_7d` | **0.579** | High trajectory complexity |
| `shannon_entropy_sma_30d` | 0.88 | Moderate entropy at onset; later rises to ~2.6 |
| `delta_sma_7d_km` | **−7.65 km** | Non-trivial weekly SMA change |
| `maneuver_count_30d` | 1 | Escalates later (large −110 km fold in Apr) |
| F10.7 / Ap | **70.2 / 9** | Quiet solar cycle phase — **not** drag-driven LEO false positive |

**Narrative:** Under quiet space weather, Luch-1 still showed **extreme Hurst + complex control**. Public concern about proximity to French military satcom (Athena-Fidus) is anchored at **Sep 2018**; the series was hard-anomalous from **mid-January 2018**, with a large relocation fold in **April** still before the public peak.

---

## 4. Case: Shiyan-12 01 — GEO RPO (2021–22)

| Field | Value |
|-------|-------|
| **Event ID** | `sy12_geo_rpo_2021_22` |
| **Object** | NORAD **50321** — SHIYAN-12 01 (SY-12 01) |
| **Type** | GEO RPO / inspection |
| **WF window** | 2021-12-01 → 2022-12-01 |
| **Public report culmination (`t_peak`)** | **2022-06-15** |
| **Open-source anchors** | AMOS / open SSA: SY-12 GEO proximity with US objects; SWF Chinese Military RPO fact sheet |
| **Hard hit** | **Yes** |
| **Lead-time** | **154 days** (shortest interest lead, still ~5 months) |
| **First hard detection** | **2022-01-12** · score **0.534** |
| **Max anomaly** | 0.573 @ 2022-08-24 |
| **Pre-peak elevated noise** | **Yes** (mean 0.485, max 0.534) |

### Timeline

```
2021-12-01   WF window (post late-2021 launch era)
2022-01-12   ★ FIRST HIT score 0.534  ────────────── lead 154 d ──┐
2022-03-09   Fold 0.506 · ΔSMA ≈ −18 km                           │
2022-04-20   Fold 0.507                                           │
2022-06-15   ══ PUBLIC ANCHOR: reported GEO RPO season ═══════════╡ culmination
2022-08-24   Max score 0.573
2022-12-01   WF window closes
```

### Why the model fired (first hit 2022-01-12)

| Feature @ first hit | Value | Interpretation |
|---------------------|-------|----------------|
| `anomaly_score` | **0.534** | Hard hit early in GEO ops life |
| `hurst_exponent_sma` | **0.887** | Strong persistence |
| `kolmogorov_proxy_7d` | **0.632** | **High** complexity — active inspection-style control |
| `maneuver_count_30d` | **6** | High maneuver cadence |
| `shannon_entropy_sma_30d` | 0.77 | Rising later |
| `delta_sma_7d_km` | +0.13 km | Small at first hit; later −18 km fold |
| F10.7 / Ap | 103.2 / 3 | Quiet geomagnetic |

**Narrative:** After entering GEO operations, SY-12 already exhibited **high Kolmogorov + high maneuver count + persistent Hurst**. Open SSA/AMOS-style reporting of US-object proximity is anchored mid-2022; Athena hard-detected anomalous noise from **12 Jan 2022**.

---

## 5. Case: Luch-2 / Olymp-K 2 — trailing Western GEO (2023)

| Field | Value |
|-------|-------|
| **Event ID** | `luch2_trailing_2023` |
| **Object** | NORAD **55841** — LUCH-5X (OLYMP-K 2) |
| **Type** | GEO trailing / shadowing |
| **WF window** | 2023-04-01 → 2024-03-01 |
| **Public report culmination (`t_peak`)** | **2023-10-15** |
| **Open-source anchors** | Launch ~**12 Mar 2023**; **Breaking Defense Oct 2023**: second Luch trailing Western systems in GEO |
| **Hard hit** | **Yes** |
| **Lead-time** | **197 days** |
| **First hard detection** | **2023-04-01** · score **0.551** (first fold of window) |
| **Max anomaly** | 0.569 @ 2023-09-02 (weeks before public peak) |
| **Pre-peak elevated noise** | **Yes** |

### Timeline

```
2023-03-12   Launch Olymp-K 2 (context)
2023-04-01   ★ FIRST HIT score 0.551  ────────────── lead 197 d ──┐
2023-08-05   Fold 0.555                                           │
2023-09-02   Max pre-peak 0.569 · Shannon 2.29                    │
2023-10-15   ══ PUBLIC ANCHOR: Breaking Defense trailing story ═══╡ culmination
2024-03-01   WF window closes
```

### Why the model fired (first hit 2023-04-01)

| Feature @ first hit | Value | Interpretation |
|---------------------|-------|----------------|
| `anomaly_score` | **0.551** | Immediate hard hit post-launch window |
| `shannon_entropy_sma_30d` | **2.115** | **Very high** ΔSMA disorder |
| `hurst_exponent_sma` | **0.910** | Strong persistence |
| `delta_sma_7d_km` | +0.48 km | Active weekly SMA change |
| `maneuver_count_30d` | 2 | Early ops maneuvers |
| `kolmogorov_proxy_7d` | 0.16 | Lower than Luch-1 2018; Shannon+Hurst dominate isolation |
| F10.7 / Ap | 125.3 / 14 | Moderate; not extreme storm |

**Narrative:** Within weeks of launch, Olymp-K 2 already showed a **noisy, persistent GEO control signature**. Press coverage of trailing Western GEO assets (Oct 2023) comes **~6.5 months** after Athena’s first hard flag.

---

## 6. Placebo controls (same calendars, civil baselines)

Same solar/geomagnetic calendar as the interest cases. If space weather alone caused hits, placebos would hard-hit. They **do not**.

| Event | Object | Peak (shared calendar) | Hard hit ≥0.50 | Soft ≥0.45 | Elevated pre-peak | Max score | Max asof |
|-------|--------|------------------------|----------------|------------|-------------------|-----------|----------|
| `placebo_terra_2015` | TERRA 25994 | 2015-09-15 (vs Luch Intelsat) | **No** | Yes (weak) | **No** | 0.478 | 2015-10-08 |
| `placebo_terra_2018` | TERRA 25994 | 2018-09-01 (vs Athena-Fidus) | **No** | No | **No** | 0.489 | 2018-11-05 |
| `placebo_noaa20_2023` | NOAA-20 43013 | 2023-10-15 (vs Luch-2) | **No** | Yes (weak) | **No** | 0.463 | 2023-08-05 |

**Reading:** TERRA/NOAA can show high Shannon (EO LEO dynamics) and high Hurst from drag/SK, but the **joint IF profile never crosses 0.50** inside the report window, and pre-peak noise is **not** elevated by the project’s criterion. Discriminator = **GEO inspection / relocation regime**, not calendar weather alone.

---

## 7. Master timeline (interest only)

| # | Public case | Report peak | First Athena hard hit | Lead | Dominant first-hit drivers | Public culmination (open source) |
|---|-------------|-------------|----------------------|------|----------------------------|----------------------------------|
| 1 | Luch Intelsat mid-2015 | 2015-04-15 | **2014-10-15** (0.646) | **182 d** | **ΔSMA −72 km**, Hurst 0.80 | Gunter: colocation Intelsat 7/901 |
| 2 | Luch Intelsat 2015 | 2015-09-15 | **2015-01-15** (0.537) | **243 d** | **Hurst 0.94**, man=6, Shannon | Gunter/CSIS: Intelsat 905 ~24.5°W |
| 3 | Luch Athena-Fidus 2018 | 2018-09-01 | **2018-01-15** (0.524) | **229 d** | **Hurst 0.96**, Kolmogorov 0.58 | Press / FR statements re Athena-Fidus |
| 4 | SY-12 GEO RPO | 2022-06-15 | **2022-01-12** (0.534) | **154 d** | Kolmogorov 0.63, man=6, Hurst | AMOS/SWF RPO reporting |
| 5 | Luch-2 trailing 2023 | 2023-10-15 | **2023-04-01** (0.551) | **197 d** | **Shannon 2.1**, Hurst 0.91 | Breaking Defense Oct 2023 |

**Mean lead-time (1st hit → public peak): ~201 days.**

---

## 8. Cross-case pattern: “why noise?”

Across interest cases, first hard hits cluster around **one or more** of:

1. **Persistent control (Hurst 0.79–0.96)** — not mean-reverting passive GEO.
2. **High maneuver cadence** (often 2–6 steps / 30d) or **large weekly ΔSMA** (slot moves of tens of km).
3. **Shannon / Kolmogorov** elevated when the control pattern is irregular or complex.
4. **Quiet-to-moderate space weather** at many first hits → reduces “it was just a storm” explanations (reinforced by placebos).

CUSUM is often **0** at first hit: detection is **regime-level multivariate isolation**, not a single CUSUM spike.

---

## 9. Explicit limits (scientific honesty)

1. Long lead-times often mean the object was already in an **anomalous operating regime** from early in the WF window — not a single classified “intent prediction.”
2. Anchors (`t_peak`) are **open-source publication / documented episode dates**, not precise classified TCA times.
3. Pair-risk is a **proximity/cointegration support** signal, not full SGP4 conjunction analysis.
4. XGBoost class labels are **not** the walk-forward hit criterion; IF anomaly score is.

---

## 10. Reproduce

```bash
python scripts/run_walkforward.py run --step-days 14 --holdout-days 3 --threshold 0.50
python scripts/run_walkforward.py summary
```

| File | Role |
|------|------|
| `data/catalog/events_walkforward.json` | Public anchors + sources |
| `data/alerts/walkforward/wf_<event>.json` | Per-fold scores + features |
| `data/alerts/walkforward/wf_analysis_new_ml.json` | First hit + top pre-peak folds |
| `data/alerts/walkforward_summary.json` | Aggregate metrics |
| `docs/WALKFORWARD_PRE_REPORT_ML.md` | Protocol summary |
| **This file** | Case-by-case noise attribution |

---

*Athena-SDA — walk-forward case report: noise before public reports.*
