# Athena-SDA 🛰️

**Space Domain Awareness (SDA) Copilot** — embasamento **quantitativo + ML** para detecção de anomalias orbitais, rastreamento de risco (aproximação / shadowing / conjunção) e priorização de atenção, com copiloto IBM Granite (watsonx.ai).

> IBM SkillsBuild AI Builders Challenge — tema *Advance Space Exploration with AI*.  
> Foco narrativo: **tecnologia de inteligência / SDA militar** (espírito Palantir), não “tracker civil genérico”.

O front (globo 3D, board) é a **vitrine**. O argumento do projeto é a **coluna quant + ML + pesquisa** (patentes + teorias) e como aplicamos isso a uma **watchlist militar-first**.

> **Continuar em outra sessão:** leia [`docs/SESSION_HANDOFF.md`](docs/SESSION_HANDOFF.md) (estado, decisões, plano do dia seguinte, comandos, armadilhas).

---

## O que o sistema faz

1. **Ingere** histórico orbital (seed / Hugging Face TLE history / CelesTrak diário)
2. **Extrai** features do framework matemático (Shannon, Hurst, Kolmogorov, CUSUM, cointegração, …)
3. **Detecta anomalias** com Isolation Forest treinado no **passado** e score no **dia**
4. **Classifica ameaça** com XGBoost (NORMAL / ANÔMALO / SUSPEITO / HOSTIL)
5. **Calibra** com Fuzzy Mamdani (idade do TLE, proximidade, entropia…)
6. **Prioriza atenção/sensores** com critério de Kelly
7. **Explica** com o copiloto **Bob** (Granite ou briefing local) — **depois** do quant, não no lugar dele

---

## Pesquisa por trás (não “saiu do nada”)

A arquitetura **não inventa** o pipeline de inteligência do zero. Ela **traduz** metodologias publicadas (patentes Palantir e literatura quantitativa) para SDA com TLE público, de forma **reproduzível e open**.

### Patentes Palantir → o que herdamos → o que melhoramos na aplicação

| Referência | Ideia original | No Athena | Nossa aplicação / melhoria |
|------------|----------------|-----------|----------------------------|
| **US 2023/0050870 A1** AI Meta-Constellation | DMP + AIP, micro-modelos, insight-first downlink | Micro-modelos IF/XGB/Fuzzy; alertas em vez de dump de TLE | Solo + watchlist militar; hot-swap de baseline diária/semanal |
| **US 2024/0394296 A1** LLM + Geospatial | 4 etapas: filtro físico → ML quant → LLM descritivo → score | DQ → IF/XGB → Bob → fuse/report | SDA orbital (não real estate); Bob só explica scores já calculados |
| **US 12,657,514 B2** Sensor correlation | Data API + Inference API + **DAG** | `pipeline.py` / `anomaly_monitor.py` | Cadeia TLE→features→ML→fuzzy→Kelly fixa e auditável |
| **US 12,450,265 B2** Time-series geo | Trajetórias (espaço×tempo), compressão p/ UI | Histórico **~12 anos (2014→hoje)** + injeção diária + globo SGP4 | Foco em elementos Kepler + comportamento, não só lat/lon |
| **US 12,374,011 B2** Ontology map | Objetos de inteligência + filtros no mapa | Asset / suspect / baseline + threat board | Ontologia SDA (proteger vs caçar), não GIS genérico |

Detalhes e figuras: `docs/references/patentes_palantir.md`.

### Posicionamento

> **Herança metodológica** (como organizar inteligência) + **coluna quant explícita** (como medir órbita) + **ML de anomalia** (como generalizar o “normal”) + **IA generativa só na ponta** (como falar com o analista).

---

## Por que cada ferramenta quantitativa?

Cada score existe por um **motivo de SDA**. Documentação longa: `docs/references/fundamentacao_matematica.md` e `framework_matematico_completo.md`. Resumo executivo:

