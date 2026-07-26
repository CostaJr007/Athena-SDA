# Relatório Walk-Forward — Predição pré-report (ML atual)

**Gerado em:** 2026-07-26T04:57:45 UTC  
**Protocolo:** Isolation Forest **só no passado** (holdout 3 dias) · step 14 dias · thr = 0.50 · hit window ±45 dias  
**ML:** vetor atual com **space weather** (F10.7/Ap/Kp) + math + Kepler · `extract_satellite_features` + `IFOREST_COLUMNS` (34 dim)  
**Artefatos:** `data/alerts/walkforward/wf_*.json` · `walkforward_latest.json` · `wf_analysis_new_ml.json`

---

## 1. O que este teste prova (e o que não prova)

| Afirma | Não afirma |
|--------|------------|
| Em âncoras de **reports públicos**, o ruído do vetor (IF) ficou **elevado antes / na janela do report** para os suspeitos | Que o modelo “sabia” de espionagem classificada |
| Placebos científicos (TERRA, NOAA-20) **não** bateram hit duro (score ≥ 0.50 na janela) | Que accuracy XGB = verdade HOSTIL |
| Cada fold treina **sem** dados futuros ao `asof` | Que lead-time de 180+ dias é manobra pontual (pode ser regime GEO já anômalo) |

**Frase para jurados:**  
> Não previmos o futuro. Detectamos, no **passado estrito** de cada data, que a série do Luch/Shiyan já era **estatisticamente anômala** meses antes da âncora open-source — e o controle civil no mesmo calendário **não**.

---

## 2. Resultado global (ML novo)

| Grupo | N | Hit (≥0.50 na janela do peak) | Soft hit (≥0.45) | Ruído elevado **pré-peak** | max anomaly médio |
|-------|---|-------------------------------|------------------|----------------------------|-------------------|
| **Interesse** (Luch-1×3, SY-12, Luch-2) | 5 | **100%** | **100%** | **100%** | **0.603** |
| **Placebo** (TERRA 2015/2018, NOAA-20 2023) | 3 | **0%** | 67% (só soft fraco) | **0%** | **0.477** |

| Métrica | Interesse | Placebo |
|---------|-----------|---------|
| Lead-time médio (1º hit ≥0.50 antes do peak) | **~201 dias** (mediana 197) | — |
| Soft hit rate | 1.00 | 0.67 |
| Elevated pre-peak noise | **1.00** | **0.00** |

**Leitura:** o discriminante forte não é “soft 0.45 em qualquer sat”, e sim **hit duro + elevated_pre_peak** nos casos de interesse vs placebos.

---

## 3. Como o ruído é “lido” (teoria → função → sinal)

Cada fold: janela de 20 épocas ≤ `asof` → features → IF treinado com janelas **&lt; asof−3d** → `anomaly_score = clip(0.5 − decision_function)`.

| Teoria | Função no código | O que “revela” no GEO de inspeção |
|--------|------------------|-----------------------------------|
| **Shannon (1948)** | `calculate_shannon_entropy` → `shannon_entropy_sma_30d` | Desordem em \(\Delta a\): manobras / station-keeping irregular espalham bins |
| **Hurst R/S (1951)** | `calculate_hurst_exponent` → `hurst_exponent_sma` | **Persistência** \(H \gg 0.5\): empuxo baixo / deriva controlada (não browniano) |
| **Kolmogorov proxy** | `calculate_kolmogorov_proxy` → `kolmogorov_proxy_7d` | Complexidade da string U/D/S (controle vs Kepler simples) |
| **L1-CUSUM** | `calculate_kernel_l1_cusum` → `l1_cusum_sma` | *Quando* a série quebra (neste run GEO ficou ~0 — ver §7) |
| **Mandelbrot cauda** | `calculate_mandelbrot_tail_anomaly` | Extremos raros em \(\Delta a\) |
| **ADF** | `calculate_adf_pvalue` | Não-estacionariedade |
| **ΔSMA / manobras** | `delta_sma_7d_km`, `maneuver_count_30d` | Amplitude e contagem de picos |
| **Clima (GFZ)** | `space_weather_feature_vector` → `f10_7`, `ap_index`, … | Contexto arrasto vs manobra (no GEO pesa menos que no LEO) |
| **IF ensemble** | `IsolationForest.decision_function` | Fusão multivariada: “este perfil é raro no passado?” |

