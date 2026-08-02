# Consenso Fechado — Execução para Grok (Athena-SDA)

**Mandato (âncora de toda decisão):** tornar o PoC *auditável e irrefutável* — não aumentar acurácia. A prova é: separação de regime anômalo (interesse vs placebo) com walk-forward past-only, features determinísticas sem bugs, modelos versionados, N experimental maior, e narrativa honesta que antecipe as objeções de um revisor técnico.

**Objetivo explícito:** NÃO treinar modelo novo "mais forte". NÃO substituir weak labels por event labels. NÃO inventar lead-time heroico.

---

## Passo 0 — Snapshot baseline (obrigatório, antes de QUALQUER mudança de código)

O executor deve salvar os números atuais ANTES de tocar no código, para depois provar "corrigimos bugs e a conclusão se manteve" (ou detectar mudança de conclusão antes de um juiz).

```bash
cd D:\Athena-SDA
python scripts/run_walkforward.py summary > docs/baseline_wf_summary_2026-07-31.txt
python scripts/run_walkforward.py run --events luch1_intelsat_2015,placebo_terra_2015 --step-days 14 --holdout-days 3
```

Registrar em `docs/baseline_wf_snapshot.json` (copiar do JSON gerado):
- mean max score (interesse e placebo), pre_peak_mean, noise_ramp por evento
- first_hit / asof por evento
- p95 do score pré-pico placebo
- hash SHA-256 de `models/*.joblib` atuais
- sha256 de `data/features/train_windows_latest.csv` (se existir)

Depois de cada lote de mudanças, re-rodar e comparar. **Se a conclusão mudar, parar e reportar antes de continuar.**

---

## Lote A — Prova crível (implementar nesta ordem)

### A1. Métricas honestas no walk-forward (JSON é a fonte da verdade)

**Arquivo:** `src/walkforward.py` (+ resumo em `scripts/run_walkforward.py summary`)

Adicionar ao JSON de cada evento (obrigatório, sempre presente):

```json
{
  "first_hit": { "asof": "...", "score": ..., "fold_index": 0, "first_fold_hit": true },
  "pre_peak_noise": {
    "pre_peak_anomaly_mean": ...,
    "pre_peak_anomaly_max": ...,
    "noise_ramp": ...,          // late_pre_peak_mean - early_pre_peak_mean
    "n_pre_peak_folds": ...,
    "n_folds_above_thr_pre_peak": ...,
    "p95_pre_peak": ...
  },
  "lead_time_days": null        // SOMENTE se first_fold_hit == false; caso contrário null
}
```

- `lead_time_days` deve ser `null` (não calculado) quando `first_fold_hit == true`. Semântica: "dias entre primeira observação ≥ thr e t_peak, dentro da janela definida" — nunca "previsão do evento".
- `noise_ramp` pode ser ~0 ou negativo. **Não "corrigir"** o valor — é o ponto honesto.
- O summary final (`walkforward_summary.json`) deve incluir uma tabela: evento × {first_fold_hit, pre_peak_mean, noise_ramp, n_folds_above_thr, lead_time_days}.

**Critério de aceite:** nenhum JSON de evento contém `lead_time_days` não-null quando o hit foi no primeiro fold.

### A2. Separar joblibs do monitor vs pipeline + registry.json

**Arquivo:** `src/anomaly_monitor.py:346-347`

- REMOVER a linha que grava o IF do monitor em `models/isolation_forest.joblib` (o IF do pipeline **não** pode ser sobrescrito pelo monitor).
- Criar `models/registry.json` (≈30 linhas) com versão mínima:

```json
{
  "schema": 1,
  "models": [
    {
      "name": "isolation_forest_monitor",
      "path": "models/isolation_forest_monitor.joblib",
      "trained_at": "...",
      "n_windows": ...,
      "n_sats": ...,
      "holdout_days": ...,
      "contamination": ...,
      "seed": 42,
      "feature_hash": "sha256 do sorted feature_columns",
      "homology_mode": "proxy|ripser",
      "source": "train_baseline_from_history"
    },
    {
      "name": "isolation_forest_pipeline",
      "path": "models/isolation_forest.joblib",
      "trained_at": "...",
      "feature_hash": "...",
      "source": "train_and_save_models"
    }
  ]
}
```

