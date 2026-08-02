# Protocol pre-registration — Athena-SDA walk-forward validation

**Status:** locked for paper analyses after this date  
**Registered:** 2026-08-01 (UTC)  
**Project:** Athena-SDA (military-first quant noise detection)  
**Code commit reference:** regenerate with `git rev-parse HEAD` at analysis time  

---

## 1. Research question (fixed)

Do past-only Isolation Forest scores on public-TLE **quantitative noise features** separate **military-interest case windows** (open-source behavioral anchors) from **civil EO placebo windows** under the same protocol?

---

## 2. Primary claims (fixed wording)

| ID | Claim |
|----|--------|
| **A** | Interest events: elevated anomaly scores / hard hits near public \(t_{\text{peak}}\) |
| **B** | Civil EO placebos: lower scores; hard-hit rate near zero at pre-specified thr |

Secondary (honest regime description, not primary success):

- `noise_ramp` (late − early pre-peak mean)  
- `first_fold_hit` (already elevated at first scorable fold)  
- Multi-scale Hurst/Shannon feature chemistry  

---

## 3. Data inclusion (pre-specified)

### 3.1 Interest (military / dual-use suspects on watchlist)

NORADs with citable open-source or dual-use catalog anchors in `events_walkforward.json` (v4+), including:

- GEO: Luch/Olymp-K 1 (40258), Luch-2 (55841), SY-12 (50321)  
- LEO experimental/recon/military: SY-7 (39208), Yaogan-29 (41038), Yaogan-3 (32289), COSMOS 2550 (48865), CSS Tianhe (48274)  
- MEO dual-use: BeiDou-3 M11 (43603)  

**Independence rule:** report both **n_events** and **n_unique_norads**. Luch-1 multi-window events are temporal replications, not independent objects.

### 3.2 Placebos (civil EO controls)

TERRA, AQUA, Landsat-8, NOAA-18/20 (and calendar-matched windows).  
**Excluded from primary placebo set:** Starlink / active mega-constellation (station-keeping confounder).

### 3.3 Training normality (IF)

Roles **baseline + asset** only; exclude commercial constellation purpose from IF train.

---

## 4. Model & features (pre-specified)

| Item | Spec |
|------|------|
| Detector | Isolation Forest (`n_estimators`≥120, `random_state=42`) |
| Score | \(\mathrm{clip}(0.5 - \mathrm{decision\_function}, 0, 1)\) |
| Features | `IFOREST_COLUMNS` (no pair geometry; multi-scale Hurst/Shannon included) |
| Homology | Proxy mode default (`homology_mode` recorded) |
| Priority layer | XGB / pairs / Bob — **not** used for hard-hit Claims A/B |

---

## 5. Walk-forward protocol (pre-specified)

| Parameter | Value |
|-----------|--------|
| `step_days` | 14 |
| `holdout_days` | 3 |
| `hit_window_days` | ±45 around \(t_{\text{peak}}\) |
| Train at fold | windows with `window_end < asof − holdout` on normality anchors |
| Score | target NORAD latest window ≤ asof |

**Hard threshold (pre-specified rule):**

\[
thr = \max\bigl(0.50,\ p_{95}(\text{scores on normality-anchor train windows})\bigr)
\]

Per-orbit thr optional for operations; **primary paper table uses thr = 0.50** for comparability, and reports calibrated thr in sensitivity appendix.

**Hard hit:** any fold with score ≥ thr inside hit window of \(t_{\text{peak}}\).

---

## 6. Primary endpoints (pre-specified)

1. Hard-hit rate interest vs placebo  
2. Mean (and distribution) of **max anomaly score** per event  
3. Mean **pre-peak anomaly mean**  
4. Mann–Whitney U one-sided: interest max scores > placebo max scores  
5. Gap: \(\overline{\max}_{I} - \overline{\max}_{P}\)

**Figures (pre-specified):** pre-peak score curves per event (score vs asof, vertical line at \(t_{\text{peak}}\)).

---

## 7. Analysis code (reproducible)

```bash
python scripts/run_anomaly_monitor.py train-baseline --holdout-days 1
python scripts/run_paper_validation.py --run-wf --threshold 0.50
python scripts/plot_prepeak_curves.py
```

Artifacts:

- `data/alerts/paper_validation_latest.json`  
- `docs/paper/RESULTS_TABLES.md`  
- `docs/paper/figures/prepeak_*.png`  
- `docs/paper/LIMITATIONS.md`  

---

## 8. What is *not* pre-registered as success

- XGBoost accuracy  
- Soft hit @ 0.45  
- Mean lead-time days as “forecast skill”  
- Intent / espionage ground truth  

---

## 9. Amendments

Any change to §3–§6 after first full paper run must be labeled **post-hoc** in the manuscript.

| Date | Amendment | Reason |
|------|-----------|--------|
| — | — | — |

---

*Pre-registration locks the analysis plan for Claims A+B. Implementation lives in `src/walkforward.py`, `src/doctrine.py`, `src/calibration.py`, `scripts/run_paper_validation.py`.*