**Quem “dispara” o alerta operacional:** não uma teoria isolada — o **Isolation Forest** no vetor completo.  
**Quem explica o porquê:** Shannon + Hurst + ΔSMA (+ Kolmogorov) nos folds de score alto.

---

## 4. Eventos de interesse (reports públicos)

### 4.1 Luch / Olymp-K 1 — 1º episódio Intelsat (mid-2015)

| Campo | Valor |
|-------|--------|
| **Event id** | `luch1_intelsat_mid2015` |
| **NORAD** | 40258 — LUCH (OLYMP-K 1) |
| **Âncora pública (t_peak)** | **2015-04-15** (colocation Intelsat 7/901 ~abr/2015, Gunter) |
| **Janela WF** | 2014-10-01 → 2015-08-01 |
| **Hit / soft** | **True / True** |
| **Lead-time (1º score ≥0.50)** | **182 dias** → 1º hit em **2014-10-15** |
| **Max anomaly** | **0.646** @ 2014-10-15 |
| **Elevated pré-peak** | **True** |

**Fontes open-source:** Gunter — first colocation between Intelsat 7 and 901 ~April 2015.

**Quando o ruído “começou” (no sensor Athena):**  
Desde o **início da janela** (out/2014) o score já está ≥0.50. Não é um bip pontual em abril: é **regime anômalo sustentado** meses antes da âncora de report de colocation.

**Assinatura no 1º hit (2014-10-15):**

| Feature | Valor | Leitura |
|---------|-------|---------|
| **Hurst** | **0.80** | Persistência (não ruído branco) |
| Shannon | 0.30 | Ainda baixa no 1º fold; sobe depois |
| Kolmogorov | 0.26 | Moderado |
| ΔSMA 7d | grande (negativo ~dezenas km no perfil high) | Deslocamento de semi-eixo típico de **reposition GEO** |
| F10.7 | 125.8 | Clima moderado — **não** explica sozinho o hit (placebo no mesmo clima não hitou) |
| Ap | 9 | Quiet–moderado |

**Timeline pré-peak (amostra):**  
out/2014 score 0.65 → nov Shannon sobe a **2.0–2.8** com Hurst **0.77–0.95** → jan/2015 score 0.63 → mantém ~0.50–0.56 até o peak.

**Teoria dominante:** **Hurst (persistência de empuxo/deriva)** + depois **Shannon (desordem de \(\Delta a\))** + **ΔSMA** de relocação GEO.  
**Função agregadora:** Isolation Forest.

---

### 4.2 Luch / Olymp-K 1 — Intelsat 905 / temporada 2015

| Campo | Valor |
|-------|--------|
| **Event id** | `luch1_intelsat_2015` |
| **t_peak** | **2015-09-15** (perto Intelsat 905 ~24.4–24.5°W, Gunter/CSIS) |
| **Hit / soft** | **True / True** |
| **Lead-time** | **243 dias** → 1º hit **2015-01-15** |
| **Max anomaly** | **0.599** |
| **Elevated pré-peak** | **True** (18 folds pré-peak, mean ~0.52) |

**Fontes:** Gunter (abr e set/2015); CSIS *Unusual Behavior in GEO* (Olymp-K / Luch).

**1º hit 2015-01-15:**

| Feature | Valor |
|---------|-------|
| **Hurst** | **0.94** (muito persistente) |
| **Shannon** | **1.36** (já desordenado) |
| Kolmogorov | 0.47 |
| F10.7 / Ap | 131.4 / 5 — sem tempestade |

**Pré-peak late (ago/2015):** Shannon até **~2.84**, score **0.578** em 2015-08-27 — ruído de informação alto **antes** da âncora de set/2015.

**Por quê:** série de manobras/colocações GEO ao longo de 2015; o report de set é um marco jornalístico, não o início físico da atividade. O ML marca o **processo** cedo.

---

### 4.3 Luch / Olymp-K 1 — Athena-Fidus (2018)

