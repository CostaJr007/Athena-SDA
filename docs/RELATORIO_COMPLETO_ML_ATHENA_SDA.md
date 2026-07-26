# Relatório completo — ML, bases de dados, matemática e ponderação  
## Athena-SDA (Space Domain Awareness)

**Versão:** 2026-07-26  
**Escopo:** como o machine learning foi construído, de onde vêm os dados, como o ruído orbital é detectado, como clima solar e “rotas” (geometria/pares) são ponderados, e o que **não** foi feito (incl. estudos IBM).

---

## 0. Resumo executivo (1 página)

Athena-SDA **não prevê o futuro** e **não inventa o céu**. Ele:

1. **Ingere TLE reais** de objetos públicos (watchlist militar-first, 24 NORADs).  
2. **Extrai um vetor matemático de ruído** (Shannon, Hurst, Kolmogorov, CUSUM, Mandelbrot, ADF, RKHS, topologia, etc.) sobre janelas da **série** de cada satélite.  
3. **Injeta clima espacial real** (F10.7, Ap, Kp, SN + rolling 7d) no mesmo vetor, no **dia da janela**, para separar arrasto solar de manobra.  
4. **Treina Isolation Forest no passado da série** (holdout: o dia de hoje não entra no baseline).  
5. **Compara a última janela** (dado novo) com esse baseline → `anomaly_score`.  
6. **Pondera atenção operacional** com pares suspect×asset (distância + cointegração) e, em paralelo, classifica com XGBoost + fuzzy + Kelly (camada de doutrina, labels fracos).  
7. **Valida lead-time** com walk-forward em âncoras de reports open-source (ex. Luch/Olymp-K), sem treinar “olhando o futuro”.

| Afirmação para banca | Status |
|----------------------|--------|
| Dados de órbita são reais | **Sim** (TLE history + CelesTrak) |
| Clima solar/geomagnético é real | **Sim** (GFZ + NOAA opcional) |
| Detecção = desvio na série | **Sim** (IF past-train / present-score) |
| Labels HOSTIL = verdade de inteligência | **Não** — heurística / doutrina |
| Paper IBM de ruído foi a base do motor | **Não** (ver §11) |

---

## 1. Arquitetura do pipeline ML

```
┌──────────────────────────────────────────────────────────────────────────┐
│  FONTES DE DADOS                                                         │
│  TLE history (HF space-track mirror) + CelesTrak CATNR diário            │
│  Space weather GFZ (F10.7/Ap/Kp/SN) ± NOAA F10.7                         │
│  Catalog watchlist (roles asset/suspect/baseline)                        │
└────────────────────────────┬─────────────────────────────────────────────┘
                             ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  JANELA DE 20 ÉPOCAS por satélite (série temporal Kepleriana)            │
│  extract_satellite_features()                                            │
│    • Kepler + Δa/Δi + contagem de manobras (CUSUM spikes)                │
│    • Math: Shannon, Kolmogorov, Hurst, Mandelbrot, ADF, L1-CUSUM…        │
│    • Geometria: dist. a assets, cointegração, Łukasiewicz                │
│    • Space weather no timestamp da janela (12 features)                  │
└────────────────────────────┬─────────────────────────────────────────────┘
                             ▼
        ┌────────────────────┴────────────────────┐
        ▼                                         ▼
 Isolation Forest (34 dim)                 XGBoost (38 dim)
  baseline = PASSADO da série               + anomaly_score
  score = ÚLTIMA janela                     classes 0–3 (labels fracos)
  anomaly_score ∈ [0,1]                     pesos assimétricos HOSTIL↑
        │                                         │
        └────────────────────┬────────────────────┘
                             ▼
              Pares suspect×asset + Fuzzy Mamdani + Kelly
              attention = 0.45·anom + 0.55·pair_risk
              DQ gate: TLE ruim → UNRELIABLE (não vira HOSTIL)
                             ▼
              Alerts JSON/CSV + risk board + walk-forward (validação)
```

