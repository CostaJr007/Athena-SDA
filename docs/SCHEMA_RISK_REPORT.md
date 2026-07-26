# Schema `athena.risk_report.v1`

Contrato entre o monitor Python e o frontend tático.

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `schema` | string | Sempre `athena.risk_report.v1` |
| `generated_at` | ISO datetime | Quando o score foi gerado |
| `day` | `YYYY-MM-DD` | Dia operacional do snapshot |
| `summary` | object | Contagens agregadas |
| `summary.n_scored` | int | Objetos no board |
| `summary.n_anomalies` | int | `is_anomaly` |
| `summary.n_pairs` | int | Pares suspect×asset avaliados |
| `summary.n_pair_elevated` | int | Pares acima do threshold de atenção |
| `summary.threshold` | float | Threshold de attention usado |
| `board[]` | array | Lista ordenada (atenção desc. no gerador) |
| `board[].norad_id` | int | NORAD |
| `board[].object_name` | string | Nome catálogo |
| `board[].role` | `asset` \| `suspect` \| `baseline` | Watchlist |
| `board[].anomaly_score` | float | Isolation Forest (0–1 clip) |
| `board[].attention_score` | float | Fusão 0.45·anom + 0.55·pair |
| `board[].status` | string | `NOMINAL` / `ANOMALY` / `PAIR_ELEVATED` / `UNRELIABLE_DATA` |
| `board[].pair` | object\|null | Melhor par suspect→asset (se houver) |
| `board[].features_snapshot` | object | Hurst, Shannon, SW, dist, coint… |
| `board[].data_quality` | object | score, reliable, issues, tle_age_hours |
| `top_pairs[]` | array | Top N pares para o board UI |
| `model` | string | Path do IF monitor (auditoria) |
| `train_meta` | object | Meta do último treino baseline |

## UI threat map (só apresentação)

| Condição | Badge UI |
|----------|----------|
| `PAIR_ELEVATED` + pair CRITICAL / att≥0.65 / pair_risk≥0.9 | **HOSTILE** |
| `PAIR_ELEVATED` ou pair_risk≥0.55 | **SUSPECT** |
| `is_anomaly` / `ANOMALY` / `UNRELIABLE_DATA` | **ANOMALY** |
| resto | **NOMINAL** (+ cor por role no globo) |

Implementação: `src/frontend/src/lib/risk-report.ts`.

## Sync para o Vite

```bash
python scripts/run_anomaly_monitor.py run-daily   # opcional refresh
bash scripts/sync_frontend_data.sh
# copia data/alerts/*_latest.json → src/frontend/public/data/
```
