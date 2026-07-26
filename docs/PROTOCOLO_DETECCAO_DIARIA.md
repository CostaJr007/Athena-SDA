# Protocolo de detecção diária (padronizado)

## Intenção

> Tenho a **série** de cada satélite. Chega o dado de **ontem/hoje**.  
> Comparo com a série. Se algo **muda com relevância** → detecção.

Isso é o desenho do monitor — não “treinar no dia que quero prever”.

## Ciclo (D = hoje UTC)

```
série histórica ──► baseline IF (= normal do objeto + clima)
TLE novo (D0)   ──► última janela de features
comparar        ──► anomaly_score vs baseline
relevância      ──► alerta se outlier da série OU salto Δ vs ontem
```

| Passo | Comando | O que faz |
|-------|---------|-----------|
| 1 | `ingest-daily` | Anexa TLE frescos à **direita** da série |
| 2 | `train-baseline --holdout-days 1` | Treina só com janelas que terminam **antes de D−1** (ontem e antes = normal) |
| 3 | `score` | Pontua a **última** janela (inclui o dado novo) |
| 4 | relatório | `data/alerts/anomalies_YYYY-MM-DD.json` |

Tudo de uma vez:

```bash
python scripts/run_anomaly_monitor.py run-daily
# padrão: sempre retreina baseline no passado, depois score
# --skip-retrain  se quiser só pontuar sem atualizar baseline
```

## Relevância (quando vira alerta)

1. **Outlier da série** — `anomaly_score ≥ threshold` (padrão 0.55): o ponto de hoje não parece o “normal” aprendido no passado  
2. **Mudança dia-a-dia** — `score_delta_1d ≥ 0.08` e nível já elevado: ontem vs hoje mudou de forma relevante  
3. **DQ** — se TLE ruim/stale → `UNRELIABLE_DATA` (não conta como HOSTIL)

Camadas extras (não substituem a série):

- Space weather (F10.7/Ap) no vetor → menos falso positivo de arrasto  
- Pares suspect×asset → atenção operacional se geometria feia  

## Amostragem da série no treino

- `hybrid` (padrão): metade da **série longa** + metade **recente**  
- `recent`: só ponta atual  
- `full`: janelas espaçadas em todo o histórico  

```bash
python scripts/run_anomaly_monitor.py train-baseline --sample-mode hybrid --holdout-days 1
```

## O que NÃO fazer

- Treinar o baseline **incluindo o dia que se quer detectar** (vazamento)  
- Usar só labels heurísticas como “verdade” de ameaça (o canal de detecção de mudança é o IF na série)  
- Alertar sem checar `data_quality.reliable`  

## Walk-forward

É o mesmo princípio no tempo histórico (eventos Luch etc.): em cada data `asof`, treina no passado e pontua o ponto — prova de “viu antes do report”. Ver `scripts/run_walkforward.py`.