**Princípio de design (math-first):**  
o ML **não** “aprende o TLE bruto”. Ele aprende a **distribuição de vetores de ruído** que o motor matemático produz a partir de TLE reais. O Isolation Forest responde: *“esta janela se parece com o normal desta série (e deste clima)?”*

---

## 2. Bases de dados — proveniência e tamanho

### 2.1 Órbita (TLE / elementos)

| Item | Valor |
|------|--------|
| Store | `data/history/epochs.parquet` (+ CSV) |
| Volume | **~249 558** épocas |
| Objetos | **24** NORADs (watchlist) |
| Intervalo | **2014-01-01 → 2026-07-25** (UTC) |
| Campos | `norad_id`, `timestamp`, SMA, e, i, RAAN, n, bstar, `tle_age_hours`, `source` |

**Cadeia de origem:**

1. **Seed histórico** — dataset Hugging Face  
   `juliensimon/space-track-tle-history`  
   (parquets anuais filtrados por watchlist; progresso em `data/history/seed_progress.json`).  
   Natureza: repositório público de TLE no estilo **Space-Track / 18 SPCS** (espelho de pesquisa, não a API classificada).

2. **Ingest diário** — **CelesTrak** GP por `CATNR`  
   `https://celestrak.org/NORAD/elements/gp.php?CATNR=…&FORMAT=csv`  
   Anexa a direita da série (dado “de hoje”).

3. **Catálogo** — `data/catalog/watchlist.json`  
   NORADs validados em GP CelesTrak; roles **asset / suspect / baseline** são **doutrina do projeto**, não label oficial de ameaça.

**Física:** SMA ~6 650–42 500 km, mean motion ~1–16 rev/dia — coerente com LEO→GEO reais, não com séries mock.

### 2.2 Clima espacial (solar / geomagnético)

| Item | Valor |
|------|--------|
| Store | `data/space_weather/daily.parquet` |
| Volume | **~4 589** dias (recorte 2014–2026; arquivo GFZ vai a 1932) |
| Fonte primária | **GFZ Potsdam** — `Kp_ap_Ap_SN_F107_since_1932.txt` |
| Fonte auxiliar | **NOAA SWPC** JSON F10.7 (refresh recente) |
| Módulo | `src/space_weather.py` |

Índices diários: F10.7 obs/adj, Ap, Kp médio, sunspot number + features rolling 7 dias.

### 2.3 Eventos de validação (não são labels de treino)

`data/catalog/events_walkforward.json` — âncoras de **reports open-source** (Gunter, CSIS, imprensa) para Luch/Olymp-K, Shiyan, placebos (ex. TERRA).  
Usados só no **walk-forward**, nunca como “y_true” de treino do XGBoost.

### 2.4 O que **não** entra como “base de verdade”

| Artefato | Natureza |
|----------|----------|
| Labels NORMAL…HOSTIL | Heurísticas em `label_features_for_threat` |
| Roles da watchlist | Priorização operacional Athena |
| Accuracy ~95% do XGB | Consistência com heurística, **não** ground-truth de espionagem |
| Sintético (`generate_mock_tle_history`) | Fallback / boost raro; treino atual = **`history_store`** |

---

## 3. Vetor de features — tamanho e composição

### 3.1 Dimensões

| Conjunto | Dimensão | Conteúdo |
|----------|----------|----------|
| `FEATURE_COLUMNS` | **37** | Kepler + math + SW + multi-objeto |
| `IFOREST_COLUMNS` | **34** | 37 − {dist, coint, Łukasiewicz} |
| `XGB_COLUMNS` | **38** | 37 + `anomaly_score` |
| Space weather | **12** | ~35% do IF — clima é first-class |

### 3.2 Blocos do vetor

**A. Kepler instantâneo (5)**  
`semi_major_axis_km`, `eccentricity`, `inclination_deg`, `raan_deg`, `mean_motion_rev_per_day`