### Comportamento de **um** objeto (série temporal de elementos)

| Ferramenta | Pergunta que responde | Por que importa militarmente | Onde no código |
|------------|----------------------|------------------------------|----------------|
| **Entropia de Shannon** \(H(\Delta a)\) | A variação de altitude é **previsível** ou **caótica**? | Manobra / controle espalha \(\Delta a\); órbita passiva concentra | `engine.calculate_shannon_entropy` → feature + Fuzzy |
| **Kolmogorov (proxy zlib)** | A trajetória “parece lei física simples” ou **controle complexo**? | Evasão / RPO gera padrões que **comprimem mal** | `calculate_kolmogorov_proxy` |
| **Expoente de Hurst** | Há **tendência persistente** (baixo empuxo) ou ruído/reversão? | Propulsão iônica sutil não aparece como “salto”, mas como \(H>0.5\) | `calculate_hurst_exponent` |
| **L1-CUSUM** | **Quando** a série quebrou em relação ao baseline recente? | Marca início de manobra / change-point | `calculate_kernel_l1_cusum` + contagem de manobras |
| **ADF** | A série deixou de ser “estacionária” no sentido estatístico? | Apoio a quebra de regime | `calculate_adf_pvalue` |
| **Mandelbrot / cauda** | Os extremos de \(\Delta a\) são “ruído normal” ou **impulsos raros**? | Queima química vs micro-arrasto | `calculate_mandelbrot_tail_anomaly` |
| **Isolation Forest** | Este vetor de features é **atípico** vs o passado treinado? | Anomalia **não supervisionada** no monitoramento diário | `models.py` / `anomaly_monitor.py` |
| **XGBoost** | Dado o vetor (+ anomaly), qual **classe de ameaça**? | Normal → Hostil com probabilidades | `models.predict_threat` |

### Relação entre **dois** objetos (espionagem / colisão / RPO)

| Ferramenta | Pergunta | Por que não basta olhar um satélite | Onde |
|------------|----------|-------------------------------------|------|
| **Proximidade / range** | Quão perto de um **asset protegido**? | HOSTIL sem geometria vira falso alarme | `orbital.min_distance_to_assets` |
| **Cointegração** | Os SMA de A e B **andam juntos** no tempo? | **Shadowing**: o seguidor “cola” na dinâmica do alvo | `engine.calculate_cointegration_pvalue` |
| **Łukasiewicz** \(v(p\to q)\) | A hipótese “se cointegrado, então persistência (Hurst)” é **coerente**? | Valida tese lógica com verdades parciais \([0,1]\) | `calculate_lukasiewicz_implication` |
| **TCA / route cross** | Qual a **mínima distância no tempo** (conjunção)? | Risco de colisão / aproximação futura | frontend `orbit-crossing` + roadmap backend |

**Por que cointegração (em uma frase):**  
correlação pontual mente; **cointegração** pergunta se duas séries compartilham tendência de longo prazo — assinatura clássica de um objeto que **mantém formação / perseguição** em relação a outro (cenário de inspeção orbital / shadowing).

**Por que Shannon (em uma frase):**  
um satélite só com arrasto tem \(\Delta a\) “chato” (baixa entropia); manobras e controle deixam a sequência de mudanças **mais informacionalmente rica** (alta entropia).

### Fusão sob incerteza e priorização

| Ferramenta | Papel |
|------------|--------|
| **Fuzzy Mamdani** | TLE velho **baixa** confiança; proximidade crítica **sobe** severidade — calibra o ML |
| **Fusão XGB ⊕ Fuzzy** | XGB é primário; fuzzy escala com geometria (`pipeline.fuse_xgb_fuzzy`) |
| **Kelly** | Quanto “orçamento de atenção/sensor” alocar a este alerta |
| **Williams** | Prior **estático** (país / purpose / órbita polar) — não substitui comportamento |
| **Data quality** | Ruído de catálogo ≠ hostilidade (etapa ① estilo patente LLM+GIS) |

