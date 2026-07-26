"""
Space weather indices for Athena-SDA (drag vs maneuver context).

Primary archive (historical + near-real-time):
  GFZ Helmholtz — Kp, ap, Ap, SN, F10.7obs/adj (CC BY 4.0)
  https://kp.gfz-potsdam.de/app/files/Kp_ap_Ap_SN_F107_since_1932.txt

Live helpers (optional refresh):
  NOAA SWPC JSON F10.7, CelesTrak SW last 5 years

Store: data/space_weather/daily.parquet (+ csv mirror)
Lookup: date (UTC day)
"""
from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import numpy as np
import pandas as pd
import requests

from src.config import DATA_DIR

SW_DIR = DATA_DIR / "space_weather"
DAILY_PARQUET = SW_DIR / "daily.parquet"
DAILY_CSV = SW_DIR / "daily.csv"
META_JSON = SW_DIR / "meta.json"

GFZ_URL = "https://kp.gfz-potsdam.de/app/files/Kp_ap_Ap_SN_F107_since_1932.txt"
NOAA_F107_URL = "https://services.swpc.noaa.gov/json/f107_cm_flux.json"

# Quiet-solar defaults if store empty / missing day
DEFAULTS = {
    "f10_7": 120.0,
    "f10_7_adj": 120.0,
    "ap_index": 8.0,
    "kp_mean": 2.0,
    "sunspot_number": 50.0,
}

CANONICAL = [
    "date",
    "f10_7",
    "f10_7_adj",
    "ap_index",
    "kp_mean",
    "sunspot_number",
    "source",
]


def ensure_dirs() -> None:
    SW_DIR.mkdir(parents=True, exist_ok=True)


def _parse_gfz_text(text: str) -> pd.DataFrame:
    """
    GFZ line format (blank-separated):
    YYYY MM DD days days_m Bsr dB Kp1..Kp8 ap1..ap8 Ap SN F10.7obs F10.7adj D
    Missing F10.7 = -1.0
    """
    rows = []
    for line in text.splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        p = line.split()
        if len(p) < 27:
            continue
        try:
            y, m, d = int(p[0]), int(p[1]), int(p[2])
            kp_vals = [float(p[i]) for i in range(7, 15)]
            # skip invalid Kp markers
            kp_ok = [k for k in kp_vals if k >= 0]
            kp_mean = float(np.mean(kp_ok)) if kp_ok else float("nan")
            ap_daily = float(p[23])
            sn = float(p[24])
            f_obs = float(p[25])
            f_adj = float(p[26])
            if f_obs < 0:
                f_obs = float("nan")
            if f_adj < 0:
                f_adj = float("nan")
            if sn < 0:
                sn = float("nan")
            if ap_daily < 0:
                ap_daily = float("nan")
            rows.append(
                {
                    "date": pd.Timestamp(year=y, month=m, day=d, tz="UTC"),
                    "f10_7": f_obs,
                    "f10_7_adj": f_adj,
                    "ap_index": ap_daily,
                    "kp_mean": kp_mean,
                    "sunspot_number": sn,
                    "source": "gfz:kp_f107",
                }
            )
        except Exception:
            continue
    if not rows:
        return pd.DataFrame(columns=CANONICAL)
    df = pd.DataFrame(rows)
    df = df.sort_values("date").drop_duplicates(subset=["date"], keep="last")
    return df[CANONICAL].reset_index(drop=True)


def fetch_gfz_archive(timeout: int = 180) -> pd.DataFrame:
    """Download full GFZ archive (1932→now). ~5 MB."""
    r = requests.get(GFZ_URL, timeout=timeout)
    r.raise_for_status()
    return _parse_gfz_text(r.text)


