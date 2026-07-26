# Space weather no ML Athena-SDA

## Por quê

Arrasto em LEO sobe com **F10.7** alto e tempestades **Ap/Kp**. Sem essas variáveis, ΔSMA / Shannon / CUSUM podem parecer “manobra” quando é só atmosfera. O modelo usa o clima no **timestamp da época** (ou `reference_time` no walk-forward) para separar drag natural de manobra.

## Índices (FEATURE_COLUMNS)

| Feature | Significado |
|---------|-------------|
| `f10_7` | Fluxo solar 10.7 cm (s.f.u.), observado (GFZ F10.7obs) |
| `f10_7_adj` | F10.7 ajustado |
| `ap_index` | Amplitude geomagnética diária (Ap) |
| `kp_mean` | Média dos 8 Kp do dia |
| `sunspot_number` | Número de manchas (SN) |
| `f10_7_delta_7d` | Variação F10.7 em 7 dias |
| `f10_7_mean_7d` | Média F10.7 7 dias |
| `ap_mean_7d` / `ap_max_7d` | Ap média / pico 7 dias |
| `ap_delta_7d` | Ap do dia − média 7d |
| `geomagnetic_storm` | 1 se `ap_max_7d ≥ 30` |
| `space_weather_available` | 1 se store local OK |

## Fonte

- **GFZ Potsdam** (primária): `Kp_ap_Ap_SN_F107_since_1932.txt` (CC BY 4.0; Matzka et al. 2021)
- **NOAA SWPC** (opcional): JSON F10.7 recente para refresh
- Store: `data/space_weather/daily.parquet` (+ `daily.csv`)

## Comandos

```bash
# Seed / refresh (default: desde 2014; --force rebaixa)
python3 scripts/run_anomaly_monitor.py seed-space-weather
python3 scripts/run_anomaly_monitor.py seed-space-weather --force --start-year 2014
python3 scripts/run_anomaly_monitor.py space-weather-status

# Retreinar após seed (novas features no vetor)
python3 -c "from src.models import train_and_save_models; train_and_save_models()"
python3 scripts/run_anomaly_monitor.py train-baseline
python3 scripts/run_anomaly_monitor.py score
```

## Integração

- `src/space_weather.py` — download, store, lookup, rolling, feature vector
- `extract_satellite_features` injeta SW no vetor ML
- Isolation Forest inclui SW (clima “normal” do baseline); XGB também
- Labels fracas: sob tempestade / F10.7 alto, ΔSMA leve tende a **não** virar HOSTIL/ANÔMALO (drag vs manobra)
- Bob: `tool_get_space_weather()` lê o store live (não é stub)
- Walk-forward / alerts: snapshot com `f10_7`, `ap_index`, `geomagnetic_storm`, …

## Defaults quietos (store vazio)

F10.7=120, Ap=8, Kp=2, SN=50 — e `space_weather_available=0`.
