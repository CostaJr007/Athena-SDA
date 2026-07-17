# ATHENA-SDA — Documento Mestre do Projeto

> **Hackathon:** AI Builders Challenge — Agosto 2025
> **Tema:** Advance Space Exploration with AI
> **Stack:** Python + XGBoost + Isolation Forest + Fuzzy Logic + IBM Granite/Bob + Streamlit
> **Última atualização:** 2026-07-14

---

## ÍNDICE

1. [Visão Geral do Projeto](#1-visão-geral-do-projeto)
2. [Base Patentária (30+ patentes)](#2-base-patentária)
3. [Dados Reais](#3-dados-reais)
4. [Arquitetura do Sistema](#4-arquitetura-do-sistema)
5. [Pipeline de Machine Learning](#5-pipeline-de-machine-learning)
6. [Fundamentação Matemática (14 teorias)](#6-fundamentação-matemática)
7. [Bob — O Copiloto de Inteligência](#7-bob--o-copiloto-de-inteligência)
8. [Dashboard e Interface](#8-dashboard-e-interface)
9. [Cenários de Demonstração](#9-cenários-de-demonstração)
10. [Roadmap de Implementação](#10-roadmap-de-implementação)
11. [Métricas para o Pitch](#11-métricas-para-o-pitch)

---

## 1. VISÃO GERAL DO PROJETO

### O que é

**Athena-SDA** é um copiloto de **Space Domain Awareness (SDA)** que combina machine learning, lógica fuzzy, teoria da informação e IBM Granite/Bob para monitorar 30.000 objetos em órbita, classificar ameaças e gerar briefings táticos em linguagem natural.

### Problema

30.000 objetos rastreados. Operadores humanos não conseguem monitorar todos. Sistemas atuais geram alertas, mas não **explicam, priorizam, nem recomendam ações**.

### Solução em 3 camadas

```
CAMADA 1 — ML + Matemática (olho):   Classifica 30.000 → ~15 alertas/dia
CAMADA 2 — Bob/Granite (cérebro):    Explica, contextualiza, recomenda
CAMADA 3 — Dashboard (tela):         Globo 3D + cards + chat
```

### Métrica principal

> **De 30.000 objetos para 15 decisões por dia.**

---

## 2. BASE PATENTÁRIA

### Patentes-âncora (arquitetura extraída)

| Patente | Empresa | O que nos ensinou |
|---------|---------|-------------------|
| US 2023/0050870 A1 | Palantir | DMP+AIP: decompor missão → selecionar sensores → micro-modelos → insight-first downlink |
| US 12,450,265 B2 | Palantir | 3D Tiles (X,Y,T) + RDP: simplificar séries temporais |
| US 12,657,514 B2 | Palantir | Data API + Inference API + DAG dinâmico de modelos |
| US 2024/0394296 A1 | Palantir | **LLM + GIS em 4 etapas** |
| US 12,374,011 B2 | Palantir | Ontologia + UTF Grid + histogramas interativos |

### Patentes de suporte

| Fonte | Quantidade | Destaque |
|-------|-----------|----------|
| Palantir Technologies | 8 patentes | Meta-Constellation, Sensor Fusion, LLM+Geospatial, Ontology Map |
| Lockheed Martin | 4 patentes | Deep NN sat, Detecção míssil, Discriminação decoy |
| Raytheon / GD / L3Harris | 6 patentes | GAN SAR, RL tracking, Cripto, Phased array |
| China CAST / CASC | 10+ patentes | Defesa ativa orbital, Perseguição-evasão, Anti-decepção, FDNN |
| **TOTAL** | **30+ patentes** | Publicadas entre 2023 e Junho/2026 |

---

## 3. DADOS REAIS

### Fontes primárias

| Fonte | O que fornece | Acesso | Custo |
|-------|--------------|--------|-------|
| CelesTrak.org | TLE de 30.000 objetos | `curl` público | Grátis |
| Space-Track.org | TLE oficial US Space Force | Conta gratuita | Grátis |
| N2YO.com | Posição em tempo real | API free tier | Grátis |
| UCS Satellite Database | Propósito de cada satélite | Download CSV | Grátis |
| NOAA Space Weather | F10.7, Ap index | API REST | Grátis |

### Estrutura do TLE (Two-Line Element)

```
ISS (ZARYA)
1 25544U 98067A   24195.55001157  .00001234  00000+0  23456-4 0  9992
2 25544  51.6420 150.1234 0004567 100.1234 260.5678 15.50123456123456
```

Parâmetros extraídos: inclinação, excentricidade, semi-eixo maior, RAAN, argumento do perigeu, anomalia média, movimento médio.

### Escopo temporal

- **12 meses de histórico** para baseline de normalidade
- **Atualização diária** para demo ao vivo
- **~5.5 milhões de registros** (30k objetos × 365 dias, com amostragem)

---

## 4. ARQUITETURA DO SISTEMA

```
┌─────────────────────────────────────────────────────────────────┐
│                       ATHENA-SDA                              │
│                                                                  │
│ ① DATA INGEST                                                    │
│   CelesTrak TLE ──── NOAA Space Weather ──── UCS Database        │
│                         │                                        │
│                         ▼                                        │
│ ② FEATURE EXTRACTOR (20+ features)                               │
│   Shannon Entropy │ Kolmogorov │ Hurst │ Mandelbrot │ Ricci     │
│   Homologia │ Chern-Simons proxy │ Fuzzy │ Hilbert/RKHS          │
│                         │                                        │
│                         ▼                                        │
│ ③ ANOMALY DETECTOR (Isolation Forest)                            │
│   "Este objeto está se comportando diferente do normal?"         │
│                         │                                        │
│                         ▼                                        │
│ ④ THREAT CLASSIFIER (XGBoost)                                    │
│   🟢 NORMAL | 🟡 ANÔMALO | 🟠 SUSPEITO | 🔴 HOSTIL               │
│                         │                                        │
│              (só alertas 🟠🔴 seguem)                             │
│                         │                                        │
│                         ▼                                        │
│ ⑤ FUZZY INFERENCE (skfuzzy)                                      │
│   Lida com incerteza: TLE velho, bordas de decisão               │
│   Output: threat_level + confidence + ambiguity                  │
│                         │                                        │
│                         ▼                                        │
│ ⑥ BOB ANALYST (IBM Granite + Tool Calling)                       │
│   Pipeline LLM+Geospatial 4 etapas (Palantir US 2024/0394296)    │
│   Contextualiza → Explica → Prioriza → Recomenda                 │
│                         │                                        │
│                         ▼                                        │
│ ⑦ DASHBOARD (Streamlit)                                          │
│   Globo 3D │ Cards de ameaça │ Chat Bob │ Histogramas            │
└─────────────────────────────────────────────────────────────────┘
```

---

## 5. PIPELINE DE MACHINE LEARNING

### Features (20+ por objeto)

```python
features = {
    # Parâmetros orbitais instantâneos (7)
    "semi_major_axis_km": 6878.0,
    "eccentricity": 0.001,
    "inclination_deg": 51.6,
    "raan_deg": 150.1,
    "arg_perigee_deg": 100.1,
    "mean_anomaly_deg": 260.5,
    "mean_motion_rev_per_day": 15.5,
    
    # Variações temporais (4)
    "delta_sma_7d_km": 0.15,
    "delta_sma_30d_km": 0.45,
    "delta_inc_30d_deg": 0.02,
    "maneuver_count_30d": 1,
    
    # Matemáticas avançadas (9+)
    # (implementadas na Seção 6)
    "shannon_entropy_sma_30d": ...,
    "kolmogorov_proxy_7d": ...,
    "hurst_exponent_sma": ...,
    "mandelbrot_tail_score": ...,
    "ricci_mean": ...,
    "ricci_delta_7d": ...,
    "persistent_h0_count": ...,
    "chern_simons_proxy": ...,
    "spectral_anomaly_rkhs": ...,
    
    # Contexto (2)
    "intrinsic_threat_value": ...,  # Williams (1938)
    "tle_age_hours": 12,
}
```

### Modelos

| Modelo | Algoritmo | Tipo | Output |
|--------|-----------|------|--------|
| Anomaly Detector | Isolation Forest | Não-supervisionado | anomaly_score (0-1) |
| Threat Classifier | XGBoost | Supervisionado | 🟢🟡🟠🔴 |
| Fuzzy Inference | skfuzzy (Mamdani) | Baseado em regras | threat_level + confidence |
| Kelly Allocator | Critério de Kelly | Decisão | resource_allocation |

### Labels (ground truth simulado)

Baseado em doutrina militar pública de Space Domain Awareness:

- `min_distance_to_military_km < 10` → HOSTIL
- `delta_sma_7d > 5.0 km` → HOSTIL
- `delta_sma_7d > 2.0 AND min_dist < 50` → SUSPEITO
- `maneuver_count_30d >= 3` → SUSPEITO
- `delta_sma_7d > 1.0` → ANÔMALO
- Demais → NORMAL

---

## 6. FUNDAMENTAÇÃO MATEMÁTICA

### Matriz completa: 14 teorias aplicadas

| # | Teoria | Autor/Ano | Feature | Tipo |
|---|--------|-----------|---------|------|
| 1 | Valor Intrínseco | Williams (1938) | `intrinsic_threat_value` | Estático |
| 2 | Kernel Regression | Lo et al. (2000) | `kernel_typicality_score` | Não-paramétrico |
| 3 | Kernel L1 CUSUM | — | `l1_cusum_sma` | Sequencial robusto |
| 4 | Caudas Pesadas | Mandelbrot (1963) | `mandelbrot_tail_score` | Distribucional |
| 5 | Memória Longa R/S | Hurst (1951) | `hurst_exponent` | Temporal |
| 6 | Entropia de Shannon | Shannon (1948) | `entropy_sma_30d` | Informacional |
| 7 | Complexidade de Kolmogorov | Kolmogorov (1965) | `kolmogorov_proxy_7d` | Algorítmica |
| 8 | Homologia Persistente | Edelsbrunner (2002) | `h0_persistent`, `h1_persistent` | Topológica |
| 9 | Curvatura de Ricci | Ollivier (2007) | `ricci_mean`, `ricci_delta` | Geométrica |
| 10 | Chern-Simons (proxy) | Chern-Simons (1974) | `topological_violation` | Topológica |
| 11 | Fuzzy Sets | Zadeh (1965) | `fuzzy_threat`, `fuzzy_confidence` | Lógica |
| 12 | Lógica Łukasiewicz | Łukasiewicz (1920) | `lukasiewicz_implication` | Lógica |
| 13 | Critério de Kelly | Kelly (1956) | `kelly_allocation` | Decisão |
| 14 | Hilbert/RKHS | Hilbert (~1900) | `spectral_anomaly` | Geométrica |

### Ordem de aplicação (do básico ao avançado)

```
FASE 1 (MVP):     Features orbitais básicas → XGBoost
FASE 2 (Avançado): Shannon + Kolmogorov + Hurst
FASE 3 (Expert):   Mandelbrot + Ricci + Homologia + Chern-Simons
FASE 4 (Decisão):  Fuzzy + Kelly + Hilbert/RKHS
```

### Status de implementação por teoria

| Status | Teorias |
|--------|---------|
| ✅ Implementação direta (5-20 linhas) | Shannon, Kolmogorov, Hurst, Mandelbrot, Zadeh, Łukasiewicz, Kelly, Williams, Lo, Hilbert |
| ⚠️ Aproximação necessária | Ollivier-Ricci, Homologia Persistente (samplear), Chern-Simons (proxy) |
| ❌ Apenas conceitual | Chern-Simons exato (fora do escopo) |

---

## 7. BOB — O COPILOTO DE INTELIGÊNCIA

### O que Bob faz (baseado na patente Palantir US 2024/0394296 A1)

Pipeline LLM + Geospatial em 4 etapas:

| Etapa | O que faz | Exemplo |
|-------|-----------|---------|
| **1. Filtro** | Remove falsos positivos, objetos irrelevantes | "Dos 15 alertas, 12 são manutenção rotineira. 3 requerem análise." |
| **2. Quantitativo** | XGBoost gera score numérico | threat_score = 0.87 |
| **3. Descritivo** | Granite gera descrição contextual | "Objeto #44231 (Yaogan-31, China). 3 manobras em 24h. ΔSMA: +2.3, -1.1, +0.8 km." |
| **4. Classificador** | Granite classifica e recomenda | "🟠 SUSPEITO. Confiança: 87%. Recomendo tasking óptico + notificar USSF." |

### Tool Calling (APIs que Bob consulta)

```
get_object_history(norad_id)     → 12 meses de TLE
get_close_approaches(norad_id)   → Aproximações <50km em 48h
get_space_weather()              → F10.7, Ap index
get_object_metadata(norad_id)    → País, propósito, lançamento
get_similar_events(norad_id)     → Eventos históricos similares
```

### Exemplo de briefing gerado

```
🚨 BRIEFING SDA — 2026-07-14 04:52 UTC

OBJETO: #44231 (Yaogan-31, China)
CLASSIFICAÇÃO: 🟠 SUSPEITO
CONFIANÇA FUZZY: 87% | AMBIGUIDADE: 13%

ANÁLISE:
- 3 manobras orbitais em 24h (ΔSMA: +2.3, -1.1, +0.8 km)
- Entropia de Shannon: 2.1 (caótico — normal é 0.3)
- Expoente de Hurst: 0.78 (fortemente persistente)
- Curvatura de Ricci: -0.45 (divergência da vizinhança)
- Aproximou-se do satélite militar US #22988: 15.2 km
- TLE tem 12h de idade (precisão ±100m)

AÇÃO RECOMENDADA (Kelly allocation: 42% dos recursos):
1. 🔴 Notificar USSF SDA cell
2. 📡 Solicitar tasking óptico (próximo overpass: 06:30 UTC)
3. 📊 Monitorar 24h com threshold de 10 km
4. 📋 Gerar relatório para JSpOC
```

---

## 8. DASHBOARD E INTERFACE

### Layout

```
┌──────────────────────────────────────────────────────────┐
│  ATHENA-SDA                           🟢 29.947 🟡 35│
│  Space Domain Awareness Copilot           🟠 12  🔴 3   │
├────────────────────┬─────────────────────────────────────┤
│                    │  🚨 ALERTAS ATIVOS (Kelly ranked)   │
│   🌍 GLOBO 3D     │  🔴 42% — Objeto #44231 (Yaogan-31) │
│   • 30k objetos   │  🟠 28% — Objeto #52901              │
│   • Coloridos por │  🟠 15% — Objeto #67012              │
│     classificação │  ...                                  │
│   • Trajetórias   │                                      │
│   • Hover = info  │  📊 HISTOGRAMAS                      │
│                    │  [Por país] [Por classe] [Por órbita]│
├────────────────────┴─────────────────────────────────────┤
│  💬 BOB CHAT                                          │
│  Bob: 15 alertas nas últimas 24h. 3 prioritários.    │
│  Operador: Detalhe o #44231                          │
│  Bob: Yaogan-31, China. 3 manobras. Padrão suspeito. │
│  [_________________________________________________] │
└──────────────────────────────────────────────────────────┘
```

### Tecnologias

- **Streamlit** — framework do dashboard
- **Plotly/Cesium** — globo 3D
- **Folium** — mapa 2D (fallback)
- **Altair/Plotly** — histogramas interativos

---

## 9. CENÁRIOS DE DEMONSTRAÇÃO

### Cenário principal: Alerta de reconhecimento orbital

```
1. TLEs do dia são ingeridos (10 segundos)
2. ML processa 30.000 objetos:
   - 29.947 🟢 NORMAL
   - 35 🟡 ANÔMALO
   - 12 🟠 SUSPEITO
   - 3 🔴 HOSTIL
3. Bob analisa os 15 alertas 🟠🔴 (5 segundos cada)
4. Dashboard mostra:
   - #44231 (Yaogan-31, China): 🔴 HOSTIL — aproximou de US MILSAT
   - #67012 (debris anômalo): 🟠 SUSPEITO — manobras inexplicadas
   - #88001 (Cosmos-2560, Rússia): 🟠 SUSPEITO — mudança de órbita
5. Operador pergunta: "Bob, o #44231 já fez isso antes?"
6. Bob: "Sim. Padrão similar em Março/2024 sobre o Pacífico."
```

### Cenário secundário: Falso positivo com TLE velho

```
1. Objeto #52901: TLE com 96h de idade
2. Fuzzy detecta alta incerteza (ambiguidade: 49%)
3. Bob: "Confiança baixa (51%). TLE desatualizado.
         Não recomendo escalar. Aguardar update."
```

---

## 10. ROADMAP DE IMPLEMENTAÇÃO

### Fases

```
FASE 0 (30min)  ▸ Setup: IBM Cloud + watsonx.ai + repositório
FASE 1 (2h)     ▸ Download TLE Space-Track/CelesTrak + UCS DB
FASE 2 (2h)     ▸ Feature Extractor: features orbitais básicas (7)
FASE 3 (2h)     ▸ Treino: Isolation Forest + XGBoost (MVP)
FASE 4 (2h)     ▸ Features avançadas: Shannon + Kolmogorov + Hurst + Mandelbrot
FASE 5 (2h)     ▸ Features expert: Ricci + Homologia + Chern-Simons proxy
FASE 6 (2h)     ▸ Fuzzy Inference System + Kelly Allocator
FASE 7 (2h)     ▸ Bob Integration: Granite + Tool Calling + Prompt Engineering
FASE 8 (2h)     ▸ Dashboard Streamlit: globo 3D + cards + chat
FASE 9 (1h30)   ▸ Polish + Pitch Deck + Ensaio
```

### Prioridade

| Prioridade | O que | Por quê |
|-----------|-------|---------|
| 🔴 MUST | Features básicas + XGBoost + Bob + Dashboard | MVP funcional |
| 🟡 SHOULD | Shannon + Kolmogorov + Hurst + Fuzzy | Diferencial matemático |
| 🟢 NICE | Ricci + Homologia + Chern-Simons + Kelly | Excelência acadêmica |

---

## 11. MÉTRICAS PARA O PITCH

| Métrica | Valor | Como medir |
|---------|-------|------------|
| Objetos monitorados | 30.000+ | Space-Track catalog |
| Features por objeto | 20+ | Pipeline de extração |
| Redução cognitiva | De 30.000 para ~15 alertas/dia | Filtro ML + Fuzzy |
| Precisão do classificador | >85% | Validação cruzada |
| Tempo de análise do Bob | <5s por alerta | Timestamp |
| Teorias matemáticas aplicadas | 14 | Documentadas |
| Patentes referenciadas | 30+ | Mapeadas |
| Mercado real | $6.9B SDA + $30B Space Force | Market reports |
| Contratantes reais | Palantir + Pentágono | Prova de mercado |

---

## APÊNDICE: Referências Completas

### Patentes
Ver documento `references/ATHENA-SDA.md` para lista completa com 30+ patentes.

### Teorias Matemáticas
- Shannon, C.E. (1948). *A Mathematical Theory of Communication*. Bell System Technical Journal.
- Kolmogorov, A.N. (1965). *Three approaches to the quantitative definition of information*. Problems of Information Transmission.
- Hurst, H.E. (1951). *Long-term storage capacity of reservoirs*. Transactions of ASCE.
- Mandelbrot, B. (1963). *The variation of certain speculative prices*. Journal of Business.
- Zadeh, L.A. (1965). *Fuzzy sets*. Information and Control.
- Ollivier, Y. (2007). *Ricci curvature of Markov chains on metric spaces*. Journal of Functional Analysis.
- Edelsbrunner, H. et al. (2002). *Topological persistence and simplification*. Discrete & Computational Geometry.
- Kelly, J.L. (1956). *A new interpretation of information rate*. Bell System Technical Journal.
- Williams, J.B. (1938). *The Theory of Investment Value*. Harvard University Press.
- Lo, A.W. et al. (2000). *Foundations of technical analysis*. Journal of Finance.

### Dados
- CelesTrak: https://celestrak.org
- Space-Track: https://www.space-track.org
- UCS Satellite Database: https://www.ucsusa.org/resources/satellite-database
- NOAA Space Weather: https://www.swpc.noaa.gov

### IBM Tools
- watsonx.ai: https://www.ibm.com/watsonx
- Granite Models: https://huggingface.co/ibm-granite
- IBM Cloud: https://cloud.ibm.com

---

*Documento gerado como referência mestre do projeto Athena-SDA.*
*Hackathon AI Builders Challenge — Agosto 2025*