def fetch_noaa_f107_recent(timeout: int = 60) -> pd.DataFrame:
    """Optional: recent F10.7 points from SWPC JSON (merge into daily)."""
    try:
        r = requests.get(NOAA_F107_URL, timeout=timeout)
        r.raise_for_status()
        data = r.json()
    except Exception:
        return pd.DataFrame(columns=CANONICAL)
    rows = []
    for item in data if isinstance(data, list) else []:
        try:
            ts = pd.Timestamp(item.get("time_tag"), tz="UTC")
            flux = float(item.get("flux"))
            day = ts.normalize()
            rows.append(
                {
                    "date": day,
                    "f10_7": flux,
                    "f10_7_adj": flux,
                    "ap_index": np.nan,
                    "kp_mean": np.nan,
                    "sunspot_number": np.nan,
                    "source": "noaa:f107_json",
                }
            )
        except Exception:
            continue
    if not rows:
        return pd.DataFrame(columns=CANONICAL)
    df = pd.DataFrame(rows)
    # one value per day — last report
    df = df.sort_values("date").drop_duplicates(subset=["date"], keep="last")
    return df[CANONICAL]


def save_daily(df: pd.DataFrame) -> Path:
    ensure_dirs()
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"], utc=True)
    df = df.sort_values("date").drop_duplicates(subset=["date"], keep="last")
    for c in ("f10_7", "f10_7_adj", "ap_index", "kp_mean", "sunspot_number"):
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    # forward/back fill mild gaps for training continuity
    df = df.set_index("date").sort_index()
    df[["f10_7", "f10_7_adj", "ap_index", "kp_mean", "sunspot_number"]] = (
        df[["f10_7", "f10_7_adj", "ap_index", "kp_mean", "sunspot_number"]]
        .ffill()
        .bfill()
    )
    df = df.reset_index()
    try:
        df.to_parquet(DAILY_PARQUET, index=False)
        path = DAILY_PARQUET
    except Exception:
        path = DAILY_CSV
    df.to_csv(DAILY_CSV, index=False)
    meta = {
        "saved_at": datetime.now(timezone.utc).isoformat(),
        "n_days": int(len(df)),
        "range": [str(df["date"].min()), str(df["date"].max())] if len(df) else [],
        "source_primary": "gfz:kp_f107",
    }
    META_JSON.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return path


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Map legacy column names (f10_7_obs / sn_sunspot) → canonical schema."""
    if df is None or len(df) == 0:
        return pd.DataFrame(columns=CANONICAL)
    df = df.copy()
    rename = {
        "f10_7_obs": "f10_7",
        "sn_sunspot": "sunspot_number",
        "sn": "sunspot_number",
        "Ap": "ap_index",
        "ap": "ap_index",
        "kp": "kp_mean",
    }
    for old, new in rename.items():
        if old in df.columns and new not in df.columns:
            df = df.rename(columns={old: new})
    for c in CANONICAL:
        if c not in df.columns:
            df[c] = np.nan if c != "source" else "unknown"
    df["date"] = pd.to_datetime(df["date"], utc=True)
    return df[CANONICAL].sort_values("date").reset_index(drop=True)


def load_daily() -> pd.DataFrame:
    ensure_dirs()
    if DAILY_PARQUET.exists():
        try:
            df = pd.read_parquet(DAILY_PARQUET)
            return _normalize_columns(df)
        except Exception:
            pass
    if DAILY_CSV.exists():
        try:
            df = pd.read_csv(DAILY_CSV)
            return _normalize_columns(df)
        except Exception:
            pass
    return pd.DataFrame(columns=CANONICAL)


def seed_space_weather(
    *,
    start_year: int = 2014,
    merge_noaa: bool = True,
    force: bool = False,
    keep_full_archive: bool = False,
) -> Dict[str, Any]:
    """
    Download GFZ full archive, keep from start_year (or full if keep_full_archive),
    optional NOAA F10.7 refresh. Returns status meta.
    """
    if not force and DAILY_PARQUET.exists():
        existing = load_daily()
        if len(existing) > 100:
            # Refresh only if store is older than ~2 days
            last = pd.Timestamp(existing["date"].max())
            age_days = (pd.Timestamp.now(tz="UTC") - last).total_seconds() / 86400.0
            if age_days < 2.0:
                print(f"Space weather cache fresh (last={last.date()}, age={age_days:.1f}d) — skip download (use --force)")
                clear_lookup_cache()
                return status()

    print(f"Fetching GFZ Kp/Ap/F10.7 archive…")
    gfz = fetch_gfz_archive()
    print(f"  GFZ rows: {len(gfz)}")
    if len(gfz) == 0:
        raise RuntimeError("GFZ space weather download empty")

    if keep_full_archive:
        df = gfz.copy()
    else:
        start = pd.Timestamp(year=start_year, month=1, day=1, tz="UTC")
        df = gfz[gfz["date"] >= start].copy()

    if merge_noaa:
        try:
            noaa = fetch_noaa_f107_recent()
            if len(noaa):
                # prefer GFZ Ap/Kp; update F10.7 from NOAA for overlapping recent days
                # keep GFZ for days that already have Ap; NOAA only fills/refreshes F10.7
                gfz_dates = set(pd.to_datetime(df["date"], utc=True).dt.normalize())
                noaa_only = noaa[~pd.to_datetime(noaa["date"], utc=True).dt.normalize().isin(gfz_dates)]
                # For overlapping days, update f10_7 from NOAA when present
                noaa_lut = {
                    pd.Timestamp(r["date"]).normalize(): float(r["f10_7"])
                    for _, r in noaa.iterrows()
                    if pd.notnull(r.get("f10_7"))
                }
                if noaa_lut:
                    dnorm = pd.to_datetime(df["date"], utc=True).dt.normalize()
                    for i, d in enumerate(dnorm):
                        if d in noaa_lut:
                            df.iloc[i, df.columns.get_loc("f10_7")] = noaa_lut[d]
                if len(noaa_only):
                    df = pd.concat([df, noaa_only], ignore_index=True)
                df = df.sort_values("date").drop_duplicates(subset=["date"], keep="last")
                print(f"  merged NOAA F10.7 recent points: {len(noaa)}")
        except Exception as e:
            print(f"  NOAA F10.7 skip: {e}")

    path = save_daily(df)
    print(f"Space weather store: {path}  days={len(df)}  {df['date'].min().date()} → {df['date'].max().date()}")
    clear_lookup_cache()
    meta = status()
    meta["path"] = str(path)
    return meta


def _build_lookup(df: pd.DataFrame) -> Dict[Any, Dict[str, float]]:
    out: Dict[Any, Dict[str, float]] = {}
    for _, row in df.iterrows():
        key = pd.Timestamp(row["date"]).normalize()
        if key.tzinfo is None:
            key = key.tz_localize("UTC")
        else:
            key = key.tz_convert("UTC")
        out[key] = {
            "f10_7": float(row.get("f10_7") or DEFAULTS["f10_7"]),
            "f10_7_adj": float(row.get("f10_7_adj") or row.get("f10_7") or DEFAULTS["f10_7_adj"]),
            "ap_index": float(row.get("ap_index") if pd.notnull(row.get("ap_index")) else DEFAULTS["ap_index"]),
            "kp_mean": float(row.get("kp_mean") if pd.notnull(row.get("kp_mean")) else DEFAULTS["kp_mean"]),
            "sunspot_number": float(
                row.get("sunspot_number") if pd.notnull(row.get("sunspot_number")) else DEFAULTS["sunspot_number"]
            ),
        }
    return out


@lru_cache(maxsize=1)
def _cached_store() -> Tuple[pd.DataFrame, Dict[Any, Dict[str, float]]]:
    df = load_daily()
    if len(df) == 0:
        return df, {}
    return df, _build_lookup(df)


def clear_lookup_cache() -> None:
    _cached_store.cache_clear()


def lookup_space_weather(
    when,
    *,
    defaults: bool = True,
) -> Dict[str, float]:
    """
    Return daily indices for the UTC calendar day of `when`.
    Falls back to nearest previous day, then defaults.
    """
    df, lut = _cached_store()
    if when is None:
        day = pd.Timestamp.now(tz="UTC").normalize()
    else:
        ts = pd.Timestamp(when)
        if ts.tzinfo is None:
            ts = ts.tz_localize("UTC")
        else:
            ts = ts.tz_convert("UTC")
        day = ts.normalize()

    if day in lut:
        base = dict(lut[day])
    elif lut:
        # nearest previous day
        keys = sorted(lut.keys())
        prev = [k for k in keys if k <= day]
        if prev:
            base = dict(lut[prev[-1]])
        elif defaults:
            base = dict(DEFAULTS)
        else:
            base = {k: float("nan") for k in DEFAULTS}
    elif defaults:
        base = dict(DEFAULTS)
    else:
        base = {k: float("nan") for k in DEFAULTS}

    # rolling context from store if available
    base.update(_rolling_features(df, day))
    return base


def _rolling_features(df: pd.DataFrame, day: pd.Timestamp) -> Dict[str, float]:
    """7-day deltas and means ending at day (for drag context)."""
    out = {
        "f10_7_delta_7d": 0.0,
        "f10_7_mean_7d": float(DEFAULTS["f10_7"]),
        "ap_mean_7d": float(DEFAULTS["ap_index"]),
        "ap_max_7d": float(DEFAULTS["ap_index"]),
        "geomagnetic_storm": 0.0,
    }
    if df is None or len(df) == 0:
        return out
    d = df.copy()
    d["date"] = pd.to_datetime(d["date"], utc=True)
    end = day
    start = day - pd.Timedelta(days=7)
    w = d[(d["date"] >= start) & (d["date"] <= end)].sort_values("date")
    if len(w) == 0:
        return out
    f = w["f10_7"].astype(float)
    ap = w["ap_index"].astype(float)
    out["f10_7_mean_7d"] = float(f.mean())
    out["ap_mean_7d"] = float(ap.mean())
    out["ap_max_7d"] = float(ap.max())
    if len(f) >= 2:
        out["f10_7_delta_7d"] = float(f.iloc[-1] - f.iloc[0])
    # Storm flag: Ap >= 30 ≈ stormy (rough)
    out["geomagnetic_storm"] = 1.0 if out["ap_max_7d"] >= 30.0 else 0.0
    return out


def space_weather_feature_vector(when, auto_seed: bool = False) -> Dict[str, float]:
    """Flat feature dict for extract_satellite_features / ML (keys match FEATURE_COLUMNS)."""
    df, _ = _cached_store()
    if auto_seed and (df is None or len(df) == 0):
        try:
            seed_space_weather(start_year=2014, merge_noaa=True)
            clear_lookup_cache()
        except Exception:
            pass

    sw = lookup_space_weather(when)
    available = 1.0 if (df is not None and len(df) > 0) else 0.0
    ap = float(sw.get("ap_index", DEFAULTS["ap_index"]))
    ap7 = float(sw.get("ap_mean_7d", ap))
    return {
        "f10_7": float(sw.get("f10_7", DEFAULTS["f10_7"])),
        "f10_7_adj": float(sw.get("f10_7_adj", DEFAULTS["f10_7_adj"])),
        "ap_index": ap,
        "kp_mean": float(sw.get("kp_mean", DEFAULTS["kp_mean"])),
        "sunspot_number": float(sw.get("sunspot_number", DEFAULTS["sunspot_number"])),
        "f10_7_delta_7d": float(sw.get("f10_7_delta_7d", 0.0)),
        "f10_7_mean_7d": float(sw.get("f10_7_mean_7d", DEFAULTS["f10_7"])),
        "ap_mean_7d": ap7,
        "ap_max_7d": float(sw.get("ap_max_7d", ap)),
        "ap_delta_7d": float(ap - ap7),
        "geomagnetic_storm": float(sw.get("geomagnetic_storm", 0.0)),
        "space_weather_available": available,
    }


def status() -> Dict[str, Any]:
    df = load_daily()
    return {
        "path_parquet": str(DAILY_PARQUET),
        "exists": DAILY_PARQUET.exists() or DAILY_CSV.exists(),
        "n_days": int(len(df)),
        "range": [str(df["date"].min()), str(df["date"].max())] if len(df) else [],
    }
