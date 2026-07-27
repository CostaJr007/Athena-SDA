# Demonstração: previsão matemática **antes** dos reports documentados

**Athena-SDA** · Validação walk-forward (expanding window)  
**Dados:** TLE públicos HF `space-track-tle-history` filtrados à watchlist · **2014-01-01 → 2026-07-25**  
**Artefatos:** `data/alerts/walkforward/wf_*.json` · `demostracao_previsao_pre_report.csv`

---

## 1. Tese que estamos demonstrando

> Com **apenas** séries TLE e o stack **math + Isolation Forest** (sem notícia, sem label classificado),  
> o sistema produz **sinais de anomalia de comportamento** **antes** da data pública do report  
> (Gunter/CSIS/Breaking Defense/SWF/AMOS),  
> enquanto satélites **placebo** no **mesmo calendário** não disparam o mesmo padrão.

Isso é **previsão relativa a publicação open-source**:  
o modelo **não “lê o futuro”**; ele detecta **ruído/desvio no passado** que **antecede** o marco temporal do report.

---

## 2. O que é o detector (1 minuto)

```
TLE (passado) → features math (Shannon, Hurst, Kolmogorov, Mandelbrot, ADF, Δa, …)
             → Isolation Forest treinado SÓ no passado de cada data
             → anomaly_score ∈ [0,1]
```

| Peça | Papel |
|------|--------|
| **Math** | Descreve o *tipo* de ruído (caos, persistência, extremos, não-estacionariedade) |
| **Isolation Forest** | Diz se o *vetor* é atípico vs o “normal” aprendido **antes** daquela data |
| **Walk-forward** | Em datas sucessivas *antes* do report, repete treino+score **sem peeking** |
| **Placebo** | Mesmo calendário, satélite “civil/estável” — controle de falso alarme |

### Protocolo (sem vazamento de futuro)

Para cada data `asof` no caminho até o report `t_peak`:

1. Treinar IF só com janelas com `window_end < asof − 3 dias`  
2. Scorear o satélite-alvo na janela que termina em `asof`  
3. Registrar `anomaly_score(asof)`  
4. Comparar a curva **antes** de `t_peak` com a de um **placebo**

**Soft alarme:** score ≥ 0,45  
**Alarme rígido:** score ≥ 0,50  
**Elevated pré-peak:** max/média pré-peak compatíveis com ruído elevado (critério do pipeline)

---

## 3. Reports documentados (âncoras públicas)

