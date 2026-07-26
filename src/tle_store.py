"""
TLE history store for Athena-SDA anomaly monitoring.

Canonical epoch table (one row = one TLE / orbital element set):
  norad_id, object_name, timestamp, semi_major_axis_km, eccentricity,
  inclination_deg, raan_deg, mean_motion_rev_per_day, bstar,
  tle_age_hours, source

Flow:
  historical seed  →  data/history/epochs.parquet (or csv)
  daily inject     →  append new epochs
  train            →  sliding windows ending BEFORE today
  score            →  windows ending at latest epoch
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd
import requests

from src.config import DATA_DIR, MU_EARTH_KM3_S2
from src.orbital import sma_from_mean_motion

HISTORY_DIR = DATA_DIR / "history"
DAILY_DIR = DATA_DIR / "daily"
ALERTS_DIR = DATA_DIR / "alerts"
CATALOG_DIR = DATA_DIR / "catalog"
EPOCHS_PARQUET = HISTORY_DIR / "epochs.parquet"
EPOCHS_CSV = HISTORY_DIR / "epochs.csv"

CANONICAL_COLS = [
    "norad_id",
    "object_name",
    "timestamp",
    "semi_major_axis_km",
    "eccentricity",
    "inclination_deg",
    "raan_deg",
    "mean_motion_rev_per_day",
    "bstar",
    "tle_age_hours",
    "source",
]


def _load_default_watchlist() -> Dict[int, str]:
    """Military-first map from data/catalog/watchlist.json (fallback hardcoded)."""
    try:
        from src.catalog import name_map

        m = name_map()
        if m:
            return m
    except Exception:
        pass
    return {
        25544: "ISS (ZARYA)",
        39166: "NAVSTAR 68 (USA 242)",
        41038: "YAOGAN-29",
        40258: "LUCH (OLYMP-K 1)",
        25994: "TERRA",
        43013: "NOAA 20 (JPSS-1)",
    }


# Populated from catalog at import; refresh via reload_watchlist()
DEFAULT_WATCHLIST: Dict[int, str] = _load_default_watchlist()


def reload_watchlist() -> Dict[int, str]:
    """Re-read catalog JSON (clears cache) and refresh DEFAULT_WATCHLIST."""
    global DEFAULT_WATCHLIST
    try:
        from src.catalog import clear_watchlist_cache, name_map

        clear_watchlist_cache()
        DEFAULT_WATCHLIST = name_map()
    except Exception:
        DEFAULT_WATCHLIST = _load_default_watchlist()
    return DEFAULT_WATCHLIST


def ensure_dirs() -> None:
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    DAILY_DIR.mkdir(parents=True, exist_ok=True)
    ALERTS_DIR.mkdir(parents=True, exist_ok=True)
    CATALOG_DIR.mkdir(parents=True, exist_ok=True)
    (DATA_DIR / "features").mkdir(parents=True, exist_ok=True)


def _sma(mm: float) -> float:
    try:
        return float(sma_from_mean_motion(float(mm)))
    except Exception:
        n = float(mm) * (2 * np.pi / 86400.0)
        if n <= 0:
            return float("nan")
        return float((MU_EARTH_KM3_S2 / (n ** 2)) ** (1.0 / 3.0))


def normalize_epochs_df(df: pd.DataFrame, source: str = "unknown") -> pd.DataFrame:
    """Map various TLE schemas into the canonical Athena epoch table."""
    if df is None or len(df) == 0:
        return pd.DataFrame(columns=CANONICAL_COLS)

    raw = df.copy()
    # lower-case map for flexible matching
    lower = {c.lower(): c for c in raw.columns}

    def col(*names: str) -> Optional[str]:
        for n in names:
            if n in raw.columns:
                return n
            if n.lower() in lower:
                return lower[n.lower()]
        return None

    id_c = col("norad_id", "NORAD_CAT_ID", "norad", "NORAD", "satid")
    name_c = col("object_name", "OBJECT_NAME", "name", "OBJECT_ID", "satname")
    epoch_c = col("timestamp", "epoch", "EPOCH", "EPOCH_UTC")
    mm_c = col("mean_motion_rev_per_day", "MEAN_MOTION", "mean_motion", "n")
    inc_c = col("inclination_deg", "INCLINATION", "inclination", "incl")
    ecc_c = col("eccentricity", "ECCENTRICITY", "eccen")
    raan_c = col("raan_deg", "RA_OF_ASC_NODE", "raan", "RAAN", "right_ascension")
    bstar_c = col("bstar", "BSTAR", "b_star")
    sma_c = col("semi_major_axis_km", "semi_major_axis", "sma_km")

    if not id_c or not epoch_c or not mm_c:
        raise ValueError(
            f"Cannot normalize TLE frame — need norad/epoch/mean_motion. cols={list(raw.columns)}"
        )

    out = pd.DataFrame()
    out["norad_id"] = pd.to_numeric(raw[id_c], errors="coerce").astype("Int64")
    out["object_name"] = raw[name_c].astype(str) if name_c else "UNKNOWN"
    out["timestamp"] = pd.to_datetime(raw[epoch_c], errors="coerce", utc=True)
    out["mean_motion_rev_per_day"] = pd.to_numeric(raw[mm_c], errors="coerce")
    out["inclination_deg"] = (
        pd.to_numeric(raw[inc_c], errors="coerce") if inc_c else 0.0
    )
    out["eccentricity"] = pd.to_numeric(raw[ecc_c], errors="coerce") if ecc_c else 0.0
    out["raan_deg"] = pd.to_numeric(raw[raan_c], errors="coerce") if raan_c else 0.0
    out["bstar"] = pd.to_numeric(raw[bstar_c], errors="coerce") if bstar_c else 0.0
    if sma_c:
        out["semi_major_axis_km"] = pd.to_numeric(raw[sma_c], errors="coerce")
    else:
        out["semi_major_axis_km"] = out["mean_motion_rev_per_day"].map(_sma)

    out["tle_age_hours"] = 0.0
    out["source"] = source

    out = out.dropna(subset=["norad_id", "timestamp", "mean_motion_rev_per_day"])
    out["norad_id"] = out["norad_id"].astype(int)
    out = out[CANONICAL_COLS]
    out = out.sort_values(["norad_id", "timestamp"]).drop_duplicates(
        subset=["norad_id", "timestamp"], keep="last"
    )
    return out.reset_index(drop=True)


def load_history() -> pd.DataFrame:
    ensure_dirs()
    if EPOCHS_PARQUET.exists():
        try:
            df = pd.read_parquet(EPOCHS_PARQUET)
            return normalize_epochs_df(df, source="history")
        except Exception:
            pass
    if EPOCHS_CSV.exists():
        df = pd.read_csv(EPOCHS_CSV)
        return normalize_epochs_df(df, source="history")
    return pd.DataFrame(columns=CANONICAL_COLS)


def save_history(df: pd.DataFrame) -> Path:
    ensure_dirs()
    df = normalize_epochs_df(df, source=str(df["source"].iloc[0]) if len(df) else "history")
    try:
        df.to_parquet(EPOCHS_PARQUET, index=False)
        path = EPOCHS_PARQUET
    except Exception:
        df.to_csv(EPOCHS_CSV, index=False)
        path = EPOCHS_CSV
    # always keep a csv mirror for easy inspection
    df.to_csv(EPOCHS_CSV, index=False)
    return path


def append_epochs(new_df: pd.DataFrame) -> Tuple[pd.DataFrame, int]:
    """Merge new epochs into history; returns (full_history, n_new_rows)."""
    hist = load_history()
    fresh = normalize_epochs_df(new_df, source=str(new_df.get("source", pd.Series(["ingest"])).iloc[0]) if len(new_df) else "ingest")
    if len(hist) == 0:
        save_history(fresh)
        return fresh, len(fresh)
    before = len(hist)
    merged = pd.concat([hist, fresh], ignore_index=True)
    merged = merged.sort_values(["norad_id", "timestamp"]).drop_duplicates(
        subset=["norad_id", "timestamp"], keep="last"
    )
    save_history(merged)
    return merged, int(len(merged) - before)


def history_as_sat_histories(
    df: Optional[pd.DataFrame] = None,
    norad_ids: Optional[Sequence[int]] = None,
    min_epochs: int = 20,
) -> Dict[int, pd.DataFrame]:
    """
    Group canonical epochs into per-sat DataFrames compatible with
    extract_satellite_features (needs semi_major_axis_km, inclination_deg, ...).
    """
    df = load_history() if df is None else df
    if len(df) == 0:
        return {}
    if norad_ids is not None:
        ids = set(int(x) for x in norad_ids)
        df = df[df["norad_id"].isin(ids)]

    out: Dict[int, pd.DataFrame] = {}
    for sid, g in df.groupby("norad_id"):
        g = g.sort_values("timestamp").copy()
        if len(g) < min_epochs:
            continue
        # feature extractor expects these names
        hist = pd.DataFrame(
            {
                "timestamp": g["timestamp"].values,
                "semi_major_axis_km": g["semi_major_axis_km"].values,
                "eccentricity": g["eccentricity"].values,
                "inclination_deg": g["inclination_deg"].values,
                "raan_deg": g["raan_deg"].values,
                "mean_motion_rev_per_day": g["mean_motion_rev_per_day"].values,
                "tle_age_hours": g["tle_age_hours"].values,
            }
        )
        out[int(sid)] = hist.reset_index(drop=True)
    return out


# ── Ingest sources ──────────────────────────────────────────────────────────

def fetch_celestrak_group(group: str = "active", timeout: int = 120) -> pd.DataFrame:
    """
    Pull latest GP (TLE-equivalent) from CelesTrak public API (CSV).
    Groups: active, visual, stations, starlink, oneweb, gps-ops, ...
    """
    url = f"https://celestrak.org/NORAD/elements/gp.php?GROUP={group}&FORMAT=csv"
    r = requests.get(url, timeout=timeout)
    r.raise_for_status()
    from io import StringIO

    raw = pd.read_csv(StringIO(r.text))
    # CelesTrak CSV uses NORAD_CAT_ID, EPOCH, MEAN_MOTION, INCLINATION, ...
    raw["source"] = f"celestrak:{group}"
    return normalize_epochs_df(raw, source=f"celestrak:{group}")


def fetch_celestrak_catnr(norad_id: int, timeout: int = 30) -> pd.DataFrame:
    """Fetch a single object by NORAD catalog number (reliable; avoids GROUP=active 403)."""
    url = f"https://celestrak.org/NORAD/elements/gp.php?CATNR={int(norad_id)}&FORMAT=csv"
    r = requests.get(url, timeout=timeout)
    r.raise_for_status()
    from io import StringIO

    raw = pd.read_csv(StringIO(r.text))
    return normalize_epochs_df(raw, source=f"celestrak:catnr:{norad_id}")


def fetch_celestrak_by_ids(
    norad_ids: Optional[Iterable[int]] = None,
    timeout: int = 30,
    pause_s: float = 0.15,
) -> pd.DataFrame:
    """
    Pull latest GP for each NORAD via CATNR.
    Preferred path for the military watchlist (precise, no huge group dump).
    """
    import time

    ids = list(int(x) for x in (norad_ids or DEFAULT_WATCHLIST.keys()))
    frames: List[pd.DataFrame] = []
    for i, nid in enumerate(ids):
        try:
            df = fetch_celestrak_catnr(nid, timeout=timeout)
            if len(df):
                # Prefer catalog display name when present
                name = DEFAULT_WATCHLIST.get(nid)
                if name:
                    df = df.copy()
                    df["object_name"] = name
                frames.append(df)
                print(f"  CATNR {nid}: ok ({len(df)} row)")
            else:
                print(f"  CATNR {nid}: empty")
        except Exception as e:
            print(f"  CATNR {nid}: failed ({e})")
        if pause_s and i < len(ids) - 1:
            time.sleep(pause_s)
    if not frames:
        return pd.DataFrame(columns=CANONICAL_COLS)
    all_df = pd.concat(frames, ignore_index=True)
    all_df = all_df.sort_values(["norad_id", "timestamp"]).drop_duplicates(
        subset=["norad_id", "timestamp"], keep="last"
    )
    return all_df.reset_index(drop=True)


def fetch_celestrak_watchlist(
    norad_ids: Optional[Iterable[int]] = None,
    groups: Sequence[str] = ("visual", "stations"),
    prefer_catnr: bool = True,
) -> pd.DataFrame:
    """
    Fetch latest TLEs for the watchlist.

    Default: per-NORAD CATNR (accurate). Optionally also merge group dumps
    (visual/stations — avoid GROUP=active which often returns 403).
    """
    ids = set(int(x) for x in (norad_ids or DEFAULT_WATCHLIST.keys()))
    frames: List[pd.DataFrame] = []

    if prefer_catnr:
        try:
            df_ids = fetch_celestrak_by_ids(ids)
            if len(df_ids):
                frames.append(df_ids)
        except Exception as e:
            print(f"  CelesTrak CATNR path failed: {e}")

    # Fill any missing NORADs from group dumps
    have = set(frames[0]["norad_id"].unique()) if frames else set()
    missing = ids - have
    if missing or not prefer_catnr:
        for g in groups:
            try:
                df = fetch_celestrak_group(g)
                frames.append(df)
                print(f"  CelesTrak group={g}: {len(df)} rows")
            except Exception as e:
                print(f"  CelesTrak group={g} failed: {e}")

    if not frames:
        return pd.DataFrame(columns=CANONICAL_COLS)
    all_df = pd.concat(frames, ignore_index=True)
    all_df = all_df[all_df["norad_id"].isin(ids)]
    all_df = all_df.sort_values(["norad_id", "timestamp"]).drop_duplicates(
        subset=["norad_id", "timestamp"], keep="last"
    )
    # Overlay catalog names
    for nid, name in DEFAULT_WATCHLIST.items():
        mask = all_df["norad_id"] == nid
        if mask.any():
            all_df.loc[mask, "object_name"] = name
    return all_df.reset_index(drop=True)


def fetch_hf_constellation_latest(max_rows: int = 50_000) -> pd.DataFrame:
    """Daily constellation TLEs from Hugging Face (juliensimon/space-datasets)."""
    try:
        from datasets import load_dataset
    except ImportError as e:
        raise ImportError("pip install datasets  # required for HF ingest") from e

    ds = load_dataset("juliensimon/constellation-tle-latest", split="train")
    # Convert to pandas (may be multi-config)
    try:
        df = ds.to_pandas()
    except Exception:
        df = pd.DataFrame(ds)
    if len(df) > max_rows:
        df = df.sample(max_rows, random_state=42)
    return normalize_epochs_df(df, source="hf:constellation-tle-latest")


def seed_from_existing_csv(path: Optional[Path] = None) -> pd.DataFrame:
    """Import project CSV (real_tle_history_*) into the history store."""
    path = path or (DATA_DIR / "real_tle_history_2024_2026.csv")
    if not path.exists():
        return pd.DataFrame(columns=CANONICAL_COLS)
    raw = pd.read_csv(path)
    norm = normalize_epochs_df(raw, source=f"seed:{path.name}")
    append_epochs(norm)
    return norm


SEED_PROGRESS_PATH = HISTORY_DIR / "seed_progress.json"


def _write_seed_progress(payload: Dict) -> None:
    ensure_dirs()
    payload = dict(payload)
    payload["updated_at"] = datetime.now(timezone.utc).isoformat()
    SEED_PROGRESS_PATH.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


def _year_already_seeded(year: int, min_rows: int = 500) -> bool:
    """Skip re-download if history already has enough rows from this HF year file."""
    hist = load_history()
    if len(hist) == 0:
        return False
    src = hist["source"].astype(str)
    n = int((src == f"hf:tle_{year}").sum())
    if n >= min_rows:
        return True
    # Fallback: many epochs in that calendar year
    ts = pd.to_datetime(hist["timestamp"], utc=True, errors="coerce")
    n2 = int((ts.dt.year == int(year)).sum())
    return n2 >= min_rows * 2


def _load_hf_year_filtered(year: int, ids: set) -> pd.DataFrame:
    """
    Memory-safe load: download year parquet via huggingface_hub, scan with
    PyArrow batches, keep only watchlist NORADs. Avoids datasets.to_pandas()
    on ~20M rows (which OOM / freezes VS Code).
    """
    import pyarrow as pa
    import pyarrow.compute as pc
    import pyarrow.parquet as pq

    try:
        from huggingface_hub import hf_hub_download
    except ImportError as e:
        raise ImportError("pip install huggingface_hub pyarrow") from e

    path = hf_hub_download(
        repo_id="juliensimon/space-track-tle-history",
        filename=f"data/tle_{year}.parquet",
        repo_type="dataset",
    )
    print(f"  parquet: {path}")
    pf = pq.ParquetFile(path)
    schema_names = set(pf.schema_arrow.names)
    id_col = None
    for c in ("norad_id", "NORAD_CAT_ID", "norad"):
        if c in schema_names:
            id_col = c
            break
    if id_col is None:
        raise ValueError(f"no norad column in schema: {pf.schema_arrow.names}")

    id_list = pa.array(list(ids), type=pa.int64())
    chunks: List[pd.DataFrame] = []
    kept = 0
    # Batch scan — never hold full year in RAM as pandas
    for i, batch in enumerate(pf.iter_batches(batch_size=200_000)):
        tbl = pa.Table.from_batches([batch])
        col = tbl.column(id_col)
        # cast to int64 when possible
        try:
            col_i = pc.cast(col, pa.int64(), safe=False)
        except Exception:
            col_i = pc.cast(pc.cast(col, pa.string()), pa.int64(), safe=False)
        mask = pc.is_in(col_i, value_set=id_list)
        filtered = tbl.filter(mask)
        if filtered.num_rows == 0:
            continue
        # replace id col with cast ints for normalize
        names = filtered.column_names
        arrays = []
        for name in names:
            if name == id_col:
                arrays.append(pc.cast(filtered.column(name), pa.int64(), safe=False))
            else:
                arrays.append(filtered.column(name))
        filtered = pa.Table.from_arrays(arrays, names=names)
        pdf = filtered.to_pandas()
        chunks.append(pdf)
        kept += len(pdf)
        if (i + 1) % 25 == 0:
            print(f"  batch {i+1}: kept so far {kept:,}")

    if not chunks:
        return pd.DataFrame()
    return pd.concat(chunks, ignore_index=True)


def seed_from_hf_year_parquets(
    norad_ids: Optional[Sequence[int]] = None,
    start_year: int = 2024,
    end_year: Optional[int] = None,
    skip_existing_years: bool = True,
) -> pd.DataFrame:
    """
    Preferred seed path: year parquets via PyArrow batch filter + watchlist.

    Network: ~0.5–1 GB/year (HF cache). Disk after filter: tens of MB.
    Safe for low-RAM — does NOT load full year into pandas at once.
    """
    ids = set(int(x) for x in (norad_ids or DEFAULT_WATCHLIST.keys()))
    end_year = int(end_year or datetime.now(timezone.utc).year)
    years = list(range(int(start_year), end_year + 1))
    print(f"HF year-parquet seed (pyarrow): years={years}  watchlist={len(ids)} NORADs")

    frames: List[pd.DataFrame] = []
    by_norad: Dict[int, int] = {i: 0 for i in ids}
    # seed counts from existing history
    try:
        hist0 = load_history()
        if len(hist0):
            for nid, c in hist0.groupby("norad_id").size().items():
                if int(nid) in by_norad:
                    by_norad[int(nid)] = int(c)
    except Exception:
        pass

    progress: Dict = {
        "phase": "hf_year_parquet_pyarrow",
        "years": years,
        "watchlist_n": len(ids),
        "years_done": [],
        "kept_total": int(sum(by_norad.values())),
        "by_norad": by_norad,
        "status": "running",
    }
    _write_seed_progress(progress)

    for year in years:
        print(f"\n=== year {year} ===")
        progress["current_year"] = year
        if skip_existing_years and _year_already_seeded(year):
            print(f"  skip: already seeded enough for {year}")
            progress["years_done"].append({"year": year, "kept": "skipped_existing"})
            progress["status"] = f"skipped_{year}"
            _write_seed_progress(progress)
            continue

        progress["status"] = f"loading_{year}"
        _write_seed_progress(progress)
        try:
            hit = _load_hf_year_filtered(year, ids)
            print(f"  watchlist hits: {len(hit):,}")
        except Exception as e:
            print(f"  FAILED year {year}: {e}")
            progress.setdefault("errors", []).append({"year": year, "error": str(e)})
            _write_seed_progress(progress)
            continue

        if len(hit) == 0:
            progress["years_done"].append({"year": year, "kept": 0})
            _write_seed_progress(progress)
            continue

        norm = normalize_epochs_df(hit, source=f"hf:tle_{year}")
        for nid, name in DEFAULT_WATCHLIST.items():
            m = norm["norad_id"] == nid
            if m.any():
                norm.loc[m, "object_name"] = name

        frames.append(norm)
        counts = norm.groupby("norad_id").size().to_dict()
        for nid, c in counts.items():
            by_norad[int(nid)] = int(by_norad.get(int(nid), 0) + int(c))
        progress["by_norad"] = by_norad
        progress["kept_total"] = int(sum(by_norad.values()))
        progress["years_done"].append({"year": year, "kept": int(len(norm))})
        progress["status"] = f"done_{year}"
        _write_seed_progress(progress)

        append_epochs(norm)
        print(f"  appended {len(norm):,} → history")

    if not frames:
        # may have skipped all because already present
        hist = load_history()
        if len(hist):
            progress["status"] = "completed_or_skipped"
            _write_seed_progress(progress)
            print(f"No new year frames; history already has {len(hist):,} rows.")
            return hist
        progress["status"] = "empty"
        _write_seed_progress(progress)
        print("No HF year data collected.")
        return pd.DataFrame(columns=CANONICAL_COLS)

    out = pd.concat(frames, ignore_index=True)
    progress["status"] = "completed"
    _write_seed_progress(progress)
    print(f"\nSeed complete: +{len(out):,} new epoch rows from this run")
    print(f"Progress file: {SEED_PROGRESS_PATH}")
    return out


def seed_from_hf_history_streaming(
    norad_ids: Optional[Sequence[int]] = None,
    start_year: int = 2024,
    max_rows: int = 20_000,
    *,
    prefer_year_parquet: bool = True,
    end_year: Optional[int] = None,
) -> pd.DataFrame:
    """
    Seed HF TLE history into the store.

    Default: year-parquet path (reliable). Pass prefer_year_parquet=False for
    legacy full-archive streaming (slow; stops at max_rows).
    """
    if prefer_year_parquet:
        return seed_from_hf_year_parquets(
            norad_ids=norad_ids,
            start_year=start_year,
            end_year=end_year,
        )

    try:
        from datasets import load_dataset
    except ImportError as e:
        raise ImportError("pip install datasets") from e

    ids = set(int(x) for x in (norad_ids or DEFAULT_WATCHLIST.keys()))
    print(f"Streaming HF TLE history for {len(ids)} NORADs since {start_year}…")
    progress: Dict = {
        "phase": "hf_stream",
        "scanned": 0,
        "kept": 0,
        "max_rows": max_rows,
        "status": "running",
        "by_norad": {int(i): 0 for i in ids},
    }
    _write_seed_progress(progress)

    ds = load_dataset("juliensimon/space-track-tle-history", split="train", streaming=True)

    collected = []
    n = 0
    for row in ds:
        n += 1
        if n % 200_000 == 0:
            progress["scanned"] = n
            progress["kept"] = len(collected)
            _write_seed_progress(progress)
            print(f"  scanned {n:,} … kept {len(collected)}")
        rid = row.get("norad_id") or row.get("NORAD_CAT_ID")
        if rid is None or int(rid) not in ids:
            continue
        ep = row.get("epoch") or row.get("EPOCH")
        if ep is None:
            continue
        try:
            year = pd.Timestamp(ep).year
        except Exception:
            continue
        if year < start_year:
            continue
        collected.append(row)
        progress["by_norad"][int(rid)] = progress["by_norad"].get(int(rid), 0) + 1
        if len(collected) >= max_rows:
            break

    progress["scanned"] = n
    progress["kept"] = len(collected)
    if not collected:
        progress["status"] = "empty"
        _write_seed_progress(progress)
        print("No HF history rows collected.")
        return pd.DataFrame(columns=CANONICAL_COLS)

    df = normalize_epochs_df(pd.DataFrame(collected), source="hf:space-track-tle-history")
    append_epochs(df)
    progress["status"] = "completed"
    _write_seed_progress(progress)
    print(f"Seeded {len(df)} epochs from HF history into store.")
    return df


def save_daily_snapshot(df: pd.DataFrame, day: Optional[str] = None) -> Path:
    ensure_dirs()
    day = day or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    path = DAILY_DIR / f"tle_{day}.csv"
    df.to_csv(path, index=False)
    meta = {
        "day": day,
        "n_rows": int(len(df)),
        "n_sats": int(df["norad_id"].nunique()) if len(df) else 0,
        "saved_at": datetime.now(timezone.utc).isoformat(),
    }
    (DAILY_DIR / f"tle_{day}.meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return path
