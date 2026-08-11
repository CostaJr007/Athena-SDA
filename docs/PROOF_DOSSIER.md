# Athena-SDA — Proof Dossier (embasamento · funcionamento · diferencial)

> Este documento prova, com referências verificadas e procedimentos
> reproduzíveis, que o Athena-SDA (a) tem **embasamento matemático/acadêmico
> verificável**, (b) **funciona** de forma reproduzível e (c) tem **diferencial
> real** frente a projetos open-source de SDA.
>
> Estado: **2026-08-10** — framework matemático corrigido (LZ76, DFA, MMD,
> Page CUSUM+EWMA ARL, permutation entropy, SSA, BOCPD, LKF innovation,
> fusão evidencial Dempster-Shafer).

---

## 1. Embasamento — cada feature aponta para sua referência verificada

| Feature | Identidade matemática | Referência verificada |
|---|---|---|
| `shannon_entropy_sma_30d` | Entropia de Shannon plug-in (bias documentado em n=20) | Shannon 1948, *Bell Syst. Tech. J.* 27 — DOI 10.1002/j.1538-7305.1948.tb01338.x |
| `lz76_complexity` | Complexidade LZ76 (Kaspar-Schuster) | Kaspar & Schuster 1987, *Phys. Rev. A* 36:842 — DOI 10.1103/PhysRevA.36.842 |
| `dfa_hurst_sma` | Detrended Fluctuation Analysis α | Peng et al. 1994, *Phys. Rev. E* 49:1685 — DOI 10.1103/PhysRevE.49.1685; Hu et al. 2001 (trend caveat) DOI 10.1103/PhysRevE.64.011114 |
| `permutation_entropy` | Entropia de permutação (ordinal) | Bandt & Pompe 2002, *PRL* 88:174102 — DOI 10.1103/PhysRevLett.88.174102 |
| `complexity_entropy_c` | Complexidade Jensen-Shannon (plano H-C) | Rosso et al. 2007, *PRL* 99:154102 — DOI 10.1103/PhysRevLett.99.154102 |
| `page_cusum_sma` | CUSUM bilateral de Page, calibrado ARL₀≈365 | Page 1954, *Biometrika* 41:100 — DOI 10.1093/biomet/41.1-2.100; Moustakides 1986 (otimalidade) DOI 10.1214/aos/1176350057; Siegmund 1985 (ARL) |
| `ewma_sma` | EWMA (ótimo para shifts pequenos) | Roberts 1959, *Technometrics* 1:239 — DOI 10.1080/00401706.1959.10489860; Lucas & Saccucci 1990 |
| `bocpd_change_prob_3d` | BOCPD — probabilidade bayesiana de regime | Adams & MacKay 2007, arXiv:0710.3742 |
| `innovation_score` | KF linear em SMA + inovação normalizada ε=yᵀS⁻¹y | **Zollo & Weigel 2023**, *Adv. Space Res.* — DOI 10.1016/j.asr.2023.10.032 (open access) |
| `ssa_residual_last` | SSA — resíduo de reconstrução low-rank | Broomhead & King 1986, *Physica D* 20:217 — DOI 10.1016/0167-2789(86)90031-X; Golyandina et al. 2001 |
| `mmd_typicality` | MMD two-sample (typicality = 1−p) | Gretton et al. 2012, *JMLR* 13:723 — jmlr.org/papers/v13/gretton12a.html |
| `mandelbrot_tail_score` | Hill estimator em \|ΔSMA\| (extremeness rank) | Hill 1975, *Ann. Stat.* 3:1163 — DOI 10.1214/aos/1176343247; Mandelbrot 1963 |
| `adf_pvalue` | ADF em SMA detrended (baixo poder em n=20 documentado) | Dickey & Fuller 1979, *JASA* 74:427 — DOI 10.2307/2286348 |
| `cointegration_pvalue` | Engle-Granger (alinhado, ≥20 pts, FDR) | Engle & Granger 1987, *Econometrica* 55:251 — DOI 10.2307/1913236 |
| `dcca_rho` (par) | Detrended cross-correlation | Podobnik & Stanley 2008, *PRL* 100:084102 — DOI 10.1103/PhysRevLett.100.084102 |
| `h0/h1_persistent` | Persistência homológica (H0 barra infinita incluída) | Edelsbrunner et al. 2002, *DCG* 28:511 — DOI 10.1007/s00454-002-2885-2 |
| `static_threat` | Heurística doutrinária (TVA/JP 3-60) — **não é matemática** | JP 3-60 *Joint Targeting* (jcs.mil) |
| fusão `evidence.*` | Dempster-Shafer (belief/plausibility/conflito) | Shafer 1976, Princeton UP; Smets & Kennes 1994, *AIJ* 66:191 — DOI 10.1016/0004-3702(94)90026-4 |

