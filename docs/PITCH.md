# Athena-SDA — Pitch Script (1 minute)

> Framing honesto: arquitetura **inspirada em patentes públicas da Palantir** —
> nunca "construído com Palantir" nem afiliação. Validação por walk-forward
> em eventos documentados; benchmark público SPLID quando disponível.

---

## Abertura (0:00–0:15) — o problema

> "Operadores não conseguem vigiar 45.000+ objetos do catálogo espacial
> (18 SDS / USSPACECOM) o tempo todo. Legacy systems lançam alertas sem
> explicar, priorizar ou recomendar ação. O Athena-SDA transforma TLE
> públicos + clima espacial em **insights operacionais militares** — de
> milhares de objetos para um punhado de decisões por dia."

## A arquitetura (0:15–0:40) — o que construímos

> "Implementamos a arquitetura de 5 patentes públicas da Palantir:
>
> - **Micro-modelos orquestrados** com hot-swap por dia (patente AI
>   Meta-Constellation): Isolation Forest de normalidade + XGBoost de
>   prioridade + fusão evidencial Dempster-Shafer;
> - **LLM que explica, nunca reescreve scores** (patente ML+LLM geospatial):
>   o copiloto Bob contextualiza cada alerta e cita fontes abertas quando há
>   correspondência com eventos documentados;
> - **Contratos de API tipados** (patente sensor-correlation): Data API
>   (TLE), Inference API (registry de modelos), Open API (risk_report v1
>   validado por schema);
> - **Ontologia com cross-filters** (patente ontology-map): role × país ×
>   órbita filtram o board e o globo em tempo real;
> - **Replay temporal** (patente time-series geo): a curva de score até o
>   âncora público com slider.
>
> E uma camada matemática **corrigida e citada por feature** — LZ76, DFA,
> MMD, CUSUM/EWMA calibrados por ARL, SSA, BOCPD, inovação de Kalman
> (Zollo & Weigel 2023) — com DOI por método no Proof Dossier."

## A prova (0:40–0:55) — funciona e é honesto

> "Validação **walk-forward em eventos militares documentados** (Luch/
> Olymp-K, Yaogan, Shiyan, SY-12) com placebos civis: hard hits com lead de
> 150–240 dias nos casos de interesse, e os placebos **não** disparam
> (Claims A+B re-validadas). [Números finais aqui após a re-validação.]
> Benchmark público SPLID (MIT ARCLab) — onde a top solução usa XGBoost, a
> nossa stack — dá uma métrica comparável contra o estado da arte."

## Fechamento (0:55–1:00)

> "O único pipeline open-source de SDA militar com validação temporal em
> eventos documentados, framework matemático citado por feature e
> arquitetura ontológica padrão Palantir. **De 30.000 objetos a ~15 decisões
> por dia — com explicação.**"

---

## Roteiro de demo (3 min, ao vivo)

1. **Globo + board** — abrir o mission board; hover nos watchlist tracks
   (cores Maven: amarelo suspeito, azul asset).
2. **Cross-filters** — filtrar CN + GEO + suspect → board e globo dim
   (patente ontology-map).
3. **Luch/Olymp-K** — selecionar #40258 → RightDock: belief/plausibility da
   fusão evidencial + Kelly + "Task sensor" validate-only.
4. **Replay** — aba Replay no PoC panel: slider até `t_peak` com a fonte
   citada (patente time-series geo).
5. **Quant report** — abrir o HTML por NORAD (features e sinais).

## Armadilhas a evitar

- ❌ "Detectamos espiões com 99% de acurácia" — dizemos "análise
  comportamental do catálogo público, pattern-of-life ≠ intenção".
- ❌ "Real-time tracking" — TLE público é stale por definição; dizemos
  "análise do catálogo público com cadência de 1–4 TLEs/dia".
- ❌ "Construído com Palantir" — dizemos "arquitetura inspirada em patentes
  públicas verificadas (docs/references/palantir_patents.md)".
