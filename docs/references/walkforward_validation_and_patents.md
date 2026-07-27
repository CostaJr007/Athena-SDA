# Walk-Forward Historical Validation & Palantir Patent Architecture Reference

**Athena-SDA** · Historical temporal validation of documented maneuvers/RPO · Architecture inspired by public Palantir patent publications.

> **Objective:** Validate that the **Math → ML stack** detects behavioral anomaly signatures *prior to or during* publicly reported event windows — operating strictly without look-ahead leakage.

---

## 1. Core Walk-Forward Methodology (Expanding Window)

```
Timeline →

[===== TRAIN on past only =====] | gap | [SCORE window] | [EVENT documented]
                                 ^                      ^
                            train_cutoff            evaluation_end
```

### Execution Rules:

1. **Strict Holdout:** At each fold \(t\), Isolation Forest (and model calibration) observes data strictly prior to `timestamp < t_cutoff`.
2. **Feature Isolation:** Mathematical features (Shannon, Hurst, CUSUM, cointegration) are computed using time series bounded by the score window — never using future TLE records.
3. **Public Anchors:** Open-source reporting milestones (CSIS/SWF/SpaceNews) define temporal evaluation anchors.
4. **Validation Criteria:** Successful detection is defined by coherent elevation in anomaly scores and mathematical features around event windows relative to placebo controls.

---

## 2. Tested Hypotheses

| ID | Hypothesis | Expected Math Signal | ML / Pair Score |
|----|------------|----------------------|-----------------|
| **H1** | Deliberate maneuver increases altitude disorder | Shannon↑, Kolmogorov↑, CUSUM change-point | anomaly_score↑ |
| **H2** | Low-thrust / persistent drift | Hurst \(> 0.5\) | Anomaly vs passive baseline |
| **H3** | Temporal shadowing / tracking | **Cointegration** p-value↓ between suspect & target | pair_score↑ |
| **H4** | Rendezvous & Proximity Operations (RPO) | Min distance↓, TCA geometry | Fuse + Kelly attention↑ |
| **H5** | Catalog noise / stale data | DQ score↓, TLE age↑ | Gate: do **not** classify as HOSTILE |

---

## 3. Documented Public Anchors for Walk-Forward Validation

