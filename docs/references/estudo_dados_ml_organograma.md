# Estudo fechado: dados, volumes e organograma de trabalho

**Athena-SDA** · Fonte de verdade para iniciar implementação depois  
**Data:** 2026-07-25  
**Escopo:** quanto baixar, de onde, o que entra no ML, ordem de trabalho

---

## 0. Decisões fechadas (resumo executivo)

| Decisão | Valor |
|---------|--------|
| Escala do ML | **Watchlist ~24 NORADs** (asset/suspect/baseline) — **não** o céu inteiro |
| O que o ML aprende | Vetor de **features matemáticas** de desvio do normal (ruído anômalo), não TLE bruto |
| Walk-forward | **Só no final**, pós-treino — teste de lead-time vs reports públicos |
| Histórico alvo | **~2 anos** (2024→hoje), estender se walk-forward exigir |
| Estratégia de download | **Streaming + filtro NORAD** ou **parquet por ano** — **nunca** baixar 12 GB “por esport |
| Disco útil no projeto | **≪ 1 GB** para dados de treino/score (ordem de dezenas de MB) |
| Pico de rede (se baixar anos inteiros) | **~2–4 GB** opcional (2024+2025+2026 parquet crú); **recomendado: streaming filtrado ≪ 500 MB** |

---

## 1. Quantos gigas? (números reais)

### 1.1 O que existe “lá fora” (catálogo completo)

| Fonte | Conteúdo | Tamanho típico | Precisamos baixar tudo? |
|-------|----------|----------------|-------------------------|
| **HF `juliensimon/space-track-tle-history`** | ~238–239M TLEs, 1959–2026, 1 parquet/ano | **~11–12 GB** total | **Não** |
| HF `tle_2024.parquet` | Todos os objetos 2024 | **~934 MB** (medido 2026-07-25) | Opcional (depois filtra) |
| HF `tle_2025.parquet` | Todos os objetos 2025 | **~988 MB** | Opcional |
| HF `tle_2026.parquet` | Todos os objetos 2026 (parcial) | **~530 MB** | Opcional |
| HF 2024+2025+2026 se baixar anos inteiros | 3 arquivos | **~2,45 GB** | Só se stream for inviável |
| HF `tle_2022` / `tle_2023` | anos anteriores | **~821 / ~753 MB** | Só se walk-forward exigir |
| **HF `constellation-tle-latest`** | Snapshot diário ~2k sats constelações | **≪ 50 MB** (card: ordem de poucos MB–centenas KB de rows) | Opcional backup |
| **CelesTrak GP** (grupos/CATNR) | Latest por objeto/grupo | **KB–poucos MB** por request | Sim, diário |
| **Space-Track.org** | GP / GP_History oficial | Conta grátis; history grande | Opcional se HF faltar |
| Disco local atual Athena | history + daily + catalog | **~0,3 MB** dados + **~5–6 MB** modelos | — |

Fontes de tamanho HF (ordem de grandeza pública): dataset card / space-datasets — **~10.9–12 GB**, **238M+ rows**.

### 1.2 O que o Athena **vai usar de fato** no ML

Estimativa para **24 sats × 2 anos × ~4–12 TLE/dia** (cadência TLE varia por objeto):

| Cenário | Linhas (ordem) | Tabela canônica em disco |
|---------|----------------|---------------------------|
| Conservador (4 ep/dia) | ~70k | **~15–30 MB** |
| Típico (8 ep/dia) | ~140k | **~30–60 MB** |
| Denso (12 ep/dia, 2,5 y) | ~260k | **~50–100 MB** |
| Features + janelas IF | 10³–10⁴ rows | **~5–50 MB** |
| Modelos joblib (IF+XGB) | — | **~5–10 MB** |

**Conclusão de volume para o hackathon / pipeline Athena:**

| Item | Disco a reservar | Rede |
|------|------------------|------|
| **Mínimo viável (recomendado)** | **100–300 MB** livres em `data/` | Streaming HF filtrado: **dezenas a poucas centenas de MB** transferidos (só linhas keep) |
| **Confortável** | **1 GB** | Mesmo + 1–2 anos parquet se quiser cache local |
| **Evitar** | Baixar **12 GB** full history | Só se for repositório espelho offline |

