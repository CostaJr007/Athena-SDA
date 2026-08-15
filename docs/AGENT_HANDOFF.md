# Athena-SDA — Instruções de Handoff para outra IA

> Documento de continuidade. Objetivo: permitir que um agente de IA autônomo
> **analise o projeto e continue o trabalho** sem o contexto da sessão anterior.
> Leia este arquivo **antes** de mexer no código.

## 1. O que é o projeto

**Athena-SDA** — copiloto *military-first* de Space Domain Awareness (SDA).
Transforma histórico público de TLE (Two-Line Elements) + space weather (GFZ
F10.7/Ap/Kp) em **análise quantitativa de ruído orbital** e **detecção de
micro-anomalias** sobre uma watchlist curada (24 NORADs: asset/suspect/baseline).

Pipeline: `TLE → features quantitativos (engine) → Isolation Forest past-only →
prioridade (XGB/Dempster-Shafer/pares) → risk report JSON → missão board (React/Three.js)`.

Inspiração declarada: **Palantir Gotham/Foundry** — objeto-cêntrico, grafo de
links, ontologia tipada, contratos de schema, lineage/provenance, LLM que
explica mas **não recomputa** scores.

## 2. Estado atual (o que já foi feito)

Rodada seguinte (ops + S6 fechado + fatias T1–T9):

- Cron real (marker como comentário *trailing*, não prefixo que comentava o job).
- `run_daily_ingest.sh` sai 1 se algum stage falha; sync via `.py`.
- UI consome `investigation.v1`; ACK chama FSM (`POST /api/alert-state`).
- Pc/TCA extras em `src/conjunction.py` (não reescrevem `pair_risk`).
- Tipo `Document`, RAG citado em Bob/Granite, what-if, watchlist API, compose.

Nesta rodada anterior foram concluídos:

- **Bugs S0 corrigidos** em `src/anomaly_monitor.py`:
  - snapshot versionado `isolation_forest_monitor_<data>.joblib` (antes usava
    `meta_out` indefinido + `re` sem import → nunca funcionava);
  - `resolve_thresholds()` des-`None` do `--threshold` default (`None` quebrava
    `estimate_anomaly_onset` com `float(None)`).
- **Logging** (`src/logging_setup.py`) + conversão de `except: pass` silenciosos
  nos caminhos críticos.
- **Testes**: 37 testes `pytest` em `tests/` + CI em `.github/workflows/ci.yml`.
- **Empacotamento**: `pyproject.toml`, `requirements-dev.txt`, `Dockerfile`,
  `.dockerignore`.
- **Higiene**: `scripts/sync_frontend_data.py` (substitui `.ps1`/`.sh`) +
  `.gitignore` para artefatos regeneráveis.
- **Produto (S6)**: workflow de ciclo de vida de alertas e provenance/lineage em
  `src/object_layer.py`; harness de validação contínua em
  `scripts/run_continuous_validation.py`.

## 3. Como verificar a saúde do projeto

```bash
cd /run/media/adeilsoncosta/Novo\ volume/Athena-SDA   # ajuste o caminho real

# Testes (rápidos, sem rede)
python -m pytest -q                 # esperado: 57+ passed

# Smoke test do núcleo quant
python scripts/smoke_test.py        # esperado: SMOKE OK

# Compilação
python -m py_compile src/*.py scripts/*.py

# Frontend (typecheck + build)
cd src/frontend && npm run build    # esperado: sucesso (aviso de chunk é conhecido)

# Pipeline diário (requer dados em data/history)
python scripts/run_anomaly_monitor.py status
python scripts/run_anomaly_monitor.py run-daily --skip-if-fresh
python scripts/run_continuous_validation.py
python scripts/compat_refresh.py     # pc/tca + investigation.v1 + sync UI
python scripts/sync_frontend_data.py --quiet
```

## 4. Mapa de arquivos (o que importa)