### Tier secundário (sinal auxiliar, não narrativa principal)

Ricci (proxy), Homologia/TDA (proxy se sem `ripser`), Chern-Simons (desvio de \(\mathbf h=\mathbf r\times\mathbf v\)), RKHS (typicality vs referência). Continuam no vetor de features; o pitch e o report enfatizam **Tier A/B** acima.

---

## Pipeline real (código) — DAG de micro-modelos

```
TLE history (watchlist 2014→hoje) + daily inject + space weather (GFZ)
        │
        ▼
[1] Data quality (idade TLE, gaps, saltos)
        │
        ▼
[2] Feature Extractor quant + SW  (engine + models + space_weather)
        │
        ├──────────────────────────────┐
        ▼                              ▼
Proximidade + Cointegração      Isolation Forest (baseline = SÉRIE passada)
(pair_score / orbital)                 │
        │                              ▼
        │                       anomaly_score (+ Δ vs ontem)
        │                              │
        └──────────────┬───────────────┘
                       ▼
                XGBoost multi-class
                       │
                       ▼
                Fuzzy Mamdani + Kelly + attention (0.45 anom + 0.55 pair)
                       │
                       ▼
         Bob (LLM) explica + recomenda
         UI: globo + mission board
         Validação: walk-forward pré-report
```

Isso espelha o **DAG de inferência** (patente de sensor correlation) e as **4 etapas** LLM+GIS (filtro → quant → texto → decisão).

### Watchlist militar-first (foco do treino)

Não treinamos “o céu inteiro”. Treinamos e monitoramos uma **frota curada** (`data/catalog/watchlist.json`, **24 NORADs**):

| Papel | Função |
|-------|--------|
| **asset** | Plataformas a proteger (proximidade / Kelly) |
| **suspect** | Interesse (recon/SIGINT/RPO/shadowing) |
| **baseline** | Civis estáveis — ancoram o Isolation Forest |

### Dados: o que se baixa vs o que fica no repo

O seed **baixa** o histórico TLE grande (Hugging Face) e **guarda só o filtro** da watchlist. Por isso o PC pode ter **vários GB em cache** e o GitHub só **dezenas de MB** de dados de ML — isso é intencional.

```
HF space-track-tle-history  (~0,5–1 GB/ano no cache; total cache ~7 GB típico)
        │  filtro: só NORADs da watchlist (anos 2014, 2015, …)
        ▼
data/history/epochs.parquet   (~13 MB, ~250k épocas)
        │  **NÃO são só 2 anos de treino**
        │  cobertura real: **2014-01-01 → 2026-07** (~**12,5 anos**)
        +
CelesTrak CATNR diário        → data/daily/ + append no history
        +
GFZ F10.7 / Ap / Kp           → data/space_weather/daily.parquet (mesmo range 2014+)
        +
modelos treinados             → models/*.joblib (~5 MB)
        │  IF monitor: amostragem **hybrid** na série longa (2014→ontem)
        │  walk-forward: folds em eventos 2015–2023 com treino só no passado
```

| Onde | Tamanho típico | O que é |
|------|----------------|---------|
| `~/.cache/huggingface/.../space-track-tle-history` | **vários GB** | download bruto (todos os objetos do ano) — **não** vai pro Git |
| `data/history/epochs.parquet` | **~13 MB** | TLE reais **filtrados** (24 sats, **~12 anos**) — **sim**, no Git |
| `data/space_weather/` | **~MB** | índices solares/geomagnéticos GFZ (2014+) — **sim** |
| `models/` | **~5 MB** | IF + XGB + RKHS já treinados na série longa — **sim** |
| `data/alerts/walkforward/` | **~MB** | validação pré-report (Luch, SY-12, placebos) — **sim** |

> **Nota:** docs antigas falavam em “~2 anos (2024–2026)”. O seed atual e o treino usam **bem mais**: history store **2014→hoje**.

