# ATHENA-SDA — Documento do Projeto

> **Hackathon:** AI Builders Challenge — Agosto 2025
> **Tema:** Advance Space Exploration with AI
> **Equipe:** Athena-SDA
> **Stack:** Python + XGBoost + IBM Granite/Bob + Streamlit

---

## 1. O QUE É O ATHENA-SDA?

### Elevator pitch (30 segundos)

> *"Existem 30.000 objetos em órbita da Terra. Operadores humanos não conseguem monitorar todos. O Athena-SDA usa machine learning para classificar cada objeto em níveis de ameaça e o IBM Bob como analista de inteligência que explica, prioriza e recomenda ações em linguagem natural — como um copiloto Palantir para o espaço."*

### Problema real

| Fato | Consequência |
|------|-------------|
| ~30.000 objetos rastreados (satélites ativos + debris) | Impossível monitorar manualmente |
| Satélites militares chineses fazem manobras de aproximação | Space Force precisa detectar padrões |
| Catálogo público (Space-Track) é gratuito mas bruto | Dado existe, inteligência não |
| Sistemas atuais geram alertas | Mas não **explicam, priorizam, nem recomendam** |

### Solução

Um sistema de 3 camadas:

```
CAMADA 1 — ML (olho):        Classifica 30.000 objetos em 🟢🟡🟠🔴
CAMADA 2 — Bob (cérebro):    Explica OS ALERTAS (não todos) em linguagem natural
CAMADA 3 — Dashboard (tela): Globo 3D + cards de ameaça + chat com Bob
```

---

## 2. EM QUE NOS BASEAMOS

### 30+ patentes de fronteira mapeadas

| Fonte | Quantidade | Destaque |
|-------|-----------|----------|
| 🟣 **Palantir Technologies** | 8 patentes | AI Meta-Constellation, Sensor Fusion, **LLM + Geospatial**, Ontology Map |
| 🇺🇸 **Lockheed Martin** | 4 patentes | Deep NN para satélite, Detecção de míssil, Discriminação de decoy |
| 🇺🇸 **Raytheon / GD / L3Harris** | 6 patentes | GAN SAR, RL tracking, Cripto militar, Phased array |
| 🇨🇳 **China CAST / CASC** | 10 patentes | Defesa ativa orbital, Perseguição-evasão, Anti-decepção |

### As 5 patentes-âncora (arquitetura extraída)

| Patente | O que nos ensinou |
|---------|-------------------|
| **US 2023/0050870 A1** (Palantir) | Arquitetura DMP+AIP: decompor missão → selecionar sensores → micro-modelos → insight-first downlink |
| **US 12,450,265 B2** (Palantir) | 3D Tiles (X,Y,T) + algoritmo RDP: simplificar séries temporais pra renderização rápida |
| **US 12,657,514 B2** (Palantir) | Data API + Inference API + DAG dinâmico: pipeline reconfigurável de modelos |
| **US 2024/0394296 A1** (Palantir) | **LLM + GIS em 4 etapas:** filtro físico → ML quantitativo → LLM descritivo → LLM classificador |
| **US 12,374,011 B2** (Palantir) | Ontologia + UTF Grid + histogramas interativos: objetos de inteligência no mapa |

### Por que essas patentes importam

- Publicadas entre **2023 e Junho/2026** — tecnologia na fronteira
- Palantir está construindo isso **agora** (contratos com Pentágono, Space Force)
- China está patentendo defesa orbital ativa — é uma corrida real
- **Nenhuma delas integra LLM como copiloto de decisão** — essa é a nossa lacuna

---

## 3. QUAIS DADOS VAMOS USAR

### Fonte primária: TLE do Space-Track / CelesTrak

**O que é TLE (Two-Line Element):** Formato padrão que descreve a órbita de qualquer objeto no espaço. Duas linhas de 69 caracteres contêm: inclinação, excentricidade, altitude, movimento médio e outros parâmetros orbitais.

**Exemplo real (ISS):**
```
ISS (ZARYA)
1 25544U 98067A   24195.55001157  .00001234  00000+0  23456-4 0  9992
2 25544  51.6420 150.1234 0004567 100.1234 260.5678 15.50123456123456
```

