"""Remote TLE extraction via DuckDB + Hugging Face parquet (legacy bootstrap).

Prefer: python scripts/run_anomaly_monitor.py seed-history --hf
"""
import duckdb
import os
import pandas as pd

print("Connecting to public Space-Track TLE history via DuckDB...")

# In-memory DuckDB
con = duckdb.connect()

# Install and load httpfs for remote parquet
con.execute("INSTALL httpfs;")
con.execute("LOAD httpfs;")

# Base URL for juliensimon/space-track-tle-history parquets.
# Folder layout is parquet/ with many files; DuckDB can read with wildcards.
# Hugging Face datasets also supports hf:// URLs in recent versions.
parquet_url = "hf://datasets/juliensimon/space-track-tle-history/**/*.parquet"

query = f"""
SELECT norad_id, epoch, inclination, raan, eccentricity, arg_perigee,
       mean_anomaly, mean_motion, bstar, intl_designator, altitude_km
FROM '{parquet_url}'
WHERE year(epoch) >= 2024
  AND norad_id IN (44231, 43013, 25994, 41905, 43941, 43603, 39166, 25544)
ORDER BY epoch
"""

print("Running remote extraction. DuckDB is filtering ~238M cloud records...")
try:
    df = con.execute(query).df()

    if len(df) > 0:
        DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "data"))
        os.makedirs(DATA_DIR, exist_ok=True)
        csv_path = os.path.join(DATA_DIR, "real_tle_history_2024_2026.csv")
        df.to_csv(csv_path, index=False)
        print(f"Success! {len(df)} real records saved to {csv_path}")
    else:
        print("No records found for these filters (check hf:// permission or timeout).")
except Exception as e:
    print(f"DuckDB query error: {e}")
    print("Trying CelesTrak REST fallback (active GP, last ~30 days) for live real data:")

    import requests

    url = "https://celestrak.org/NORAD/elements/gp.php?GROUP=active&FORMAT=json"
    print("Downloading current global active catalog (CelesTrak)...")
    r = requests.get(url)
    if r.status_code == 200:
        data = r.json()
        df_celes = pd.DataFrame(data)

        target_ids = [44231, 43013, 25994, 41905, 43941, 43603, 39166, 25544]
        df_filtered = df_celes[df_celes["NORAD_CAT_ID"].isin(target_ids)]

        DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "data"))
        os.makedirs(DATA_DIR, exist_ok=True)
        csv_path = os.path.join(DATA_DIR, "real_celestrak_active.csv")
        df_filtered.to_csv(csv_path, index=False)
        print(f"CelesTrak success! {len(df_filtered)} satellites saved to {csv_path}")
    else:
        print("CelesTrak fallback also failed.")