- O `feature_hash` (sha256 do `sorted(feature_columns)`) deve ser conferido no load: se o hash do joblib não bater com o registry → aviso explícito (não fallback silencioso).
- Escrever o registry no fim de `train_baseline_from_history` e de `train_and_save_models`.

**Critério de aceite:** rodar `train-baseline` NÃO altera `models/isolation_forest.joblib` (comparar sha256 antes/depois).

### A3. RKHS fora do IF (ou com reference real) + ablação IF no mesmo treino

**Arquivo:** `src/models.py:223-225`, `src/anomaly_monitor.py` (build_feature_windows)

- **Decisão:** remover `spectral_anomaly_rkhs` das `IFOREST_COLUMNS` do monitor até existir `rkhs_reference` real (média/cov de janelas NORMAL passadas do mesmo regime/orbit_class). Alternativa aceitável: carregar `models/rkhs_reference.joblib` se existir; senão, feature ausente (não zeros).
- **Ablação leve do IF** no mesmo `train-baseline`: rodar 2 variantes — com e sem o grupo {RKHS} (e se viável, {homologia H0/H1}) — e reportar no registry: separação interesse/placebo (pre_peak_mean gap) e FPR placebo. Critério de contribuição: se remover o grupo NÃO piora separação nem sobe FPR placebo, o grupo fica de fora permanentemente.

**Critério de aceite:** `train_windows_latest.csv` não contém coluna RKHS constante; registry registra resultado da ablação.

### A4. Split temporal + purga no XGB

**Arquivo:** `src/models.py:757-765` (`train_test_split` aleatório)

- Substituir por split temporal com purga: treino = janelas com `window_end < cutoff`, teste = `window_end >= cutoff + purge_days` (purga = 30 dias). As janelas são sobrepostas (step=5) do mesmo satélite — a purga é obrigatória.
- Guardar `cutoff` e `purge_days` no registry.
- Métricas de teste continuam salvas em `models/training_metrics.json` mas **não** devem ser expostas como "prova" no dashboard/README — o campo vira `"role": "internal_priority_calibration"`.

**Critério de aceite:** nenhuma janela de teste tem `window_end` dentro de [cutoff, cutoff+purge]; README/UI não exibem acc como métrica de validação.

### A5. Guards e correções de features (bugs P1-3)

| # | Arquivo | Correção |
|---|---------|----------|
| 1 | `src/fuzzy.py` | Clamp `dist_military = min(dist, 500.0)` (manter try/except como fallback) |
| 2 | `src/engine.py` `calculate_kolmogorov_proxy` | Guard: `len(s) < 10 → 0.0` |
| 3 | `src/pair_score.py` `_align_series` | Alinhar por timestamps (merge/join por época), não "últimos N pontos" |
| 4 | `src/tle_store.py` / load | `tle_age_hours` recalculado no load via `tle_age_hours_at` (já existe em models.py:80-113); parquet armazena epoch, não idade |
| 5 | `src/engine.py` `calculate_mandelbrot_tail_anomaly` | Guard: denominador ≈ 0 → 0.0 |
| 6 | `src/engine.py:48-78` Hurst | Revisar estimador (lags mínimos razoáveis) ou documentar limitação + usar ADF como complemento; NÃO mudar limiar de forma mágica |

**Critério de aceite:** os 6 bugs têm teste ou execução manual documentada; outputs de exemplo nos docs (antes/depois para o fuzzy clamp).

### A6. Smoke tests mínimos (novos arquivos de teste — repo tem ZERO)

Criar `tests/` com pytest (adicionar `pytest` ao requirements):

1. `test_engine.py` — kolmogorov série curta = 0; mandelbrot sem div/0; hurst std=0 não crasha
2. `test_models.py` — `anomaly_score ∈ [0,1]`; `tle_age_hours_at` com timezone (2015 não parece 11 anos velho); fallback de colunas NÃO silencioso (aviso)
3. `test_fuzzy.py` — `dist > 500` não retorna 0.0 por crash silencioso
4. `test_pair_score.py` — cointegração com séries dessincronizadas não produz falso positivo óbvio
5. `test_walkforward_smoke.py` — 1 evento placebo: past-only respeitado (nenhuma janela de treino com end ≥ cutoff)
6. `test_monitor.py` — `train-baseline` não altera `models/isolation_forest.joblib`

