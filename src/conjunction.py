"""
Conjunction geometry: TCA + approximate Pc (Foster 2-D).

Does NOT rewrite pair_risk / anomaly_score. Extra fields only.

Prefers `sgp4` when installed. Without it (or without enough Kepler
elements) returns a documented Kepler-circular fallback so the pipeline
never crashes and tests stay network-free.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple

import numpy as np
import pandas as pd

from src.config import MU_EARTH_KM3_S2, R_EARTH_KM

# Hard-body radius for two catalog objects (operational default, not classified).
HBR_KM = 0.02
# Along-track growth ~ km / sqrt(hour) — conservative public-catalog prior.
SIGMA0_KM = 0.5
SIGMA_RATE = 0.35

try:
    from sgp4.api import WGS72, Satrec, jday  # type: ignore

    HAS_SGP4 = True
except Exception:  # pragma: no cover - optional extra
    HAS_SGP4 = False
    Satrec = None  # type: ignore
    WGS72 = None  # type: ignore
    jday = None  # type: ignore


def _last_row(hist: pd.DataFrame) -> Optional[pd.Series]:
    if hist is None or len(hist) == 0:
        return None
    if "timestamp" in hist.columns:
        h = hist.copy()
        h["timestamp"] = pd.to_datetime(h["timestamp"], utc=True, errors="coerce")
        h = h.dropna(subset=["timestamp"]).sort_values("timestamp")
        if len(h) == 0:
            return None
        return h.iloc[-1]
    return hist.iloc[-1]


def _epoch_days_since_1949(ts: datetime) -> float:
    epoch = datetime(1949, 12, 31, tzinfo=timezone.utc)
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return (ts - epoch).total_seconds() / 86400.0


def _satrec_from_row(row: pd.Series):
    if not HAS_SGP4:
        return None
    try:
        ts = pd.to_datetime(row.get("timestamp"), utc=True, errors="coerce")
        if pd.isna(ts):
            ts = datetime.now(timezone.utc)
        else:
            ts = ts.to_pydatetime()
        satnum = int(row.get("norad_id") or 0)
        bstar = float(row.get("bstar") or 0.0)
        ecc = float(row.get("eccentricity") or 0.001)
        inc = np.deg2rad(float(row.get("inclination_deg") or 0.0))
        raan = np.deg2rad(float(row.get("raan_deg") or 0.0))
        argp = np.deg2rad(float(row.get("arg_perigee_deg") or 0.0))
        ma = np.deg2rad(float(row.get("mean_anomaly_deg") or 0.0))
        n_rev_day = float(row.get("mean_motion_rev_per_day") or 0.0)
        if n_rev_day <= 0 and row.get("semi_major_axis_km"):
            sma = float(row["semi_major_axis_km"])
            period = 2 * np.pi * np.sqrt((sma ** 3) / MU_EARTH_KM3_S2)
            n_rev_day = 86400.0 / period
        no_kozai = n_rev_day * 2.0 * np.pi / 1440.0  # rad/min
        sat = Satrec()
        sat.sgp4init(
            WGS72,
            "i",
            satnum,
            _epoch_days_since_1949(ts),
            bstar,
            0.0,
            0.0,
            ecc,
            argp,
            inc,
            ma,
            no_kozai,
            raan,
        )
        return sat
    except Exception:
        return None


def _propagate_sgp4(sat, when: datetime) -> Optional[np.ndarray]:
    jd, fr = jday(when.year, when.month, when.day, when.hour, when.minute, when.second + when.microsecond * 1e-6)
    err, r, _v = sat.sgp4(jd, fr)
    if err != 0 or r is None:
        return None
    return np.array(r, dtype=float)


def _kepler_eci(row: pd.Series, when: datetime) -> Optional[np.ndarray]:
    """Circular-orbit fallback (argp/ma often missing in the epoch store)."""
    try:
        sma = float(row.get("semi_major_axis_km") or 0.0)
        if sma <= R_EARTH_KM:
            return None
        inc = np.deg2rad(float(row.get("inclination_deg") or 0.0))
        raan = np.deg2rad(float(row.get("raan_deg") or 0.0))
        n_rev_day = float(row.get("mean_motion_rev_per_day") or 0.0)
        if n_rev_day <= 0:
            period = 2 * np.pi * np.sqrt((sma ** 3) / MU_EARTH_KM3_S2)
            n_rev_day = 86400.0 / period
        t0 = pd.to_datetime(row.get("timestamp"), utc=True, errors="coerce")
        if pd.isna(t0):
            t0 = datetime.now(timezone.utc)
        else:
            t0 = t0.to_pydatetime()
        if when.tzinfo is None:
            when = when.replace(tzinfo=timezone.utc)
        if t0.tzinfo is None:
            t0 = t0.replace(tzinfo=timezone.utc)
        dt_s = (when - t0).total_seconds()
        ma = 2.0 * np.pi * n_rev_day * (dt_s / 86400.0)
        # Perifocal circular: x = sma cos M, y = sma sin M
        x_p = sma * np.cos(ma)
        y_p = sma * np.sin(ma)
        cos_o, sin_o = np.cos(raan), np.sin(raan)
        cos_i, sin_i = np.cos(inc), np.sin(inc)
        x = cos_o * x_p - sin_o * np.cos(inc) * y_p
        y = sin_o * x_p + cos_o * np.cos(inc) * y_p
        z = sin_i * y_p
        return np.array([x, y, z], dtype=float)
    except Exception:
        return None


def foster_pc(miss_km: float, sigma_km: float, hbr_km: float = HBR_KM) -> float:
    """2-D Foster Pc for a circular combined covariance of radius sigma_km."""
    if sigma_km <= 1e-9 or not np.isfinite(miss_km) or not np.isfinite(sigma_km):
        return 0.0
    # Pc = (HBR^2 / (2 σx σy)) exp(-d^2 / (2σ^2)) with σx=σy=sigma
    expo = -0.5 * (miss_km ** 2) / (sigma_km ** 2)
    pc = (hbr_km ** 2) / (2.0 * sigma_km * sigma_km) * np.exp(expo)
    return float(np.clip(pc, 0.0, 1.0))


def combined_sigma_km(hours_from_epoch: float) -> float:
    hours = max(0.0, float(hours_from_epoch))
    return float(SIGMA0_KM + SIGMA_RATE * np.sqrt(hours))


def estimate_conjunction(
    hist_s: pd.DataFrame,
    hist_a: pd.DataFrame,
    *,
    horizon_hours: float = 36.0,
    step_seconds: int = 120,
    now: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Scan [now, now+horizon] for TCA. Adds Pc + covariance; never mutates scores."""
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    row_s = _last_row(hist_s)
    row_a = _last_row(hist_a)
    empty = {
        "tca_utc": None,
        "miss_distance_km": None,
        "pc": None,
        "covariance": None,
        "method": "unavailable",
        "hours_to_tca": None,
    }
    if row_s is None or row_a is None:
        return empty

    sat_s = _satrec_from_row(row_s)
    sat_a = _satrec_from_row(row_a)
    use_sgp4 = bool(sat_s is not None and sat_a is not None)
    method = "sgp4" if use_sgp4 else "kepler_circular"

    n_steps = max(2, int(horizon_hours * 3600 / step_seconds))
    best_d = float("inf")
    best_t = now
    best_rs = None
    best_ra = None
    for i in range(n_steps + 1):
        t = now + timedelta(seconds=i * step_seconds)
        if use_sgp4:
            rs = _propagate_sgp4(sat_s, t)
            ra = _propagate_sgp4(sat_a, t)
        else:
            rs = _kepler_eci(row_s, t)
            ra = _kepler_eci(row_a, t)
        if rs is None or ra is None:
            continue
        d = float(np.linalg.norm(rs - ra))
        if d < best_d:
            best_d = d
            best_t = t
            best_rs = rs
            best_ra = ra

    if best_rs is None or not np.isfinite(best_d):
        return empty

    hours = (best_t - now).total_seconds() / 3600.0
    sigma = combined_sigma_km(hours)
    pc = foster_pc(best_d, sigma)
    return {
        "tca_utc": best_t.astimezone(timezone.utc).isoformat(),
        "miss_distance_km": round(float(best_d), 3),
        "pc": float(f"{pc:.6g}"),
        "covariance": {
            "model": "isotropic_alongtrack_growth",
            "sigma_km": round(sigma, 4),
            "hbr_km": HBR_KM,
            "trace": round(3.0 * sigma * sigma, 4),
        },
        "method": method,
        "hours_to_tca": round(hours, 3),
    }