**B. Dinâmica temporal (4)**  
`delta_sma_7d_km`, `delta_sma_30d_km`, `delta_inc_30d_deg`, `maneuver_count_30d`  
(manobras ≈ picos de L1-CUSUM em subjanelas)

**C. Motor matemático de ruído (12)**  
Shannon, Kolmogorov proxy, Hurst, Mandelbrot tail, ADF p-value, Williams threat, L1-CUSUM, spectral RKHS, Chern–Simons proxy, Ricci mean, H0/H1 persistentes, `tle_age_hours`

**D. Space weather (12)** — ver §6  
`f10_7`, `f10_7_adj`, `ap_index`, `kp_mean`, `sunspot_number`, rolling 7d, `geomagnetic_storm`, `space_weather_available`

**E. Multi-objeto / “rotas” (3)** — só XGB no treino full  
`min_distance_to_military_km`, `cointegration_pvalue`, `lukasiewicz_implication`

---

## 4. Modelos matemáticos — como o ruído é descrito

Implementação: `src/engine.py`. Fundamentação: `docs/references/fundamentacao_matematica.md` e `framework_matematico_completo.md`.

### 4.1 Por que “ruído” e não “posição”

TLE já é um estado filtrado/publicado. O sinal tático de interesse é a **mudança de regime** da série: manobra, shadowing, station-keeping atípico, ou arrasto. Cada proxy responde a um **tipo** de ruído:

| Proxy | Ideia | Interpretação orbital |
|-------|--------|------------------------|
| **Entropia de Shannon** (1948) | Desordem de \(\Delta a\) em bins | Manobra/controle espalha \(\Delta a\); Kepler estável concentra |
| **Kolmogorov proxy** (1965) | Compressão zlib de tokens U/D/S | Trajetória “simples” comprime; controle complexo resiste |
| **Hurst** R/S (1951) | Persistência de longo prazo | \(H>0.5\): tendência (baixo empuxo); \(H\approx0.5\): ruído; \(H<0.5\): reversão (SK) |
| **L1-CUSUM kernelizado** | Quando a série quebra | Localiza *mudança de regime* no tempo |
| **Mandelbrot (cauda)** | Extremos / leis de potência | Saltos raros vs ruído gaussiano |
| **ADF** | Estacionariedade | Quebra de estacionariedade ⇒ processo mudou |
| **RKHS espectral** | Distância em kernel RBF vs referência | Anomalia no espaço de features embutidas |
| **Ricci (Ollivier proxy)** | Curvatura local entre vizinhanças | Aproximação geométrica tática |
| **Homologia H0/H1** | Topologia da nuvem 3D | Órbita fechada vs fuga/espiral |
| **Chern–Simons proxy** | Helicidade \(\mathbf{v}\cdot\boldsymbol{\omega}\) | Força não conservativa (propulsão) |
| **Cointegração Engle–Granger** | Acoplamento de duas SMAs | Shadowing / perseguição em par |
| **Łukasiewicz** | Implicação fuzzy \(p\to q\) | Lógica de “se próximo então ameaça…” |

### 4.2 Detecção de ruído em camadas (não um único número)

1. **Descrição** — features math transformam a janela em um “perfil de ruído”.  
2. **Distribuição** — Isolation Forest aprende o envelope de perfis **normais no passado**.  
3. **Ponto atual** — última janela vira `anomaly_score = clip(0.5 − decision_function)`.  
4. **Relevância temporal** — \(\Delta\) score vs relatório de ontem (mudança dia-a-dia).  
5. **Geometria de rota** — pair_risk (distância + coint) eleva atenção mesmo se IF for só “médio”.  
6. **Clima** — SW no vetor + soft-suppress de HOSTIL sob tempestade com \(\Delta a\) leve.  
7. **DQ** — TLE stale/gap/jump absurdo ⇒ `UNRELIABLE_DATA` (ruído de catálogo ≠ tática).

