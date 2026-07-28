# ========================================================================
# ML IMPROVEMENT INSTRUCTIONS — ATHENA-SDA (REAL / PRODUCTION VERSION)
# Self-contained document for any AI to follow step by step.
# Project: Athena-SDA
# Date: 2026-07-25
# ========================================================================
#
# CONTEXT:
# The real Athena-SDA version is highly sophisticated, reaching 96.3%
# accuracy with 26 mathematical and topological features. The ML engine is
# correct, coherent, and has robust out-of-time (walk-forward) validation.
#
# CURRENT PROBLEM (POLISH):
# Only 5 "edge cases" remain that do not break the pipeline, but cause
# distortions in limit situations:
# 1. Fuzzy crashes when distance > 500km
# 2. Kolmogorov inflated for short orbits
# 3. Mandelbrot estimator with division-by-zero risk
# 4. Cointegration comparing desynchronized time series
# 5. TLE age frozen in the Parquet database
#
# PRIORITY: Execute in the listed order. Each step is independent.
#
# ========================================================================

# ========================================================================
# STEP 1: FIX SILENT FUZZY ENGINE CRASH
# ========================================================================
# FILE: src/fuzzy.py
# FUNCTION: fuzzy_inference_threat()
# LINES: ~96
#
# PROBLEM: The universe of variable `dist_military` goes up to 500 km. When
# the computed distance is 501+ km, skfuzzy raises an exception and the
# fallback sets threat = 0.0. Satellites far from assets are marked NORMAL,
# even if orbital features (entropy, Hurst) indicate extreme anomalies.
#
# BEFORE (Line 96):
#     sim.input['dist_military'] = min_dist_mil
#
# AFTER:
#     # Clamp to the maximum universe support so inference does not explode
#     sim.input['dist_military'] = min(float(min_dist_mil), 500.0)
#
# Test: A satellite at 800km with high anomaly must no longer return threat 0.0.


# ========================================================================
# STEP 2: FIX KOLMOGOROV PROXY INFLATION FOR SHORT SERIES
# ========================================================================
# FILE: src/engine.py
# FUNCTION: calculate_kolmogorov_proxy(sma_series)
# LINES: ~42-45
#
# PROBLEM: The zlib compression header size on very short strings
# (e.g. "SSSSS") is larger than the string itself. The compression ratio
# exceeds 1.0, resulting in Kolmogorov = 1.0 (maximum chaotic complexity)
# for perfectly constant orbits.
#
# BEFORE (Lines 42-45):
#     if len(s) == 0:
#         return 0.0
#     compressed = zlib.compress(s)
#     return float(np.clip(len(compressed) / len(s), 0.0, 1.0))
#
# AFTER:
#     if len(s) < 10:
#         return 0.0  # Too short for zlib header entropy to dominate
#     compressed = zlib.compress(s)
#
#     # Subtract header bytes (typically 11 bytes for short strings)
#     comp_len = max(len(compressed) - 11, 1)
#     return float(np.clip(comp_len / len(s), 0.0, 1.0))


# ========================================================================
# STEP 3: GUARD HILL ESTIMATOR (MANDELBROT) AGAINST DIVISION BY ZERO
# ========================================================================
# FILE: src/engine.py
# FUNCTION: calculate_mandelbrot_tail_anomaly(series)
# LINES: ~247-251
#
# PROBLEM: If `tail_data` contains elements where `tail_data / threshold` is
# 1.0000000000001, the logarithm is ~0. The sum of logs can reach exact
# zero, generating ZeroDivisionError when computing `alpha`.
#
# BEFORE (Lines 249-250):
#     # Hill estimator for the tail alpha
#     alpha = len(tail_data) / np.sum(np.log(tail_data / threshold))
#
# AFTER:
#     # Hill estimator for the tail alpha with epsilon guard
#     log_sum = np.sum(np.log(tail_data / threshold))
#     if log_sum < 1e-9:
#         return 0.0
#     alpha = len(tail_data) / log_sum


