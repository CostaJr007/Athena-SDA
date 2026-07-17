# Referências Técnicas das Patentes Palantir Technologies

Este documento reúne a arquitetura de software, diagramas, esquemas de projeto e links para as imagens originais de patentes da Palantir Technologies mapeadas para o **Projeto Athena-SDA**. 

Ele serve como memória técnica permanente para guiar a implementação dos pipelines de engenharia, machine learning e interfaces do projeto.

---

## 1. US 2023/0050870 A1 — AI Meta-Constellation
* **Título:** *Systems and methods for AI meta-constellation*
* **Inventores:** Andrew Elder, Anand Gupta, Daniel Cervelli, Robert Imig, Tess Druckenmiller.
* **Propósito:** Software de coordenação e reconfiguração dinâmica em órbita de cargas úteis de satélites heterogêneos.

### Diagramas Originais da Patente
* [Figura 1 — Fluxo Geral do Método](https://patentimages.storage.googleapis.com/ea/24/cd/6616de542b4ec4/US20230050870A1-20230216-D00000.png)
* [Figura 2 — Fluxo de Execução no Edge (Satélite)](https://patentimages.storage.googleapis.com/7a/3b/f3/e1d777884a5ea5/US20230050870A1-20230216-D00002.png)
* [Figura 3 — Arquitetura AIP + DMP Integrada](https://patentimages.storage.googleapis.com/f6/94/7a/80ee1928616c83/US20230050870A1-20230216-D00003.png)
* [Figura 4 — Diagrama de Conectividade do Sistema AIP](https://patentimages.storage.googleapis.com/a8/91/c7/c2720fb96c6484/US20230050870A1-20230216-D00004.png)
* [Figura 5 — Interfaces de Dados (Data API / Inference API)](https://patentimages.storage.googleapis.com/ac/51/ee/78f477c40221bf/US20230050870A1-20230216-D00005.png)

### Arquitetura de Design
O sistema divide-se em duas camadas dinâmicas:
1. **DMP (Development and Management Platform - Terrestre):**
   * Armazena modelos globais de ML e conjuntos de dados.
   * Compila, valida e gerencia contêineres leves ("micro-modelos").
   * Decompõe missões em tarefas e seleciona satélites específicos com base em órbitas e sensores adequados.
2. **AIP (AI Inference Platform - Edge/Espacial):**
   * Roda embarcado no hardware do satélite.
   * Executa a ingestão de sensores, ortorretificação rápida, detecção local por micro-modelos.
   * Suporta **hot-swapping** (troca rápida de modelos em tempo real sem interrupção de conectividade física com os sensores).
   * Faz *downlink* apenas do metadado gerado (redução drástica de dados).

---

## 2. US 2024/0394296 A1 — LLM + Geospatial Analysis
* **Título:** *Geospatial data analysis and visualization using machine learning models and language models*
* **Propósito:** Prospecção e avaliação qualitativa de lotes geoespaciais cruzando dados físicos estruturados e dados regulatórios não estruturados através de LLMs.

### Diagramas Originais da Patente
* [Figura 1 — Método do Pipeline de Análise](https://patentimages.storage.googleapis.com/90/d3/1c/67a14cefef40c6/US20240394296A1-20241128-D00000.png)
* [Figura 2 — Exibição Gráfica de Capacidades](https://patentimages.storage.googleapis.com/b9/42/4e/1973b7770398f9/US20240394296A1-20241128-D00001.png)
* [Figura 3 — Interface de Parcelamento do Mapa](https://patentimages.storage.googleapis.com/63/c1/99/becc071b717509/US20240394296A1-20241128-D00002.png)
* [Figura 4 — Indicadores de Score das Parcelas](https://patentimages.storage.googleapis.com/19/ea/6a/269bde9088f3e6/US20240394296A1-20241128-D00003.png)

### Fluxo Metodológico (4 Etapas)
1. **Filtro Físico Inicial:** Limpa o mapa descartando áreas restritas ou de relevo impróprio.
2. **Modelo Quantitativo Preditivo:** Um regressor ML estima a capacidade de geração de energia (NCF) ou conectividade física baseado em clima histórico.
3. **LLM Descritivo (Tese):** Lê e resume os dados semânticos (zoneamento, regulação ambiental local, etc.) injetados no contexto, criando uma *Descrição de Potencial*.
4. **LLM Classificador:** Consome a descrição qualitativa e gera scores de decisão e recomendações finais.

---

## 3. US 12,450,265 B2 — Time-Series Geo Fusion
* **Título:** *System and method for processing time-related geospatial data from one or more data sources*
* **Inventores:** Peter Wilczynski, Daniel Zangri.
* **Propósito:** Alinhamento e compressão de trajetórias de movimento geoespacial de alta frequência para exibição com latência zero.

### Diagramas Originais da Patente
* [Figura 1 — Sistema de Ingestão e Geração de Telhas](https://patentimages.storage.googleapis.com/US12450265B2/US12450265-20251021-D00000.png)
* [Figura 2 — Fluxo Geral de Renderização](https://patentimages.storage.googleapis.com/US12450265B2/US12450265-20251021-D00001.png)
* [Figura 3A/B — Método de Agregação de Telhas Temporais](https://patentimages.storage.googleapis.com/US12450265B2/US12450265-20251021-D00002.png)
* [Figura 4A/B/C — Agregação Multidimensional de Telhas](https://patentimages.storage.googleapis.com/US12450265B2/US12450265-20251021-D00003.png)
* [Figura 5 — Arquitetura de Comunicação Cliente-Servidor](https://patentimages.storage.googleapis.com/US12450265B2/US12450265-20251021-D00004.png)

### Arquitetura de Design
* **Criação de Telhas 3D ($X, Y, Tempo\ T$):** Mapeia os dados espaciais e a linha do tempo em cubos indexados no banco de dados.
* **Simplificação Multidimensional:** Quando o usuário afasta a linha do tempo (*zoom out temporal*), o sistema aplica algoritmos de compressão (como Ramer-Douglas-Peucker) nos caminhos vetoriais, mantendo a integridade gráfica da trajetória sem travar o cliente por excesso de pontos.

---

## 4. US 12,657,514 B2 — Sensor Correlation
* **Título:** *Systems and methods for AI inference platform and sensor correlation*
* **Inventores:** Robert Imig, Steven Fackler, Ian Peters, Mark Elliot, Joseph Ellis, Andres Felipe Orozco, Akash Jain.
* **Propósito:** Pipeline de fusão dinâmica e orquestração dirigida de múltiplos sensores físicos (SAR, EO/IR, RF, FMV) no Edge.

### Diagramas Originais da Patente
* [Figura 1 — Orquestradores no Ambiente de Deployment](https://patentimages.storage.googleapis.com/d3/ce/94/65ffc88b0ddc62/US20230196201A1-20230622-D00000.png)
* [Figura 2 — Sistema de Correlação e Orquestração](https://patentimages.storage.googleapis.com/9f/c1/3d/3ef00f434daba3/US20230196201A1-20230622-D00001.png)
* [Figura 3 — Detalhe da Conectividade dos Sensores no Edge](https://patentimages.storage.googleapis.com/ca/c9/ed/b7bf198a0bf9e5/US20230196201A1-20230622-D00002.png)
* [Figura 4 — Arquitetura Interna do AIP System](https://patentimages.storage.googleapis.com/23/58/b7/702555c4652bfb/US20230196201A1-20230622-D00003.png)

### Arquitetura de Design
* **Data API e Inference API:** Criam uma blindagem entre hardware e software. Sensores e algoritmos conectam-se por especificações formais.
* **Grafos Acíclicos Direcionados (DAGs):** As saídas de um sensor/modelo acionam e alimentam outros de forma coordenada (ex: detecção de RF ativa busca de imagem por satélite SAR e depois classifica via CV).

---

## 5. US 12,374,011 B2 — Ontology Map
* **Título:** *Interactive data object map*
* **Inventores:** Lauren Shearer, Anand Gupta, Cassandra Wang, Tess Druckenmiller, Dan Cervelli, Vineel Kodikanti.
* **Propósito:** Indexação e exibição de objetos ontológicos de inteligência com filtros dinâmicos rápidos sobre um mapa geográfico.

### Diagramas Originais da Patente
* [Figura 1 — Interface do Mapa de Objetos](https://patentimages.storage.googleapis.com/US12374011B2/US12374011-20250729-D00000.png)
* [Figura 2A/B — Mapeamento Hierárquico de Ontologia de Camadas](https://patentimages.storage.googleapis.com/US12374011B2/US12374011-20250729-D00001.png)
* [Figura 3A/B — Geração de Histograma e Seleção Retangular](https://patentimages.storage.googleapis.com/US12374011B2/US12374011-20250729-D00002.png)
* [Figura 4A/B — Busca Geográfica por Raio e Filtragem](https://patentimages.storage.googleapis.com/US12374011B2/US12374011-20250729-D00003.png)
* [Figura 5A/B — Renderização de Heatmap de Objetos](https://patentimages.storage.googleapis.com/US12374011B2/US12374011-20250729-D00004.png)

### Arquitetura de Design
* **UTF Grid:** Índice local no cliente que mapeia a localização dos pixels aos IDs dos objetos sem requisições adicionais de backend.
* **Filtros Cruzados:** Selecionar um conjunto de objetos gera histogramas de propriedades na tela do cliente. Filtrar uma barra do histograma faz *drill-down* imediato no mapa e recalcula as demais estatísticas.

---

## 6. Mapeamento de Herança no Athena-SDA

O **Athena-SDA** foi desenhado herdando diretamente estes princípios:

```
                  ┌────────────────────────────────────────────────┐
                  │                  ATHENA-SDA                    │
                  └───────────────────────┬────────────────────────┘
                                          │
    ┌─────────────────────────────────────┼─────────────────────────────────────┐
    ▼                                     ▼                                     ▼
[US 2023/0050870 A1]              [US 2024/0394296 A1]                  [US 12,374,011 B2]
AI Meta-Constellation              LLM + GIS integration                 Ontology & Histograms
Herança:                          Herança:                              Herança:
Uso de Micro-Modelos de ML        Decisão qualitativa e                 Histogramas dinâmicos de
para detecção de anomalias        explicabilidade de ameaça             países e tipos de órbitas
e priorização de telemetria       em linguagem natural                  com filtros cruzados no
no satélite (borda/Edge).         usando o copiloto Bob/Granite.        painel lateral da aplicação.
```