### 4.3 Protocolo diário (série vs hoje)

```
SÉRIE até D−holdout  ──treino──►  baseline IF  (= normal + clima histórico)
ÚLTIMA janela (D0)   ──score───►  anomaly_score
Δ vs ontem           ──filtro──►  CHANGE_RELEVANT se salto relevante
```

- `holdout_days=1` (padrão): **ontem e o passado treinam; hoje só compara.**  
- Amostragem **hybrid**: metade da série longa + metade ponta recente (cobertura ~2014→2026 no último treino monitor).  
- Doc: `docs/PROTOCOLO_DETECCAO_DIARIA.md`.

---

## 5. Modelos de machine learning

### 5.1 Isolation Forest (canal principal de “ruído vs normal”)

| Aspecto | Pipeline principal | Monitor diário |
|---------|--------------------|----------------|
| Arquivo | `models/isolation_forest.joblib` | `isolation_forest_monitor.joblib` |
| Features | 34 (IFOREST) | 34 (IFOREST) |
| Contaminação | 0.08 | 0.08 |
| Estimators | 200 | 200 |
| Treino | ~960 janelas history_store | ~1440 janelas hybrid, cutoff D−1 |
| Score | `clip(0.5 − decision_function)` | idem |

**Ideia:** isola pontos raros no espaço de features sem precisar de label HOSTIL.  
O “normal” inclui variação Kepleriana **e** climas solares já vistos no passado.

### 5.2 XGBoost (camada de classificação operacional)

| Aspecto | Valor |
|---------|--------|
| Classes | 0 NORMAL, 1 ANÔMALO, 2 SUSPEITO, 3 HOSTIL |
| Features | 38 (vetor + anomaly_score) |
| Hiperparâmetros | 140 trees, depth 5, lr 0.08, multi:softprob |
| Sample weights | {0:1, 1:1.5, 2:3, 3:5} — erro em HOSTIL custa mais |
| Labels | `label_features_for_threat` (dist, Δa, Hurst, coint, anomaly, **clima**) |
| Métricas internas (último treino) | acc ≈ 0.95, macro-F1 ≈ 0.87, logloss ≈ 0.15 |
| Fonte de treino | **`history_store`** (não full synthetic) |

**Limitação explícita:** métricas de test set medem acordo com a **heurística**, não com ground-truth classificado. Para banca, o canal honesto de detecção é o **IF + walk-forward**, não o accuracy do XGB.

### 5.3 Fuzzy Mamdani + Kelly

- **Fuzzy** (`src/fuzzy.py`): funde distância, anomaly, propósito em escore linguístico (NORMAL…HOSTIL), com clamp e fallback 0.5 se regra não disparar.  
- **Kelly** (`engine.calculate_kelly_allocation`): aloca “atenção/orçamento de análise” \(f^* \propto\) probabilidade × severidade do propósito.

### 5.4 Pares e “rotas” (geometria operacional)

`src/pair_score.py` + `src/orbital.py`:

- Distância mínima aproximada suspect→asset (proxy Kepler, **não** TCA SGP4 completo).  
- Cointegração das SMAs alinhadas (`merge_asof` / caudas).  
- `pair_risk` funde geometria + acoplamento temporal.  
- **Atenção final:**  
  \[
  \text{attention} = 0.45\cdot\text{anomaly\_score} + 0.55\cdot\text{pair\_risk}
  \]
- Par CRITICAL / ELEVATED forte pode marcar `PAIR_ELEVATED` mesmo se IF sozinho não passar do thr 0.55.

Isso é a ponderação **rota/proximidade vs ruído de série**.

---

## 6. Ponderação clima solar vs órbita / rotas

### 6.1 Por que solar entra no mesmo vetor

Arrasto em LEO sobe com **F10.7** e tempestades **Ap/Kp**. Sem SW, \(\Delta a\) + Shannon + CUSUM sob tempestade parecem manobra. Com SW, o IF vê o **mesmo \(\Delta a\) em climas diferentes** e aprende regimes.

