# ATHENA-SDA — Project Document

> **Hackathon:** AI Builders Challenge
> **Theme:** Advance Space Exploration with AI
> **Team:** Athena-SDA
> **Stack:** Python + XGBoost + IBM Granite / Bob + Streamlit + React 3D Globe

---

## 1. WHAT IS ATHENA-SDA?

### Elevator Pitch (30 seconds)

> *"There are over 30,000 objects in Earth's orbit. Human operators cannot monitor all of them manually. Athena-SDA uses machine learning to classify every object by threat tier, combined with IBM Bob as an AI intelligence analyst that explains, prioritizes, and recommends actions in natural language — acting as a space-domain intelligence copilot."*

### Real-World Challenge

| Fact | Consequence |
|------|-------------|
| ~30,000 tracked objects (active satellites + debris) | Impossible to monitor manually |
| Non-cooperative military satellites perform stealth maneuvers | Space operators require pattern detection |
| Public space catalogs (Space-Track/CelesTrak) are raw data | Raw data exists, operational intelligence does not |
| Legacy tracking systems issue alerts | Legacy tools do not **explain, prioritize, or recommend** actions |

### Solution Architecture

A 3-layer intelligence system:

```
LAYER 1 — ML Engine (Perception):   Classifies 30,000 objects into 🟢🟡🟠🔴 tiers
LAYER 2 — Bob Analyst (Reasoning): Explains operational alerts in natural language
LAYER 3 — Dashboard (Interface):    3D Globe + Risk Cards + Bob Analyst Chat
```

---

## 2. FOUNDATIONAL RESEARCH & PATENTS

### 30+ Frontier Patents Mapped

| Source | Count | Highlights |
|--------|-------|------------|
| 🟣 **Palantir Technologies** | 8 patents | AI Meta-Constellation, Sensor Fusion, **LLM + Geospatial**, Ontology Map |
| 🇺🇸 **Lockheed Martin** | 4 patents | Deep NN for satellite tracking, Missile detection, Decoy discrimination |
| 🇺🇸 **Raytheon / GD / L3Harris** | 6 patents | GAN SAR, RL tracking, Military crypto, Phased array |
| 🇨🇳 **China CAST / CASC** | 10 patents | Active orbital defense, Pursuit-evasion, Anti-deception |

### 5 Anchor Patents (Architectural Extraction)

| Patent | Key Concept Extracted |
|--------|-----------------------|
| **US 2023/0050870 A1** (Palantir) | DMP+AIP Architecture: task decomposition → sensor selection → micro-models → insight-first downlink |
| **US 12,450,265 B2** (Palantir) | 3D Tiles (X,Y,T) + RDP algorithm: simplifying time series for rapid visualization |
| **US 12,657,514 B2** (Palantir) | Data API + Inference API + Dynamic DAG: reconfigurable model pipeline |
| **US 2024/0394296 A1** (Palantir) | **4-Stage LLM + GIS:** physical filter → quantitative ML → descriptive LLM → classifier LLM |
| **US 12,374,011 B2** (Palantir) | Ontology + UTF Grid + interactive histograms: geospatial intelligence objects |

---

## 3. DATA ARCHITECTURE

### Primary Source: TLE Data (Space-Track / CelesTrak)

**What is TLE (Two-Line Element):** Standardized format describing satellite orbital elements. Two 69-character lines contain inclination, eccentricity, mean motion, right ascension, and altitude parameters.

**Data Ingest:**
- TLE records for watchlist objects (~250k epochs, 2014–2026)
- **Space Weather (GFZ Potsdam / NOAA):** F10.7 solar flux and geomagnetic Kp/Ap indices
- **UCS Satellite Database & SATCAT:** Country of origin, mission purpose, launch dates

```
TLE Time Series ──▶ Feature Extractor ──▶ ML Training Dataset
                        │
                        ├── semi_major_axis_km
                        ├── eccentricity
                        ├── inclination_deg
                        ├── delta_sma_7d
                        ├── delta_inc_30d
                        ├── maneuver_count_30d
                        ├── min_distance_to_military_km
                        └── country_purpose (military / civil)
```

---

## 4. HOW IT WORKS

