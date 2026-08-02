# Relatório de Discussão — ML & Dados (Athena-SDA)

**Propósito:** documento de trabalho para debate entre equipe/IA sobre as melhorias de ML e dados.
**Objetivo do projeto (âncora da decisão):** *detecção quantitativa de ruído orbital com ML + validação walk-forward honesta, em arquitetura inspirada nas patentes Palantir* (micro-modelos hot-swap · DAG Data→Inference · LLM pós-quant · ontology board).
**Regra de ouro do consenso:** toda mudança deve fortalecer (a) a história científica do walk-forward, (b) a reprodutibilidade, (c) a conexão patente→módulo. Nada que enfraqueça a honestidade vale a pena, mesmo que aumente acurácia.

---

## 0. Onde estamos (fatos verificados em 2026-07-31)

| Item | Estado atual |
|------|--------------|
| Dados | 249.580 épocas, 24 NORADs, 2014-01-01 → 2026-07-27, clima espacial GFZ real (4.589 dias) |
| Walk-forward | 5/5 hard hits interesse, 0/3 placebos (limiar 0.50), mean max 0.603 vs 0.477 |
| Porém | 4/5 eventos: `first_hit` no **primeiro fold possível**; `noise_ramp` ≈ 0 ou negativo |
| XGBoost | ~95% acc, mas rótulo é função determinística das mesmas features (circular) + split aleatório |
| Pipeline | IF monitor sobrescreve IF do pipeline (joblibs idênticos); RKHS degenerada (constante 1.0) |
| UI | Frontend React consome `risk_report_latest.json` real; demo de trilhas no globo é estática |

---

## 1. O que NÃO está em discussão (consenso já formado)

1. **Manter a postura honesta** — rótulos são "weak labels", acurácia ≠ prova de intenção hostil.
2. **Manter o protocolo past-only** do walk-forward (cutoff − holdout) — sem look-ahead.
3. **Remover o Streamlit demo** — já feito; React é a única UI.
4. **IF mede "estranheza da série do objeto"**; distância/coint ficam fora do IF (entram no XGB).

---

## 2. Pontos em aberto (ordenados por prioridade de consenso)

### P0-1 · A narrativa do walk-forward: "lead-time" vs "persistência"

**Problema:** o README vende "~201 dias de lead-time médio". Os dados mostram outra coisa:
- `luch1_intelsat_2015`: first_hit no fold 1, ramp **+0.0017** (plano)
- `luch1_intelsat_mid2015`: ramp **−0.033** · `sy12_geo_rpo_2021_22`: ramp **−0.0255** · `luch2_trailing_2023`: ramp **−0.0327**
- O que o walk-forward prova: **nível** anômalo persistente (média pré-pico 0.52 ≥ 0.50), não **subida** antes do reporte.

**Opções de consenso:**
- **A (recomendada):** reescrever a narrativa — "os objetos de interesse eram estatisticamente ruidosos **desde o início da janela**, em nível que os placebos não alcançam". Trocar a métrica de "lead_time" por "n_folds acima do limiar antes do pico" e "nível médio pré-pico vs placebo".
- B: exigir rampa real (`noise_ramp ≥ δ`) para contar "hit" — destrói o 5/5 e a demo.
- C: manter como está — risco de um avaliador técnico notar a contradição e desqualificar tudo.

**Recomendação Athena:** A, sem exceção. Honestidade aqui é o único ativo defensável.

**Pergunta para a outra IA:** *O lead-time pode ser defendido como "primeira vez que cruzou o limiar dentro da janela", mesmo sendo o primeiro fold? Ou devemos tratar como detecção de nível desde t_start?*

---

### P0-2 · XGBoost circular + split aleatório = acurácia sem significado

**Problema:** `src/models.py:273-337` (`label_features_for_threat`) cria o rótulo a partir das MESMAS features que o XGB consome (distância, ΔSMA, Hurst, coint, anomaly_score). O split é aleatório sobre janelas sobrepostas (step=5) do mesmo satélite → vazamento entre janelas vizinhas. A acc ~95% diz "o modelo aprendeu a função que criou o rótulo".

