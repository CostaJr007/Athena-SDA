# Athena-SDA — Handoff de sessão (continuar)

**Última atualização:** 2026-07-25 (Linux)  
**Workspace:** `/run/media/adeilsoncosta/Novo volume/Athena-SDA`  
**Sessão anterior (Windows):** `D:\Athena-SDA` — mesmo disco/projeto; handoff antigo migrado para cá.  
**Repo GitHub:** https://github.com/CostaJr007/Athena-SDA (remoto ainda **atrasado** vs disco)

Use este arquivo no início da próxima sessão: *“leia docs/SESSION_HANDOFF.md e continue”*.

---

## 1. Visão do produto (não perder o foco)

| Prioridade | Conteúdo |
|------------|----------|
| **Núcleo** | Quant + ML para anomalia, risco, proximidade/shadowing; embasamento em patentes Palantir + teorias matemáticas |
| **Narrativa** | SDA **militar** / espírito Palantir — não tracker civil genérico |
| **UI** | Vitrine (globo + board); polish militar **depois** do backend/ML estável |
| **IA (Bob)** | Só **depois** do quant (etapas ③④ da patente LLM+GIS) — explica scores, não inventa ameaça |

**Pitch em uma linha:**  
Watchlist militar-first + **~12 anos de TLE (HF 2014→hoje, filtrado)** + injeção diária + Isolation Forest no passado + score no presente + space weather + pares (dist/coint) + Fuzzy/XGB/Kelly + Bob pós-quant + walk-forward pré-report.

---

## 2. Decisões fechadas

1. **Frontend base = Kimi `src/frontend/`** (não Lovable). Lovable em `src/frontend-lovable-backup/`.
2. **Visual Athena:** painéis pretos, estrelas no chrome, texto zinc/branco, accent emerald.
3. **Route Cross / Conjunction lab:** dois satélites, órbitas + TCA + proximidade geométrica.
4. **Watchlist pequena (~15–25 NORADs):** assets + suspeitos + baseline — **não** treinar o céu inteiro.
5. **Catálogo canônico:** `data/catalog/watchlist.json` com `role`: `asset` | `suspect` | `baseline`.
6. **NORADs validados no CelesTrak** (2026-07-25) — nomes antigos no código (YAOGAN-31 em 44231, USA-245 em 43941, etc.) estavam **errados** ou 404; lista nova usa IDs públicos reais.
7. **Ingest preferencial:** CelesTrak **CATNR** por NORAD (evita `GROUP=active` 403).
8. **Front polish militar pesado:** adiar até JSON real do ML estável.

---

## 3. O que já foi implementado

### Catálogo + dados (esta sessão Linux)

| Path | Função |
|------|--------|
| `data/catalog/watchlist.json` | **24 objetos**: 7 asset, 11 suspect, 6 baseline |
| `src/catalog.py` | Loader (roles, name_map, asset_ids, get_meta, summary) |
| `src/tle_store.py` | `DEFAULT_WATCHLIST` vem do JSON; `fetch_celestrak_by_ids` / CATNR |
| `src/anomaly_monitor.py` | Score enriquece com role/country/purpose do catálogo |
| `src/pipeline.py` | Assets protegidos via `asset_ids()` do catálogo |
| `src/config.py` | `MILITARY_ASSET_IDS` do catálogo |
| `scripts/run_anomaly_monitor.py` | `catalog`, `status` com coverage; ingest CATNR |

### Frontend (`src/frontend/`)
- Base Kimi completa (Three.js, TLE live, SGP4 worker).
- Docks L/R: Mission board, Conjunction lab, Track intel + Bob stub.
- Cross/compare: `lib/orbit-crossing.ts`, `CrossRoutePanel`.
- Rodar: `cd src/frontend && npm install && npm run dev` → http://127.0.0.1:3000

### Backend / quant / monitor
| Path | Função |
|------|--------|
| `src/engine.py` | Shannon, Kolmogorov, Hurst, CUSUM, ADF, coint, … |
| `src/models.py` | Features, IF, XGBoost |
| `src/pipeline.py` | DAG features → prox/coint → IF → XGB → Fuzzy → Kelly |
| `src/fuzzy.py` | Mamdani |
| `src/tle_store.py` | Histórico unificado + CelesTrak + HF |
| `src/anomaly_monitor.py` | Train past + score diário + DQ |
| `scripts/run_anomaly_monitor.py` | CLI |

### Estado dos dados (2026-07-26 Linux)

| Store | Estado |
|-------|--------|
| History | **~70 939 épocas**, **24/24** sats, range **2024-01-01 → 2026-07-25** (HF year parquet pyarrow) |
| Daily | `data/daily/tle_2026-07-26.csv` — 24/24 CATNR |
| Alerts | `anomalies_latest.json` + **`proximity_latest.json`** + **`risk_report_latest.json`** |
| Score | 24 scored; pares 33; elevated ~11; fuse IF+pair (attention) |
| Modelos IF | `isolation_forest_monitor.joblib` — **24 sats / 1200 janelas** (2026-07-26) |
| Seed | `data/history/seed_progress.json` — completed 2024–2026 |

**Nota:** seed antigo com `datasets.to_pandas()` OOM/travou VS Code no ano 2025; corrigido para **PyArrow batch filter**.

### Git
- Local à frente do remote; muito untracked.
- **Não** commitar `.env` / tokens / `node_modules`.

---

## 4. Watchlist (resumo)

**Assets (proteger):** ISS, GPS×2, DMSP×2, COSMO-SkyMed, TerraSAR-X  

**Suspects (caçar):** Yaogan×2, Gaofen×2, Shiyan×2, Luch/Olymp-K×2, Cosmos 2550, Beidou-3 M11, CSS Tianhe  