### Complete Pipeline Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                       ATHENA-SDA ENGINE                         │
│                                                                 │
│ ① DATA INGEST                                                   │
│   CelesTrak ──▶ Raw TLE History                                 │
│   GFZ Potsdam ─▶ Space Weather (F10.7, Ap, Kp)                   │
│   UCS Database ▶ Purpose & Ownership Catalog                     │
│                         │                                       │
│                         ▼                                       │
│ ② FEATURE EXTRACTOR                                             │
│   TLE → 34 Orbital + Topological + Space Weather Features        │
│   + Multi-Year Historical Baseline                              │
│                         │                                       │
│                         ▼                                       │
│ ③ ANOMALY DETECTOR (Isolation Forest)                           │
│   "Is this object deviating from its historical baseline?"       │
│   Output: anomaly_score (0.0 = normal, 1.0 = highly anomalous)   │
│                         │                                       │
│                         ▼                                       │
│ ④ THREAT CLASSIFIER (XGBoost + Fuzzy Mamdani + Kelly)           │
│   "What is the operational risk level?"                         │
│   Output: 🟢NORMAL | 🟡ANOMALOUS | 🟠SUSPECT | 🔴HOSTILE          │
│                         │                                       │
│                         ▼                                       │
│ ⑤ BOB ANALYST (IBM Granite Copilot)                             │
│   4-Stage LLM + GIS Pipeline (Palantir Patent US 2024/0394296):  │
│   Stage 1: Filters relevant alerts (eliminates false positives) │
│   Stage 2: ML Engine → quantitative score                       │
│   Stage 3: IBM Granite → contextual qualitative description      │
│   Stage 4: IBM Granite → final classification & recommendation  │
│                         │                                       │
│                         ▼                                       │
│ ⑥ DASHBOARD & FRONTEND                                          │
│   🌍 3D Interactive Globe with Orbital Traces                    │
│   📊 Prioritized Risk Cards                                     │
│   💬 Intelligence Analyst Chat (Briefing & Q&A)                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 5. MACHINE LEARNING ENGINE

| Component | Model | Type | Input | Output |
|-----------|-------|------|-------|--------|
| Anomaly Detector | Isolation Forest | Unsupervised | 34 noise & Kepler features | anomaly_score (0–1) |
| Threat Classifier | XGBoost | Supervised | 38 features + anomaly_score | 🟢🟡🟠🔴 Tiers |
| Risk Calibration | Mamdani Fuzzy | Rule Engine | Distance, Cointegration, Anomaly | Operational Risk |

---
    "eccentricity": 0.001,              # quão circular é a órbita
    "inclination_deg": 51.6,            # ângulo em relação ao equador
    "raan_deg": 150.1,                  # orientação do plano orbital
    "arg_perigee_deg": 100.1,           # orientação da elipse
    "mean_anomaly_deg": 260.5,          # posição na órbita
    "mean_motion_rev_per_day": 15.5,    # voltas por dia
    
    # Variações temporais (detectam manobras)
    "delta_sma_7d_km": 0.15,           # mudança de altitude em 7 dias
    "delta_sma_30d_km": 0.45,          # mudança em 30 dias
    "delta_inc_30d_deg": 0.02,         # mudança de inclinação
    "delta_ecc_30d": 0.0001,           # mudança de excentricidade
    
    # Contagem de eventos
    "maneuver_count_7d": 0,            # quantas manobras na semana
    "maneuver_count_30d": 1,           # quantas no mês
    
    # Proximidade de ativos militares
    "min_distance_to_military_km": 450.0,  # distância do sat militar mais próximo
    "military_nearby_count": 3,            # quantos sat militares num raio de 500km
}
```

### Como rotulamos (ground truth simulado)

Não temos acesso a classificações reais de ameaça (classificado). Criamos regras baseadas em **doutrina militar pública**:

```python
def label_object(features):
    """
    Regras de doutrina de Space Domain Awareness:
    - Manobra >2km em 7 dias + perto de militar = SUSPEITO
    - Manobra >5km ou aproximação <10km = HOSTIL
    - Múltiplas manobras sem motivação = SUSPEITO
    """
    if features["min_distance_to_military_km"] < 10:
        return "HOSTIL"
    if features["delta_sma_7d_km"] > 5.0:
        return "HOSTIL"
    if (features["delta_sma_7d_km"] > 2.0 and 
        features["min_distance_to_military_km"] < 50):
        return "SUSPEITO"
    if features["maneuver_count_30d"] >= 3:
        return "SUSPEITO"
    if features["delta_sma_7d_km"] > 1.0:
        return "ANÔMALO"
    return "NORMAL"