**Fontes (reais, públicas):**

| Dado | Fonte | Uso |
|------|--------|-----|
| TLE histórico | HF [`juliensimon/space-track-tle-history`](https://huggingface.co/datasets/juliensimon/space-track-tle-history) (espelho tipo Space-Track) | série 2014+ |
| TLE diário | [CelesTrak](https://celestrak.org) GP `CATNR` | ponta da série |
| Clima espacial | [GFZ Potsdam](https://kp.gfz-potsdam.de/) Kp/Ap/F10.7 (+ NOAA F10.7 opcional) | features de arrasto vs manobra |
| Eventos WF | Open source (Gunter, CSIS, imprensa) em `events_walkforward.json` | âncoras de report, **não** labels classificados |

**Comandos de dados:**

```bash
# Histórico (1ª vez: baixa anos HF → cache GB → grava só watchlist)
python scripts/run_anomaly_monitor.py seed-history --hf --start-year 2014

# Clima solar/geomagnético
python scripts/run_anomaly_monitor.py seed-space-weather --force --start-year 2014

# Ciclo diário: ingest TLE → baseline no passado → score de hoje
python scripts/run_anomaly_monitor.py run-daily

# Walk-forward (predição pré-report, IF só no passado de cada asof)
python scripts/run_walkforward.py run
python scripts/run_walkforward.py summary
```

Docs: `docs/PROTOCOLO_DETECCAO_DIARIA.md`, `docs/references/space_weather_ml.md`,  
`docs/RELATORIO_COMPLETO_ML_ATHENA_SDA.md`, `docs/RELATORIO_WALKFORWARD_PRE_REPORT_ML_NOVO.md`.

### Honestidade sobre escala

| Camada | Demo / hackathon (estado atual) | Roadmap |
|--------|----------------------------------|---------|
| Objetos | Watchlist **24** militar-first | Expandir catálogo com mesma ontologia |
| Histórico / treino | **~12 anos (2014→hoje)**, ~250k épocas filtradas + daily | Space-Track API oficial |
| Clima | GFZ diário no vetor ML (12 features) | OMNI2 / validação cruzada NOAA |
| Labels HOSTIL | Heurísticas + fuse (não “verdade absoluta”) | Labels fracos + validação analista |
| Validação | Walk-forward vs reports open-source + placebos | Mais eventos + conjunção física |
| Propagação | SGP4 no front; Kepler/aprox no backend demo | SGP4 unificado no pair score |
| Bob | Template / watsonx | Sempre **pós-quant** |

---

## Instalação

```bash
cd Athena-SDA
python -m venv .venv

# Windows
.venv\Scripts\activate
# Linux/macOS
source .venv/bin/activate

pip install -r requirements.txt
```

### Credenciais (opcional)

```bash
copy .env.example .env   # Windows
# edite .env com WATSONX_* e/ou SPACETRACK_*
```

**Nunca** commite `.env` nem senhas no código.

### Treinar modelos

```bash
python -c "from src.models import train_and_save_models; train_and_save_models()"
```

Gera `models/isolation_forest.joblib`, `xgboost_model.joblib`, `rkhs_reference.joblib`, `training_metrics.json`.

### Rodar dashboard

```bash
streamlit run app.py
```

Abra `http://localhost:8501`.

### Dados reais (já versionados no clone)

O repositório já inclui `data/history/epochs.parquet`, `data/space_weather/`, e `models/*.joblib`.  
Para **re-seed** ou atualizar:

```bash
python scripts/run_anomaly_monitor.py seed-history --hf --start-year 2014
python scripts/run_anomaly_monitor.py seed-space-weather --force
python -c "from src.models import train_and_save_models; train_and_save_models()"
python scripts/run_anomaly_monitor.py train-baseline --sample-mode hybrid
```

(Opcional) Space-Track oficial: conta + `.env` e `python download_spacetrack.py`.

### Monitor de anomalias (passado + diário)

```bash
python scripts/run_anomaly_monitor.py seed-history --hf --start-year 2014
python scripts/run_anomaly_monitor.py seed-space-weather
python scripts/run_anomaly_monitor.py ingest-daily          # TLE do dia (CelesTrak CATNR)
python scripts/run_anomaly_monitor.py train-baseline        # IF na SÉRIE (holdout = ontem)
python scripts/run_anomaly_monitor.py score                 # compara última janela vs baseline
python scripts/run_anomaly_monitor.py run-daily             # protocolo completo (retreina + score)
python scripts/run_anomaly_monitor.py status
python scripts/run_walkforward.py run                       # validação pré-report
```

Alertas: `data/alerts/anomalies_latest.json`.  
WF: `data/alerts/walkforward/walkforward_latest.json`.

Frontend tático (globo + board): `src/frontend` — `npm install && npm run dev`.

---

## Estrutura

```
Athena-SDA/
├── app.py                         # Dashboard Streamlit
├── scripts/run_anomaly_monitor.py # seed / daily / SW / score
├── scripts/run_walkforward.py     # validação past-only
├── src/
│   ├── config.py                  # FEATURE_COLUMNS (+ space weather)
│   ├── engine.py                  # Shannon, Hurst, CUSUM, …
│   ├── models.py                  # extract / train / predict
│   ├── space_weather.py           # GFZ F10.7/Ap/Kp
│   ├── anomaly_monitor.py         # série=passado → score=hoje
│   ├── walkforward.py             # pre-report
│   ├── tle_store.py               # history + ingest
│   ├── pair_score.py              # suspect × asset
│   ├── orbital.py / fuzzy.py / bob.py
│   └── frontend/                  # UI tática (globo)
├── models/                        # IF, XGB, RKHS (treinados)
├── data/
│   ├── history/epochs.parquet     # TLE watchlist (~13 MB no Git)
│   ├── space_weather/             # clima diário
│   ├── catalog/                   # watchlist + events WF
│   └── alerts/                    # score diário + walkforward
├── docs/                          # relatórios ML, protocolo, WF
└── .env.example
```

---

## Chat Bob — exemplos

- `Quais alertas ativos?`
- `Briefing do #44231`
- `Histórico do #2001`
- `Aproximações do #44231`
- `Clima espacial`

---

## Segurança

- API keys e senhas Space-Track **somente** via variáveis de ambiente / `.env`
- `.gitignore` bloqueia `.env`, venv e caches
- Se alguma senha já vazou em versão antiga do repo, **troque a senha imediatamente**

---

## Referências

| Documento | Conteúdo |
|-----------|----------|
| `docs/RELATORIO_COMPLETO_ML_ATHENA_SDA.md` | ML, bases, math, ponderação solar/rotas, IBM |
| `docs/RELATORIO_WALKFORWARD_PRE_REPORT_ML_NOVO.md` | WF com ML atual: lead-time, features, placebos |
| `docs/PROTOCOLO_DETECCAO_DIARIA.md` | Série=passado; hoje=comparação |
| `docs/references/space_weather_ml.md` | F10.7/Ap/Kp no vetor |
| `docs/references/patentes_palantir.md` | Patentes Palantir → módulos |
| `docs/references/fundamentacao_matematica.md` | Formulação das teorias |
| `docs/SESSION_HANDOFF.md` | Estado da sessão / handoff |
| `PROJETO.md` / `PROJETO_COMPLETO.md` | Documento mestre do desafio |
| [juliensimon/space-datasets](https://github.com/juliensimon/space-datasets) | Pipelines HF de TLE/SATCAT |

**Citar no pitch:** patentes como *inspiração arquitetural*; teorias como *instrumentos de medida*; Athena como *aplicação SDA militar-first com quant + ML + copiloto pós-quant*. Dados: *TLE e clima reais; cache HF grande no PC; repo com store filtrado + modelos*.