**Fontes:**

| Fonte | Acesso | Custo | Latência |
|-------|--------|-------|----------|
| **CelesTrak.org** | `curl` público, sem conta | Grátis | Diário |
| **Space-Track.org** | API REST com conta gratuita | Grátis | ~4h |
| **N2YO.com** | API REST, free tier 1000/dia | Grátis | Tempo real |

**O que baixamos:**
- TLE de **todos os objetos ativos** (~10.000 satélites + fragmentos rastreáveis)
- **12 meses de histórico** para estabelecer baseline de normalidade
- **Atualização diária** para o demo ao vivo

### Dados de contexto (enriquecem a análise)

| Fonte | O que agrega |
|-------|-------------|
| **UCS Satellite Database** | Catálogo com **propósito** de cada satélite: militar, civil, comercial, científico |
| **Space Weather (NOAA)** | Índice F10.7 (fluxo solar) e Ap (tempestade geomagnética) — afetam arrasto orbital |
| **CelesTrak SATCAT** | Metadados: país de origem, data de lançamento, status |

### Como os dados são usados

```
TLE (12 meses) ──▶ Extração de features ──▶ Dataset de treino
                     │
                     ├── semi_major_axis_km
                     ├── eccentricity
                     ├── inclination_deg
                     ├── mean_motion_rev_per_day
                     ├── delta_sma_7d      (mudança em 7 dias)
                     ├── delta_inc_30d     (mudança de inclinação em 30 dias)
                     ├── maneuver_count_30d
                     ├── min_distance_to_military_km
                     └── country_purpose    (militar? civil?)
```

---

## 4. COMO FUNCIONA

### Arquitetura completa

```
┌─────────────────────────────────────────────────────────────────┐
│                       ATHENA-SDA                              │
│                                                                  │
│ ① DATA INGEST                                                    │
│   CelesTrak ──▶ TLE bruto                                        │
│   NOAA ──────▶ clima espacial                                    │
│   UCS DB ────▶ catálogo de propósito                             │
│                         │                                        │
│                         ▼                                        │
│ ② FEATURE EXTRACTOR                                              │
│   TLE → 15 features orbitais + temporais + contexto              │
│   + baseline de 12 meses (média, desvio padrão)                  │
│                         │                                        │
│                         ▼                                        │
│ ③ ANOMALY DETECTOR (Isolation Forest)                            │
│   "Este objeto está se comportando diferente do normal?"         │
│   Output: anomaly_score (0.0 = normal, 1.0 = muito anômalo)      │
│                         │                                        │
│                         ▼                                        │
│ ④ THREAT CLASSIFIER (XGBoost)                                    │
│   "Se está anômalo, qual o nível de ameaça?"                     │
│   Output: 🟢NORMAL | 🟡ANÔMALO | 🟠SUSPEITO | 🔴HOSTIL           │
│                         │                                        │
│              (só alertas 🟠🔴 seguem)                             │
│                         │                                        │
│                         ▼                                        │
│ ⑤ BOB ANALYST (IBM Granite)                                      │
│   Pipeline LLM+Geospatial (4 etapas, baseado na patente          │
│   Palantir US 2024/0394296):                                     │
│                                                                  │
│   Etapa 1: Filtra alertas relevantes (elimina falsos positivos)  │
│   Etapa 2: XGBoost → score quantitativo (0.0 - 1.0)              │
│   Etapa 3: Granite → descrição qualitativa contextual             │
│   Etapa 4: Granite → classificação final + recomendação          │
│                         │                                        │
│                         ▼                                        │
│ ⑥ DASHBOARD (Streamlit)                                          │
│   🌍 Globo 3D com objetos orbitais                               │
│   📊 Cards de ameaça com prioridade                              │
│   💬 Chat com Bob (briefing, Q&A, comandos)                      │
│   📈 Histogramas interativos (drill-down por país, classe, risco)│
└─────────────────────────────────────────────────────────────────┘
```

### Fluxo de uma análise completa

