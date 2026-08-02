"""
Anomaly monitoring loop for Athena-SDA — standard daily protocol.

  SERIES (past)   --train--->  baseline Isolation Forest  (= object "normal")
  NEW DATA (D0)   --score--->  latest window vs baseline
  RELEVANCE       --alert--->  strong deviation OR day-over-day jump (delta score)

Operational Cycle (D = today UTC):
  1) ingest-daily     -> append fresh TLEs to history series
  2) train-baseline   -> trains ONLY on windows ending BEFORE D - holdout
                         (default holdout=1: "yesterday and before" = normal; "today" excluded)
  3) score            -> scores LATEST window per satellite against baseline
  4) relevance        -> anomaly_score >= thr  and/or  delta_score vs yesterday's report

Design:
  - Series is the memory; model does not "memorize today" in training.
  - Evaluation is distributional (IF) + contextual (SW, pairs, DQ).
  - Alerts are filtered through Data Quality gates.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

from src.config import IFOREST_COLUMNS, MODELS_DIR, FEATURE_COLUMNS
from src.models import extract_satellite_features, load_models, predict_threat
from src.tle_store import (
    ALERTS_DIR,
    DATA_DIR,
    DEFAULT_WATCHLIST,
    ensure_dirs,
    history_as_sat_histories,
    load_history,
)


def _watchlist_names() -> dict:
    try:
        from src.catalog import name_map

        return name_map() or dict(DEFAULT_WATCHLIST)
    except Exception:
        return dict(DEFAULT_WATCHLIST)


def _watchlist_meta(norad_id: int) -> dict:
    try:
        from src.catalog import get_meta

        return get_meta(int(norad_id))
    except Exception:
        return {
            "norad_id": int(norad_id),
            "name": DEFAULT_WATCHLIST.get(int(norad_id), str(norad_id)),
            "role": "unknown",
            "country": "UNKNOWN",
            "purpose": "unknown",
            "orbit_class": "LEO",
        }

FEATURES_DIR = DATA_DIR / "features"
IFOREST_MONITOR_PATH = MODELS_DIR / "isolation_forest_monitor.joblib"
MONITOR_META_PATH = MODELS_DIR / "anomaly_monitor_meta.json"
WINDOW = 20  # epochs required by extract_satellite_features
RKHS_REF_PATH = MODELS_DIR / "rkhs_reference.joblib"


def _load_rkhs_reference() -> Optional[np.ndarray]:
    """Normal-regime reference for spectral RKHS (optional diagnostic feature)."""
    if not RKHS_REF_PATH.exists():
        return None
    try:
        ref = joblib.load(RKHS_REF_PATH)
        arr = np.asarray(ref, dtype=float)
        if arr.ndim == 1:
            arr = arr.reshape(1, -1)
        if arr.size == 0 or arr.shape[1] < 10:
            return None
        # extract_satellite_features uses 10-dim subset
        return arr[:, :10] if arr.shape[1] >= 10 else arr
    except Exception:
        return None


# -- Data quality (light gate) -----------------------------------------------

def data_quality_score(
    hist: pd.DataFrame,
    *,
    reference_time: Optional[pd.Timestamp] = None,
) -> Dict[str, Any]:
    """
    Simple DQ metrics for the latest state of a history series.
    Low score -> do not treat anomaly as HOSTILE; mark UNRELIABLE.

    tle_age is recomputed vs reference_time (asof) or UTC now — never trusts
    frozen 0.0 placeholders from parquet ingest.
    """
    from src.models import tle_age_hours_at

    issues: List[str] = []
    score = 1.0

    if len(hist) < WINDOW:
        return {"score": 0.0, "issues": ["insufficient_history"], "reliable": False}

    last = hist.iloc[-1]
    age = tle_age_hours_at(
        last.get("timestamp"),
        reference_time=reference_time,
        fallback=float(last.get("tle_age_hours", 24.0) or 24.0),
    )
    if age > 72:
        score -= 0.35
        issues.append(f"tle_stale_{age:.0f}h")
    elif age > 36:
        score -= 0.15
        issues.append(f"tle_aging_{age:.0f}h")

    # Gaps in timeline
    ts = pd.to_datetime(hist["timestamp"], utc=True, errors="coerce")
    if ts.notna().sum() >= 2:
        gaps = ts.diff().dt.total_seconds().dropna() / 3600.0
        max_gap = float(gaps.max()) if len(gaps) else 0.0
        if max_gap > 168:  # > 7 days
            score -= 0.3
            issues.append(f"gap_{max_gap:.0f}h")
        elif max_gap > 72:
            score -= 0.15
            issues.append(f"gap_{max_gap:.0f}h")

    # Impossible jumps (SMA)
    sma = hist["semi_major_axis_km"].astype(float).values
    if len(sma) >= 2:
        d = np.abs(np.diff(sma))
        if np.nanmax(d) > 200:  # >200 km single-step LEO is extreme
            score -= 0.25
            issues.append("sma_jump")

    # Physical bounds
    mm = float(last["mean_motion_rev_per_day"])
    if not (0.5 < mm < 20):
        score -= 0.4
        issues.append("mean_motion_oob")

    score = float(np.clip(score, 0.0, 1.0))
    return {
        "score": score,
        "issues": issues,
        "reliable": score >= 0.45,
        "tle_age_hours": age,
    }


# -- Feature windows from history --------------------------------------------

def _select_window_ends(
    ends: List[int],
    *,
    max_windows: int,
    sample_mode: str = "hybrid",
) -> List[int]:
    """
    sample_mode:
      recent  -- only last N (current regime)
      full    -- N windows spaced across full series
      hybrid  -- half long-series + half recent (operational default)
    """
    if not ends or max_windows <= 0:
        return []
    if len(ends) <= max_windows:
        return ends

    mode = (sample_mode or "hybrid").lower()
    if mode == "recent":
        return ends[-max_windows:]
    if mode == "full":
        idx = np.linspace(0, len(ends) - 1, num=max_windows, dtype=int)
        return [ends[i] for i in sorted(set(idx.tolist()))]

    # hybrid: span history + dense recent tip
    n_recent = max(1, max_windows // 2)
    n_span = max_windows - n_recent
    recent = ends[-n_recent:]
    older = ends[:-n_recent] if len(ends) > n_recent else []
    if older and n_span > 0:
        idx = np.linspace(0, len(older) - 1, num=min(n_span, len(older)), dtype=int)
        span = [older[i] for i in sorted(set(idx.tolist()))]
    else:
        span = []
    merged = sorted(set(span + recent))
    # if set collapse, pad with more recent
    if len(merged) < max_windows:
        for e in reversed(ends):
            if e not in merged:
                merged.append(e)
            if len(merged) >= max_windows:
                break
        merged = sorted(merged)
    return merged[-max_windows:]


def build_feature_windows(
    sat_histories: Dict[int, pd.DataFrame],
    *,
    end_before: Optional[pd.Timestamp] = None,
    end_after: Optional[pd.Timestamp] = None,
    step: int = 2,
    max_windows_per_sat: int = 40,
    sample_mode: str = "hybrid",
    names: Optional[Dict[int, str]] = None,
) -> Tuple[pd.DataFrame, List[Dict[str, Any]]]:
    """
    Sliding windows of length WINDOW -> feature rows for IF training / scoring.

    end_before: only use windows whose last epoch is < end_before (past train)
    end_after: only windows with last epoch >= end_after (recent score set)
    sample_mode: hybrid | recent | full -- how to subsample the series
    """
    names = names or {}
    rows: List[Dict[str, float]] = []
    meta: List[Dict[str, Any]] = []
    rkhs_ref = _load_rkhs_reference()

    for sid, hist in sat_histories.items():
        h = hist.sort_values("timestamp").reset_index(drop=True)
        if end_before is not None:
            h = h[pd.to_datetime(h["timestamp"], utc=True) < end_before]
        if len(h) < WINDOW:
            continue

        # indices of window ends
        ends = list(range(WINDOW, len(h) + 1, step))
        if end_after is not None:
            # only windows that end in the recent period
            filtered = []
            for e in ends:
                t_end = pd.to_datetime(h.iloc[e - 1]["timestamp"], utc=True)
                if t_end >= end_after:
                    filtered.append(e)
            ends = filtered
        ends = _select_window_ends(ends, max_windows=max_windows_per_sat, sample_mode=sample_mode)

        for e in ends:
            sub = h.iloc[e - WINDOW : e]
            try:
                win_end = pd.to_datetime(sub["timestamp"].iloc[-1], utc=True, errors="coerce")
                cat = _watchlist_meta(int(sid))
                feats = extract_satellite_features(
                    sub,
                    country=str(cat.get("country") or "UNKNOWN"),
                    purpose=str(cat.get("purpose") or "unknown"),
                    orbit_class=str(
                        cat.get("orbit_class")
                        or ("LEO" if float(sub["semi_major_axis_km"].iloc[-1]) < 8000 else "MEO")
                    ),
                    min_distance_to_military_km=500.0,
                    reference_time=win_end if pd.notnull(win_end) else None,
                    reference_matrix=rkhs_ref,
                )
            except Exception:
                continue
            rows.append(feats)
            meta.append(
                {
                    "norad_id": int(sid),
                    "object_name": names.get(int(sid), str(sid)),
                    "window_end": str(sub["timestamp"].iloc[-1]),
                    "n_epochs": int(len(sub)),
                }
            )

    if not rows:
        return pd.DataFrame(columns=IFOREST_COLUMNS), []

    X = pd.DataFrame(rows)
    for c in IFOREST_COLUMNS:
        if c not in X.columns:
            X[c] = 0.0
    X = X[IFOREST_COLUMNS].astype(float).replace([np.inf, -np.inf], 0.0).fillna(0.0)
    return X, meta


# -- Train baseline on the past ----------------------------------------------

def train_baseline_from_history(
    *,
    holdout_days: int = 1,
    contamination: float = 0.06,
    n_estimators: int = 200,
    watchlist: Optional[Sequence[int]] = None,
    max_windows_per_sat: int = 80,
    sample_mode: str = "hybrid",
    military_doctrine: bool = True,
) -> Dict[str, Any]:
    """
    Fit Isolation Forest on feature windows that end BEFORE (now - holdout_days).

    Military doctrine (default):
      Train on baseline + asset roles only (= normality anchors).
      Suspects are scored later for detection — not mixed into "normal".

    Protocol: series up to yesterday (holdout=1) defines normal.
    Today's data is NOT included in training — only in scoring.
    """
    from src.doctrine import doctrine_summary, ids_for_if_training

    ensure_dirs()
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    FEATURES_DIR.mkdir(parents=True, exist_ok=True)

    names = _watchlist_names()
    all_ids = list(watchlist) if watchlist is not None else list(names.keys())
    if military_doctrine:
        train_ids = ids_for_if_training(all_ids, min_ids=4)
    else:
        train_ids = list(all_ids)

    hists = history_as_sat_histories(norad_ids=train_ids, min_epochs=WINDOW)
    if not hists:
        hists = history_as_sat_histories(norad_ids=all_ids, min_epochs=WINDOW)
    if not hists:
        hists = history_as_sat_histories(min_epochs=WINDOW)
    if not hists:
        raise RuntimeError(
            "Insufficient history. Run: seed-history and/or ingest-daily before training."
        )

    train_norads = sorted(hists.keys())
    cutoff = pd.Timestamp.now(tz="UTC") - timedelta(days=holdout_days)
    X, meta = build_feature_windows(
        hists,
        end_before=cutoff,
        step=3,
        max_windows_per_sat=max_windows_per_sat,
        sample_mode=sample_mode,
        names=names,
    )
    if len(X) < 30:
        print("Few windows with holdout -- training on all available history for train roles.")
        X, meta = build_feature_windows(
            hists,
            step=2,
            max_windows_per_sat=max(100, max_windows_per_sat),
            sample_mode=sample_mode,
            names=names,
        )
    if len(X) < 15:
        raise RuntimeError(f"Only {len(X)} feature windows -- collect more history.")

    win_ts = pd.to_datetime([m["window_end"] for m in meta], utc=True, errors="coerce")
    win_min = str(win_ts.min()) if win_ts.notna().any() else None
    win_max = str(win_ts.max()) if win_ts.notna().any() else None

    print(
        f"IF Training (military normality anchors): {len(X)} windows, {X.shape[1]} features, "
        f"cutoff={cutoff.date()} sample={sample_mode} n_sats={len(train_norads)}"
    )
    print(f"  train NORADs (baseline+asset): {train_norads}")
    if win_min and win_max:
        print(f"  window_end coverage: {win_min[:10]} -> {win_max[:10]}")
    iforest = IsolationForest(
        n_estimators=n_estimators,
        contamination=contamination,
        random_state=42,
        n_jobs=-1,
    )
    iforest.fit(X)

    joblib.dump(iforest, IFOREST_MONITOR_PATH)

    raw = iforest.decision_function(X)
    scores = np.clip(0.5 - raw, 0.0, 1.0)
    try:
        from src.engine import homology_backend
        hom_mode = homology_backend()
    except Exception:
        hom_mode = "proxy"
    # Orbit labels for calibration table (paper thr)
    orbit_labels = []
    for m in meta:
        try:
            orbit_labels.append(str(_watchlist_meta(int(m["norad_id"])).get("orbit_class") or "LEO"))
        except Exception:
            orbit_labels.append("LEO")
    from src.calibration import build_calibration_table

    calibration = build_calibration_table(list(scores), orbit_labels, floor=0.50)
    meta_out = {
        "protocol": "military_baseline_train__suspect_score",
        "doctrine": "military_first_sda",
        "description": (
            "IF trained on baseline+asset past windows only (normality anchors). "
            "Daily scoring compares each sat (esp. suspects) to that baseline. "
            "Hard thr calibrated as max(0.50, p95 of normality-anchor scores), per orbit when possible. "
            "Does NOT overwrite isolation_forest.joblib (priority pipeline). "
            "Palantir-style: Data→Quant→IF Inference→priority (XGB/pairs)→LLM explain."
        ),
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "n_windows": int(len(X)),
        "n_sats": int(len({m["norad_id"] for m in meta})),
        "train_norad_ids": train_norads,
        "train_roles": ["baseline", "asset"],
        "military_doctrine": bool(military_doctrine),
        "holdout_days": holdout_days,
        "contamination": contamination,
        "sample_mode": sample_mode,
        "max_windows_per_sat": max_windows_per_sat,
        "feature_columns": list(IFOREST_COLUMNS),
        "homology_mode": hom_mode,
        "rkhs_in_iforest": False,
        "score_mean": float(np.mean(scores)),
        "score_p95": float(np.percentile(scores, 95)),
        "score_p99": float(np.percentile(scores, 99)),
        "calibration": calibration,
        "recommended_anomaly_threshold": float(
            (calibration.get("global") or {}).get("recommended_thr") or 0.50
        ),
        "cutoff_utc": str(cutoff),
        "train_window_end_min": win_min,
        "train_window_end_max": win_max,
        "doctrine_summary": doctrine_summary(),
    }
    try:
        from src.model_registry import register_model

        register_model(
            "monitor_if",
            path=IFOREST_MONITOR_PATH,
            feature_columns=IFOREST_COLUMNS,
            extra={
                "n_windows": meta_out["n_windows"],
                "n_sats": meta_out["n_sats"],
                "cutoff_utc": meta_out["cutoff_utc"],
                "contamination": contamination,
                "homology_mode": hom_mode,
                "score_p95": meta_out["score_p95"],
                "train_roles": meta_out["train_roles"],
                "doctrine": "military_first_sda",
                "random_state": 42,
            },
        )
    except Exception as exc:
        print(f"Warning: model registry update failed: {exc}")

    MONITOR_META_PATH.write_text(json.dumps(meta_out, indent=2, default=str), encoding="utf-8")

    feat_path = FEATURES_DIR / "train_windows_latest.csv"
    roles = []
    for m in meta:
        try:
            roles.append(_watchlist_meta(int(m["norad_id"])).get("role", "unknown"))
        except Exception:
            roles.append("unknown")
    X.assign(
        norad_id=[m["norad_id"] for m in meta],
        window_end=[m["window_end"] for m in meta],
        role=roles,
    ).to_csv(feat_path, index=False)
    print(f"Model saved: {IFOREST_MONITOR_PATH}")
    print(f"Train features: {feat_path}")
    return meta_out


def _load_previous_day_scores(day: str) -> Dict[int, float]:
    """Map norad_id -> anomaly_score from yesterday's report (for delta relevance)."""
    try:
        d = datetime.strptime(day, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except Exception:
        return {}
    prev = (d - timedelta(days=1)).strftime("%Y-%m-%d")
    path = ALERTS_DIR / f"anomalies_{prev}.json"
    if not path.exists():
        return {}
    try:
        rep = json.loads(path.read_text(encoding="utf-8"))
        out: Dict[int, float] = {}
        for a in rep.get("alerts") or []:
            if a.get("norad_id") is None:
                continue
            out[int(a["norad_id"])] = float(a.get("anomaly_score") or 0.0)
        return out
    except Exception:
        return {}


def _load_monitor_iforest() -> IsolationForest:
    path = IFOREST_MONITOR_PATH
    if not path.exists():
        path = MODELS_DIR / "isolation_forest.joblib"
    if not path.exists():
        raise FileNotFoundError(
            "No monitor Isolation Forest. Run train-baseline first."
        )
    return joblib.load(path)


# -- Anomaly onset (when noise first rose on the series) ---------------------

def _sma_series_onset(
    hist: pd.DataFrame,
    *,
    window: int = 30,
    z_threshold: float = 3.0,
) -> Optional[str]:
    """
    First epoch where |SMA - rolling median| / MAD exceeds z_threshold.
    Lightweight change-point proxy (not intent date).
    """
    h = hist.sort_values("timestamp").reset_index(drop=True)
    if len(h) < window + 2:
        return None
    sma = h["semi_major_axis_km"].astype(float).values
    ts = pd.to_datetime(h["timestamp"], utc=True, errors="coerce")
    for i in range(window, len(sma)):
        base = sma[i - window : i]
        med = float(np.median(base))
        mad = float(np.median(np.abs(base - med)))
        if mad < 1e-9:
            mad = 1e-6
        z = abs(float(sma[i]) - med) / mad
        if z >= z_threshold:
            t = ts.iloc[i]
            if pd.notnull(t):
                return str(t)
    return None


def estimate_anomaly_onset(
    hist: pd.DataFrame,
    iforest: IsolationForest,
    *,
    norad_id: int = 0,
    threshold: float = 0.55,
    soft_threshold: float = 0.45,
    sustained: int = 2,
    max_windows: int = 40,
    step: int = 6,
) -> Dict[str, Any]:
    """
    Estimate when anomalous noise *first* rose on this object's series.

    Method:
      - Score spaced feature windows with current monitor IF.
      - first_elevated_at = first window_end with score >= threshold that is
        followed by (sustained-1) consecutive elevated samples.
      - sma_change_at = first large SMA z-score break.
    """
    out: Dict[str, Any] = {
        "first_elevated_at": None,
        "method": "if_sustained",
        "threshold": float(threshold),
        "soft_threshold": float(soft_threshold),
        "sustained": int(sustained),
        "n_windows_scored": 0,
        "max_score_in_scan": None,
        "sma_change_at": None,
        "note": (
            "Estimate: TLE window end / epoch -- not intent date or maneuver clock."
        ),
    }
    sma_at = _sma_series_onset(hist)
    out["sma_change_at"] = sma_at

    h = hist.sort_values("timestamp").reset_index(drop=True)
    if len(h) < WINDOW + step:
        out["method"] = "sma_only" if sma_at else "insufficient_history"
        if sma_at:
            out["first_elevated_at"] = sma_at
        return out

    # Spaced windows across the series (chronological)
    ends = list(range(WINDOW, len(h) + 1, max(1, step)))
    if len(ends) > max_windows:
        idx = np.linspace(0, len(ends) - 1, num=max_windows, dtype=int)
        ends = [ends[i] for i in sorted(set(int(i) for i in idx))]

    scores: List[Tuple[str, float]] = []
    cat = _watchlist_meta(int(norad_id))
    for e in ends:
        sub = h.iloc[e - WINDOW : e]
        try:
            win_end = pd.to_datetime(sub["timestamp"].iloc[-1], utc=True, errors="coerce")
            feats = extract_satellite_features(
                sub,
                country=str(cat.get("country") or "UNKNOWN"),
                purpose=str(cat.get("purpose") or "unknown"),
                orbit_class=str(
                    cat.get("orbit_class")
                    or (
                        "LEO"
                        if float(sub["semi_major_axis_km"].iloc[-1]) < 8000
                        else "MEO"
                    )
                ),
                min_distance_to_military_km=500.0,
                reference_time=win_end if pd.notnull(win_end) else None,
            )
            row = pd.DataFrame([{c: float(feats.get(c, 0.0)) for c in IFOREST_COLUMNS}])
            row = row.replace([np.inf, -np.inf], 0.0).fillna(0.0)
            raw = float(iforest.decision_function(row)[0])
            score = float(np.clip(0.5 - raw, 0.0, 1.0))
            scores.append((str(sub["timestamp"].iloc[-1]), score))
        except Exception:
            continue

    out["n_windows_scored"] = len(scores)
    if scores:
        out["max_score_in_scan"] = float(max(s for _, s in scores))

    # First sustained elevation at hard threshold
    first: Optional[str] = None
    need = max(1, sustained)
    for i, (t, sc) in enumerate(scores):
        if sc < threshold:
            continue
        ok = True
        for j in range(1, need):
            if i + j >= len(scores):
                ok = False
                break
            if scores[i + j][1] < soft_threshold:
                ok = False
                break
        if ok:
            first = t
            break

    if first is None:
        # Soft: first single breach of soft thr if scan peaked high
        for t, sc in scores:
            if sc >= soft_threshold:
                first = t
                out["method"] = "if_first_soft"
                break

    out["first_elevated_at"] = first
    if first is None and sma_at:
        out["first_elevated_at"] = sma_at
        out["method"] = "sma_change_fallback"
    elif first is None:
        out["method"] = "no_onset_detected"

    return out


# -- Score daily / latest ----------------------------------------------------

def score_latest(
    *,
    anomaly_threshold: float = 0.55,
    use_full_pipeline: bool = True,
    watchlist: Optional[Sequence[int]] = None,
    with_pairs: bool = True,
    delta_relevance: float = 0.08,
) -> Dict[str, Any]:
    """
    Compares latest window of each satellite against series baseline.

    Relevance (alert):
      - anomaly_score >= threshold  (distributional shift vs series), OR
      - delta_score vs yesterday's report >= delta_relevance

    Writes data/alerts/anomalies_YYYY-MM-DD.json
    """
    ensure_dirs()
    ids = list(watchlist) if watchlist is not None else None
    hists = history_as_sat_histories(norad_ids=ids, min_epochs=WINDOW)
    if not hists:
        hists = history_as_sat_histories(min_epochs=WINDOW)
    if not hists:
        raise RuntimeError("No satellites with history >= 20 epochs for scoring.")

    iforest = _load_monitor_iforest()
    mon_meta = {}
    if MONITOR_META_PATH.exists():
        mon_meta = json.loads(MONITOR_META_PATH.read_text(encoding="utf-8"))

    # Optional full stack
    xgb = None
    rkhs = None
    if use_full_pipeline:
        try:
            iforest_full, xgb, rkhs, _ = load_models()
            _ = iforest_full
        except Exception as e:
            print(f"Full pipeline models not loaded ({e}); IF-only scoring.")
            use_full_pipeline = False

    # Precompute best proximity to protected assets
    asset_hists: Dict[int, pd.DataFrame] = {}
    try:
        from src.catalog import asset_ids

        for aid in asset_ids():
            if aid in hists:
                asset_hists[int(aid)] = hists[int(aid)]
    except Exception:
        pass
    if not asset_hists:
        asset_hists = {}

    from src.orbital import min_distance_to_assets as _min_dist_assets
    from src.engine import calculate_cointegration_pvalue as _coint_p

    alerts: List[Dict[str, Any]] = []
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    prev_scores = _load_previous_day_scores(day)
    calibration = mon_meta.get("calibration") or {}
    from src.calibration import threshold_for_orbit

    thr_global = float(
        mon_meta.get("recommended_anomaly_threshold")
        or (calibration.get("global") or {}).get("recommended_thr")
        or anomaly_threshold
    )
    thr_elevated = float(
        (calibration.get("global") or {}).get("p90")
        or mon_meta.get("score_p95")
        or max(0.45, thr_global - 0.05)
    )

    for sid, hist in hists.items():
        hist = hist.sort_values("timestamp").reset_index(drop=True)
        sub = hist.iloc[-WINDOW:]
        win_end = pd.to_datetime(sub["timestamp"].iloc[-1], utc=True, errors="coerce")
        ref_t = win_end if pd.notnull(win_end) else None
        dq = data_quality_score(hist, reference_time=None)
        cat = _watchlist_meta(int(sid))
        name = cat.get("name") or DEFAULT_WATCHLIST.get(int(sid), str(sid))
        sma_last = float(sub["semi_major_axis_km"].iloc[-1])
        orbit_guess = cat.get("orbit_class") or (
            "LEO" if sma_last < 8000 else ("GEO" if sma_last > 35000 else "MEO")
        )

        # Context: distance / coint vs protected assets
        min_dist = 500.0
        closest_asset = None
        coint_p = 1.0
        if asset_hists:
            others = {k: v for k, v in asset_hists.items() if k != int(sid)}
            if others:
                min_dist, closest_asset = _min_dist_assets(hist, others, cap_km=2000.0)
                if closest_asset is not None and closest_asset in hists:
                    try:
                        from src.pair_score import _align_series

                        sa, aa = _align_series(hist, hists[closest_asset])
                        coint_p = _coint_p(sa, aa) if len(sa) >= 20 else 1.0
                    except Exception:
                        n = min(80, len(hist), len(hists[closest_asset]))
                        coint_p = _coint_p(
                            hist["semi_major_axis_km"].astype(float).values[-n:],
                            hists[closest_asset]["semi_major_axis_km"].astype(float).values[-n:],
                        )

        try:
            feats = extract_satellite_features(
                sub,
                reference_matrix=rkhs,
                country=str(cat.get("country") or "UNKNOWN"),
                purpose=str(cat.get("purpose") or "unknown"),
                reference_time=None,  # live inference: age vs now
                orbit_class=str(orbit_guess),
                min_distance_to_military_km=float(min_dist),
                cointegration_pvalue=float(coint_p),
            )
        except Exception as e:
            alerts.append(
                {
                    "norad_id": int(sid),
                    "object_name": name,
                    "role": cat.get("role", "unknown"),
                    "country": cat.get("country", "UNKNOWN"),
                    "purpose": cat.get("purpose", "unknown"),
                    "status": "FEATURE_ERROR",
                    "error": str(e),
                    "data_quality": dq,
                }
            )
            continue

        # Isolation Forest anomaly score vs baseline
        row = pd.DataFrame([{c: float(feats.get(c, 0.0)) for c in IFOREST_COLUMNS}])
        row = row.replace([np.inf, -np.inf], 0.0).fillna(0.0)
        try:
            raw = float(iforest.decision_function(row)[0])
        except Exception:
            raw = float(iforest.decision_function(row.values)[0])
        anomaly_score = float(np.clip(0.5 - raw, 0.0, 1.0))
        feats["anomaly_score"] = anomaly_score

        # Per-orbit calibrated hard threshold (paper A+B)
        thr_use = threshold_for_orbit(calibration, str(orbit_guess), default=thr_global)

        # Delta vs yesterday = day-over-day shift
        prev = prev_scores.get(int(sid))
        score_delta = float(anomaly_score - prev) if prev is not None else None
        changed_relevant = bool(
            score_delta is not None and score_delta >= delta_relevance and anomaly_score >= thr_elevated * 0.85
        )
        series_outlier = bool(anomaly_score >= thr_use)

        from src.doctrine import classify_military_status

        mil = classify_military_status(
            role=str(cat.get("role") or "unknown"),
            reliable=bool(dq.get("reliable")),
            series_outlier=series_outlier,
            day_over_day_relevant=changed_relevant,
            pair_elevated=False,
        )

        rec: Dict[str, Any] = {
            "norad_id": int(sid),
            "object_name": name,
            "role": cat.get("role", "unknown"),
            "country": cat.get("country", "UNKNOWN"),
            "purpose": cat.get("purpose", "unknown"),
            "orbit_class": orbit_guess,
            "window_end": str(sub["timestamp"].iloc[-1]),
            "anomaly_score": anomaly_score,
            "anomaly_threshold_used": float(thr_use),
            "score_prev_day": prev,
            "score_delta_1d": score_delta,
            "series_outlier": series_outlier,
            "day_over_day_relevant": changed_relevant,
            "is_anomaly": bool(mil.get("is_anomaly")),
            "is_military_detection": bool(mil.get("is_military_detection")),
            "is_platform_health_flag": bool(mil.get("is_platform_health_flag")),
            "is_calibration_object": bool(mil.get("is_calibration_object")),
            "military_alert_eligible": bool(mil.get("military_alert_eligible")),
            "status": mil.get("status") or "NOMINAL",
            "data_quality": dq,
            "min_distance_to_asset_km": float(min_dist) if asset_hists else None,
            "closest_asset_norad": int(closest_asset) if closest_asset is not None else None,
            "cointegration_pvalue": float(coint_p) if asset_hists else None,
            "features_snapshot": {
                k: float(feats.get(k, 0.0))
                for k in (
                    "delta_sma_7d_km",
                    "shannon_entropy_sma_30d",
                    "hurst_exponent_sma",
                    "kolmogorov_proxy_7d",
                    "l1_cusum_sma",
                    "tle_age_hours",
                    "f10_7",
                    "f10_7_adj",
                    "ap_index",
                    "kp_mean",
                    "f10_7_delta_7d",
                    "ap_mean_7d",
                    "ap_max_7d",
                    "ap_delta_7d",
                    "geomagnetic_storm",
                    "space_weather_available",
                    "min_distance_to_military_km",
                    "cointegration_pvalue",
                )
            },
        }

        if use_full_pipeline and xgb is not None:
            try:
                ml = predict_threat(iforest, xgb, feats)
                rec["xgb_class"] = ml["xgb_class"]
                rec["xgb_confidence"] = ml["xgb_confidence"]
                rec["xgb_proba"] = ml["xgb_proba"]
            except Exception as e:
                rec["xgb_error"] = str(e)

        # Onset of anomalous noise on the series
        try:
            rec["anomaly_onset"] = estimate_anomaly_onset(
                hist,
                iforest,
                norad_id=int(sid),
                threshold=float(anomaly_threshold),
                soft_threshold=float(max(0.40, anomaly_threshold - 0.10)),
                sustained=2,
                max_windows=32,
                step=7,
            )
        except Exception as e:
            rec["anomaly_onset"] = {"error": str(e), "method": "onset_error"}

        alerts.append(rec)

    # Sort: military detections first, then score
    alerts.sort(
        key=lambda a: (
            -int(bool(a.get("is_military_detection"))),
            -int(bool(a.get("is_anomaly"))),
            -float(a.get("anomaly_score", 0)),
            a.get("norad_id", 0),
        )
    )

    from src.doctrine import doctrine_summary

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "day": day,
        "protocol": "military_baseline_train__suspect_score",
        "doctrine": "military_first_sda",
        "compare": {
            "baseline": "IF trained on baseline+asset past windows (normality anchors)",
            "point": "latest WINDOW epochs per sat (includes today's inject)",
            "military_alert": "suspects with series outlier / change; pair elevates priority",
            "calibration": "baseline role scored but not threat-escalated",
            "relevance": (
                f"anomaly_score>={anomaly_threshold} OR "
                f"delta_score_1d>={delta_relevance} with elevated level"
            ),
            "prev_day_scores_loaded": len(prev_scores),
            "delta_relevance": delta_relevance,
        },
        "n_scored": len(alerts),
        "n_anomalies": sum(1 for a in alerts if a.get("is_anomaly")),
        "n_military_detections": sum(1 for a in alerts if a.get("is_military_detection")),
        "n_platform_health_flags": sum(1 for a in alerts if a.get("is_platform_health_flag")),
        "n_series_outliers": sum(1 for a in alerts if a.get("series_outlier")),
        "n_day_over_day_relevant": sum(1 for a in alerts if a.get("day_over_day_relevant")),
        "n_unreliable": sum(1 for a in alerts if a.get("status") == "UNRELIABLE_DATA"),
        "threshold": thr_global,
        "threshold_cli_default": anomaly_threshold,
        "calibration": calibration,
        "model": str(IFOREST_MONITOR_PATH if IFOREST_MONITOR_PATH.exists() else MODELS_DIR / "isolation_forest.joblib"),
        "train_meta": mon_meta,
        "doctrine_summary": doctrine_summary(),
        "alerts": alerts,
    }

    # Pair layer (suspect x asset) + unified risk report
    pair_report = None
    if with_pairs:
        try:
            from src.pair_score import (
                build_risk_report,
                merge_pairs_into_alerts,
                score_all_pairs,
            )

            print("Scoring suspect x asset pairs...")
            pair_report = score_all_pairs()
            report = merge_pairs_into_alerts(report, pair_report)
            risk = build_risk_report(report, pair_report)
            print(
                f"Pairs: {pair_report.get('n_pairs_scored')} scored, "
                f"elevated={pair_report.get('n_elevated')} -> risk_report_latest.json"
            )
            print(f"Risk report day={risk.get('day')} board={len(risk.get('board') or [])}")
        except Exception as e:
            print(f"Pair scoring skipped/failed: {e}")

    out_path = ALERTS_DIR / f"anomalies_{day}.json"
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    # also latest pointer
    (ALERTS_DIR / "anomalies_latest.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # flat CSV for easy view
    flat = []
    for a in alerts:
        pair = a.get("pair") or {}
        flat.append(
            {
                "norad_id": a.get("norad_id"),
                "object_name": a.get("object_name"),
                "role": a.get("role"),
                "status": a.get("status"),
                "anomaly_score": a.get("anomaly_score"),
                "score_prev_day": a.get("score_prev_day"),
                "score_delta_1d": a.get("score_delta_1d"),
                "series_outlier": a.get("series_outlier"),
                "day_over_day_relevant": a.get("day_over_day_relevant"),
                "attention_score": a.get("attention_score"),
                "is_anomaly": a.get("is_anomaly"),
                "dq_score": (a.get("data_quality") or {}).get("score"),
                "window_end": a.get("window_end"),
                "xgb_class": a.get("xgb_class"),
                "pair_asset": pair.get("asset_norad"),
                "pair_risk": pair.get("pair_risk"),
                "pair_dist_km": pair.get("min_distance_km"),
            }
        )
    pd.DataFrame(flat).to_csv(ALERTS_DIR / f"anomalies_{day}.csv", index=False)

    print(
        f"Scored {report['n_scored']} sats -> anomalies={report['n_anomalies']} "
        f"(series_outliers={report.get('n_series_outliers')} "
        f"delta_1d_relevant={report.get('n_day_over_day_relevant')}) "
        f"unreliable={report['n_unreliable']}"
    )
    print(f"Report: {out_path}")
    return report