### 6.2 As 12 features solares/geomagnéticas

| Feature | Papel na ponderação implícita |
|---------|--------------------------------|
| `f10_7`, `f10_7_adj` | Nível de atividade solar (densidade termosfera) |
| `ap_index`, `kp_mean` | Tempestade geomagnética no dia |
| `sunspot_number` | Contexto de ciclo |
| `*_delta_7d`, `*_mean_7d`, `ap_max_7d` | Dinâmica recente (não só snapshot) |
| `geomagnetic_storm` | Flag Ap_max_7d ≥ 30 |
| `space_weather_available` | 1 = clima real; 0 = defaults quietos |

Lookup: **data UTC da janela** (`reference_time` no walk-forward; now no live).

### 6.3 Ponderação **explícita** nas labels (doutrina)

Em `label_features_for_threat`:

- Se `geomagnetic_storm` ou Ap≥30 ou F10.7≥180 (**high_drag_climate**):  
  - limiares de Δa para HOSTIL/SUSPEITO/ANÔMALO **sobem**;  
  - Δa leve + distante de assets → tende a **NORMAL** (arrasto).  
- Geometria crítica (dist < 25 km + coint / anomaly) **ainda pode** ser HOSTIL — o clima não “absolve” RPO óbvio.

### 6.4 Ponderação **implícita** no IF/XGB

Não há peso manual “30% solar / 70% Kepler”. Os modelos **aprendem** importâncias a partir dos dados. O desenho garante que:

- IF **inclui** SW (clima faz parte do normal);  
- IF **exclui** dist/coint (para não treinar “sempre perto = anômalo” sem contexto multi-objeto no baseline univariado);  
- XGB **inclui** SW + geometria + anomaly (classificação operacional completa).

### 6.5 Diagrama de fusão de atenção

```
anomaly_score (série + math + SW)     pair_risk (rota/proximidade)
              0.45                              0.55
                 \                              /
                  \_____ attention_score ______/
                              |
              + DQ gate + status (ANOMALY / PAIR_ELEVATED / CHANGE_RELEVANT)
                              |
                         risk board / Kelly
```

---

## 7. Como o treino foi feito (números)

### 7.1 Pipeline IF + XGB (`train_and_save_models`)

1. Carrega history store → janelas de 20 épocas, step 5, últimas ~40/sat.  
2. Injeta país/propósito do catálogo, dist a assets, coint, **SW do dia**.  
3. Labels fracos; se quase sem HOSTIL, threat boost sintético leve (no último run: **não** diluiu — history basta).  
4. Fit IF em janelas “normais”; gera `anomaly_score` unificado.  
5. Relabel leve com anomaly; fit XGB com pesos de classe.  
6. Salva `models/*.joblib` + `training_metrics.json`.

**Último estado:** n_samples=960, n_features=38, `training_source=history_store`.

### 7.2 Monitor (`train-baseline` + `score`)

1. Cutoff = now − 1 dia.  
2. Amostra hybrid na série → IF.  
3. Score só última janela; Δ vs `anomalies_{ontem}.json`.  
4. Pares + relatório `data/alerts/anomalies_YYYY-MM-DD.json`.

**Último estado:** 1440 janelas, cobertura window_end **2014-01-04 → 2026-07-25**.

### 7.3 Walk-forward (`src/walkforward.py`)

Em cada `asof` ao longo de um evento:

- IF treinado **só** com janelas com fim < asof − holdout;  
- score do alvo;  
- hit se score elevado **antes** de `t_peak` do report;  
- placebos (ex. TERRA) controlam falso positivo genérico.

Isso responde “detectamos ruído **antes** do report?” sem contaminar o treino.

---

## 8. Fluxo de detecção ponta a ponta (exemplo conceitual)

