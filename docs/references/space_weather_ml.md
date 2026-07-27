# Space Weather Integration in Athena-SDA ML Pipeline

## Rationale

Atmospheric drag in Low Earth Orbit (LEO) increases sharply during elevated **F10.7 solar flux** and **Ap/Kp geomagnetic storms**. Without incorporating space weather metrics into feature extraction, orbital decay ($\Delta \text{SMA}$, Shannon entropy, CUSUM) can be misidentified as propulsive maneuvers. Athena-SDA injects space weather metrics at exact epoch timestamps (or `asof` reference dates during walk-forward validation) to decouple natural drag from intentional maneuvers.

## Feature Vector (`FEATURE_COLUMNS`)

| Feature | Description |
|---------|-------------|
| `f10_7` | Observed 10.7 cm solar radio flux (s.f.u.) via GFZ Potsdam |
| `f10_7_adj` | Adjusted F10.7 solar flux |
| `ap_index` | Daily geomagnetic amplitude index (Ap) |
| `kp_mean` | Daily mean of 8 Kp indices |
| `sunspot_number` | Daily sunspot count (SN) |
| `f10_7_delta_7d` | 7-day F10.7 delta variation |
| `f10_7_mean_7d` | 7-day rolling mean F10.7 |
| `ap_mean_7d` / `ap_max_7d` | 7-day rolling mean / peak Ap index |
| `ap_delta_7d` | Daily Ap − 7-day mean Ap |
| `geomagnetic_storm` | Binary flag (1 if `ap_max_7d ≥ 30`) |
| `space_weather_available` | Binary flag (1 if local store active) |

## Data Provenance

- **GFZ Potsdam (Primary):** `Kp_ap_Ap_SN_F107_since_1932.txt` (CC BY 4.0; Matzka et al. 2021)
- **NOAA SWPC (Optional):** Live F10.7 JSON API refresh
- **Local Store:** `data/space_weather/daily.parquet` (+ `daily.csv`)

## Execution Commands

```bash
# Seed or refresh space weather history from 2014 to present
python scripts/run_anomaly_monitor.py seed-space-weather --force --start-year 2014
python scripts/run_anomaly_monitor.py space-weather-status

# Retrain baseline and score after seeding
python scripts/run_anomaly_monitor.py train-baseline
python scripts/run_anomaly_monitor.py score
```