| ID | Objeto | Peak (report / marco open-source) | Fonte (aberta) |
|----|--------|-----------------------------------|----------------|
| `luch1_intelsat_mid2015` | Luch / Olymp-K 1 (#40258) | **2015-04-15** | Gunter: colocação entre Intelsat 7/901 ~abr/2015 |
| `luch1_intelsat_2015` | Luch-1 | **2015-09-15** | Gunter/CSIS: perto de Intelsat 905 ~set/2015 |
| `luch1_athena_fidus_2018` | Luch-1 | **2018-09-01** | Open press: preocupação Athena-Fidus (FR) ~2018 |
| `sy12_geo_rpo_2021_22` | Shiyan-12 01 (#50321) | **2022-06-15** | AMOS/SWF: RPO GEO SY-12 2021–22 |
| `luch2_trailing_2023` | Luch-5X (#55841) | **2023-10-15** | Launch mar/2023; Breaking Defense out/2023 “trailing Western systems” |

**Placebos (controle):**

| ID | Objeto | Peak (mesmo calendário) |
|----|--------|-------------------------|
| `placebo_terra_2015` | TERRA #25994 | 2015-09-15 |
| `placebo_terra_2018` | TERRA | 2018-09-01 |
| `placebo_noaa20_2023` | NOAA-20 #43013 | 2023-10-15 |

---

## 4. Resultado matemático principal

### 4.1 Tabela de evidência (pré-report)

| Evento / peak | Satélite | Elevated **antes** do peak? | Soft hit (≥0,45) na janela | Hit rígido (≥0,50) | Max IF pré/na série | **Lead soft** (1º soft ≤ peak) | Near-peak IF |
|---------------|----------|----------------------------|---------------------------|--------------------|-----------------------|--------------------------------|--------------|
| Intelsat **abr/2015** | Luch-1 | **SIM** | **SIM** | não | **0,73** | **~182 dias** | 0,63 |
| Intelsat **set/2015** | Luch-1 | **SIM** | **SIM** | não | **0,64** | **~243 dias** | 0,48 |
| Athena-Fidus **2018** | Luch-1 | **SIM** | **SIM** | não | **0,66** | **~243 dias** | 0,57 |
| SY-12 **2022** | SY-12 01 | **SIM** | **SIM** | não | **0,62** | **~154 dias** | 0,46 |
| Luch-2 **2023** | Luch-5X | **SIM** | **SIM** | **SIM** | **0,66** | **~197 dias** | 0,50 |
| Placebo TERRA 2015 | TERRA | **NÃO** | **NÃO** | não | 0,41 | — | 0,33 |
| Placebo TERRA 2018 | TERRA | **NÃO** | **NÃO** | não | 0,44 | — | 0,36 |
| Placebo NOAA 2023 | NOAA-20 | **NÃO** | soft fraco | não | 0,46 | (não elevated) | 0,34 |

CSV reproduzível: `data/alerts/walkforward/demostracao_previsao_pre_report.csv`

### 4.2 Agregado (prova de separação)

| Métrica | Interesse (5 reports) | Placebo (3 controles) |
|---------|----------------------|------------------------|
| Taxa **elevated_pre_peak** | **100% (5/5)** | **0% (0/3)** |
| Taxa **soft hit** | **100% (5/5)** | 33% (1/3, sem elevated) |
| Taxa **hit rígido** | 20% (1/5) | **0%** |
| Média **max anomaly** | **0,66** | **0,44** |
| Lead soft médio | **~204 dias** antes do peak | — |

**Interpretação para demo:**

1. Em **todos** os casos de interesse, o detector marcou ruído elevado **no intervalo pré-report**.  
2. Nos **placebos** do mesmo calendário, **não** há elevated pré-peak.  
3. O alarme **soft (≥0,45)** antecede o marco público em **~5–8 meses** (ordem de grandeza dos leads).  
4. O limiar rígido 0,50 é conservador (só Luch-2 “bate” no peak window); o argumento forte é **pré-peak + contraste placebo + max IF**.

---

## 5. Como dizer no pitch (frase pronta)

> “Rodamos walk-forward: em cada data *antes* do report open-source, o Isolation Forest é treinado *somente* com o passado e pontua o satélite.  
> Nos casos Luch (Intelsat 2015, Athena-Fidus 2018) e SY-12 (2022), o score de anomalia já estava elevado **meses antes** da âncora pública,  
> enquanto TERRA/NOAA no mesmo calendário permaneceram no regime normal.  
> Ou seja: o **ruído matemático da órbita antecipa** o que a literatura aberta só documenta depois.”

---

## 6. O que **não** afirmar

| Não dizer | Por quê |
|-----------|---------|
| “Previmos espionagem classificada” | Só TLE + reports públicos |
| “Accuracy 99% / prova forense” | Labels fracos; thr rígido 20% hit |
| “CUSUM sozinho pegou tudo” | Sinal principal = **IF no vetor math** + contraste placebo |
| “Sem dados de 2015” | **Já resolvido:** history 2014–2026 |

---

## 7. Como reproduzir

```bash
cd "/run/media/adeilsoncosta/Novo volume/Athena-SDA"

# (se precisar re-seed anos dos reports)
# python3 scripts/run_anomaly_monitor.py seed-history --hf --start-year 2014 --end-year 2023 --skip-local

python3 scripts/run_walkforward.py run --step-days 14 --threshold 0.50
python3 scripts/run_walkforward.py summary

# tabela da demonstração
python3 -c "import pandas as pd; print(pd.read_csv('data/alerts/walkforward/demostracao_previsao_pre_report.csv').to_string())"
```

---

## 8. Conclusão

| Pergunta | Resposta demonstrável |
|----------|------------------------|
| O modelo viu algo **antes** do report? | **Sim** — elevated pré-peak em 5/5 casos de interesse |
| Isso é “achismo”? | **Não** — treino sem futuro + placebo no mesmo tempo |
| O que “prevê”? | **Publicação/documentação open-source de comportamento anômalo**, via desvio estatístico da série orbital |
| Separação vs normal? | Max IF **0,66** vs placebo **0,44**; elevated 100% vs 0% |

**Demonstração fechada para o argumento:** math + IF em walk-forward **antecipam o marco temporal dos reports documentados**, com controle placebo negativo.