1. **Série** do YAOGAN-29 com milhares de TLEs reais 2014–2026.  
2. **Baseline** aprende perfis de Shannon/Hurst/Δa sob vários F10.7/Ap.  
3. **Hoje** entra novo TLE CelesTrak → última janela de 20 épocas.  
4. Features: se Δa sobe **com** Ap alto, SW contextualiza; se Δa sobe **com** clima quieto e Hurst alto, IF eleva score.  
5. **Par** vs COSMO-SkyMed: dist baixa + coint → pair_risk alto.  
6. **attention** sobe; status pode ser ANOMALY ou PAIR_ELEVATED.  
7. Analista vê board — não é “prova em tribunal”, é **prioridade SDA embasada em dado público**.

---

## 9. O que é simulado e o que não é (transparência)

| Componente | Real? |
|------------|-------|
| TLE history + daily | **Real** (fontes públicas) |
| F10.7 / Ap / Kp | **Real** (GFZ) |
| Features math | **Derivadas** de dados reais (não inventadas) |
| IF anomaly | **Modelo** treinado em dados reais |
| Labels XGB | **Heurística** |
| Roles watchlist | **Doutrina** |
| Mock TLE | Só se faltar history (não é o path atual) |
| Pair distance | **Proxy** (não TCA oficial) |

---

## 10. Como apresentar aos jurados (script curto)

> “Usamos elementos orbitais públicos reais (histórico tipo Space-Track + CelesTrak) e índices solares/geomagnéticos do GFZ.  
> Transformamos cada janela da série em um vetor de ruído matemático (Shannon, Hurst, CUSUM, etc.) **mais** o clima daquele dia.  
> O Isolation Forest aprende o normal **no passado**; o ponto de hoje é comparado — não re-treinado no próprio dia.  
> Proximidade a ativos (rotas) e clima solar entram na ponderação de atenção e nas regras de arrasto vs manobra.  
> Não afirmamos ground-truth classificado de intenção hostil: afirmamos **detecção de desvio embasada em dados reais** e validação walk-forward em casos open-source como Luch.”

---

## 11. Estudos IBM, ruído e o que foi (ou não) pesquisado

### 11.1 Resposta direta

| Pergunta | Resposta |
|----------|----------|
| O motor Athena foi **implementado a partir** de papers IBM de ruído? | **Não.** |
| Havia menção a IBM no planejamento do projeto? | **Sim, como item opcional de reforço teórico** (bloco 0.6 no organograma de dados/ML), **não como base do código.** |
| Foi feita nesta sessão uma revisão profunda da literatura IBM sobre ruído orbital? | **Não como eixo do design.** Foi feito um **mapeamento pontual** do que a IBM publicou em SSA open-source (abaixo). |
| Há trabalho IBM **relevante** para o tema SDA/ML? | **Sim** — linha Space Tech SSA (com Moriba Jah / UT Austin), open-source `IBM/spacetech-ssa`. |

### 11.2 O que a IBM tem em SSA (contexto externo)

- Projeto open-source **IBM Space Tech – SSA** (`ibm.github.io/spacetech-ssa`, GitHub `IBM/spacetech-ssa`): playground de ML para SSA em LEO (predição de trajetórias ASO, conjunções, etc.), em parceria histórica com pesquisa de Moriba Jah.  
- Foco típico IBM SSA: **predizer onde objetos estão / vão**, conjunções, pipeline experimental ML — **não** o mesmo stack math-first (Shannon–Hurst–CUSUM–RKHS–TDA) do Athena.  
- Anúncios open-source SSA + KubeSat (~2020) para “democratizar” space tech.

### 11.3 De onde **veio** a fundação teórica do Athena

| Linha | Origem no projeto |
|-------|-------------------|
| Shannon, Kolmogorov, Hurst, Mandelbrot, CUSUM, ADF, cointegração | Literatura clássica + `docs/references/fundamentacao_matematica.md` |
| RKHS / Ricci / homologia / Chern–Simons proxies | Framework quant do projeto (proxies implementáveis, não papers IBM) |
| Arquitetura multi-estágio / COP / DAG | Inspiração **Palantir** (patentes mapeadas em `docs/references/patentes_palantir.md`) — **não** produto Palantir |
| SSA + ML genérico | Estado da arte (surveys SSA/ML, práticas de anomaly detection) |
| IBM | Listado como **bibliografia futura opcional** no organograma; **não** citação fundante do `engine.py` |