> **Resposta curta:** para o ML da watchlist **não precisamos de vários gigas**.  
> Precisamos de **ordem de 0,05–0,3 GB** de dados úteis.  
> O dataset HF “cheio” tem **~12 GB**, mas isso é o **universo**; o nosso recorte é **filtado**.

### 1.3 Três modos de ingestão (escolher 1 como padrão)

| Modo | Como | Download | Quando usar |
|------|------|----------|-------------|
| **A — Streaming filtrado (padrão)** | `load_dataset(..., streaming=True)` + keep `norad_id ∈ watchlist` + `year≥2024` | Baixo (só kept + overhead stream) | Default Athena |
| **B — Parquet por ano + filtro local** | Baixar `tle_2024.parquet`, `tle_2025.parquet`, … e filtrar | ~0,5–3+ GB se vários anos | Se stream for lento/instável |
| **C — CATNR / Space-Track só diário** | CelesTrak CATNR (já feito) + opcional API Space-Track | MB | Operação diária, não baseline 2y |

**Padrão fechado: A para seed histórico; CelesTrak CATNR para diário.**

---

## 2. Onde buscar dados (mapa de fontes abertas)

### 2.1 Primárias (usar)

| # | Fonte | URL / ID | Auth | Papel no Athena |
|---|-------|----------|------|-----------------|
| 1 | **Hugging Face TLE history** | `juliensimon/space-track-tle-history` | Não (CC-BY-4.0) | Seed 2y filtrado watchlist |
| 2 | **CelesTrak GP** | `celestrak.org/NORAD/elements/gp.php?CATNR=` / `GROUP=` | Não | Ingest diário |
| 3 | **Catálogo Athena** | `data/catalog/watchlist.json` | Local | Quem entra no ML |
| 4 | **HF constellation latest** | `juliensimon/constellation-tle-latest` | Não | Backup “hoje” se CelesTrak falhar |

### 2.2 Secundárias (opcional / enriquecimento)

| Fonte | Auth | Uso |
|-------|------|-----|
| **Space-Track.org** API (GP, GP_History) | Conta grátis | History oficial se HF incompleto para um NORAD |
| **HF space-track-satcat** | Não | Metadados objeto (país, tipo) |
| **UCS Satellite Database** | Público (CSV/site) | purpose civil/militar (contexto Williams/ontology) |
| **NOAA space weather** (F10.7, Ap) | Público | Contexto arrasto (fase 2, não bloqueia ML v1) |
| **N2YO** | API key free tier | Tempo real pontual (não treino) |

### 2.3 O que **não** baixar para o ML v1

- Catálogo `GROUP=active` completo diário “para treinar o céu”
- Full 12 GB HF sem filtro
- Imagens SAR/EO (fora de escopo TLE/SDA quant deste hackathon)
- Ephemeris de alta taxa comercial (caro / desnecessário para demo de features)

### 2.4 Layout canônico em disco (após ingestão)

```
data/
├── catalog/
│   ├── watchlist.json           # ontologia (pequeno)
│   └── events_walkforward.json  # âncoras (só validação final)
├── history/
│   ├── epochs.parquet           # CANÔNICO treino/score (~dezenas MB)
│   ├── epochs.csv
│   └── seed_progress.json       # andamento do stream
├── daily/
│   └── tle_YYYY-MM-DD.csv       # auditoria do dia (KB–MB)
├── features/
│   └── train_windows_*.csv      # janelas IF
└── alerts/
    ├── anomalies_latest.json    # operação
    └── walkforward_*.json       # só pós-treino / validação
models/
├── isolation_forest_monitor.joblib
├── anomaly_monitor_meta.json
└── xgboost_model.joblib
```

---

## 3. O que entra no ML (lembrete de método)

```
TLE (history) 
  → features MATH (Shannon, Hurst, CUSUM, Kolmogorov, fractal/Mandelbrot, …)
  → Isolation Forest = “distoa do normal?”
  → XGB/Fuzzy/Kelly = classe + incerteza + prioridade
  → [FINAL] walk-forward em reports = teste de lead-time
```