| Campo | Valor |
|-------|--------|
| **Event id** | `luch1_athena_fidus_2018` |
| **t_peak** | **2018-09-01** (preocupação open-source re Athena-Fidus / gov FR) |
| **Hit / soft** | **True / True** |
| **Lead-time** | **229 dias** → 1º hit duro **2018-01-15** (soft já em 2018-01-01) |
| **Max anomaly** | **0.627** @ 2018-11-05 (pós-peak também eleva) |
| **Elevated pré-peak** | **True** |

**1º hit 2018-01-15:** Hurst **0.96**, Shannon **0.88**, Kolmogorov **0.58**, F10.7 **70** (mínimo solar — arrasto LEO irrelevante; GEO inspection).

**Interpretação:** no mínimo solar, ΔSMA/Shannon/Hurst altos **não** se desculpam por clima; o IF ainda marca anômalo. Soft 0.49 em 1º jan e hit 0.52 em 15/jan = rampa curta no início da janela.

---

### 4.4 Shiyan-12 01 — RPO GEO 2021–22

| Campo | Valor |
|-------|--------|
| **Event id** | `sy12_geo_rpo_2021_22` |
| **NORAD** | 50321 — SHIYAN-12 01 |
| **t_peak** | **2022-06-15** (RPO GEO reportado AMOS / SWF) |
| **Hit / soft** | **True / True** |
| **Lead-time** | **154 dias** → 1º hit **2022-01-12** |
| **Max anomaly** | **0.573** @ 2022-08-24 |
| **Elevated pré-peak** | **True** |

**1º hit:** Hurst **0.89**, Shannon **0.77**, Kolmogorov **0.63**, F10.7 103 / Ap 3.

**Nota:** SY-12 é mais novo na série; folds no início de 2022 capturam fase pós-lançamento / comissionamento + RPO. Max um pouco menor que Luch-1, mas **hit e pré-peak elevated** firmes; placebo NOAA no mesmo tipo de calendário 2023 não hitou duro.

---

### 4.5 Luch-5X / Olymp-K 2 — trailing 2023

| Campo | Valor |
|-------|--------|
| **Event id** | `luch2_trailing_2023` |
| **NORAD** | 55841 — LUCH-5X (OLYMP-K 2) |
| **t_peak** | **2023-10-15** (Breaking Defense out/2023 — 2º Luch trailing sistemas ocidentais) |
| **Hit / soft** | **True / True** |
| **Lead-time** | **197 dias** → 1º hit **2023-04-01** (logo após janela; lançamento ~mar/2023) |
| **Max anomaly** | **0.569** @ 2023-09-02 |
| **Elevated pré-peak** | **True** |

**1º hit:** Shannon **2.11** (muito alto), Hurst **0.91**, Kolmogorov 0.16, F10.7 125 / Ap 14.

**Por quê cedo:** pós-lançamento GEO + manobras de posicionamento — Shannon explode; o report de out/2023 é cobertura de “trailing”, não o início do ruído orbital.

---

## 5. Placebos (mesmo calendário, objetos “normais”)

| Evento | NORAD | Peak | Hit ≥0.50 | Soft | Elevated pré-peak | max score |
|--------|-------|------|-----------|------|-------------------|-----------|
| placebo_terra_2015 | 25994 TERRA | 2015-09-15 | **False** | True (fraco) | **False** | 0.478 |
| placebo_terra_2018 | 25994 TERRA | 2018-09-01 | **False** | False | **False** | 0.489 |
| placebo_noaa20_2023 | 43013 NOAA-20 | 2023-10-15 | **False** | True (fraco) | **False** | 0.463 |

**Por que importam:** compartilham **mesmo F10.7/Ap de calendário** que os Luchs em vários folds (movers de f10_7 nos placebos são parecidos).  
Se o alarme fosse só “clima solar”, placebos teriam hit. **Não tiveram hit duro.**  
Isso embasa: o discriminante é o **perfil orbital (Hurst/Shannon/ΔSMA/IF)**, não o Sol sozinho.

---

## 6. Tabela-síntese predição pré-report