### 11.4 Honestidade acadêmica recomendada

Se o jurado perguntar “vocês usaram os estudos da IBM?”:

> “Conhecemos a linha IBM Space Tech SSA (open-source com foco em predição de trajetória/LEO).  
> Nosso núcleo é **outro**: features de informação/estocástica/topologia sobre séries TLE reais + Isolation Forest past-train, com clima GFZ e pares geométricos.  
> IBM SSA e Athena são **complementares**, não o mesmo paper reimplementado.  
> Papers IBM/quant/fractal estavam no backlog de reforço teórico (item 0.6), não no caminho crítico de implementação.”

### 11.5 Se quiser aproximar IBM no futuro (opcional)

- Benchmark de predição/erro orbital no estilo spacetech-ssa vs nosso detector de **mudança**.  
- Citar Jah / SSA literature em slide de “estado da arte”.  
- **Não** substituir o math stack por caixa-preta só porque é IBM.

---

## 12. Arquivos-chave do repositório

| Área | Path |
|------|------|
| Features math | `src/engine.py` |
| Extract + train + labels | `src/models.py` |
| Schema features | `src/config.py` |
| Space weather | `src/space_weather.py` |
| Monitor diário | `src/anomaly_monitor.py` |
| Pares / rotas | `src/pair_score.py`, `src/orbital.py` |
| Walk-forward | `src/walkforward.py` |
| TLE store | `src/tle_store.py` |
| Fuzzy / Kelly | `src/fuzzy.py` |
| CLI | `scripts/run_anomaly_monitor.py` |
| Math docs | `docs/references/fundamentacao_matematica.md` |
| Protocolo diário | `docs/PROTOCOLO_DETECCAO_DIARIA.md` |
| Pre-report demo | `docs/DEMOSTRACAO_PREVISAO_PRE_REPORT.md` |
| SW no ML | `docs/references/space_weather_ml.md` |
| Este relatório | `docs/RELATORIO_COMPLETO_ML_ATHENA_SDA.md` |

---

## 13. Comandos de reprodução

```bash
# Clima (GFZ)
python scripts/run_anomaly_monitor.py seed-space-weather --force --start-year 2014

# Baseline na série (passado) + score do hoje
python scripts/run_anomaly_monitor.py train-baseline --holdout-days 1 --sample-mode hybrid
python scripts/run_anomaly_monitor.py score

# Ciclo diário completo
python scripts/run_anomaly_monitor.py run-daily

# Retreino IF+XGB pipeline
python -c "from src.models import train_and_save_models; train_and_save_models()"

# Walk-forward (validação pre-report)
python scripts/run_walkforward.py
```

---

## 14. Conclusões

1. **Bases:** orbitais e solares **reais e rastreáveis**; doutrina e labels **explícitos e fracos**.  
2. **ML:** math-first → IF (ruído vs normal na série) → XGB/fuzzy/Kelly (prioridade) → pares (rotas).  
3. **Ruído:** multi-proxy clássico + distribuição IF + Δ diário + DQ.  
4. **Solar vs rotas:** SW no vetor e nas labels de arrasto; rotas via pair_risk com peso 0.55 na attention.  
5. **IBM:** relevante no ecossistema SSA open-source, **não** foi a fundação implementada do motor de ruído Athena; backlog teórico opcional.  
6. **Para jurados:** vender **detecção de desvio em dados públicos**, não “accuracy de guerra espacial”.

---

*Documento gerado para o projeto Athena-SDA. Pode ser anexado ao pitch, ao repositório e ao handoff de sessão.*