**Opções:**
- **A (recomendada):** split **temporal com purga** (treino < corte, teste > corte + gap) e reportar métricas por classe; ou
- **B:** abandonar a acurácia como métrica pública; XGB vira só "calibrador de prioridade" pós-IF (alinhado à patente 296 etapa ② quant → ④ score);
- C: manter com nota de rodapé.

**Recomendação Athena:** A + B em conjunto — o XGB sobrevive como peça de prioridade, mas o dashboard não exibe mais "accuracy 94.79%" sem a ressalva. A validação científica principal **é e deve continuar sendo o IF walk-forward**.

**Pergunta:** *Vale investir em treinar XGB com rótulos baseados em eventos públicos reais (anos 2014-2026, t_peak ± janela) em vez de heurística? Qual o tamanho mínimo de rótulos para isso não virar overfit?*

---

### P0-3 · IF do monitor sobrescreve IF do pipeline

**Problema:** `src/anomaly_monitor.py:346-347` grava o IF do monitor **por cima de** `isolation_forest.joblib` (usado pelo XGB). Rodar `train-baseline` muda silenciosamente o modelo do pipeline.

**Opções:**
- **A (recomendada):** arquivos separados + metadados de versão (n_windows, cutoff, hash do schema de features) — conversa direta com a patente 070 (hot-swap de micro-modelos versionados: `if_baseline_{asof}.joblib`).
- B: só separar os arquivos, sem versionamento.

**Recomendação Athena:** A, é barato e tira um bug silencioso + adiciona a feature de patente que já está marcada como "não implementada" no checklist.

**Pergunta:** *Model registry mínimo: vale um `models/registry.json` (métricas, data de treino, features usadas) ou é overhead para o hackathon?*

---

### P0-4 · RKHS degenerada no treino do monitor

**Problema:** `src/models.py:223-225` — sem `reference_matrix`, usa `np.zeros((1,10))` → `spectral_anomaly_rkhs` = **1.0 constante** em todas as janelas de treino (confirmado no CSV de features). Feature no vetor, zero informação.

**Opções:**
- **A (recomendada):** passar `reference_matrix` real (média/covariância de janelas passadas) em `build_feature_windows`; ou
- B: remover RKHS das colunas do IF até ter referência real.

**Recomendação Athena:** A se simples de plugar; senão B (honestidade: não pagar para ter feature morta). Reavaliar se o RKHS contribui além das features já existentes (ablação).

**Pergunta:** *O RKHS adiciona capacidade de detecção marginal real acima de Shannon+Hurst+CUSUM+ADF? Se sim, com qual reference_matrix?*

---

### P1-1 · Separação placebo é fina demais

**Problema:** placebos com max 0.46–0.49 (soft hits 2/3 no limiar secundário 0.45); média placebo 0.4765, a 0.025 do limiar 0.50. Só 3 placebos (2 NORADs) e 5 eventos para 3 NORADs de interesse.

**Opções:**
- **A (recomendada):** expandir painel — +4-6 eventos e +5-8 placebos (baselines civis diversos: LEO/GEO/MEO) no mesmo calendário; reportar distribuições (não só hit/miss) e um teste simples (ex.: quantil 95% do placebo vs limiar).
- B: baixar limiar para 0.45 — NÃO (piora a história).
- C: aceitar e reportar a fragilidade como limitação.

**Recomendação Athena:** A. Dados reais existem até 2026-07-27; rodar mais folds é barato. Isso é o que mais fortalece a validação com menos código novo.

**Pergunta:** *Qual a métrica estatística mais honesta para "separação" com n pequeno: teste de permutação sobre folds, ou AUC do score pré-pico (interesse vs placebo) por evento?*

---

### P1-2 · Reproducibilidade: dependências e determinismo

**Problema:** `requirements.txt` sem pinagem; `ripser`/`sgp4` comentados — a feature de homologia H0/H1 **muda silenciosamente** entre máquinas com/sem ripser (fallback proxy em `engine.py:108-128`). Seeds fixas (42) existem, bom.

