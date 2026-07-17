# Athena-SDA 🛰️

**Space Domain Awareness (SDA) Copilot** — pipeline híbrido de ML + lógica fuzzy + copiloto IBM Granite (watsonx.ai).

> IBM SkillsBuild AI Builders Challenge — tema *Advance Space Exploration with AI*.

---

## O que o sistema faz

1. **Ingere** históricos orbitais (demo sintético + opcional TLE real CelesTrak/Space-Track)
2. **Extrai** 25+ features do framework matemático (Shannon, Hurst, Kolmogorov, CUSUM, ADF, RKHS, Ricci, Homologia, Chern-Simons, Williams, cointegração…)
3. **Detecta anomalias** com Isolation Forest
4. **Classifica ameaça** com XGBoost (NORMAL / ANÔMALO / SUSPEITO / HOSTIL)
5. **Calibra** com Fuzzy Mamdani (TLE age, proximidade, entropia…)
6. **Prioriza sensores** com critério de Kelly
7. **Explica** com o copiloto **Bob** (Granite ou briefing local + tools)

Arquitetura inspirada em patentes Palantir (LLM+GIS US 2024/0394296, Meta-Constellation, Inference DAG).

---

## Pipeline real (código)

```
Catálogo (demo / TLE)
        │
        ▼
Feature Extractor (src/models.py + src/engine.py)
        │
        ▼
Proximidade orbital + Cointegração (src/orbital.py, src/pipeline.py)
        │
        ▼
Isolation Forest ──► anomaly_score
        │
        ▼
XGBoost multi-class ──► proba / classe
        │
        ▼
Fuzzy Mamdani ──► calibração + confiança
        │
        ▼
Fusão XGB⊕Fuzzy + Kelly
        │
        ▼
Dashboard Streamlit + Bob (briefing / tools)
```

### Honestidade sobre escala

| Camada | Demo local | Produção (roadmap) |
|--------|------------|---------------------|
| Objetos | ~18 satélites curados | Catálogo Space-Track (~30k) |
| Histórico | 30 dias sintéticos + seeds CelesTrak | GP History real |
| Propagação | Kepler simplificado | SGP4 / skyfield |
| Bob | Template local + tools | watsonx Granite |

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

---

## Estrutura

```
Athena-SDA/
├── app.py                 # Dashboard Streamlit
├── src/
│   ├── config.py          # Schema de features, paths
│   ├── engine.py          # 16 teorias matemáticas
│   ├── models.py          # Extract / train / predict
│   ├── pipeline.py        # DAG completo de inferência
│   ├── orbital.py         # Proximidade / geometria
│   ├── fuzzy.py           # Mamdani
│   ├── bob.py             # Copiloto + tools
│   └── utils.py           # Mock TLE / shadowing
├── models/                # Artefatos joblib + métricas
├── data/                  # TLE seeds / histórico
├── docs/references/       # Math + patentes
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

- Framework matemático: `docs/references/framework_matematico_completo.md`
- Patentes Palantir: `docs/references/patentes_palantir.md`
- Documento mestre: `PROJETO_COMPLETO.md`
