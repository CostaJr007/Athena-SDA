# Athena-SDA — Methods & claims for a detection paper

**Status:** working scientific package (hackathon → preprint-ready skeleton)  
**Doctrine:** military-first SDA (protect assets · detect suspects · baseline = normality)

---

## 1. Research question

Can a **public-TLE quantitative noise feature set** combined with a **past-only Isolation Forest**, trained on **non-suspect normality anchors**, detect **elevated orbital regimes** on military-interest satellites in time windows associated with **open-source behavioral reports**, while **civil EO controls** remain below a calibrated hard threshold?

---

## 2. Formal claims (A + B)

### Claim A — Interest / report-aligned regimes

On military-interest case studies (e.g. Luch / Olymp-K, Shiyan-12) with public report anchors \(t_{\text{peak}}\), the past-only anomaly score is **elevated** (hard hit and/or high pre-peak mean) under a fixed protocol with **no look-ahead**.

### Claim B — Placebo separation

Under the **same** protocol and calendars, **civil EO placebos** (TERRA, AQUA, Landsat, NOAA, …) show **lower** score distributions and **near-zero hard-hit rate** at  
\(\ thr = \max(0.50,\ p_{95}^{\text{normality anchors}})\).

Together **A+B** support: the algorithm detects **noise regimes that co-occur with documented atypical military-interest behavior**, relative to quiet civil controls — **not** classified intent and **not** media-date prediction.

---

## 3. Data

| Source | Role |
|--------|------|
| Public TLE history (watchlist NORADs, ~2014–2026) | Orbital time series |
| GFZ F10.7 / Ap / Kp | Space-weather context (drag vs maneuver) |
| `events_walkforward.json` | Open-source case anchors + placebos |
| Watchlist roles asset/suspect/baseline | Military ontology |

---

## 4. Quantitative feature model (noise)

For each sliding window (default ≥20 epochs), `extract_satellite_features` builds a vector including:

| Block | Features (examples) | Physical / SDA reading |
|-------|---------------------|------------------------|
| Keplerian state | SMA, ecc, inc, RAAN, \(n\) | Geometry |
| Deltas / activity | \(\Delta\)SMA 7d/30d, maneuver proxy | Relocation / impulses |
| **Multi-scale persistence** | Hurst full/short, `persistence_hurst_gap`, Shannon full/short | **Micro-trajectory / sustained control** |
| Complexity / breaks | Kolmogorov proxy, L1-CUSUM, ADF, Mandelbrot tail | Pattern complexity, regime breaks |
| Topology proxy | Chern–Simons, Ricci, H0/H1 (proxy mode) | Structural change (approximate) |
| Space weather | F10.7, Ap, Kp, storm flags | Confounder control |

**Isolation Forest inputs** exclude pair geometry (distance/coint) so the detector measures **series strangeness**, not “near an asset”. Pairs are a **priority** channel only.

---

## 5. Detection model

### 5.1 Normality (train)

- Isolation Forest on windows with `window_end < cutoff`  
- **Roles:** baseline + asset only (suspects excluded from normality)  
- Commercial mega-constellation anchors (e.g. Starlink) excluded from train  
- Contamination ~0.06–0.08, `random_state=42`  
- Score: \(\text{anomaly} = \mathrm{clip}(0.5 - \mathrm{decision\_function}, 0, 1)\)

### 5.2 Calibration (threshold)

- Empirical distribution of IF scores on normality-anchor train windows  
- \(thr = \max(0.50,\ p_{95})\) global; optional per-orbit thr (LEO/MEO/GEO)  
- Soft elevated band uses ~p90 for day-over-day relevance only  

### 5.3 Walk-forward protocol (no cheating)

For each case event:

1. Grid `asof` from \(t_{\text{start}}\) to \(t_{\text{end}}\) (step 14 d)  
2. At each `asof`, fit IF only on windows ending before `asof − holdout`  
3. Score the target NORAD window at `asof`  
4. **Hard hit** if score ≥ thr within \(\pm\) hit_window of \(t_{\text{peak}}\)  
5. Report also: pre-peak mean/max, `noise_ramp`, `first_fold_hit`

### 5.4 Priority layer (not Claim A/B)

XGBoost weak labels + fuzzy + suspect×asset pair risk + Kelly-style attention.  
**LLM (Bob)** explains scores and may cite open-source cases; **never** rewrites quant scores.

---

## 6. Evaluation metrics (paper tables)

| Metric | Use |
|--------|-----|
| Hard hit rate interest / placebo | Claim A / B |
| Mean max score; mean pre-peak mean | Effect size |
| p95 placebo max | Calibration check |
| Mann–Whitney U (interest > placebo) | Nonparametric separation (small N caution) |
| `noise_ramp`, `first_fold_hit` | Honest “level vs ramp” interpretation |
| Unique NORAD counts | Independence caveat |

Reproduce:

```bash
python scripts/run_anomaly_monitor.py train-baseline
python scripts/run_paper_validation.py --run-wf --threshold 0.50
```

Artifacts: `data/alerts/paper_validation_latest.json`, `docs/paper/RESULTS_TABLES.md`.

---

## 7. Interpretation rules (for writing)

1. Prefer **Claim A+B + gap + MW** over “lead-time days”.  
2. If `first_fold_hit` and `noise_ramp≈0`: write **persistent elevated regime consistent with documented atypical operations**, not “predicted the report date”.  
3. Open-source anchors **validate co-occurrence of quant noise with public narratives**, not ground-truth intent.  
4. Globe decorative tracks are **out of scope** for the paper methods.

---

## 8. Limitations (must appear in article)

- Small number of unique interest NORADs; repeated Luch-1 windows  
- TLE noise, irregular sampling  
- Homology/Chern–Simons are **proxies** on reconstructed geometry  
- Soft threshold (0.45) is operational only — not for primary claims  
- Active constellation station-keeping can look noisy if misused as placebo  

---

## 9. Ethics

Public data only; no claim of classified targeting; results for **research / operator attention research** in SDA, not automated kinetic decision.

## 10. Paper pack (this repo)

| Artifact | Path |
|----------|------|
| Pre-registration | `docs/paper/PROTOCOL_PREREGISTRATION.md` |
| Limitations | `docs/paper/LIMITATIONS.md` |
| Results tables | `docs/paper/RESULTS_TABLES.md` |
| Pre-peak figures | `docs/paper/figures/prepeak_*.png` |
| Validation JSON | `data/alerts/paper_validation_latest.json` |

```bash
python scripts/run_paper_validation.py --run-wf --threshold 0.50
python scripts/plot_prepeak_curves.py
```

---

*See also: `docs/FOUNDATION_QUANT_VALIDATION.md`, `docs/FULL_ML_REPORT_ATHENA_SDA.md`.*