```
1. DADOS ENTRAM
   CelesTrak: 10.000 TLEs do dia
   Baseline: 12 meses de histórico

2. ML PROCESSA (2 segundos)
   10.000 objetos → 15 features cada → Isolation Forest → XGBoost
   Resultado: 9.950 🟢 NORMAL, 35 🟡 ANÔMALO, 12 🟠 SUSPEITO, 3 🔴 HOSTIL

3. BOB ANALISA OS 15 ALERTAS (5 segundos)
   Para CADA alerta 🟠🔴:
   ├── Consulta APIs (clima espacial, UCS database)
   ├── Gera descrição contextual
   ├── Classifica com confiança
   └── Recomenda ação

4. OPERADOR VÊ NO DASHBOARD
   3 cards vermelhos no topo (prioridade)
   Clica em um → Bob explica: "Objeto #44231 mudou órbita 3x.
   Aproximou-se do satélite militar US #22988. Confiança: 87%."
   Chat: "Bob, mostre a trajetória desse objeto nos últimos 7 dias"
```

---

## 5. O PAPEL DO BOB NO SISTEMA

### Bob NÃO É um gerador de relatório

Bob é um **analista de inteligência artificial** que participa do pipeline de decisão em 4 etapas:

### O que Bob faz (específico)

| Função | Exemplo |
|--------|---------|
| **Contextualizar** | "O objeto #44231 é um satélite chinês da série Yaogan (reconhecimento militar). Está em órbita desde 2019. Normalmente opera a 500km." |
| **Explicar anomalia** | "Em 7 dias, alterou altitude 3 vezes (+2.3, -1.1, +0.8 km). Isso é 12× mais que seu desvio padrão histórico de 0.2 km." |
| **Cruzar inteligência** | "Aproximou-se do satélite militar US #22988 a 15.2 km às 02:14 UTC. A 15 km, é possível imagear com resolução de 0.5m." |
| **Classificar ameaça** | "Classificação: 🟠 SUSPEITO. Confiança: 87%. Padrão consistente com reconhecimento orbital." |
| **Recomendar ação** | "1) Notificar USSF SDA cell. 2) Solicitar tasking óptico (próximo overpass: 06:30 UTC). 3) Monitorar próximas 24h com threshold de 10 km." |
| **Responder perguntas** | Operador: "Bob, esse satélite já fez isso antes?" Bob: "Sim. Padrão similar em Março/2024 sobre o Pacífico. Naquela ocasião, imageou um porta-aviões." |
| **Priorizar** | "Dos 15 alertas ativos, este é prioridade 1. Os outros 14 são manobras de manutenção rotineiras." |

### Tool Calling do Bob (APIs que ele consulta)

```python
ferramentas_do_bob = {
    "get_object_history": "Consulta 12 meses de TLE de um objeto",
    "get_close_approaches": "Lista aproximações <50km nas próximas 48h",
    "get_space_weather": "Clima espacial atual (arrasto, tempestade)",
    "get_object_metadata": "País, propósito, data de lançamento (UCS DB)",
    "get_past_maneuvers": "Histórico de manobras similares deste objeto",
}
```

### Por que isso é diferente de um dashboard tradicional

| Dashboard tradicional | Athena-SDA com Bob |
|----------------------|----------------------|
| Tabela: 10.000 linhas | 15 cards priorizados |
| "Obj #44231: ΔSMA=2.3km" | "Objeto #44231: 3 manobras em 24h. Consistente com reconhecimento orbital. Recomendo tasking." |
| Operador precisa interpretar | Operador recebe análise pronta |
| Silencioso até o humano perguntar | Bob é **proativo**: alerta quando detecta |

---

## 6. O TREINAMENTO DO MACHINE LEARNING

### O que treinamos

| Modelo | Algoritmo | Tipo | Input | Output |
|--------|-----------|------|-------|--------|
| Anomaly Detector | Isolation Forest | Não-supervisionado | 15 features orbitais | anomaly_score (0-1) |
| Threat Classifier | XGBoost | Supervisionado | 15 features + anomaly_score | 🟢🟡🟠🔴 |

### Features extraídas de cada TLE

```python
features = {
    # Parâmetros orbitais instantâneos
    "semi_major_axis_km": 6878.0,       # altitude média
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
