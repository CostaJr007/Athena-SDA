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
| **US 12,450,265 B2** Time-series geo | Trajetórias (espaço×tempo), compressão p/ UI | Histórico 2 anos + injeção diária + globo SGP4 | Foco em elementos Kepler + comportamento, não só lat/lon |
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
TLE history (2y watchlist) + daily inject
        │
        ▼
[1] Data quality (idade TLE, gaps, saltos)
        │
        ▼
[2] Feature Extractor quant  (src/engine.py + src/models.py)
        │
        ├──────────────────────────────┐
        ▼                              ▼
Proximidade + Cointegração      Isolation Forest (baseline passado)
(src/orbital.py, pipeline)             │
        │                              ▼
        │                       anomaly_score
        │                              │
        └──────────────┬───────────────┘
                       ▼
                XGBoost multi-class
                       │
                       ▼
                Fuzzy Mamdani
                       │
                       ▼
            Fuse + Kelly + report
                       │
                       ▼
         Bob (LLM) explica + recomenda
         UI: globo + mission board
```

Isso espelha o **DAG de inferência** (patente de sensor correlation) e as **4 etapas** LLM+GIS (filtro → quant → texto → decisão).

### Watchlist militar-first (foco do treino)

Não treinamos “o céu inteiro”. Treinamos e monitoramos uma **frota curada**:

| Papel | Função |
|-------|--------|
| **Protected assets** | O que a doutrina “protege” (proximidade/Kelly) |
| **Adversary / suspect** | Plataformas de interesse (manobra, shadowing) |
| **Baseline control** | Poucos civis estáveis para ancorar o IF |

Histórico ~**2 anos** (HF `space-track-tle-history` filtrado) + **injeção diária** (CelesTrak / HF latest) → anomalias e ruídos de aproximação/distância.  
Ver: `scripts/run_anomaly_monitor.py`, `src/anomaly_monitor.py`, `src/tle_store.py`.

### Honestidade sobre escala

| Camada | Demo / hackathon | Roadmap |
|--------|------------------|---------|
| Objetos | Watchlist ~15–25 (militar-first) | Expandir catálogo com mesma ontologia |
| Histórico | 2 anos HF filtrado + daily | GP History / Space-Track API |
| Labels HOSTIL | Heurísticas + fuse (não “verdade absoluta”) | Labels fracos + validação analista |
| Propagação | SGP4 no front; Kepler/aprox no backend demo | SGP4 unificado no score de par |
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

### Dados reais (opcional)

```bash
# Seeds públicos CelesTrak + histórico aproximado
python generate_astro_history.py

# Space-Track (requer conta + .env)
python download_spacetrack.py
```

Depois retreine: o treino **híbrido** usa CSV real se existir e aumenta com cenários sintéticos de ameaça.

### Monitor de anomalias (passado + diário)

```bash
python scripts/run_anomaly_monitor.py seed-history          # CSV local (+ --hf para history HF)
python scripts/run_anomaly_monitor.py ingest-daily          # TLE do dia (CelesTrak)
python scripts/run_anomaly_monitor.py train-baseline        # IF no passado (holdout do dia)
python scripts/run_anomaly_monitor.py score                 # score da janela mais recente
python scripts/run_anomaly_monitor.py run-daily             # ingest + score (+ retrain se precisar)
python scripts/run_anomaly_monitor.py status
```

Alertas: `data/alerts/anomalies_latest.json`.

Frontend tático (globo + board): `src/frontend` — `npm install && npm run dev`.

---

## Estrutura

```
Athena-SDA/
├── app.py                      # Dashboard Streamlit
├── scripts/run_anomaly_monitor.py
├── src/
│   ├── config.py               # Schema de features, paths
│   ├── engine.py               # Teorias quantitativas (Shannon, Hurst, …)
│   ├── models.py               # Extract / train / predict
│   ├── pipeline.py             # DAG completo de inferência
│   ├── anomaly_monitor.py      # Treino passado + score diário
│   ├── tle_store.py            # Histórico unificado + ingest
│   ├── orbital.py              # Proximidade / geometria
│   ├── fuzzy.py                # Mamdani
│   ├── bob.py                  # Copiloto + tools
│   ├── frontend/               # UI tática (globo live)
│   └── utils.py                # Mock TLE / shadowing
├── models/                     # joblib + métricas
├── data/history|daily|alerts/  # Store do monitor
├── docs/references/            # Math + patentes (detalhe)
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
| `docs/references/patentes_palantir.md` | Patentes Palantir (Meta-Constellation, LLM+GIS, DAG, tiles, ontology) |
| `docs/references/fundamentacao_matematica.md` | Formulação das teorias |
| `docs/references/framework_matematico_completo.md` | Math + trechos de implementação |
| `docs/references/sessions/.../arquitetura_patentes_palantir.md` | Leitura profunda das patentes |
| `PROJETO.md` / `PROJETO_COMPLETO.md` | Documento mestre do desafio |
| [juliensimon/space-datasets](https://github.com/juliensimon/space-datasets) | Pipelines HF de TLE/SATCAT (treino histórico) |

**Citar no pitch:** patentes como *inspiração arquitetural*; teorias como *instrumentos de medida*; Athena como *aplicação SDA militar-first com quant + ML + copiloto pós-quant*.
