# Athena-SDA — Paper results tables (Claims A + B)

*Generated: 2026-08-02T00:35:10.392927+00:00*

Protocol: [`PROTOCOL_PREREGISTRATION.md`](PROTOCOL_PREREGISTRATION.md) · Limitations: [`LIMITATIONS.md`](LIMITATIONS.md) · Figures: [`figures/`](figures/)

## Formal claims (expanded unique-N panel)

**Claim A:** Military-interest watchlist objects with open-source / dual-use anchors exhibit elevated past-only IF scores relative to civil EO placebos (report unique NORADs).
- Supported: **False** · n_events=11 · n_unique_norads=9 · hard hit=0.5454545454545454 · mean max=0.5712291638135677

**Claim B:** Civil EO placebos under the same past-only protocol show lower scores and hard-hit rate near zero at thr=0.50 (primary table).
- Supported: **True** · hard hit=0.0 · mean max=0.4619792951273824 · p95=0.49550387121076866

## GEO headline subset (abstract)

- Claim A GEO supported: **True** · hard hit=1.0 · mean max=0.6512469606429668 · unique NORADs=3
- Claim B GEO panel placebos: hard hit=0.0 · mean max=0.4619792951273824
- Gap (GEO): **0.18926766551558444** · MW p=0.0012626262626262627

## Separation (expanded panel)

- Mean max gap (interest − placebo): **0.1092498686861853**
- Mann–Whitney (max scores, H1 interest>placebo): p=0.010212418300653595
- Mann–Whitney (pre-peak means): p=0.004147812971342383

## Per-event table

| event_id | group | NORAD | hard hit | max score | pre-peak mean | noise_ramp | first_fold_hit |
|----------|-------|-------|----------|-----------|---------------|------------|----------------|
| luch1_intelsat_2015 | interest | 40258 | True | 0.6277594743086112 | 0.5698061896892279 | -0.012130177133332865 | True |
| luch1_intelsat_mid2015 | interest | 40258 | True | 0.6748457829496773 | 0.5889999321284898 | 0.006587521039351563 | True |
| luch1_athena_fidus_2018 | interest | 40258 | True | 0.6718680301965697 | 0.5600459347921776 | 0.010931974717967141 | True |
| sy12_geo_rpo_2021_22 | interest | 50321 | True | 0.6233424703009158 | 0.5292171883677838 | -0.04829044357795087 | True |
| luch2_trailing_2023 | interest | 55841 | True | 0.65841904545906 | 0.5864114891165367 | -0.04001115704868885 | True |
| shiyan7_experimental_2015 | interest | 39208 | False | 0.4895448985041626 | 0.4312652909998309 | 0.04696268440445994 | False |
| yaogan29_recon_2020 | interest | 41038 | False | 0.41541292149626874 | 0.3539842044336193 | -0.015156148706023276 | False |
| tianhe_css_assembly_2021 | interest | 48274 | True | 0.6436651876060406 | 0.5564528623808714 | -0.015380639310549782 | True |
| yaogan3_recon_2016 | interest | 32289 | False | 0.41948113017002464 | 0.379531325843753 | -0.013491288848050065 | False |
| cosmos2550_military_leo_2022 | interest | 48865 | False | 0.555051397599939 | 0.4431331467662084 | -0.043603677864128665 | False |
| beidou3_m11_meo_2019 | interest | 43603 | False | 0.5041304633579746 | 0.46217320960251923 | -0.006867042077719154 | False |
| placebo_terra_2015 | placebo | 25994 | False | 0.48116966627445545 | 0.3946819536712406 | 0.012064905436680706 | False |
| placebo_terra_2018 | placebo | 25994 | False | 0.5016471018977601 | 0.3761247570339987 | 0.022689808289846958 | False |
| placebo_aqua_2015 | placebo | 27424 | False | 0.47406315843471664 | 0.42942676619685916 | -0.019593964344064352 | False |
| placebo_landsat8_2018 | placebo | 39084 | False | 0.4596710838230848 | 0.36669522879629324 | 0.03144150626562903 | False |
| placebo_noaa20_2023 | placebo | 43013 | False | 0.4637039717585005 | 0.39077746407914815 | -0.016379624798938786 | False |
| placebo_noaa18_2021 | placebo | 28654 | False | 0.45850509855638827 | 0.3842710254884582 | -0.01678114264970182 | False |
| placebo_starlink_2023 | placebo | 44714 | True | 0.5549326529912296 | 0.46909937862649903 | -0.013139115525737544 | False |
| placebo_gps_meo_2018 | placebo | 28874 | True | 0.5394571034754128 | 0.45348679360726213 | 0.016719361461223603 | False |
| placebo_aqua_2020 | placebo | 27424 | False | 0.395094985146771 | 0.3513935041479014 | 0.0056903461645421705 | False |

## Methods (one paragraph for article)

{'data': 'Public TLE history (~2014–2026) + GFZ F10.7/Ap/Kp', 'features': 'Keplerian + multi-scale Hurst/Shannon + CUSUM + Kolmogorov + SW', 'model': 'Isolation Forest trained on baseline+asset past windows only', 'protocol': 'Walk-forward: at each asof, fit IF on past only; score target window', 'priority_layer': 'XGB weak labels + suspect×asset pairs (not used for Claim A/B hits)', 'doctrine': 'military_first_sda', 'preregistered': True}

## Limitations

- See docs/paper/LIMITATIONS.md for full manuscript section.
- Report n_events and n_unique_norads; Luch-1 multi-window is dependent.
- Expanded LEO/MEO cases may not hard-hit; GEO headline remains strongest A+B.
- first_fold_hit / noise_ramp~0 ⇒ persistent level, not ramp-to-news.
- Open-source anchors are weak external labels, not classified intent.
- TLE noise; homology/CS are proxies.

## Suggested article outline

- 1. Introduction: SDA attention, public TLE, military-first watchlist
- 2. Related work: SSA, anomaly detection, weak open-source cases
- 3. Methods: quant features, IF past-only, doctrine roles, calibration (preregistered)
- 4. Case design: unique interest NORADs + civil EO placebos
- 5. Results: Claims A+B tables, pre-peak figures, MW tests, GEO headline
- 6. Discussion: persistence vs ramp, orbit class, operational priority layer
- 7. Limitations and ethics
- 8. Conclusion
