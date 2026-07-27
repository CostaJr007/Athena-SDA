# Melhorias Gemini aplicadas (coerentes)

**Data:** 2026-07-26  
Fonte: `instrucoes_grok_ml_quant.md`, `analise_machine_learning_athena_sda.md`, `auditoria_matematica.md`

## Aplicado

| Item Gemini | Ação no Athena |
|-------------|----------------|
| Treino em TLE real, não só sintético | `train_and_save_models` prioriza `data/history/epochs` |
| Não diluir real com sintético full | Sintético só **threat boost** leve se faltar HOSTIL/SUSPEITO |
| Geometria na feature **e** no label | Distância a assets + coint no extract e em `label_features_for_threat` |
| Score IF unificado | `clip(0.5 - decision_function)` em treino, predict e monitor |
| Custo assimétrico (FN > FP) | `sample_weight` XGB: NORMAL 1 → HOSTIL 5 |
| Contamination IF | 0.08 em history real |
| Backtest pré-report | Walk-forward com `pre_peak_noise` + pares + placebo |
| País/purpose reais (Williams) | Já via catálogo no score; treino history usa `get_meta` |
| Fuzzy dist > 500 + clamp inputs | `fuzzy.py` clip universos; fallback **0.5** (não NORMAL) |
| Kolmogorov séries curtas | `engine.py` len&lt;10 → 0 + header zlib |
| Mandelbrot Hill safe | guarda `log_sum` |
| Cointegração alinhada | `pair_score._align_series` via `merge_asof` ±12h |
| tle_age correto | `tle_age_hours_at(reference_time)`; WF passa **asof**; live usa **now** |
| DQ age | recalcula vs asof/now (não confia em 0.0 do parquet) |

## Não aplicado (fora de escopo / overkill)

- UKF + SGP4 residual full  
- Deep autoencoder / Transformer  
- Ricci Wasserstein full / 32 features  
- Meta acc>92% / recall HOSTIL 100% (não defensável em TLE público)  
- Redesign Streamlit do diagnóstico UI (front = React)

## Walk-forward e “ruído antes do report”

Sim: cada fold treina o IF **só com janelas do passado** (`window_end < asof - holdout`).  
Scores no caminho até `t_peak` medem se o **ruído/desvio** sobe **antes** da âncora pública (Luch/SY/etc.), com placebo Terra/NOAA.