def enrich_risk_report(report: Dict[str, Any], *, horizon_hours: float = 24.0) -> Dict[str, Any]:
    """Fill pc/tca on an existing risk_report without touching pair_risk.

    Used to compatibilize a report scored before conjunction extras existed.
    """
    from src.tle_store import history_as_sat_histories

    pairs = list(report.get("top_pairs") or [])
    ids: list[int] = []
    for p in pairs:
        for key in ("suspect_norad", "asset_norad"):
            if p.get(key) is not None:
                ids.append(int(p[key]))
    for row in report.get("board") or []:
        pair = row.get("pair") or {}
        if pair.get("asset_norad") is not None and row.get("norad_id") is not None:
            ids.extend([int(row["norad_id"]), int(pair["asset_norad"])])
    ids = sorted(set(ids))
    if not ids:
        return report
    hists = history_as_sat_histories(norad_ids=ids, min_epochs=5)
    cache: Dict[Tuple[int, int], Dict[str, Any]] = {}

    def conj_for(sid: int, aid: int) -> Dict[str, Any]:
        key = (sid, aid)
        if key in cache:
            return cache[key]
        hs, ha = hists.get(sid), hists.get(aid)
        if hs is None or ha is None:
            cache[key] = {}
            return cache[key]
        cache[key] = estimate_conjunction(hs, ha, horizon_hours=horizon_hours, step_seconds=300)
        return cache[key]

    new_pairs = []
    for p in pairs:
        if p.get("pc") is not None and p.get("tca_utc"):
            new_pairs.append(p)
            continue
        sid, aid = p.get("suspect_norad"), p.get("asset_norad")
        if sid is None or aid is None:
            new_pairs.append(p)
            continue
        new_pairs.append(attach_conjunction(p, conj_for(int(sid), int(aid))))
    report["top_pairs"] = new_pairs

    for row in report.get("board") or []:
        pair = row.get("pair")
        if not pair or pair.get("pc") is not None:
            continue
        sid, aid = row.get("norad_id"), pair.get("asset_norad")
        if sid is None or aid is None:
            continue
        row["pair"] = attach_conjunction(pair, conj_for(int(sid), int(aid)))
    return report


def attach_conjunction(pair_rec: Dict[str, Any], conj: Dict[str, Any]) -> Dict[str, Any]:
    """Copy conjunction fields onto a pair record without touching pair_risk."""
    out = dict(pair_rec)
    out["tca_utc"] = conj.get("tca_utc")
    out["miss_distance_km"] = conj.get("miss_distance_km")
    out["pc"] = conj.get("pc")
    out["covariance"] = conj.get("covariance")
    out["conjunction_method"] = conj.get("method")
    out["hours_to_tca"] = conj.get("hours_to_tca")
    return out
