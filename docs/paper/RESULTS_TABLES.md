# Athena-SDA — Paper results tables (Claims A + B)

*Generated: 2026-08-11T03:38:51.577635+00:00*

Protocol: [`PROTOCOL_PREREGISTRATION.md`](PROTOCOL_PREREGISTRATION.md) · Limitations: [`LIMITATIONS.md`](LIMITATIONS.md) · Figures: [`figures/`](figures/)

## Formal claims (expanded unique-N panel)

**Claim A:** Military-interest watchlist objects with open-source / dual-use anchors exhibit elevated past-only IF scores relative to civil EO placebos (report unique NORADs).
- Supported: **True** · n_events=11 · n_unique_norads=9 · hard hit=0.6363636363636364 · mean max=0.6163604240511811

**Claim B:** Civil EO placebos under the same past-only protocol show lower scores and hard-hit rate near zero at thr=0.50 (primary table).
- Supported: **True** · hard hit=0.0 · mean max=0.4566938352295559 · p95=0.49528968203893736

## GEO headline subset (abstract)

- Claim A GEO supported: **True** · hard hit=1.0 · mean max=0.7162078827827233 · unique NORADs=3
- Claim B GEO panel placebos: hard hit=0.0 · mean max=0.4566938352295559
- Gap (GEO): **0.25951404755316737** · MW p=0.0012626262626262627

## Separation (expanded panel)

- Mean max gap (interest − placebo): **0.15966658882162515**
- Mann–Whitney (max scores, H1 interest>placebo): p=0.010212418300653595
- Mann–Whitney (pre-peak means): p=0.007698592257415786

## Per-event table

| event_id | group | NORAD | hard hit | max score | pre-peak mean | noise_ramp | first_fold_hit |
|----------|-------|-------|----------|-----------|---------------|------------|----------------|
| luch1_intelsat_2015 | interest | 40258 | True | 0.6994397355890178 | 0.6401717322687852 | -0.036962367244377514 | True |
| luch1_intelsat_mid2015 | interest | 40258 | True | 0.7239896838491957 | 0.6633578711802799 | -0.024827949472093436 | True |
| luch1_athena_fidus_2018 | interest | 40258 | True | 0.724499943970675 | 0.6387549633573458 | 0.0577464784138052 | True |
| sy12_geo_rpo_2021_22 | interest | 50321 | True | 0.7115291947428062 | 0.5744838267633248 | -0.08428624195305856 | True |
| luch2_trailing_2023 | interest | 55841 | True | 0.7215808557619215 | 0.6683819682236152 | -0.0071160408554235 | True |
| shiyan7_experimental_2015 | interest | 39208 | False | 0.5532059189950747 | 0.4227472632799976 | -0.0021969155300380905 | False |
| yaogan29_recon_2020 | interest | 41038 | False | 0.385323521806205 | 0.3563564801061482 | -0.00707239889411021 | False |
| tianhe_css_assembly_2021 | interest | 48274 | True | 0.7178200433998324 | 0.5896092036664469 | -0.015709338693742803 | True |
| yaogan3_recon_2016 | interest | 32289 | False | 0.4196853014348631 | 0.3806775718992761 | -0.0005464947410252496 | False |
| cosmos2550_military_leo_2022 | interest | 48865 | False | 0.6089065798034501 | 0.4398318187584509 | -0.04562735246710853 | False |
| beidou3_m11_meo_2019 | interest | 43603 | True | 0.51398388520995 | 0.4436507988690216 | 0.027500192988811234 | False |
| placebo_terra_2015 | placebo | 25994 | False | 0.4697179134033911 | 0.39275272936657823 | 0.013388152694471078 | False |
| placebo_terra_2018 | placebo | 25994 | False | 0.45725625394911523 | 0.36728009314606447 | 0.019786653661025444 | False |
| placebo_aqua_2015 | placebo | 27424 | False | 0.4896768481291527 | 0.43059714440556784 | -0.020973657094002285 | False |
| placebo_landsat8_2018 | placebo | 39084 | False | 0.4588835246192336 | 0.3755116320482601 | 0.0223601194157369 | False |
| placebo_noaa20_2023 | placebo | 43013 | False | 0.4976951822859879 | 0.395731424993864 | -0.010017286927013147 | False |
| placebo_noaa18_2021 | placebo | 28654 | False | 0.42297074567457904 | 0.3884373438270258 | 0.012143333450670202 | False |
| placebo_starlink_2023 | placebo | 44714 | True | 0.5549326529912296 | 0.46909937862649903 | -0.013139115525737544 | False |
| placebo_gps_meo_2018 | placebo | 28874 | True | 0.5394571034754128 | 0.45348679360726213 | 0.016719361461223603 | False |
| placebo_aqua_2020 | placebo | 27424 | False | 0.4006563785454318 | 0.3716093235262047 | 0.010974311276753412 | False |

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