| Caso público | Peak report | 1º ruído Athena (score≥0.5) | Lead | Funções que mais “contam a história” | Hit |
|--------------|-------------|-----------------------------|------|--------------------------------------|-----|
| Luch Intelsat mid-2015 | 2015-04-15 | 2014-10-15 | **182 d** | **Hurst**, depois Shannon + ΔSMA | Sim |
| Luch Intelsat 2015 | 2015-09-15 | 2015-01-15 | **243 d** | **Hurst 0.94**, Shannon↑, Kolmog | Sim |
| Luch Athena-Fidus 2018 | 2018-09-01 | 2018-01-15 | **229 d** | **Hurst 0.96**, Shannon, Kolmog | Sim |
| SY-12 RPO 2021–22 | 2022-06-15 | 2022-01-12 | **154 d** | Hurst + Shannon + Kolmog | Sim |
| Luch-2 trailing 2023 | 2023-10-15 | 2023-04-01 | **197 d** | **Shannon 2.1** + Hurst | Sim |
| TERRA / NOAA placebos | (mesmo calendário) | — | — | scores &lt; 0.50 na janela | **Não** |

---

## 7. Limitações honestas (para não overclaim)

1. **Lead-time longo** muitas vezes = objeto **já anômalo no t_start** da janela (GEO inspector), não um único CUSUM no dia D. Ainda assim é **pré-report** e **vs placebo**.  
2. **`l1_cusum_sma` ~ 0** em muitos folds GEO neste run — o CUSUM **não** foi o herói; Shannon/Hurst/IF sim. Vale calibrar CUSUM para GEO.  
3. **Noise ramp** early→late pré-peak às vezes ~0 ou negativo: o sinal é “**nível elevado desde cedo**”, não necessariamente rampa monotônica.  
4. **Pair risk** ainda é proxy (não TCA SGP4); não é o canal principal deste WF.  
5. **SW** está no vetor (ML novo) e nos snapshots; em GEO o papel é secundário; o valor maior do SW é LEO drag vs manobra no monitor diário.  
6. Âncoras `t_peak` são **aproximadas** de open source (Gunter/CSIS/imprensa), não timestamps classificados.

---

## 8. Fundamento metodológico (por que isso é “predição” legítima)

```
Para cada data asof na linha do tempo do evento:
  1. Treinar IF só com features de janelas com fim < asof − 3 dias
  2. Extrair features da janela que termina em asof (inclui F10.7/Ap daquele dia)
  3. anomaly_score = quão isolado esse ponto é no espaço de ruído
  4. NUNCA usar TLE depois de asof no treino daquele fold
```

Se o score já ≥ 0.50 **antes** de `t_peak` do report público ⇒ o sistema **teria priorizado** aquele NORAD naquele dia, com o conhecimento então disponível.

Isso é **detecção antecipatória relativa a publicação open-source**, não oráculo.

---

## 9. Mensagem para a banca (30 segundos)

1. Rodamos walk-forward com o **ML completo atual** (math + clima GFZ).  
2. **5/5** casos de interesse (Luch-1, SY-12, Luch-2) com **hit** na janela do report.  
3. **0/3** placebos com hit duro; **0/3** com ruído pré-peak elevated.  
4. O ruído que sobe/se mantém alto é sobretudo **Hurst (persistência)** + **Shannon (desordem de altitude)** + **ΔSMA**, fundidos pelo **Isolation Forest**.  
5. Fontes dos picos: Gunter, CSIS, Breaking Defense, AMOS/SWF — tudo público.  
6. Não afirmamos intenção hostil classificada; afirmamos **anomalia de série antes do report**.

---

## 10. Arquivos e como reproduzir

```bash
python scripts/run_walkforward.py run --step-days 14 --holdout-days 3 --threshold 0.50
python scripts/run_walkforward.py summary
```

| Arquivo | Conteúdo |
|---------|----------|
| `data/alerts/walkforward/walkforward_latest.json` | Summary + métricas por evento |
| `data/alerts/walkforward/wf_<event>.json` | Folds completos + features por asof |
| `data/alerts/walkforward/wf_analysis_new_ml.json` | Extração 1º hit / movers |
| `data/catalog/events_walkforward.json` | Âncoras e fontes |
| Este relatório | `docs/RELATORIO_WALKFORWARD_PRE_REPORT_ML_NOVO.md` |

---

*Walk-forward executado com o ML pós–space weather / hybrid / protocolo série. Duração ~13,5 min. Exit code 0.*