### Grounding de domínio (TLE / manobra orbital)
- **Lemmens & Krag 2014**, "Two-Line-Elements-Based Maneuver Detection Methods
  for Satellites in Low Earth Orbit", *JGCD* 37(3):860 — DOI 10.2514/1.61300.
  Método 2 = robust statistics + harmonic analysis sobre a série de elementos
  (a base conceitual da nossa camada de ruído). ⚠️ **Não atribuir CUSUM a eles**
  — o método deles é propagação SGP4 + estatística robusta.
- **Bai et al. 2019**, "Mining Two-Line Element Data to Detect Orbital Maneuver
  for Satellite", *IEEE Access* 7 — DOI 10.1109/ACCESS.2019.2940248 (clustering
  de features TLE; demonstrado em YAOGAN-9).
- **Kelecy et al. 2007**, AMOS (janela deslizante em SMA/energia) — fundacional.
- **Patera 2008**, "Space Event Detection Method", *JSR* 45(3) — DOI 10.2514/1.30348.
- **Siew et al. 2025** (MIT ARCLab **SPLID** benchmark), *J. Astronautical
  Sciences* — DOI 10.1007/s40295-025-00515-5 (dataset público; top solução =
  XGBoost — a mesma stack do Athena-SDA).
- **Liu et al. 2021**, "TLE outlier detection based on expectation
  maximization", *Adv. Space Res.* — DOI 10.1016/j.asr.2021.07.013
  (ruído TLE vs manobra — honestidade metodológica).

---

## 2. Funcionamento — reprodução passo a passo

Gate: `python scripts/smoke_test.py` → **SMOKE OK** (2026-08-10, Python 3.14,
numpy/pandas/sklearn/statsmodels/xgboost instalados).