**Opções:**
- **A (recomendada):** pinar versões mínimas (`>=x.y,<x.y+1`), documentar que o fallback sem ripser é o canônico **ou** instalar ripser em todos os ambientes, e registrar no artefato qual modo foi usado.
- B: só documentar.

**Recomendação Athena:** A. Sem isso, os números do walk-forward não são reproduzíveis por um juiz.

**Pergunta:** *Vale incluir um `pip freeze > requirements.lock` versionado, ou a faixa semântica é suficiente para um hackathon?*

---

### P1-3 · Bugs conhecidos de produção (auditoria 2026-07-26)

| Bug | Local | Efeito | Consenso proposto |
|-----|-------|--------|-------------------|
| Fuzzy crash `dist > 500 km` | `src/fuzzy.py` | retorna 0.0 silencioso | Clamp `min(dist, 500)` + manter try/except como fallback |
| Kolmogorov inflado em série curta | `src/engine.py` | constante vira "complexa" | Guard `len < 10 → 0.0` |
| Cointegração fora de sincronia | `src/pair_score.py::_align_series` | coint em épocas diferentes → falso positivo | Alinhar por timestamps (merge assíncrono) |
| `tle_age_hours` congelado no parquet | `src/tle_store.py` | idade do TLE desatualiza com o tempo | Recalcular no load (`tle_age_hours_at` já existe em models.py:80-113) |
| Mandelbrot div/0 | `src/engine.py` | crash raro | Guard `denom ≈ 0 → 0.0` |
| Hurst enviesado (poucos lags) | `src/engine.py:48-78` | ISS ~0.9, limiar 0.6 pouco discriminativo | Avaliar Hurst via R/S completo ou ADF como substituto |

**Pergunta:** *Concorda que esses 6 são correções obrigatórias antes de qualquer feature nova? Há algum outro bug crítico que a auditoria perdeu?*

---

### P1-4 · Patentes → gaps de implementação (checklist)

| Patente | Gap atual | Consenso proposto |
|---------|-----------|-------------------|
| 070 (Meta-Constellation) | micro-modelos versionados por `asof`; model registry | Ver P0-3 |
| 296 (LLM+GIS) | etapa ④ "score pós-LLM" não explícita; Bob não cita evento walk-forward | Bob passa a citar "padrão compatível com {source}" quando há match temporal — **nunca** reescreve o score quant |
| 514 (Sensor DAG) | contratos Data API/Inference API formais (JSON Schema) | Documentar schema de `risk_report_latest.json` já existente (docs/SCHEMA_RISK_REPORT.md) e versionar |
| 265 (Time-series geo) | sem decimação RDP no globo; sem export de "tile" do evento | Export CSV/JSON da curva de score do walk-forward |
| 011 (Ontology) | cross-filters role × country × threat no board; histogramas | Feature de UI barata, alto impacto visual |

**Pergunta:** *Quais gaps de patente têm mais valor de demonstração para os juízes: hot-swap versionado, Bob com citação de evento, ou cross-filters no board?*

---

### P2 · Ambicioso (não bloqueia o hackathon)

1. **SGP4 real para TCA** (distância sincronizada no tempo em vez de grade de anomalia verdadeira) — `sgp4` já listado como opcional.
2. **Dataset 50+ satélites** — mais baseline para o IF e mais eventos de walk-forward.
3. **Trilhas do globo derivadas do TLE real da watchlist** em vez do catálogo demo `athena-tracks.ts` — fecha a lacuna "UI ↔ pipeline real".
4. **Bob real (watsonx/Granite)** com fallback local — já existe stub; ligar de verdade.
5. **Ablação de features** — medir contribuição marginal de cada bloco do engine (Shannon, Hurst, CUSUM, RKHS, homologia, Chern-Simons) ao IF; cortar as que não contribuem (defensável: "temos 34 features, mas só 20 carregam informação" é mais forte que "temos 34").

**Pergunta:** *Qual destes 5 gera mais valor para a avaliação? Proponho priorizar (2) → (3) → (1), e deixar (4)/(5) como extras.*

---

