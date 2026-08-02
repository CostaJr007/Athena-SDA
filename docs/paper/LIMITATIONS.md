# Limitations (paper section draft)

## Sample size and dependence

The interest panel remains **small in unique objects**. Multi-window use of Luch / Olymp-K 1 (NORAD 40258) is temporal replication, not independent spacecraft draws. Tables report **n_events** and **n_unique_norads**. Mann–Whitney and similar tests support separation under small \(N\); they are not definitive population inference.

## Open-source anchors

Public report dates \(t_{\mathrm{peak}}\) (Gunter, CSIS, SWF fact sheets, press, dual-use catalog notes) are **external evaluation anchors**. They support co-occurrence of quant noise with periods of publicly discussed atypical operations. Dual-use recon / PNT cases test military-interest class regimes.

## Elevated regime vs ramp structure

Many interest events show high `first_fold_hit` rates and near-zero or negative `noise_ramp`. The supported reading is **persistently elevated noise level** relative to normality anchors and placebos. Lead-time statistics describe window design when the series is already elevated at window open.

## TLE quality and sampling

Two-line elements are public, sparse, and noisy. Features use reconstructed series (including geometric topology proxies). Results depend on epoch density and TLE age. Data-quality gates reduce but do not eliminate this risk.

## Model and feature choices

Isolation Forest scores depend on contamination, feature set, and normality anchors. Training on **baseline+asset** (excluding suspects and commercial mega-constellations) is intentional doctrine. Multi-scale Hurst/Shannon capture persistence on short windows. Homology / Chern–Simons terms are **proxies**, not full TDA on true ephemerides.

## Placebo design

Civil EO placebos (TERRA, AQUA, Landsat, NOAA) are the primary quiet controls. Active constellation objects can hard-hit from station-keeping and are excluded from the primary placebo set for Claims A+B.

## Priority layer scope

XGBoost weak labels, fuzzy fusion, pair geometry, and LLM briefing affect **operator priority**, not the hard-hit definition of Claims A+B.

## External validity

Results apply to a curated 24-NORAD military-first watchlist with multi-year history. Generalization requires larger \(N\) and additional orbit regimes.

## Ethics

Analyses use **public data only**. The system is research / SDA attention tooling for noise analysis and alerts.