### Do zero (máquina nova)
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python scripts/run_anomaly_monitor.py seed-history --start-year 2014   # TLE histórico
python scripts/run_anomaly_monitor.py seed-space-weather --start-year 2014
python scripts/run_anomaly_monitor.py train-baseline                  # monitor IF (hot-swap versionado)
python -c "from src.models import train_and_save_models; train_and_save_models()"  # pipeline IF+XGB+referência
python scripts/run_anomaly_monitor.py score                           # risk_report_latest.json
python scripts/run_anomaly_monitor.py score-pairs                     # proximidade + pares
python scripts/run_paper_validation.py --run-wf --threshold 0.50      # Claims A+B (walk-forward)
cd src/frontend && npm install && npm run dev                         # UI mission board
```

### O que é verificado por `smoke_test.py`
1. **Detectores corrigidos respondem a manobra sintética**: Page CUSUM, EWMA e
   contagem de regimes separam um salto de +4 km de drift quieto (assert).
2. **LZ76**: rampa regular < série caótica (assert).
3. **MMD**: outlier pontua > inlier; sem referência → neutro 0.5 (assert);
   MMD excluído das colunas do IF.
4. **Schema de features**: todas as `IFOREST_COLUMNS` presentes; features
   legadas (`kolmogorov_proxy_7d`, `hurst_exponent_sma`, `l1_cusum_sma`,
   `spectral_anomaly_rkhs`, `chern_simons_proxy`, `ricci_mean`,
   `williams_threat`, `lukasiewicz_implication`, `maneuver_count_30d`) ausentes.
5. **Sem NaN/Inf** em 24 satélites reais (verificado à parte: 8 amostras, 0
   NaN).
6. **Doutrina**: baseline nunca escala militar; suspect outlier = detecção.
7. **Bob** gera briefing sem inventar scores; cita casos (NORAD 40258).

### Evidências de funcionamento (2026-08-10, features corrigidas)
- Modelos re-treinados com o schema corrigido: monitor IF 43 features ✓,
  pipeline IF 43 ✓, XGB 49 ✓, referência MMD 948×10 ✓ (schema match 100%).
- Em 24 satélites reais: **ISS (25544) destaca-se** em Page CUSUM (0.54) e
  EWMA (0.72) — consistente com station-keeping/reboost frequentes; objetos
  quietos ≈ 0 (discriminação real, sem saturação).
- Fusão evidencial: quieto bel=0.002 / anomalia bel=0.990 / conflito K=0.28 /
  TLE velho → ignorância cresce (plausibility sobe).
- Registro de modelos com **paths relativos** (corrigido o `D:\` do Windows).

### Validação Claims A+B (walk-forward) — RE-VALIDADA 2026-08-10

**Resultados finais com o framework corrigido** (`run_paper_validation --run-wf
--threshold 0.50`, 18 eventos, 11 interesse + 7 placebo):

| Painel | Hard hits | Mean max | Nota |
|---|---|---|---|
| **A — GEO headline** (Luch/SY-12, 5 eventos, 3 NORADs) | **5/5** | **0.716** | pre-peak mean 0.637 |
| **A — core** (11 eventos, 9 NORADs) | **7/11** | 0.616 | inclui LEO/MEO |
| **B — civil EO placebo** (7 eventos) | **0/7** | 0.457 | p95 = 0.495 (abaixo do thr) |
| Separação GEO | — | gap 0.260 | Mann-Whitney **p=0.0013** |
| Separação core | — | gap 0.160 | Mann-Whitney **p=0.010** |

`PAPER_CLAIMS_SUPPORTED` · exit 0. O headline 5/5 vs 0/7 é **preservado** com
a matemática corrigida — a re-validação confirma que a detecção era real, não
artefato das features quebradas. Misses honestos: Yaogan-3/29 (LEO recon,
max 0.39-0.42), Shiyan-7 (0.55).

---

## 3. Diferencial — por que NÃO é "mais um open-source"

| Dimensão | OSS típico (keeptrack.space, repos 0-1★) | Athena-SDA (pós-correção) |
|---|---|---|
| Validação de detecção de manobra | Sem validação temporal | **Walk-forward em eventos militares documentados + placebo control (Claims A+B)** |
| Grounding acadêmico | Sem citações | **20+ métodos com DOI por feature (tabela §1)** |
| Benchmark objetivo | Nenhum | **SPLID (MIT ARCLab) — top solução usa XGBoost, nossa stack** |
| Arquitetura | Monolito | **Ontologia tipada + Data/Inference/Open API + micro-modelos hot-swap** |
| Explicabilidade | Black-box | **Bob LLM com citação de fontes abertas + fusão evidencial DS** |
| Visual | Genérico | **Globo 3D tático-C2 com cross-filters ontológicos (padrão Maven/DST)** |
| Honestidade | "99% accuracy" | **Limites documentados: noise floor TLE, cadência, pattern-of-life ≠ intenção** |

**Frase de 1 linha:** *o único pipeline open-source de SDA militar com
validação walk-forward em eventos documentados, benchmark público (SPLID),
framework matemático citado por feature e arquitetura ontológica padrão
Palantir.*

---

## 4. Limitações honestas (leia antes de citar o projeto)

1. **Noise floor do TLE**: erro de SMA ~100–500 m; cadência de publicação
   1–4 TLEs/dia → detectamos a **assinatura estatística de micromovimentação**
   (mudança de regime do padrão de ruído), **não o empuxo individual**.
2. **Janelas curtas (n=20-30)**: ADF subpoderoso, R/S tendencioso (motivo da
   troca por DFA/SSA/BOCPD); persistência residual de viés documentada.
3. **Âncoras públicas ≠ ground truth forense**: eventos citados de Gunter,
   CSIS, SWF, pressa são janelas temporais de relato — não telemetria real.
4. **Pattern-of-life ≠ intenção**: classificação comportamental (per Wang & Li
   2022), nunca "espionagem confirmada".
5. **`static_threat` é doutrina, não matemática**: pesos de país/missão são
   política configurável (JP 3-60), não derivados de dados.
6. **Dados de treino**: mock + histórico real público; cenário de demo é
   narrativa separada da análise validada.
7. **Cointegração**: exige alinhamento de épocas (merge_asof) e ≥20 pontos;
   nunca testar (SMA, mean_motion) — tautologia de Kepler.

---

## 5. Rastreabilidade de código (onde cada coisa mora)

| Módulo | Papel |
|---|---|
| `src/engine.py` | 20+ métodos matemáticos corrigidos (features) |
| `src/innovation.py` | KF linear + inovação normalizada (Zollo & Weigel) |
| `src/evidence.py` | Fusão evidencial Dempster-Shafer |
| `src/changepoint.py` | PELT/binary-segmentation (auto-label de manobra) |
| `src/ontology.py` + `src/ontology.json` | Modelo de objetos tipado (OSDK-style) |
| `src/contracts.py` + `schemas/risk_report.v1.schema.json` | Contrato Open API validado |
| `src/model_registry.py` + `models/registry.json` | Registry de micro-modelos (paths relativos) |
| `src/pair_score.py` | Par suspect×asset (cointegração alinhada + DCCA + Kelly) |
| `src/bob.py` | Bob 4-estágios (LLM descreve; scores imutáveis; cita casos) |
| `docs/references/palantir_patents.md` | Citações de patentes **verificadas e corrigidas** |

---

## 6. Checklist de verificação final (antes do demo)

- [ ] `python scripts/smoke_test.py` → SMOKE OK
- [ ] `python scripts/run_paper_validation.py --run-wf --threshold 0.50` → tabela
      Claims A+B **re-validada com features corrigidas** (atualizar §2)
- [ ] `risk_report_latest.json` valida contra `schemas/risk_report.v1.schema.json`
- [ ] `git status` limpo (sem ruído CRLF — `.gitattributes` ativo)
- [ ] `npm run lint` verde + `npm run build` ok (frontend)
- [ ] SPLID benchmark (opcional, alto valor): rodar pipeline no dataset público
