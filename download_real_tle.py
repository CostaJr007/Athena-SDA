"""Stream watchlist TLE history from Hugging Face (legacy bootstrap).

Prefer: python scripts/run_anomaly_monitor.py seed-history --hf --start-year 2014
"""
import os
import sys
from pathlib import Path

import pandas as pd
from datasets import load_dataset

# Project root on path (script may be run from any cwd)
_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

print("Starting download of public satellite TLE history (Space-Track mirror)...")
print("Source: Hugging Face Datasets (juliensimon/space-track-tle-history)")

# Prefer data/catalog/watchlist.json (military-first). Fallback list is validated NORADs.
try:
    from src.catalog import name_map

    TARGET_SATS = name_map()
    if not TARGET_SATS:
        raise RuntimeError("empty catalog")
except Exception:
    TARGET_SATS = {
        25544: "ISS (ZARYA)",
        39166: "NAVSTAR 68 (USA 242)",
        41038: "YAOGAN-29",
        40258: "LUCH (OLYMP-K 1)",
        39208: "SHIYAN-7 (SY-7)",
        25994: "TERRA",
        43013: "NOAA 20 (JPSS-1)",
        44714: "STARLINK-1008",
        48274: "CSS (TIANHE)",
        43603: "BEIDOU-3 M11",
    }

norad_ids = set(TARGET_SATS.keys())

# Stream remotely so we do not download the full multi-GB archive.
ds = load_dataset("juliensimon/space-track-tle-history", split="train", streaming=True)

# Time window (last ~2 years)
START_YEAR = 2024

collected_rows = []
total_processed = 0

print(f"Filtering real history (>= {START_YEAR}) for strategic satellites:")
for k, v in TARGET_SATS.items():
    print(f" - #{k}: {v}")

print("Querying cloud data... this may take several minutes depending on connection.")

for row in ds:
    total_processed += 1

    if total_processed % 500000 == 0:
        print(f"Processed {total_processed} orbital measurements...")

    if row["norad_id"] in norad_ids:
        if row["epoch"].year >= START_YEAR:
            collected_rows.append(row)

    # Stop once we have enough samples for a bootstrap training set.
    if len(collected_rows) >= 30000:
        print("Sufficient data mass reached for training (30,000 historical TLEs).")
        break

if len(collected_rows) > 0:
    df = pd.DataFrame(collected_rows)

    DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "data"))
    os.makedirs(DATA_DIR, exist_ok=True)

    csv_path = os.path.join(DATA_DIR, "real_tle_history_2024_2026.csv")
    df.to_csv(csv_path, index=False)
    print("Download completed successfully!")
    print(f"Real data saved to: {csv_path} ({len(df)} records)")
    print(df.head())
else:
    print("No data found for the selected filters.")