# ========================================================================
# STEP 4: COMPUTE TLE AGE AT INFERENCE TIME (NOT AT INGEST)
# ========================================================================
# FILE: src/tle_store.py
# FUNCTION: normalize_epochs_df(df)
# LINES: ~154-156
# AND FILE: src/models.py
# FUNCTION: extract_satellite_features()
#
# PROBLEM: The parquet store freezes feature `tle_age_hours`. A TLE
# ingested on Monday always has age=0, even if today is Friday, breaking
# the temporal uncertainty logic of Fuzzy/XGBoost.
#
# PART A - src/tle_store.py (Lines 154-156)
# BEFORE:
#     now = pd.Timestamp.now(tz="UTC")
#     out["tle_age_hours"] = (now - out["timestamp"]).dt.total_seconds() / 3600.0
#     out["tle_age_hours"] = out["tle_age_hours"].clip(lower=0).fillna(24.0)
#
# AFTER:
#     # REMOVE THE 3 LINES ABOVE.
#     # Instead, set only a default placeholder value
#     # (Real age will be computed at feature extraction time)
#     out["tle_age_hours"] = 0.0
#
# PART B - src/models.py (Lines 99-105 inside extract_satellite_features)
# BEFORE:
#     tle_age = float(last_row.get("tle_age_hours", 12.0))
#
# AFTER:
#     # Compute true age at the exact moment the feature is extracted
#     if "timestamp" in last_row and pd.notnull(last_row["timestamp"]):
#         now = pd.Timestamp.now(tz="UTC")
#         tle_age = float((now - last_row["timestamp"]).total_seconds() / 3600.0)
#         tle_age = max(0.0, tle_age)
#     else:
#         tle_age = float(last_row.get("tle_age_hours", 12.0))


# ========================================================================
# STEP 5: TEMPORALLY ALIGN SERIES IN ENGLE-GRANGER COINTEGRATION
# ========================================================================
# FILE: src/pair_score.py
# FUNCTION: _align_series(a, b, col, max_points)
# LINES: ~61-68
#
# PROBLEM: Taking purely the last 120 rows of two satellite DataFrames does
# not guarantee they overlap in time. The cointegration test can compare
# last week's orbits with today's orbits.
#
# BEFORE:
#     sa = a.sort_values("timestamp")[col].astype(float).values
#     sb = b.sort_values("timestamp")[col].astype(float).values
#     n = min(len(sa), len(sb), max_points)
#     if n < 20:
#         return sa[-n:] if n else sa, sb[-n:] if n else sb
#     return sa[-n:], sb[-n:]
#
# AFTER:
#     # merge_asof ensures timestamps are synchronized
#     a_sorted = a.sort_values("timestamp").tail(max_points * 2)
#     b_sorted = b.sort_values("timestamp").tail(max_points * 2)
#
#     if len(a_sorted) == 0 or len(b_sorted) == 0:
#         return np.array([]), np.array([])
#
#     # Align Suspect satellite with Asset using nearest timestamp (max tolerance 12h)
#     merged = pd.merge_asof(
#         a_sorted, b_sorted, on="timestamp",
#         direction="nearest", tolerance=pd.Timedelta("12h"),
#         suffixes=('_a', '_b')
#     ).dropna(subset=[col + "_a", col + "_b"])
#
#     sa = merged[col + "_a"].astype(float).values
#     sb = merged[col + "_b"].astype(float).values
#
#     n = min(len(sa), len(sb), max_points)
#     if n < 20:
#         return sa[-n:] if n else sa, sb[-n:] if n else sb
#     return sa[-n:], sb[-n:]


# ========================================================================
# AFTER APPLYING THE CHANGES
# ========================================================================
# 1. Run the smoke test to ensure modules did not break:
#    python scripts/smoke_test.py
#
# 2. Because orbital features changed subtly (Kolmogorov, TLE Age),
#    retrain the continuous baseline and XGBoost:
#    python scripts/smoke_test.py --train
# ========================================================================
