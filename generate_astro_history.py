"""Synthetic reverse-propagation TLE history for ML bootstrap / demos.

Uses live CelesTrak seeds and linearised drag + optional ISS maneuver.
Prefer real HF history via: scripts/run_anomaly_monitor.py seed-history --hf
"""
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os

print("Starting reverse astrodynamics propagation module (SGP4-Sim)...")

# Targets: Yaogan-31, Cosmos, ISS, USA 245, etc.
TARGETS = [43013, 44797, 44798, 39232, 25544, 43941, 43603, 39166]

print("Downloading real orbital seeds from CelesTrak...")
all_seed_lines = []
headers = ""
for i, target in enumerate(TARGETS):
    celestrak_url = f"https://celestrak.org/NORAD/elements/gp.php?CATNR={target}&FORMAT=csv"
    resp = requests.get(celestrak_url)
    if resp.status_code == 200 and len(resp.text.strip()) > 0:
        lines = resp.text.strip().split("\n")
        if i == 0:
            headers = lines[0]
            all_seed_lines.append(headers)
        if len(lines) > 1:
            all_seed_lines.append(lines[1])

# Persist temporary seed CSV
seed_path = "data/celestrak_seeds.csv"
os.makedirs("data", exist_ok=True)
with open(seed_path, "w") as f:
    f.write("\n".join(all_seed_lines))

df_seeds = pd.read_csv(seed_path)
print(f"Got {len(df_seeds)} target satellites. Starting 30-day reverse propagation.")

# 2. Reverse propagation
history_records = []
now = datetime.utcnow()

# 4 TLEs per day for the last 30 days (120 TLEs per satellite)
days_history = 30
updates_per_day = 4
total_steps = days_history * updates_per_day
time_step_hours = 24 / updates_per_day

# Sensor noise variance to simulate radar-like measurement noise
noise_std = {
    "INCLINATION": 0.0005,
    "ECCENTRICITY": 0.00001,
    "MEAN_MOTION": 0.0001,
    "BSTAR": 0.00005,
}

for idx, row in df_seeds.iterrows():
    norad_id = row["NORAD_CAT_ID"]
    name = row["OBJECT_NAME"]

    incl = float(row.get("INCLINATION", 0))
    ecc = float(row.get("ECCENTRICITY", 0))
    mm = float(row.get("MEAN_MOTION", 0))
    bstar = float(row.get("BSTAR", 0))

    # Force a mid-month "maneuver" on ISS to exercise the ML path
    is_maneuvering = norad_id == 25544

    for step in range(total_steps):
        hours_back = step * time_step_hours
        epoch_time = now - timedelta(hours=hours_back)

        # Linearised basic astrodynamics:
        # Positive BSTAR (drag) → mean motion increases over time.
        # In the PAST (retrograde), mean motion was therefore LOWER.
        mm_drift = bstar * 10 * hours_back / 24.0

        past_mm = mm - mm_drift
        past_ecc = ecc + (bstar * 0.1 * hours_back / 24.0)  # eccentricity slightly higher in past
        past_incl = incl

        # Simulated maneuver (ISS, ~15 days ago)
        label = 0
        if is_maneuvering and 14 < (hours_back / 24.0) < 16:
            past_mm -= 0.05  # abrupt orbital change (delta-v)
            label = 1  # Hostile / Maneuver

        # Gaussian sensor noise
        past_mm += np.random.normal(0, noise_std["MEAN_MOTION"])
        past_ecc += np.random.normal(0, noise_std["ECCENTRICITY"])
        past_incl += np.random.normal(0, noise_std["INCLINATION"])

        history_records.append({
            "NORAD_CAT_ID": norad_id,
            "OBJECT_NAME": name,
            "EPOCH": epoch_time.strftime("%Y-%m-%dT%H:%M:%S.%f"),
            "INCLINATION": past_incl,
            "ECCENTRICITY": max(0, past_ecc),  # ecc cannot be negative
            "MEAN_MOTION": past_mm,
            "BSTAR": bstar + np.random.normal(0, noise_std["BSTAR"]),
            "MANEUVER_LABEL": label,
        })

df_history = pd.DataFrame(history_records)
df_history["EPOCH"] = pd.to_datetime(df_history["EPOCH"])
df_history = df_history.sort_values(by=["NORAD_CAT_ID", "EPOCH"]).reset_index(drop=True)

output_path = "data/real_tle_history_2024_2026.csv"
df_history.to_csv(output_path, index=False)

print(
    f"Success! {len(df_history)} historical records "
    f"(physics-based with simulated sensor noise) written to {output_path}."
)
print("Data is ready for the XGBoost bootstrap path.")