| Caminho | Papel |
|---------|-------|
| `src/config.py` | Feature schema (`FEATURE_COLUMNS`, `IFOREST_COLUMNS`, `XGB_COLUMNS`) e constantes |
| `src/engine.py` | Motor de features quant (LZ76, DFA, MMD, CUSUM/EWMA, SSA, BOCPD…) |
| `src/models.py` | `extract_satellite_features`, treino IF/XGB, `predict_threat` |
| `src/anomaly_monitor.py` | Loop diário: treina baseline, pontua, alerta |
| `src/object_layer.py` | Camada Gotham-lite: objetos, links, provenance, **workflow de alertas** |
| `src/doctrine.py` | Política de papéis (asset/suspect/baseline) e `classify_military_status` |
| `src/evidence.py` | Fusão Dempster-Shafer (belief/plausibility/conflict) |
| `src/pair_score.py` | Risco suspect×asset (distância + cointegração/DCCA) |
| `src/bob.py` | Copiloto LLM (Granite/watsonx) — tool-calling, briefing |
| `src/ontology.json` | Ontologia tipada (Satellite, Alert, Case, Weather, Evidence) |
| `src/contracts.py` | Validação de schema (`risk_report.v1`, `investigation.v1`) |
| `src/tle_store.py` | Store de épocas (parquet/CSV) + ingesta CelesTrak/HF |
| `scripts/run_anomaly_monitor.py` | CLI principal (argparse) |
| `scripts/run_continuous_validation.py` | Health check de drift/calibração |
| `scripts/sync_frontend_data.py` | Sincroniza artefatos para `src/frontend/public/data` |
| `src/frontend/src/pages/Home.tsx` | **Monólito** da UI (1.272 linhas) |
| `src/frontend/src/lib/globe-engine.ts` | **Monólito** do globo 3D (1.390 linhas) |
| `src/frontend/src/workers/propagator.worker.ts` | Propagador orbital (worker) |
| `tests/` | 50+ testes pytest (S0, object layer, conjunction, RAG, what-if, ops) |
| `docs/ROADMAP_ESTRATEGICO.md` | Cronograma do que **falta** (tracks T1–T9) |

## 5. O que falta (estratégico)

Ver `docs/ROADMAP_ESTRATEGICO.md` para o cronograma completo. Resumo das tracks:

- **T1** Refactor do frontend monólito (`Home.tsx` + `globe-engine.ts`) — **primeiro**, destrava T2/T8.
- **T2** Grafo objeto-cêntrico multi-hop (search-around) no `InvestigationCanvas`.
- **T3** Pc operacional com elipsoide 6D (hoje: extras Foster + Kepler/SGP4 opcional; `pair_risk` intacto).
- **T4** Ingestão OSINT além das fontes do walk-forward (tipo `Document` já existe).
- **T5** RAG denso / embeddings (hoje: overlap de tokens + citação `path#heading`).
- **T6** What-if sobre history real (hoje: sandbox em memória + CLI).
- **T7** Watchlist que retreina baseline (hoje: API + editor, persistência JSON).
- **T8** Lazy do globe (Three isolado ainda > 500 kB).
- **T9** Backup/restore e health da stack completa (`docker-compose.yml` já sobe board + sidecar).

## 6. Regras de ouro (NÃO quebrar)

1. **Scores são imutáveis.** Nenhum código de UI/LLM pode reescrever `anomaly_score`, classes XGB ou detecção. Estado de alerta (`OPEN/ACKNOWLEDGED/...`) é bookkeeping, não análise.
2. **Past-only.** IF treina só em janelas que terminam antes do cutoff (holdout ≥ 1 dia). O "hoje" é pontuado, nunca treinado.
3. **Normalidade = baseline + asset.** Suspeitos **não** entram no treino do IF. Constelações comerciais (Starlink) são excluídas.
4. **Bob explica, não recomputa.** LLM cita o quant; nunca gera score novo.
5. **Geometria nos features e nos labels.** Se `min_distance_to_military_km`/`cointegration_pvalue` alimentam XGB, os labels (weak labels) devem usar os mesmos sinais.

## 7. Gotchas ambientais (leia antes de assumir)

- O host roda **Python 3.14.6**, mas `requirements.txt` pina `pandas<3` e `xgboost<3`; o ambiente local tem `pandas 3.0.3` e `xgboost 3.3.0` (fora do range). Use **Python 3.11/3.12** (como CI/Dockerfile) para reprodutibilidade real.
- **`git lfs` NÃO está instalado.** Modelos (`*.joblib`) e `*.parquet` estão versionados no git — é um problema de higiene em aberto.
- **Há muitos arquivos WIP não-commitados** no working tree (ex.: `src/object_layer.py`, componentes HUD, `scripts/run_daily_ingest.sh`). Ao commitar, separe o que é código novo seu do que era WIP pré-existente.
- O frontend usa **Tailwind v3 + React 19 + Vite 7 + Three.js**; a build emite um aviso de chunk > 500 kB (track T8).
- `--threshold` default do CLI é `None` por design; sempre passe pelo `resolve_thresholds()` (não faça `float(None)`).

## 8. Por onde começar

1. Rodar a seção 3 para confirmar a baseline verde.
2. Ler `docs/ROADMAP_ESTRATEGICO.md` e escolher a **track T1** (menor risco, maior desbloqueio).
3. Antes de cada mudança, rodar `python -m pytest -q` e, se tocar frontend, `npm run build`.
4. Manter os invariantes da seção 6 e documentar qualquer novo artefato no README.
