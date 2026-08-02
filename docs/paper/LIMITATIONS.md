# Limitations (paper section draft)

This section is intended for direct reuse (with light editing) in a manuscript.

---

## Sample size and dependence

The interest panel remains **small in unique objects**. Even after expanding citable NORADs on the military-first watchlist, several events still reuse the same satellite (notably Luch / Olymp-K 1, NORAD 40258) across calendars. Those windows are **temporal replications**, not independent draws from a population of spacecraft. All headline tables must report **n_events** and **n_unique_norads**. Mann–Whitney and similar tests are reported as **supporting separation under small N**, not as definitive population inference.

## Open-source anchors are not classified labels

Public report dates \(t_{\text{peak}}\) (Gunter, CSIS, SWF fact sheets, press, dual-use catalog class notes) are **weak external anchors**. They support a claim that quant noise **co-occurs with periods of publicly discussed atypical operations**. They do **not** establish hostile intent, mission purpose, or classified ground truth. Dual-use recon / PNT cases are regime tests of military-interest classes, not proof of specific missions.

## Detection of elevated regime vs ramp-before-report

Many interest events show **high `first_fold_hit` rates** and **near-zero or negative `noise_ramp`**. The supported interpretation is **persistent elevated noise level** relative to normality anchors and placebos—not a universal early-warning ramp that “predicts” the media date. Lead-time statistics are descriptive of the analysis window design when the series is already elevated at window open.

## TLE quality and sampling

Two-line elements are public, sparse, and noisy. Features are computed on reconstructed series (including geometric proxies for topology). Results are sensitive to epoch density, TLE age, and station-keeping vs measurement artifact. Data-quality gates reduce but do not eliminate this risk.

## Model and feature choices

Isolation Forest scores depend on contamination, feature set, and which objects define normality. Training on **baseline+asset** (excluding suspects and commercial mega-constellations) is deliberate military doctrine; alternative normality definitions would change scores. Multi-scale Hurst/Shannon capture persistence structure but remain **estimators on short windows**. Homology / Chern–Simons terms are **proxies**, not full TDA on true ephemerides.

## Placebo design

Civil EO placebos (TERRA, AQUA, Landsat, NOAA) are the primary quiet controls. **Active constellation** objects can hard-hit due to station-keeping and are excluded from the primary placebo set; using them as controls would inflate false “FPR” unrelated to the military product focus.

## Priority layer out of scope for Claims A/B

XGBoost weak labels, fuzzy fusion, pair geometry, and LLM briefing affect **operator priority**, not the hard-hit definition of Claims A/B. High XGBoost accuracy measures agreement with a heuristic label function and must not be cited as detection proof.

## External validity

Results apply to a **curated 24-NORAD military-first watchlist** with multi-year history, not the full public catalog. Generalization to other regimes, nations, or orbit classes requires larger N and prospective scoring.

## Ethics

Analyses use **public data only**. The system is framed as research / SDA attention tooling, not as automated targeting or kinetic decision support.

---

*Generated as part of the Athena-SDA paper pack. Keep this language when expanding N or re-running walk-forward.*