- **Ruído que distoa do normal** = núcleo  
- **Walk-forward** = etapa de validação **depois** do treino, não o treino em si  

---

## 4. Organograma do que será feito

### 4.1 Visão em fases (macro)

```
┌──────────────────────────────────────────────────────────────────────────┐
│                         ATHENA-SDA — LINHA DO TEMPO                      │
└──────────────────────────────────────────────────────────────────────────┘

 FASE 0          FASE 1           FASE 2            FASE 3           FASE 4
 ESTUDO          DADOS            FEATURES+ML       OPERAÇÃO         VALIDAÇÃO
 (agora)         SEED             TREINO            DIÁRIA           FINAL
    │               │                 │                 │                │
    ▼               ▼                 ▼                 ▼                ▼
 Fechar         HF stream         Math vector       ingest CATNR     Walk-forward
 volumes        + CelesTrak       IF no passado     score latest     vs reports
 fontes         history store     meta + joblib     alerts JSON      lead-time
 organograma    coverage 24       (sem walkfwd)     (pares depois)   (só teste)
```

### 4.2 Organograma detalhado (WBS)

```
ATHENA-SDA
│
├── 0. GOVERNANÇA E ESTUDO                    [FECHAR / EM CURSO]
│   ├── 0.1 Escopo militar-first (watchlist 24)
│   ├── 0.2 Volume de dados e fontes (este doc)
│   ├── 0.3 Math = features; ML = desvio do normal
│   ├── 0.4 Walk-forward só no final
│   ├── 0.5 Mapa patentes → módulos
│   └── 0.6 (próximo) papers IBM/quant/fractal → reforço teórico
│
├── 1. DADOS                                  [PRÓXIMO BLOCO DE TRABALHO]
│   ├── 1.1 deps: datasets, pyarrow, (polars opcional)
│   ├── 1.2 seed-history --hf streaming filtrado watchlist ≥2024
│   ├── 1.3 seed_progress.json (scanned / kept / by_norad)
│   ├── 1.4 ingest-daily CelesTrak CATNR (24/24)
│   ├── 1.5 status: depth ≥20 épocas em ≥18 sats
│   └── 1.6 (opc) baixar parquet ano se stream falhar
│
├── 2. FEATURES MATEMÁTICAS                   [NÚCLEO QUANT]
│   ├── 2.1 engine: Shannon, Kolmogorov, Hurst, CUSUM, ADF, Mandelbrot…
│   ├── 2.2 DQ gate (ruído de catálogo ≠ anomalia tática)
│   ├── 2.3 janelas deslizantes (WINDOW=20)
│   └── 2.4 features/train_windows_*.csv auditoria
│
├── 3. ML — DESVIO DO NORMAL                  [TREINO]
│   ├── 3.1 Isolation Forest no PASSADO (holdout 1–7d)
│   ├── 3.2 meta: n_windows, n_sats, cutoff, score_p95
│   ├── 3.3 XGBoost threat (labels fracos / fuse)
│   ├── 3.4 Fuzzy + Kelly
│   └── 3.5 NÃO incluir walk-forward no loop de treino
│
├── 4. PARES (narrativa RPO/shadowing)        [APÓS 3 estável]
│   ├── 4.1 suspect × asset: distância / TCA
│   ├── 4.2 cointegração séries
│   └── 4.3 proximity_*.json
│
├── 5. OPERAÇÃO DIÁRIA                        [LOOP]
│   ├── 5.1 ingest-daily
│   ├── 5.2 retrain opcional (hot-swap baseline — patente 070)
│   ├── 5.3 score → anomalies_latest.json
│   └── 5.4 Bob só explica (pós-quant — patente 296)
│
├── 6. VALIDAÇÃO FINAL                        [DEPOIS DO TREINO]
│   ├── 6.1 events_walkforward.json (âncoras públicas)
│   ├── 6.2 expanding window: score série pré-report
│   ├── 6.3 métricas Hit@event, lead-time, FPR baseline
│   └── 6.4 report: features math que dispararam
│
├── 7. PRODUTO / UI                           [DEPOIS JSON ESTÁVEL]
│   ├── 7.1 contrato risk_report_latest.json
│   ├── 7.2 board + globo por role/threat
│   └── 7.3 (opc) painel replay de evento
│
└── 8. DOCS / PITCH
    ├── 8.1 patentes + math + casos RPO
    ├── 8.2 volumes e honestidade de escala
    └── 8.3 (opc) bib IBM/Simons/fractal
```

