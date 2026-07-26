# Athena-SDA

**Space Domain Awareness (SDA) Copilot** — sistema de inteligência orbital que combina **dados reais (TLE + clima espacial)**, um **framework matemático de ruído**, **machine learning** (Isolation Forest + XGBoost) e um **copiloto** (IBM Granite / briefing local) para detectar desvios de comportamento, priorizar atenção e validar lead-time antes de reports open-source.

| | |
|--|--|
| **Desafio** | IBM SkillsBuild AI Builders — *Advance Space Exploration with AI* |
| **Foco** | SDA militar-first (proteger assets, monitorar suspeitos) — espírito de COP/inteligência, não tracker civil genérico |
| **Repo** | [github.com/CostaJr007/Athena-SDA](https://github.com/CostaJr007/Athena-SDA) |
| **Watchlist** | 24 NORADs (7 asset · 11 suspect · 6 baseline) |
| **Histórico de treino** | **~12,5 anos** (2014-01-01 → 2026-07-25), **não** “só 2 anos” |

> Continuação de sessão: [`docs/SESSION_HANDOFF.md`](docs/SESSION_HANDOFF.md)  
> Relatório ML completo: [`docs/RELATORIO_COMPLETO_ML_ATHENA_SDA.md`](docs/RELATORIO_COMPLETO_ML_ATHENA_SDA.md)  
> Walk-forward pré-report: [`docs/RELATORIO_WALKFORWARD_PRE_REPORT_ML_NOVO.md`](docs/RELATORIO_WALKFORWARD_PRE_REPORT_ML_NOVO.md)

---

## 1. Visão geral

Athena-SDA responde três perguntas operacionais:

1. **A série orbital deste objeto mudou de forma anômala** em relação ao seu passado (e ao clima da época)?  
2. **A aproximação a um asset protegido** (geometria / cointegração) eleva a prioridade?  
3. **O ruído matemático sobe antes** de âncoras de report público (walk-forward past-only)?

O front (globo 3D) é a **vitrine**. O argumento técnico é a **coluna quant + ML + dados reais**.

```
Fontes públicas (TLE + GFZ)
        │
        ▼
Janela de 20 épocas → features (Kepler + math + space weather + pares)
        │
        ├─► Isolation Forest (baseline = SÉRIE no passado) → anomaly_score
        └─► XGBoost / Fuzzy / Kelly / pair attention → board de risco
                    │
                    ▼
         Bob (LLM) explica scores já calculados
         Walk-forward valida lead-time vs reports open-source
```

**Protocolo diário:** treina o “normal” só com a **série até ontem**; o **dado de hoje** só é comparado (sem vazar o dia no treino). Ver [`docs/PROTOCOLO_DETECCAO_DIARIA.md`](docs/PROTOCOLO_DETECCAO_DIARIA.md).

---

## 2. Dados — volumes, fontes e o que sobe no Git

### 2.1 Ideia-chave

O seed **baixa** o catálogo TLE grande (vários **GB** no cache Hugging Face) e **persiste só a watchlist** (dezenas de **MB** no repositório).  
Por isso o PC pode mostrar “giga baixados” e o GitHub ter “poucos MB de ML” — **os dois estão corretos**.

```
HF space-track-tle-history     ≈ 15 GB em cache (todos os objetos / anos)
        │  filtro: 24 NORADs da watchlist, anos 2014+
        ▼
data/history/epochs.parquet    ≈ 13 MB  (~250 mil épocas, ~12,5 anos)
        +
GFZ F10.7 / Ap / Kp            ≈ 0,1–0,3 MB úteis no store diário
        +
Modelos IF + XGB + RKHS        ≈ 5 MB
```

### 2.2 Tabela de volumes (estado atual do projeto)

| Recurso | Onde fica | Tamanho aproximado | No GitHub? | Função |
|---------|-----------|--------------------|------------|--------|
| Cache HF `space-track-tle-history` | `~/.cache/huggingface/hub/...` | **~15 GB** | **Não** | Download bruto multi-ano / multi-satélite |
| TLE filtrado (parquet) | `data/history/epochs.parquet` | **~12,9 MB** | **Sim** | Base real de treino/score (~249 558 épocas) |
| TLE filtrado (CSV espelho) | `data/history/epochs.csv` | **~45 MB** | **Não** (gitignore; duplicata do parquet) | Auditoria local |
| Space weather diário | `data/space_weather/daily.parquet` | **~0,09 MB** | **Sim** | F10.7, Ap, Kp, SN (2014→hoje) |
| SW CSV + meta | `data/space_weather/` | **~0,3 MB** | **Sim** | Espelho legível |
| Raw GFZ texto completo | `Kp_ap_...1932.txt` (local) | **~5 MB** | **Não** (re-downloadável) | Fonte bruta |
| Modelos ML | `models/*.joblib` | **~5,3 MB** | **Sim** | IF pipeline, IF monitor, XGB, RKHS |
| Métricas de treino | `models/training_metrics.json` | **~3 KB** | **Sim** | n_samples, features, scores |
| Features de treino (CSV) | `data/features/train_windows_latest.csv` | **~0,6 MB** | **Sim** | Auditoria de janelas IF |
| Alertas + walk-forward | `data/alerts/` | **~0,9 MB** | **Sim** | Score diário + WF pré-report |
| Catálogo | `data/catalog/` | **~11 KB** | **Sim** | Watchlist + eventos WF |
| **Total útil no repo (dados+modelos)** | | **~20–25 MB** | **Sim** | Clone pronto para demo |
| **Total baixado no PC (com cache HF)** | | **~15 GB+** | Cache local | Matéria-prima do seed |

### 2.3 Cobertura temporal e objetos

| Métrica | Valor |
|---------|--------|
| Intervalo TLE | **2014-01-01 → 2026-07-25** (**~12,56 anos**) |
| Satélites | **24** NORADs |
| Épocas | **249 558** |
| Space weather | **4 589** dias (2014-01-01 → 2026-07-25) |
| Roles | 7 **asset** · 11 **suspect** · 6 **baseline** |

### 2.4 Fontes (dados reais, não simulação do céu)

| Camada | Fonte | Observação |
|--------|--------|------------|
| TLE histórico | Hugging Face [`juliensimon/space-track-tle-history`](https://huggingface.co/datasets/juliensimon/space-track-tle-history) | Espelho público estilo Space-Track; filtrado na watchlist |
| TLE diário | [CelesTrak](https://celestrak.org) GP por `CATNR` | Ingest operacional |
| Clima espacial | [GFZ Potsdam](https://kp.gfz-potsdam.de/) (Kp, Ap, F10.7, SN) + NOAA F10.7 opcional | Contexto arrasto vs manobra |
| Eventos de validação | Gunter, CSIS, imprensa open-source | Âncoras de **report**, não labels classificados |
| Labels XGB NORMAL…HOSTIL | Heurísticas de doutrina no código | **Não** são ground-truth de inteligência |

### 2.5 Comandos de dados

```bash
# Seed histórico (baixa anos HF → cache GB → grava só watchlist)
python scripts/run_anomaly_monitor.py seed-history --hf --start-year 2014

# Clima espacial
python scripts/run_anomaly_monitor.py seed-space-weather --force --start-year 2014

# Status (cobertura + SW)
python scripts/run_anomaly_monitor.py status
python scripts/run_anomaly_monitor.py space-weather-status
```

---

## 3. Modelos de machine learning (o que foi treinado)

| Modelo | Arquivo | Entrada | Saída | Como foi treinado |
|--------|---------|---------|--------|-------------------|
| **Isolation Forest (pipeline)** | `models/isolation_forest.joblib` | 34 features (`IFOREST_COLUMNS`) | `anomaly_score = clip(0.5 − decision_function)` | ~**960** janelas do history store; contamination 0,08 |
| **Isolation Forest (monitor diário)** | `models/isolation_forest_monitor.joblib` | 34 features | anomaly_score no **último** ponto vs baseline | ~**1 440** janelas, sample **hybrid** na série **2014→ontem**, holdout 1 dia |
| **XGBoost multi-classe** | `models/xgboost_model.joblib` | **38** features (37 + anomaly_score) | NORMAL / ANÔMALO / SUSPEITO / HOSTIL + proba | Mesmo history store; pesos de classe {1, 1.5, 3, 5} |
| **RKHS reference** | `models/rkhs_reference.joblib` | subvetor de features | apoio a `spectral_anomaly_rkhs` | Matriz de referência de typicality |
| **Fuzzy Mamdani** | `src/fuzzy.py` (regras) | anomaly, dist, idade TLE… | calibração linguística | Não é treino estatístico; regras + clamp |
| **Kelly** | `engine.calculate_kelly_allocation` | proba × severidade | orçamento de atenção | Critério clássico de alocação |
| **Pair score** | `src/pair_score.py` | dist + cointegração | `pair_risk`, `attention = 0.45·anom + 0.55·pair` | Fusão operacional, não deep learning |

### 3.1 Dimensões do vetor de features

| Conjunto | Dimensão | Conteúdo |
|----------|----------|----------|
| `FEATURE_COLUMNS` | **37** | Kepler + deltas + math + space weather + multi-objeto |
| `IFOREST_COLUMNS` | **34** | 37 − {dist militar, coint, Łukasiewicz} — **inclui clima** |
| `XGB_COLUMNS` | **38** | 37 + `anomaly_score` |

### 3.2 Métricas internas do último treino pipeline

| Métrica | Valor | Como ler |
|---------|--------|----------|
| Fonte | `history_store` | TLE reais, sem diluir com sintético full |
| Amostras | 960 | Janelas de 20 épocas |
| Features XGB | 38 | Ver tabela acima |
| Accuracy (holdout interno) | ~0,95 | **Acordo com labels heurísticas**, não prova de espionagem |
| Macro-F1 | ~0,87 | Idem |
| Validação séria | Walk-forward | Hit 5/5 interesse vs 0/3 placebos (ML com SW) |

---

## 4. Framework matemático — teoria, definição e aplicação

Implementação: `src/engine.py` · detalhe formal: `docs/references/fundamentacao_matematica.md`.

Cada ferramenta produz uma **feature** (ou score auxiliar). O Isolation Forest **aprende a distribuição conjunta** desses sinais no passado; nenhuma teoria sozinha “é o alarme”.

### 4.1 Comportamento de um objeto (série temporal)

| Teoria | Definição (resumo) | Função no código | Aplicação SDA |
|--------|--------------------|------------------|---------------|
| **Entropia de Shannon** (1948) | \(H = -\sum p_i \log_2 p_i\) sobre bins de \(\Delta a\) | `calculate_shannon_entropy` → `shannon_entropy_sma_30d` | Mede **desordem** da variação de altitude. Kepler “chato” → baixa \(H\); manobras/controle → \(H\) alta. |
| **Complexidade de Kolmogorov (proxy)** (1965) | \(K(s)\) ≈ tamanho do menor programa; usamos **compressão zlib** da string U/D/S de \(\Delta a\) | `calculate_kolmogorov_proxy` → `kolmogorov_proxy_7d` | Trajetória física simples comprime bem; **controle complexo** comprime mal (score ↑). |
| **Expoente de Hurst** R/S (1951) | \(E[R/S] \propto n^H\); \(H>0.5\) persistência, \(H=0.5\) ruído, \(H<0.5\) reversão | `calculate_hurst_exponent` → `hurst_exponent_sma` | Detecta **baixo empuxo / deriva persistente** (ex. inspeção GEO) vs station-keeping que reverte à média. |
| **L1-CUSUM kernelizado** | Soma cumulativa de desvios vs baseline local | `calculate_kernel_l1_cusum` → `l1_cusum_sma` + `maneuver_count_30d` | **Quando** a série quebrou (change-point); conta picos de manobra. |
| **ADF** (Dickey–Fuller) | Teste de raiz unitária → p-value de não-estacionariedade | `calculate_adf_pvalue` → `adf_pvalue` | Apoia **quebra de regime** na série de altitude. |
| **Mandelbrot / cauda pesada** (1963) | Extremos vs quantil de referência (proxy de cauda) | `calculate_mandelbrot_tail_anomaly` → `mandelbrot_tail_score` | Impulsos raros (queima) vs ruído “normal” de arrasto. |
| **Anomalia espectral RKHS** | Distância em kernel RBF vs matriz de referência | `calculate_spectral_anomaly_rkhs` → `spectral_anomaly_rkhs` | Typicality do subvetor de features no **espaço de Hilbert**. |
| **Chern–Simons (proxy)** | Helicidade \(\int \mathbf{v}\cdot\boldsymbol{\omega}\) (proxy numérico) | `calculate_chern_simons_proxy` | Assinatura de fluxo **não conservativo** (propulsão). |
| **Ricci de Ollivier (proxy)** | \(1 - W_1(m_x,m_y)/d(x,y)\) entre vizinhanças | `calculate_ricci_proxy` → `ricci_mean` | Deformação local de vizinhança (aproximação tática). |
| **Homologia persistente** \(H_0,H_1\) | Filtração de complexos na nuvem 3D de posições | `calculate_persistent_homology` → `h0_persistent`, `h1_persistent` | Topologia da trajetória (órbita fechada vs fuga/espiral). |
| **Williams (prior estático)** | Score por país / purpose / classe orbital | `calculate_williams_threat` → `williams_threat` | Prior doutrinário **fixico** — não substitui comportamento. |
| **Idade do TLE** | Horas desde época vs `reference_time` / agora | `tle_age_hours` | Qualidade do dado (stale ≠ hostil). |

### 4.2 Relação entre dois objetos (rota / shadowing)

| Teoria | Definição (resumo) | Função | Aplicação SDA |
|--------|--------------------|--------|---------------|
| **Proximidade** | Distância mínima amostrada suspect→asset | `orbital.min_distance_to_assets` → `min_distance_to_military_km` | Geometria de RPO / ameaça a asset protegido. |
| **Cointegração Engle–Granger** | Duas séries compartilham tendência de longo prazo (p-value) | `calculate_cointegration_pvalue` | **Shadowing**: o seguidor “cola” na dinâmica do alvo. |
| **Łukasiewicz** | \(v(p\to q)=\min(1, 1-v(p)+v(q))\) | `calculate_lukasiewicz_implication` | Coerência fuzzy de hipóteses (“se cointegrado, então…”). |
| **Pair risk + attention** | Fusão dist + coint (+ anomalia) | `pair_score.py` | `attention_score = 0.45·anomaly + 0.55·pair_risk`. |

### 4.3 Clima espacial (no vetor de treino)

| Índice / feature | Definição | Por que no ML |
|------------------|-----------|----------------|
| **F10.7** (`f10_7`, `f10_7_adj`) | Fluxo solar 10,7 cm (s.f.u.) | Proxy de EUV → densidade termosfera → **arrasto LEO** |
| **Ap / Kp** (`ap_index`, `kp_mean`) | Atividade geomagnética | Tempestades alteram arrasto e ruído de órbita |
| **SN** (`sunspot_number`) | Manchas solares | Contexto de ciclo solar |
| Rolling 7d (`*_delta_7d`, `*_mean_7d`, `ap_max_7d`) | Variação e pico semanal | Separar clima **transitório** de manobra |
| `geomagnetic_storm` | Flag se Ap_max_7d ≥ 30 | Soft-suppress de HOSTIL por Δa leve sob tempestade |
| `space_weather_available` | 1 se store OK | Modelo sabe se o clima é real ou default |

Fonte e lookup por **data da janela**: `src/space_weather.py`. Doc: [`docs/references/space_weather_ml.md`](docs/references/space_weather_ml.md).

### 4.4 Fusão sob incerteza e priorização

| Ferramenta | Definição / papel | Função |
|------------|-------------------|--------|
| **Isolation Forest** | Isola pontos raros no espaço de features (não supervisionado) | Baseline da série; canal principal de “ruído vs normal” |
| **XGBoost** | Gradient boosting multi-classe | Classes operacionais com pesos assimétricos (HOSTIL custa mais) |
| **Fuzzy Mamdani** | Inferência por regras linguísticas | Calibra confiança (TLE velho, proximidade) |
| **Kelly** | \(f^*\) proporcional a edge × odds | Orçamento de atenção/sensor por alerta |
| **Data quality** | Score de confiabilidade do TLE | `UNRELIABLE_DATA` — ruído de catálogo ≠ tática |

---

## 5. Pipeline de inferência (DAG)

```
TLE history (2014→hoje, 24 sats) + daily CelesTrak + GFZ space weather
        │
        ▼
[1] Data quality (idade, gaps, saltos impossíveis)
        │
        ▼
[2] extract_satellite_features  (engine + SW + geometria)
        │
        ├────────────────────────────┐
        ▼                            ▼
Pares suspect×asset          Isolation Forest (passado only)
(dist + cointegração)                │
        │                            ▼
        │                     anomaly_score (+ Δ 1 dia)
        │                            │
        └────────────┬───────────────┘
                     ▼
              XGBoost + Fuzzy + Kelly
                     │
                     ▼
         attention_score + risk board + alerts JSON
                     │
                     ▼
         Bob (LLM) explica  ·  UI globo  ·  walk-forward (validação)
```

Inspiração arquitetural (não clone de produto): patentes Palantir (DAG, quant→LLM, ontologia de objetos) — ver `docs/references/patentes_palantir.md`.

---

## 6. Validação walk-forward (pré-report)

Em cada data `asof`, o IF treina **somente** com janelas com fim &lt; `asof − holdout` e pontua o alvo.  
Métricas: hit na janela do `t_peak` de report open-source vs **placebos**.

| Resultado (ML atual com space weather) | Interesse (Luch, SY-12, …) | Placebo (TERRA, NOAA-20) |
|----------------------------------------|----------------------------|---------------------------|
| Hit score ≥ 0,50 | **100%** (5/5) | **0%** (0/3) |
| Ruído elevado pré-peak | **100%** | **0%** |
| Lead-time médio 1º hit | **~201 dias** | — |

Sinais que mais “contam a história” nos casos GEO: **Hurst** (persistência) + **Shannon** (desordem de \(\Delta a\)) fundidos pelo **IF**.  
Relatório: [`docs/RELATORIO_WALKFORWARD_PRE_REPORT_ML_NOVO.md`](docs/RELATORIO_WALKFORWARD_PRE_REPORT_ML_NOVO.md).

```bash
python scripts/run_walkforward.py run
python scripts/run_walkforward.py summary
```

---

## 7. Instalação e execução

### 7.1 Ambiente

```bash
cd Athena-SDA
python -m venv .venv

# Windows
.venv\Scripts\activate
# Linux / macOS
source .venv/bin/activate

pip install -r requirements.txt
```

### 7.2 Credenciais (opcional)

```bash
cp .env.example .env   # ou copy no Windows
# WATSONX_* para Bob; SPACETRACK_* se usar API oficial
```

**Nunca** commite `.env` nem tokens.

### 7.3 Dados e modelos (já versionados)

O clone já traz `data/history/epochs.parquet`, `data/space_weather/` e `models/*.joblib`.  
Para re-seed / retreino:

```bash
python scripts/run_anomaly_monitor.py seed-history --hf --start-year 2014
python scripts/run_anomaly_monitor.py seed-space-weather --force --start-year 2014
python -c "from src.models import train_and_save_models; train_and_save_models()"
python scripts/run_anomaly_monitor.py train-baseline --holdout-days 1 --sample-mode hybrid
```

### 7.4 Operação diária

```bash
python scripts/run_anomaly_monitor.py run-daily     # ingest → baseline no passado → score
python scripts/run_anomaly_monitor.py status
```

Alertas: `data/alerts/anomalies_latest.json`.

### 7.5 Dashboard e frontend

```bash
streamlit run app.py                  # http://localhost:8501

# Demo path: sync JSON ML → UI (opcional: --run-daily)
bash scripts/demo_day.sh

cd src/frontend && npm install && npm run dev   # UI tática / globo
# http://127.0.0.1:3000 — Mission board + walk-forward + globo tintado
```

Contrato do board: [`docs/SCHEMA_RISK_REPORT.md`](docs/SCHEMA_RISK_REPORT.md).

---

## 8. Estrutura do repositório

```
Athena-SDA/
├── app.py                            # Dashboard Streamlit
├── scripts/
│   ├── run_anomaly_monitor.py        # seed, SW, daily, score
│   └── run_walkforward.py            # validação past-only
├── src/
│   ├── config.py                     # FEATURE_COLUMNS / paths
│   ├── engine.py                     # Teorias quantitativas
│   ├── models.py                     # extract, train, predict
│   ├── space_weather.py              # GFZ F10.7 / Ap / Kp
│   ├── anomaly_monitor.py            # série=passado · score=hoje
│   ├── walkforward.py                # pré-report
│   ├── tle_store.py                  # history + ingest
│   ├── pair_score.py                 # suspect × asset
│   ├── orbital.py · fuzzy.py · bob.py · pipeline.py
│   └── frontend/                     # UI tática (Vite/React)
├── models/                           # IF, XGB, RKHS, métricas
├── data/
│   ├── history/epochs.parquet        # ~13 MB, ~12,5 anos, 24 sats
│   ├── space_weather/                # clima diário
│   ├── catalog/                      # watchlist + events WF
│   ├── features/                     # janelas de treino (auditoria)
│   └── alerts/                       # diário + walkforward
├── docs/                             # relatórios e fundamentação
├── requirements.txt
└── .env.example
```

---

## 9. Honestidade científica (pitch / jurados)

| Afirmamos | Não afirmamos |
|-----------|----------------|
| TLE e clima são **dados públicos reais** | Que o XGB “prova” hostilidade classificada |
| Math + IF detectam **desvio de regime** na série | Que accuracy ~95% = detecção de espionagem |
| Walk-forward mostra ruído **antes** de reports open-source | Oráculo de intenção |
| Cache HF tem **GB**; repo tem **store filtrado** | Que o Git “perdeu” os gigas do download |

**Frase recomendada:**  
> *“Baixamos o histórico TLE multi-ano (cache ~15 GB), filtramos 24 objetos de interesse (~250k épocas, 2014–2026), injetamos clima GFZ, extraímos um vetor matemático de ruído e treinamos Isolation Forest no passado da série. Validamos lead-time em casos documentados (Luch, Shiyan) com placebos.”*

---

## 10. Documentação adicional

| Documento | Conteúdo |
|-----------|----------|
| [`docs/RELATORIO_COMPLETO_ML_ATHENA_SDA.md`](docs/RELATORIO_COMPLETO_ML_ATHENA_SDA.md) | ML, bases, ponderação solar/rotas, IBM SSA |
| [`docs/RELATORIO_WALKFORWARD_PRE_REPORT_ML_NOVO.md`](docs/RELATORIO_WALKFORWARD_PRE_REPORT_ML_NOVO.md) | Eventos, lead-time, features que dispararam |
| [`docs/PROTOCOLO_DETECCAO_DIARIA.md`](docs/PROTOCOLO_DETECCAO_DIARIA.md) | Série vs hoje |
| [`docs/references/fundamentacao_matematica.md`](docs/references/fundamentacao_matematica.md) | Formulação das teorias |
| [`docs/references/framework_matematico_completo.md`](docs/references/framework_matematico_completo.md) | Math + implementação |
| [`docs/references/space_weather_ml.md`](docs/references/space_weather_ml.md) | F10.7/Ap/Kp no vetor |
| [`docs/references/patentes_palantir.md`](docs/references/patentes_palantir.md) | Mapa patentes → módulos |
| [`docs/SESSION_HANDOFF.md`](docs/SESSION_HANDOFF.md) | Estado e handoff de sessão |
| [`PROJETO.md`](PROJETO.md) / [`PROJETO_COMPLETO.md`](PROJETO_COMPLETO.md) | Documento mestre do desafio |

---

## 11. Segurança

- Segredos **somente** em `.env` / variáveis de ambiente  
- `.gitignore` bloqueia `.env`, `node_modules`, caches, CSV duplicado e raw GFZ  
- Tokens na área de trabalho **não** devem ser commitados  

---

## 12. Licença e citação de dados

- Código do projeto: conforme repositório.  
- **GFZ** Kp/Ap/F10.7: citar Matzka et al. / termos GFZ (CC BY 4.0 para índices publicados).  
- **TLE**: catálogos públicos (CelesTrak / espelhos Space-Track); uso de acordo com os provedores.  
- Patentes Palantir: **inspiração metodológica**, não afiliação nem produto oficial.

---

*Athena-SDA — quant + ML + dados reais para Space Domain Awareness.*