**Baseline (âncora IF):** Terra, Aqua, NOAA-20, Landsat-8, NOAA-18, Starlink-1008  

Ver lista completa: `python scripts/run_anomaly_monitor.py catalog -v`

---

## 5. Plano imediato (ordem)

### A. Catálogo militar-first — **FEITO**
- [x] `data/catalog/watchlist.json`
- [x] Ligar em tle_store / CLI / monitor / pipeline
- [x] Ingest diário CATNR 24/24

### B. Dados HF ~12 anos — **FEITO** (não “só 2 anos”)
- [x] Estudo volumes: cache HF multi-GB; store útil ~dezenas de MB
- [x] Seed year-parquet 2014+ filtrado watchlist → `epochs.parquet` (~250k épocas)
- [x] Range real: **2014-01-01 → 2026-07** (~12,5 anos), 24/24 sats
- [x] Space weather GFZ no mesmo range

### C. Treino + diário — **FEITO**
- [x] `train-baseline --holdout-days 1 --sample-mode hybrid` (série longa)
- [x] `score` → `data/alerts/anomalies_latest.json` com role/country + pairs
- [x] `run-daily` protocolo série=passado / hoje=score

### D. Walk-forward + melhorias Gemini coerentes — **FEITO 2026-07-26**
- [x] `events_walkforward.json` + `src/walkforward.py` + `scripts/run_walkforward.py`
- [x] WF treina **só no passado** (ruído pré-`asof`); métricas pre_peak_noise vs placebo
- [x] Gemini coerente: history store train, geometria em label/feature, score unificado, weights assimétricos
- [x] Doc: `docs/references/melhorias_gemini_aplicadas.md`
- [ ] UKF/autoencoder/TCA SGP4 full — **não** (overkill)

### E. Score de pares (narrativa militar) — **FEITO 2026-07-26**
- [x] `src/pair_score.py` — suspect × asset (dist + coint + pair_risk)
- [x] merge no `score` diário + `attention_score`
- [x] `proximity_latest.json` + `risk_report_latest.json` (schema v1)
- [x] CLI: `score` (com pares) e `score-pairs`
- [ ] TCA full SGP4 no backend (front já tem orbit-crossing)

### F. Contrato front (só depois do JSON estável)
- [ ] Schema `risk_report_latest.json`
- [ ] RightDock/LeftDock leem JSON
- [ ] Cores no globo por threat/anomaly
- [ ] (opcional) painel Event replay walk-forward

### G. Git (quando estável)
- [ ] Commit organizado + push

---

## 6. Comandos úteis (Linux)

```bash
cd "/run/media/adeilsoncosta/Novo volume/Athena-SDA"
# opcional: source .venv/bin/activate

python scripts/run_anomaly_monitor.py catalog -v
python scripts/run_anomaly_monitor.py status

# Seed 2y (demora — streaming HF)
python scripts/run_anomaly_monitor.py seed-history --hf --start-year 2024 --max-rows 30000

python scripts/run_anomaly_monitor.py ingest-daily --source celestrak
python scripts/run_anomaly_monitor.py train-baseline --holdout-days 1
python scripts/run_anomaly_monitor.py score
python scripts/run_anomaly_monitor.py run-daily

# Frontend
cd src/frontend && npm run dev
```

---

## 7. Por que cada ferramenta (1 linha)

| Tool | Por quê |
|------|---------|
| **Shannon** | \(\Delta a\) caótico ⇒ manobra/controle |
| **Hurst** | Persistência ⇒ baixo empuxo |
| **CUSUM** | *Quando* a série quebrou |
| **Kolmogorov proxy** | Controle complexo comprime mal |
| **ADF** | Não-estacionariedade da série individual |
| **Cointegração** | Duas séries andam juntas ⇒ shadowing |
| **Proximidade / TCA** | RPO / colisão |
| **IF** | Anomalia vs baseline do passado |
| **XGB** | Classe de ameaça |
| **Fuzzy** | Incerteza (TLE age, geometria) |
| **Kelly** | Priorizar atenção/sensor |
| **Bob** | Explicar (pós-quant) |

---

## 8. Armadilhas conhecidas

1. Accuracy ~99% no treino sintético = **circular**.  
2. Ricci/Homologia/Chern-Simons = **proxies**.  
3. CelesTrak `GROUP=active` pode **403** — usar CATNR (default do ingest).  
4. Front e pipeline Python **ainda desconectados**.  
5. Labels HOSTIL são heurísticos.  
6. NORADs antigos no README/docs legados podem estar desatualizados vs `watchlist.json`.  
7. Histórico antigo (`real_tle_history_*`) mistura poucos sats com nomes incorretos — **re-seed HF** substitui a massa.  
8. `leo-live-old/` e `frontend-lovable-backup/` = backups.

---

## 9. Prompt sugerido para a próxima sessão

```text
Leia docs/SESSION_HANDOFF.md e o README.md do Athena-SDA.
Continue: seed-history --hf (2014+, watchlist do catalog) se precisar re-seed;
train-baseline, score diário, depois score de pares
(proximidade/cointegração/TCA). Não redesenhar o front até o JSON
de risco estar estável. Foco: quant + ML + narrativa militar/Palantir.
```

---

## 10. Arquivos-chave

- `docs/SESSION_HANDOFF.md` ← **este arquivo**
- `data/catalog/watchlist.json` ← catálogo militar-first
- `src/catalog.py`, `src/tle_store.py`, `src/anomaly_monitor.py`
- `scripts/run_anomaly_monitor.py`
- `README.md`, `docs/references/patentes_palantir.md`
- `src/frontend/src/pages/Home.tsx`
