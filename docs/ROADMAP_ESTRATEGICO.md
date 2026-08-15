# Athena-SDA — Cronograma do Estratégico (pós-Quick-Wins)

> Escopo militar / Palantir Gotham-Foundry. Quick-wins S0–S4 + S6 (agora
> ligado na UI: `investigation.v1` + FSM via sidecar) estão no código.
> Fatias iniciais de T1–T9 (hotkeys extraídos, code-split, Pc/TCA extra,
> Document, RAG citado, what-if, watchlist API, compose) já existem.
> Este documento cobre o que **ainda é profundo**: monólito do globe,
> hops temporais ricos, Pc operacional com covariância real, RAG denso.

Esforço: **S** = pequeno (≤1 semana) · **M** = médio (1–2 semanas) · **L** = grande (2–4 semanas).

## Visão geral das tracks

| # | Track | Esforço | Depende de | Entrega de saída |
|---|-------|---------|------------|------------------|
| T1 | Refactor do frontend monólito | M | — | `Home.tsx`/`globe-engine.ts` quebrados em módulos + Vitest |
| T2 | Grafo objeto-cêntrico multi-hop (search-around) | L | T1, `object_layer.py` | Navegação 2–3 hops no `InvestigationCanvas` |
| T3 | Conjunção/proximidade com covariância (Pc + TCA) | L | — (backend) | `pair_score.py` com SGP4 + elipsoide de covariância |
| T4 | Documentos/OSINT como objetos de 1ª classe (multi-INT) | M | `ontology.json` | Tipo `Document`, ingestão de relatórios abertos |
| T5 | Bob → copiloto analítico com RAG + citação | M | `bob.py`, `docs/` | Q&A multi-turno com fontes citadas |
| T6 | What-if / sandbox adversário | S–M | `utils.py`, `EventReplayPanel` | Injeção de manobra sintética + detecção |
| T7 | Watchlist dinâmica + ingesta Space-Track | M | `download_spacetrack.py`, UI | Gestão de NORAD/role pela UI |
| T8 | Code-splitting + performance do frontend | S | T1 | Chunk < 500 kB, lazy-load do globe |
| T9 | Operação & deploy | M | Dockerfile (feito) | Compose, persistência, monitoramento |

## Cronograma (semanas 1–8, 3 trilhas paralelas)

```
Semana  1     2     3     4     5     6     7     8
Trilha A (frontend/UI)
        [T1 refactor monólito]  [T2 grafo multi-hop        ]
                                      [T8 code-split ]
Trilha B (astrodinâmica/backend)
        [T3 SGP4 + covariância                 ]
        [T4 multi-INT documentos  ]
Trilha C (IA/operação)
        [T5 Bob RAG+citação      ]
        [T6 sandbox what-if]
        [T7 watchlist dinâmica        ]
        [T9 deploy/compose                          ]
```

## Detalhamento por fase

### Fase 1 (Semanas 1–2) — Fundações

**T1 — Refactor do frontend monólito (M)**
- Alvo: `src/frontend/src/pages/Home.tsx` (1.272 linhas) e `src/frontend/src/lib/globe-engine.ts` (1.390 linhas).
- Plano: extrair estado/UI 3D para hooks (`useGlobe`, `useSelection`, `useTimeline`), separar a engine Three.js da renderização React, tipar os contratos com `zod` (já é dependência).
- Exit: `npm run build` limpo; componentes HUD testados com Vitest; nenhuma regressão de comportamento.
- **Bloqueia** T2 e T8.

**T4 — Documentos/OSINT como objetos (M)**
- Adicionar tipo `Document`/`Intel` em `src/ontology.json` (categories Entity/Event/Document já previstas no docstring).
- Ingerir `data/catalog/events_walkforward.json` + relatórios abertos (Gunter/CSIS/SWF) como objetos linkáveis a `Case`/`Satellite` via `validatedBy`/`mentions`.
- Exit: `materialize_investigation` emite objetos `Document` com provenance; schema `investigation.v1` atualizado.

### Fase 2 (Semanas 2–4) — Capacidade analítica

**T3 — Conjunção com covariância SGP4 (L)**
- Hoje `pair_score.py` usa distância + cointegração/DCCA. Subir para propagação SGP4 (o frontend já tem `propagator.worker.ts` + `satellite.js`; backend precisa de `sgp4>=2.22` — hoje comentado em `requirements.txt`).
- Entregar Pc (probabilidade de colisão) e TCA (tempo de máxima aproximação) com elipsoide de covariância por par suspect→asset.
- Exit: `score_all_pairs` emite `pc`/`tca`/`covariance` por par; `risk_report.v1.schema.json` atualizado; testes de regressão com pares sintéticos.

**T5 — Bob RAG + citação (M)**
- Sobre `src/bob.py` (tool-calling já esboçado): adicionar índice RAG sobre `docs/` (proof dossier, paper, referências, patentes) e briefing multi-turno **com citação de fonte**.
- Invariante a preservar: Bob **explica**, nunca recomputa scores (princípio declarado no projeto).
- Exit: briefing responde "o que sustenta este alerta?" citando o artefato exato.

### Fase 3 (Semanas 3–6) — Interatividade e ingesta

**T2 — Grafo multi-hop (L)**
- Sobre `src/object_layer.py` (links já existem: `threatens`, `sameAsset`, `samePeak`, `validatedBy`, `weather`, `fusedAs`): navegação 2–3 hops temporais no `InvestigationCanvas`.
- Busca por qualquer entidade (NORAD, evento, documento, operador) com visualização de vizinhança.
- Exit: expand-neighbors funciona; resultados materializados em `investigation_latest.json`.

**T6 — Sandbox what-if (S–M)**
- Sobre `src/utils.py` (`generate_mock_tle_history`, `generate_shadowing_pair`) e `EventReplayPanel`: injetar manobra sintética num suspeito e verificar se a detecção (IF + CUSUM/EWMA) dispara.
- Exit: CLI/UI demonstra detecção de manobra injetada → serve de validação contínua de sensibilidade.

**T7 — Watchlist dinâmica (M)**
- Sobre `download_spacetrack.py` + `data/catalog/watchlist.json`: UI para adicionar/remover NORAD, reclassificar role (asset/suspect/baseline) e agendar ingesta (`install_daily_cron.sh`).
- Exit: mudança de catálogo persiste, re-treina baseline e reflete no board sem edição manual de JSON.

### Fase 4 (Semanas 6–8) — Operação e acabamento

**T8 — Code-splitting (S)**
- Vite reporta chunk de ~985 kB. Usar `React.lazy`/`import()` para o globe e painéis pesados; `manualChunks` para `three`/`satellite.js`/`recharts`.
- Exit: sem chunk > 500 kB; TTFB melhorado.

**T9 — Operação & deploy (M)**
- `docker-compose.yml` (backend pipeline + frontend build), volumes para `data/` e `models/`, healthcheck, e documentação de backup/restore.
- Exit: `docker compose up` sobe o board + pipeline reproduzível.

## Ordem de dependências (resumo)

1. **T1** primeiro (destrava T2 e T8).
2. **T3 e T4** são independentes e podem rodar em paralelo com T1 (backend puro).
3. **T5, T6, T7** independem de T1; só precisam dos quick-wins já feitos.
4. **T9** por último (empacota tudo).

## Definition of Done global

- `python -m pytest -q` verde; `python scripts/smoke_test.py` verde.
- `cd src/frontend && npm run build` verde (sem chunk warning).
- Novos artefatos respeitam os invariantes de doutrina (scores imutáveis, past-only, baseline+asset = normalidade).