### 4.3 Dependências entre blocos

```
[0 Estudo] ──► [1 Dados] ──► [2 Features] ──► [3 ML treino]
                                                  │
                          ┌───────────────────────┼───────────────────────┐
                          ▼                       ▼                       ▼
                     [4 Pares]              [5 Diário]              [6 Walk-forward FINAL]
                          │                       │                       │
                          └───────────────────────┴───────────────────────┘
                                              │
                                              ▼
                                         [7 UI + 8 Pitch]
```

**Bloqueio crítico:** sem **1.5** (depth de história), **3** e **6** não são confiáveis.

### 4.4 Checklist “pronto para iniciar trabalhos” (gate)

| Gate | Critério |
|------|----------|
| G0 | Estudo volumes/fontes/organograma aceito (este doc) |
| G1 | `datasets` + `pyarrow` instalados |
| G2 | Seed HF: ≥18/24 sats com ≥20 épocas; range ~2024→hoje |
| G3 | `train-baseline` n_sats≥15, n_windows razoável (centenas+) |
| G4 | `score` gera `anomalies_latest` com role/country |
| G5 | (depois) walk-forward em ≥1 evento coberto pelos dados |

---

## 5. Comandos-alvo (quando iniciar execução)

```bash
# deps
pip install datasets pyarrow

# seed (padrão A — streaming filtrado; max-rows evita runaway)
python scripts/run_anomaly_monitor.py seed-history --hf --start-year 2024 --max-rows 30000

# cobertura
python scripts/run_anomaly_monitor.py status
python scripts/run_anomaly_monitor.py catalog -v

# diário
python scripts/run_anomaly_monitor.py ingest-daily --source celestrak

# treino + score (núcleo ML)
python scripts/run_anomaly_monitor.py train-baseline --holdout-days 1
python scripts/run_anomaly_monitor.py score

# walk-forward: SÓ depois — scripts futuros run_walkforward.py
```

---

## 6. Estimativa de esforço (ordem)

| Fase | Trabalho | Dependência |
|------|----------|-------------|
| 1 Dados | 1 sessão (stream pode demorar dezenas de min) | rede + pip |
| 2–3 Features+ML | 1 sessão se history ok | G2 |
| 4 Pares | 1 sessão | G3 |
| 5 Diário | minutos | G3 |
| 6 Walk-forward | 1 sessão + âncoras com dados | G3 + history no período do evento |
| 7 UI contrato | 1 sessão | G4 |

---

## 7. Respostas diretas

| Pergunta | Resposta |
|----------|----------|
| Quantos GB para o ML? | **Úteis: ~0,05–0,3 GB.** Reservar **1 GB** folga. **Não** 12 GB. |
| HF tem 12 GB? | Sim o **arquivo completo**. Nós usamos **filtro/stream** da watchlist. |
| Onde? | HF `space-track-tle-history` + CelesTrak CATNR (+ Space-Track opcional). |
| Walk-forward gasta dados extra? | Mesmo history; só reprocessa no tempo. Disco de reports: MB. |
| Organograma? | Seção 4 — fases 0→8; iniciar trabalhos em **Fase 1** após aceite G0. |

---

## 8. Próximo passo após aceite deste estudo

1. Instalar deps e rodar **seed HF filtrado**  
2. Confirmar **status** (depth)  
3. **train-baseline + score**  
4. Só então pares e, **por último**, walk-forward  

Papers IBM/quant/fractal: bloco **0.6** em paralelo à Fase 1 (teoria), sem bloquear download.