**Critério de aceite:** `pytest -q` verde em ambiente limpo; adicionar `pytest` ao `requirements.txt`.

### A7. Dependências + reprodutibilidade

- `requirements.txt`: faixas `>=x.y,<next` nos pacotes principais (pelo menos numpy, pandas, scikit-learn, xgboost, statsmodels, scikit-fuzzy).
- `homology_mode` (`proxy` ou `ripser`) gravado nos artefatos (ver A2) e no summary do WF.
- Documentar que o fallback proxy SEM ripser é o modo canônico, ou instalar ripser em todos os ambientes — escolher UM e registrar.

### A8. Narrativa (escrever POR ÚLTIMO, com números pós-higiene)

**Arquivos:** `README.md` (L12 e tabela de validação), `src/frontend/public/reports/walkforward_poc.html`, `docs/DISCUSSION_ML_DATA_IMPROVEMENTS.md`

Mensagem única: *"Os objetos de interesse eram estatisticamente ruidosos desde o início da janela (nível médio pré-pico ≥ 0.50), em nível que os placebos não alcançam (p95 placebo vs limiar). Rampa ≈ 0 — não afirmamos 'ruído subiu antes do reporte', afirmamos separação de regime persistente + 0/3 placebos."*

Exigências:
- "lead-time ~201 dias" → substituir por: n_folds_above_thr, first_fold_hit, separação p95.
- Tabela de validação com colunas: evento · objetos (NORADs únicos!) · first_fold_hit · pre_peak_mean · noise_ramp · n_folds_above_thr.
- **Risco 40258 explícito:** "5/5 eventos sobre 3 NORADs de interesse (40258 aparece em 2-3 eventos) — dependência de objeto declarada."
- XGB: rotular "priority model / weak labels — não é prova científica".
- Menção de "t_start endógeno" como limitação (janela definida onde se espera atividade).

**Critério de aceite:** ninguém lê "previu o evento" em lugar nenhum do repo.

---

## Constraints (NÃO FAZER)

- ❌ Não treinar modelos novos/maiores para subir acc
- ❌ Não substituir weak labels por event labels (overfit garantido com n pequeno)
- ❌ Não baixar o threshold de hit (fica 0.50)
- ❌ Não excluir 40258 nem alterar `events_walkforward.json` neste lote (expansão = Lote B)
- ❌ Não renomear/mover arquivos do pipeline sem atualizar docs e registry
- ❌ Não commitar `.env`, `node_modules`, caches
- ❌ Não alterar o protocolo past-only do WF
- ❌ Não deletar `data/` nem `models/` existentes

---

## Definition of Done (Lote A completo)

1. `python scripts/run_walkforward.py run` + `summary` rodam com as novas métricas (first_fold_hit, noise_ramp, n_folds_above_thr, lead_time condicional)
2. sha256 de `isolation_forest.joblib` inalterado após `train-baseline`
3. `models/registry.json` existe com feature_hash e homology_mode
4. `train_windows_latest.csv` sem RKHS constante
5. `pytest -q` verde (6 arquivos de teste mínimos)
6. Números do WF re-rodados e comparados com o snapshot do Passo 0 — delta documentado
7. README + PoC sem "lead-time heroico" e com risco 40258 declarado
8. `requirements.txt` com faixas e `pytest`

---

## Lote B (depois, se o Lote A fechar)

- Expandir `events_walkforward.json`: +5–8 placebos (LEO/MEO/GEO, civis diversos), +1–2 interesses em NORAD distinto de 40258
- Reportar: AUC / Mann-Whitney de pre_peak_mean (interesse vs placebo), p95 placebo vs thr 0.50, distribuições (não só hit/miss)

## Lote C (polish)

- Bob cita evento/source do WF (sem reescrever score) · schema versionado do risk_report · trilhas do globo a partir de TLE real da watchlist · ablação XGB pós-split · SGP4 para TCA

---

*Consenso fechado em 2026-07-31 entre relatório Athena-SDA, DeepSeek (opencode) e Grok. Execução: Lote A nesta ordem, com snapshot no Passo 0.*