```

### Dataset

| Parâmetro | Valor |
|-----------|-------|
| Objetos analisados | ~10.000 satélites ativos + ~5.000 fragmentos rastreáveis |
| Período histórico | 12 meses (365 dias) |
| Features por registro | 15 |
| Registros totais | ~15.000 objetos × 365 dias = **~5.5 milhões** |
| Tamanho em disco | ~200 MB (CSV comprimido) |
| Distribuição esperada | ~95% NORMAL, ~3% ANÔMALO, ~1.5% SUSPEITO, ~0.5% HOSTIL |

### Treino no seu hardware

| Hardware | Tempo Isolation Forest | Tempo XGBoost | Total |
|----------|----------------------|---------------|-------|
| Ryzen 9 7900X (CPU 12C/24T) | ~30 segundos | ~3 minutos | **~4 minutos** |
| Com GPU ROCm | — | ~1 minuto | ~2 minutos |

---

## 7. O DASHBOARD

### Layout

```
┌──────────────────────────────────────────────────────────┐
│  ATHENA-SDA                           🟢 9.947 🟡 35 │
│  Space Domain Awareness Copilot           🟠 12  🔴 3   │
├────────────────────┬─────────────────────────────────────┤
│                    │  🚨 ALERTAS ATIVOS                  │
│                    │                                     │
│                    │  🔴 PRIORIDADE 1                     │
│   🌍 GLOBO 3D     │  ┌─────────────────────────────┐    │
│   (Cesium/Plotly) │  │ Objeto #44231               │    │
│                    │  │ 3 manobras em 24h           │    │
│   • 15.000 objetos │  │ Aproximação de US #22988    │    │
│     em órbita      │  │ Confiança: 87%              │    │
│   • Coloridos por  │  │ [Ver briefing] [Ignorar]    │    │
│     classificação  │  └─────────────────────────────┘    │
│   • Linhas de      │                                     │
│     trajetória     │  🟠 PRIORIDADE 2                     │
│   • Hover = info   │  ┌─────────────────────────────┐    │
│                    │  │ Objeto #52901               │    │
│                    │  │ Mudança orbital suspeita     │    │
│                    │  │ Confiança: 72%              │    │
│                    │  └─────────────────────────────┘    │
├────────────────────┴─────────────────────────────────────┤
│  💬 BOB CHAT                                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │ Bob: Detectei 15 alertas nas últimas 24h.        │  │
│  │ 3 requerem atenção imediata.                     │  │
│  │                                                  │  │
│  │ Operador: Bob, mostre a trajetória do #44231     │  │
│  │ dos últimos 7 dias.                              │  │
│  │                                                  │  │
│  │ Bob: Renderizando no globo...                    │  │
│  │ O objeto fez 3 manobras:                         │  │
│  │ • 10/07: +2.3 km (suspeito)                      │  │
│  │ • 12/07: -1.1 km (suspeito)                      │  │
│  │ • 13/07: +0.8 km (suspeito)                      │  │
│  │ [Digite sua pergunta...]                         │  │
│  └──────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────┘
```

---

## 8. MÉTRICAS PARA O PITCH

| Métrica | Valor | Como medir |
|---------|-------|------------|
| Objetos monitorados | 15.000+ | Catálogo Space-Track ativo |
| Features por objeto | 15 | Extraídas do TLE |
| Redução de carga cognitiva | **De 15.000 para 15 alertas/dia** | Filtro ML |
| Precisão do classificador | >85% (validação cruzada) | Métricas sklearn |
| Tempo de análise do Bob | <5 segundos por alerta | Do insight ao briefing |
| Patentes referenciadas | 30+ | Mapeadas no projeto |
| Contratantes reais | Palantir + Pentágono ($30B Space Force) | Prova de mercado |

---

## 9. POR QUE ISSO É REAL

- **Palantir** tem contrato ativo com US Space Force para SDA
- **Voyager Space + Palantir** anunciaram parceria em Junho/2024 exatamente para AI militar espacial
- **China** está patentendo defesa orbital ativa (5 patentes em 2024-2025)
- **Mercado de SDA**: $6.9 bilhões em 2025, crescendo
- **Dados são públicos**: Space-Track é mantido pelo US Space Force

---

## 10. RESUMO EM 1 PARÁGRAFO

O Athena-SDA ingere o catálogo orbital público de 15.000 objetos, extrai 15 features orbitais e temporais de cada um, e usa Isolation Forest + XGBoost treinados para classificar comportamento em 4 níveis de ameaça. Dos 15.000 objetos, apenas ~15 geram alertas por dia. Esses alertas alimentam o IBM Bob, que — seguindo a arquitetura de 4 etapas da patente Palantir US 2024/0394296 A1 (LLM + Geospatial) — contextualiza cada ameaça com dados de clima espacial e catálogos de propósito militar, gera uma descrição qualitativa, classifica com nível de confiança e recomenda ações táticas. Tudo é exibido em um dashboard com globo 3D interativo, cards de alerta priorizados e chat com o Bob. O projeto se fundamenta em 30+ patentes de fronteira (Palantir, Lockheed Martin, Raytheon, China CAST/CASC) publicadas entre 2023 e 2026.