| Event Key | Object(s) | Public Window (approx.) | Type | Target / Context | Key Features |
|-----------|-----------|-------------------------|------|------------------|--------------|
| `luch1_intelsat_2015` | Luch/Olymp-K 1 (#40258) | 2015–2019 GEO maneuvers | GEO Shadowing | Intelsat / Commercial slots | Cointegration + Δlong + CUSUM |
| `luch1_athena_fidus_2018` | Luch-1 | ~2018 | GEO Proximity | Athena-Fidus (FR) | Distance + maneuver count |
| `luch2_geo_2023` | Luch-5X / Olymp-K 2 (#55841) | 2023–2025 | GEO Shadowing | Western GEO assets | Same as Luch-1 |
| `sy12_usa_geo` | SY-12 01/02 (#50321/50322) | 2021–2022+ | GEO RPO | USA orbital objects | Pair distance + TCA |

---

## 4. Architectural Patent Alignment

Athena-SDA leverages concepts mapped from public defense patents:

1. **US 2023/0050870 A1 (AI Meta-Constellation):** Watchlist selection acts as an orbital tasking filter.
2. **US 2024/0394296 A1 (LLM + GIS):** 4-stage decision pipeline (Physics → Quant ML → Descriptive LLM → Classifier).
3. **US 12,450,265 B2 (Spatiotemporal Tiling):** 3D trajectory visualization and time-series RDP compression.
4. **US 12,657,514 B2 (DAG & Sensor API):** Data API & Inference API separation.

---
*Athena-SDA Walk-forward & Patent Architecture Reference.*extensions* no JSON de validação (sem poluir a watchlist operacional se não couber).

Arquivo alvo (a criar no código):

```
data/catalog/events_walkforward.json
```

Schema sugerido:

```json
{
  "events": [
    {
      "id": "luch2_geo_2023",
      "norad_ids": [55841],
      "pair_with": null,
      "t_start": "2023-03-12",
      "t_peak": "2023-10-01",
      "t_end": "2024-06-01",
      "type": "shadowing_geo",
      "sources": ["Breaking Defense 2023", "SWF Counterspace"],
      "expected_signals": ["cusum", "shannon", "maneuver_count"]
    }
  ]
}
```

---

## 4. Protocolo walk-forward (passos)

### 4.1 Expanding window (recomendado para demo)

Para cada evento \(E\) com âncora \(t_{peak}\):

1. **Histórico mínimo:** exigir ≥ 60–90 dias de épocas do NORAD (e do par, se houver) **antes** de \(t_{peak}\).
2. **Folds:** a cada \(step\) dias (ex.: 7 ou 14):
   - `train_end = t_i - holdout_days` (holdout 1–7 d evita leakage da janela atual)
   - Treinar IF **só** em janelas de features com `window_end < train_end` (preferir baseline + assets + suspeitos não-evento, ou frota inteira *antes* de \(t_i\)).
   - Score janelas com `window_end ∈ [t_i - W, t_i]`.
3. **Métricas por fold:**
   - `anomaly_score(t)` do suspeito
   - features Tier A (Shannon, Hurst, CUSUM, Kolmogorov)
   - se par: `coint_pvalue`, `min_distance_km`, `tca`
   - `data_quality` (não contar fold se unreliable)
4. **Lead-time:** menor \(t\) com `anomaly_score ≥ θ` **e** DQ ok, relativo a \(t_{peak}\) (dias de antecipação).
5. **Controle (placebo):** mesmo protocolo em **baseline** civil (ex. TERRA, NOAA-20) na mesma época — taxa de falso alarme de referência.

### 4.2 Métricas de validação (o que reportar no hackathon)

| Métrica | Definição | Uso no pitch |
|---------|-----------|--------------|
| **Hit@event** | Score ≥ θ em \([t_{peak}-Δ, t_{peak}+Δ]\) | “detectamos a janela documentada” |
| **Lead-time** | dias entre 1º alerta estável e \(t_{peak}\) | “antecipação relativa ao report” |
| **Feature attribution** | quais math tools cruzaram limiar | “não é caixa-preta — Shannon/CUSUM/…” |
| **Pair confirmation** | coint/dist confirmam single-sat | “assinatura de shadowing, não só manobra solo” |
| **FPR baseline** | alertas em civis estáveis no mesmo fold | honestidade / ruído |

**Não vender:** “detectamos espião com 99% accuracy”.  
**Vender:** “walk-forward em eventos open-source; micro-modelos + math; insight-first alert”.

### 4.3 Onde isso mora no código (roadmap)

| Módulo | Papel |
|--------|-------|
| `data/catalog/events_walkforward.json` | âncoras públicas |
| `src/walkforward.py` (novo) | folds, train cutoff, score series |
| `scripts/run_walkforward.py` | CLI: um evento ou batch |
| `data/alerts/walkforward_{event}.json` | curva temporal + lead-time |
| reusa | `engine.py`, `anomaly_monitor.build_feature_windows`, `catalog` |

Fluxo:

```
HF history (2y+) → epochs
     → walkforward folds
          → IF fit (past only)     [micro-modelo hot-swappable por fold]
          → math features + score
          → report vs event anchor
```

---

## 5. Patentes → extrair o máximo (mapa de tecnologia)

Não copiamos produto Palantir. **Traduzimos** mecanismos patentados para SDA + TLE + math.

### 5.1 Matriz de herança (máxima cobertura)

| Patente | Mecanismo original | No Athena (implementado / a extrair) | Walk-forward |
|---------|-------------------|--------------------------------------|--------------|
| **US 2023/0050870 A1** Meta-Constellation | DMP (solo) + AIP (edge); **micro-modelos**; hot-swap; **insight-first** downlink | DMP = treino/store (`train-baseline`, joblib); AIP = score diário; micro-modelos = IF + XGB + Fuzzy + (futuro) pair scorer; downlink = `anomalies_*.json` não dump TLE | Cada fold = **hot-swap** de baseline IF no tempo (DMP re-fit → AIP score) |
| **US 2024/0394296 A1** LLM + Geospatial | 4 etapas: filtro físico → ML quant → LLM tese → score | ① DQ/bounds ② math+IF+XGB ③ Bob descrição ④ fuse/recomendação | Bob **só** comenta folds/eventos **depois** do quant; nunca define o score |
| **US 12,657,514 B2** Sensor correlation | Data API + Inference API + **DAG** | Data API = `tle_store` canônico; Inference API = `pipeline` / `anomaly_monitor`; DAG fixo auditável features→IF→XGB→Fuzzy→Kelly→(pairs) | DAG idêntico em cada fold (reprodutibilidade) |
| **US 12,450,265 B2** Time-series geo | Trajetórias (X,Y,T); tiles; compressão RDP p/ UI | Séries Kepler+T em `history/epochs`; UI: globo SGP4 + (roadmap) downsample RDP de órbitas no front | Curva `anomaly_score(t)` e trajetória no evento = “tile temporal” do caso |
| **US 12,374,011 B2** Ontology map | Objetos de inteligência + filtros + histogramas | `watchlist.json` roles asset/suspect/baseline; board por role/country/threat | Filtro walk-forward por role; histograma de lead-time / hits por tipo de evento |

### 5.2 Checklist “tecnologia da patente → módulo”

#### Meta-Constellation (070 A1)

- [x] Micro-modelos separados (IF / XGB / Fuzzy)
- [x] Insight-first (alert JSON, não raw dump)
- [x] Watchlist = “seleção de payloads/objetos” para a missão
- [ ] Hot-swap versionado: `models/if_baseline_{asof_date}.joblib` por fold/dia
- [ ] Registry de modelos (meta: contamination, n_windows, cutoff) — parcial em `anomaly_monitor_meta.json`

#### LLM + GIS (296 A1)

- [x] Etapa ① Data quality
- [x] Etapa ② Quant + ML
- [x] Etapa ③ Bob (stub/Granite)
- [ ] Etapa ④ score de decisão **explícito** pós-texto (só calibra, não reescreve quant)
- [ ] Prompt Bob amarra **citação de evento walk-forward** quando houver match temporal

#### Sensor correlation / DAG (514 B2)

- [x] Pipeline em estágios
- [ ] Interfaces formais Data API / Inference API (contratos JSON Schema)
- [ ] DAG de **pares** como nó opcional acionado se `role=suspect` e assets próximos

#### Time-series geo (265 B2)

- [x] Store temporal de épocas
- [x] Front com tempo simulado / órbitas
- [ ] RDP ou decimação de polyline no worker do globo (zoom temporal)
- [ ] Export de “tile” do evento walk-forward (CSV/JSON da curva)

#### Ontology map (011 B2)

- [x] Roles no catálogo
- [ ] Filtros cruzados no board (role × country × anomaly)
- [ ] Histograma de alertas por classe (UI)

### 5.3 DAG canônico (patente 514 + 296 fundidos)

```
[Data API] tle_store.epochs
     │
     ▼
[1] DQ filter                    ← 296 etapa 1 / 070 quality
     │
     ▼
[2] Feature Extractor (engine)   ← math framework (nosso diferencial)
     │
     ├──────────────────┐
     ▼                  ▼
[3a] IF micro-model   [3b] Pair micro-model (coint/dist/TCA)
     │                  │
     └────────┬─────────┘
              ▼
[4] XGB threat micro-model
              ▼
[5] Fuzzy calibration
              ▼
[6] Kelly priority               ← insight-first ranking (070)
              ▼
[7] Bob LLM thesis + recs        ← 296 etapas 3–4 (pós-quant)
              ▼
[8] Ontology board / map         ← 011
```

Walk-forward **repete 1–6** em cada fold; 7–8 só no report final.

---

## 6. Math + ML + evento (uma linha por ferramenta)

| Tool | Papel no walk-forward |
|------|------------------------|
| Shannon \(H(\Delta a)\) | Sobe quando manobra “suja” a série antes/durante o report |
| Hurst | Persistência pré-evento (empuxo sutil) |
| CUSUM | Marca *quando* o regime quebrou (lead-time natural) |
| Kolmogorov proxy | Controle complexo vs arrasto “simples” |
| ADF | Não-estacionariedade da série individual |
| Cointegração | Shadowing (Luch-class) |
| Proximidade / TCA | RPO (SY/SJ-class) |
| IF | Agrega o vetor math: “fora do normal do passado” |
| Fuzzy | Penaliza TLE ruim na janela histórica |
| Kelly | Prioriza qual evento/alerta “vale sensor” |
| Bob | Explica fold + cita fonte aberta do evento |

---

## 7. Ordem de implementação sugerida

1. **Seed HF** com watchlist (cobertura ≥2024; estender anos se evento exigir).  
2. **`events_walkforward.json`** com 2–3 âncoras cobertas pelos dados (ex. Luch-2 2023+, SY-12 se houver TLE).  
3. **`src/walkforward.py`**: expanding window + export JSON de curva.  
4. **Métricas Hit@event + lead-time + placebo baseline**.  
5. **Versionar micro-modelos** por `asof` (patente 070 hot-swap).  
6. **JSON Schema** Data/Inference (patente 514).  
7. **Bob** template: “compatível com padrão documentado em {source}, scores: …”.  
8. UI: um painel “Event replay” (ontology + time-series 265).

---

## 8. Armadilhas

1. **TLE esparso** em GEO pode atrasar detecção — reportar resolução temporal.  
2. **Look-ahead:** proibido usar épocas ≥ cutoff no treino ou em features da decisão.  
3. **Labels HOSTIL** de report jornalístico ≠ ground truth forense.  
4. **Accuracy circular** do treino sintético antigo não substitui walk-forward.  
5. Patentes = **inspiração arquitetural**; não alegar afiliação Palantir.

---

## 9. Prompt de continuidade

```text
Continue Athena-SDA: (1) seed HF se necessário; (2) criar
data/catalog/events_walkforward.json com âncoras Luch/SY;
(3) implementar src/walkforward.py expanding-window reusando
engine + anomaly_monitor; (4) report Hit@event e lead-time;
(5) manter DAG e 4 etapas das patentes no design.
```