## 3. Dados — pendências de higiene

| Item | Estado | Ação |
|------|--------|------|
| `watchlist.json` | mojibake em descrições ("caA�ar", "A�ncora") | Regenerar com UTF-8 |
| PT/EN misturado | `training_metrics.json`, `wf_analysis_new_ml.json`, erros em PT (`walkforward.py:478`) | Migrar para EN (o resto do repo já é EN) |
| Docs duplicados/desatualizados | `SETUP_LINUX.md` tem duas seções "4"; `ml_improvements_step_by_step.py` não aplica à versão atual | Limpar e marcar como obsoleto |
| Artefatos duplicados | `data/alerts/reports/*.html` e `src/frontend/public/reports/*.html` são cópias | Manter sync script como única fonte de cópia (já existe .sh + .ps1) |

---

## 4. Formulário de consenso (preencher após o debate)

| # | Ponto | Opção escolhida (A/B/C) | Justificativa | Esforço | Bloqueia demo? |
|---|-------|-------------------------|---------------|---------|----------------|
| P0-1 | Narrativa walk-forward | | | | |
| P0-2 | XGB circular/split | | | | |
| P0-3 | Joblibs separados/versionados | | | | |
| P0-4 | RKHS | | | | |
| P1-1 | Placebos & eventos | | | | |
| P1-2 | Pinar dependências | | | | |
| P1-3 | 6 bugs de produção | | | | |
| P1-4 | Gaps de patente | | | | |
| P2-1..5 | Roadmap ambicioso | | | | |
| D1..D4 | Higiene de dados/docs | | | | |

**Critérios de decisão (ordem):** (1) honestidade da validação · (2) reprodutibilidade · (3) alinhamento patente→módulo · (4) esforço × impacto para os juízes.

---

## 5. Prompt sugerido para a outra IA

> "Revise este relatório e a base `D:\Athena-SDA` (src/engine.py, src/models.py, src/anomaly_monitor.py, src/walkforward.py, docs/references/*). Nosso objetivo é validação científica honesta de detecção de ruído orbital (patentes Palantir como inspiração arquitetural, não como reivindicação). Concorde ou discorde de cada ponto P0/P1 com evidência do código, aponte riscos que perdemos, e preencha o formulário de consenso com a opção e justificativa. Não proponha mudanças que sacrifiquem a honestidade do walk-forward por acurácia."

---

*Athena-SDA · Documento de trabalho para consenso de ML & dados.*

---

## 6. Status de execução (2026-08-01)

Implementado no código + retreino com ~249.580 épocas (2014–2026):

| Item | Estado |
|------|--------|
| P0-1 Narrativa | README + PoC HUD + `docs/FOUNDATION_QUANT_VALIDATION.md` |
| P0-2 XGB temporal+purga | `split_mode=temporal_purge_14d`; disclaimer em `training_metrics.json` |
| P0-3 Joblibs + registry | monitor IF ≠ pipeline IF; `models/registry.json` |
| P0-4 RKHS fora do IF | 33 colunas IF; CSV treino sem RKHS constante |
| P1-2 homology_mode | `proxy` canónico; meta + registry |
| P1-3 guards | Kolmogorov, Hurst R/S, Mandelbrot, fuzzy dist, coint asof, tle_age |
| Smoke | `scripts/smoke_test.py` OK |
| Walk-forward re-run | 5/5 hard interest · 0/3 hard placebo · `first_fold_hit_rate=0.8` · `mean_noise_ramp≈-0.018` · pre-peak mean 0.52 vs 0.38 |

**Lote B (2026-08-01):**
| Item | Estado |
|------|--------|
| Placebos LEO/MEO + NORADs interesse independentes | `events_walkforward.json` v3 (16 events) |
| Ablação de blocos | `scripts/run_feature_ablation.py` → `feature_ablation_latest.json` |
| Bob cita cases sem reescrever score | `src/bob.py` `tool_get_case_study_citations` |
| Schema / foundation | `SCHEMA_RISK_REPORT.md` + `FOUNDATION_QUANT_VALIDATION.md` |
