"""
Walk-forward validation for Athena-SDA (POST-TRAINING evaluation).

For each public event anchor:
  - expanding time folds
  - Isolation Forest trained ONLY on windows ending before fold time
  - score the target NORAD (and optional pair metrics) at the fold
  - metrics: Hit@event, lead-time, feature curves, placebo FPR

Does NOT retrain the production daily model unless asked.
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

from src.anomaly_monitor import WINDOW, build_feature_windows, data_quality_score
from src.config import IFOREST_COLUMNS, DATA_DIR, MODELS_DIR
from src.models import extract_satellite_features
from src.tle_store import ALERTS_DIR, DEFAULT_WATCHLIST, ensure_dirs, history_as_sat_histories, load_history

EVENTS_PATH = DATA_DIR / "catalog" / "events_walkforward.json"
WF_DIR = ALERTS_DIR / "walkforward"


def load_events(path: Optional[Path] = None) -> List[Dict[str, Any]]:
    p = path or EVENTS_PATH
    if not p.exists():
        raise FileNotFoundError(f"Events file missing: {p}")
    data = json.loads(p.read_text(encoding="utf-8"))
    return list(data.get("events") or [])


def _ts(s: str) -> pd.Timestamp:
    return pd.Timestamp(s, tz="UTC")


def _names() -> Dict[int, str]:
    try:
        from src.catalog import name_map

        return name_map()
    except Exception:
        return dict(DEFAULT_WATCHLIST)


def _score_window_if(
    iforest: IsolationForest,
    hist: pd.DataFrame,
    *,
    asof: pd.Timestamp,
) -> Dict[str, Any]:
    """Score last WINDOW ending at or before asof."""
    asof = pd.Timestamp(asof)
    if asof.tzinfo is None:
        asof = asof.tz_localize("UTC")
    else:
        asof = asof.tz_convert("UTC")
    h = hist[pd.to_datetime(hist["timestamp"], utc=True) <= asof].sort_values("timestamp")
    if len(h) < WINDOW:
        return {"ok": False, "reason": "insufficient_history", "anomaly_score": None}
    sub = h.iloc[-WINDOW:]
    # Critical: age vs asof (not wall-clock now) so 2015 windows aren't "11 years stale"
    dq = data_quality_score(h, reference_time=asof)
    try:
        feats = extract_satellite_features(
            sub,
            country="UNKNOWN",
            purpose="unknown",
            orbit_class="LEO" if float(sub["semi_major_axis_km"].iloc[-1]) < 8000 else "MEO",
            min_distance_to_military_km=500.0,
            reference_time=asof,
        )
    except Exception as e:
        return {"ok": False, "reason": f"feature_error:{e}", "anomaly_score": None}

    row = pd.DataFrame([{c: float(feats.get(c, 0.0)) for c in IFOREST_COLUMNS}])
    row = row.replace([np.inf, -np.inf], 0.0).fillna(0.0)
    try:
        raw = float(iforest.decision_function(row)[0])
    except Exception:
        raw = float(iforest.decision_function(row.values)[0])
    anomaly = float(np.clip(0.5 - raw, 0.0, 1.0))
    snap = {
        k: float(feats.get(k, 0.0))
        for k in (
            "shannon_entropy_sma_30d",
            "shannon_entropy_sma_short",
            "hurst_exponent_sma",
            "hurst_exponent_sma_short",
            "persistence_hurst_gap",
            "kolmogorov_proxy_7d",
            "l1_cusum_sma",
            "mandelbrot_tail_score",
            "adf_pvalue",
            "delta_sma_7d_km",
            "maneuver_count_30d",
            "tle_age_hours",
            "f10_7",
            "ap_index",
            "kp_mean",
            "f10_7_delta_7d",
            "ap_delta_7d",
            "geomagnetic_storm",
            "space_weather_available",
        )
    }
    return {
        "ok": True,
        "anomaly_score": anomaly,
        "window_end": str(sub["timestamp"].iloc[-1]),
        "data_quality": dq,
        "features": snap,
    }


def _fit_if_asof(
    hists: Dict[int, pd.DataFrame],
    cutoff: pd.Timestamp,
    *,
    contamination: float = 0.06,
    names: Optional[Dict[int, str]] = None,
    military_doctrine: bool = True,
) -> Optional[IsolationForest]:
    """
    Fit IF on past windows only. Military doctrine: use baseline+asset NORADs
    as normality anchors when enough history exists.
    """
    train_hists = hists
    if military_doctrine:
        try:
            from src.doctrine import ids_for_if_training

            train_ids = set(ids_for_if_training(list(hists.keys()), min_ids=3))
            filtered = {k: v for k, v in hists.items() if int(k) in train_ids}
            if len(filtered) >= 3:
                train_hists = filtered
        except Exception:
            pass

    X, meta = build_feature_windows(
        train_hists,
        end_before=cutoff,
        step=3,
        max_windows_per_sat=40,
        names=names or {},
    )
    if len(X) < 20:
        X, meta = build_feature_windows(
            train_hists,
            end_before=cutoff,
            step=1,
            max_windows_per_sat=60,
            names=names or {},
        )
    # Fallback: all sats if anchors too thin for this cutoff
    if len(X) < 15 and train_hists is not hists:
        X, meta = build_feature_windows(
            hists,
            end_before=cutoff,
            step=2,
            max_windows_per_sat=40,
            names=names or {},
        )
    if len(X) < 15:
        return None
    iforest = IsolationForest(
        n_estimators=120,
        contamination=contamination,
        random_state=42,
        n_jobs=-1,
    )
    iforest.fit(X)
    return iforest


def _pair_snapshot(
    suspect_hist: pd.DataFrame,
    asset_hist: pd.DataFrame,
    asof: pd.Timestamp,
) -> Dict[str, Any]:
    """Lightweight pair metrics at asof (no full pair grid)."""
    try:
        from src.pair_score import score_pair

        hs = suspect_hist[pd.to_datetime(suspect_hist["timestamp"], utc=True) <= asof]
        ha = asset_hist[pd.to_datetime(asset_hist["timestamp"], utc=True) <= asof]
        if len(hs) < WINDOW or len(ha) < WINDOW:
            return {"ok": False}
        rec = score_pair(0, 1, hs, ha)  # ids only cosmetic here
        return {
            "ok": True,
            "min_distance_km": rec.get("min_distance_km"),
            "cointegration_pvalue": rec.get("cointegration_pvalue"),
            "pair_risk": rec.get("pair_risk"),
            "risk_level": rec.get("risk_level"),
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


def run_event_walkforward(
    event: Dict[str, Any],
    *,
    hists: Optional[Dict[int, pd.DataFrame]] = None,
    step_days: int = 14,
    holdout_days: int = 3,
    anomaly_threshold: float = 0.55,
    hit_window_days: int = 45,
    contamination: float = 0.08,
    min_train_days: int = 60,
) -> Dict[str, Any]:
    """
    Expanding-window walk-forward for one event dict.
    """
    names = _names()
    if hists is None:
        hists = history_as_sat_histories(min_epochs=WINDOW)

    norads = [int(x) for x in (event.get("norad_ids") or [])]
    if not norads:
        return {"event_id": event.get("id"), "error": "no norad_ids"}

    t_start = _ts(event["t_start"])
    t_peak = _ts(event["t_peak"])
    t_end = _ts(event["t_end"])
    pair_with = [int(x) for x in (event.get("pair_with") or [])]

    # Folds from max(t_start, first_data+min_train) to t_end
    folds: List[Dict[str, Any]] = []
    # build fold dates
    fold_t = t_start
    while fold_t <= t_end:
        cutoff = fold_t - timedelta(days=holdout_days)
        # need enough past
        train_start_needed = cutoff - timedelta(days=min_train_days)
        # skip if history empty for target before fold
        results_by_norad = {}
        iforest = _fit_if_asof(hists, cutoff, contamination=contamination, names=names)
        if iforest is None:
            folds.append(
                {
                    "asof": str(fold_t.date()),
                    "cutoff": str(cutoff.date()),
                    "error": "insufficient_train_windows",
                }
            )
            fold_t = fold_t + timedelta(days=step_days)
            continue

        try:
            from src.catalog import asset_ids as _asset_ids

            default_assets = [a for a in _asset_ids() if a in hists]
        except Exception:
            default_assets = []

        for nid in norads:
            if nid not in hists:
                results_by_norad[str(nid)] = {"ok": False, "reason": "not_in_history"}
                continue
            sc = _score_window_if(iforest, hists[nid], asof=fold_t)
            sc["norad_id"] = nid
            sc["object_name"] = names.get(nid, str(nid))
            sc["is_hit"] = bool(
                sc.get("ok")
                and sc.get("anomaly_score") is not None
                and float(sc["anomaly_score"]) >= anomaly_threshold
                and (sc.get("data_quality") or {}).get("reliable", True)
            )
            # Pair noise: explicit pair_with or best among assets
            pair_targets = list(pair_with) if pair_with else default_assets[:4]
            best_pair = None
            for aid in pair_targets:
                if aid == nid or aid not in hists:
                    continue
                pr = _pair_snapshot(hists[nid], hists[aid], fold_t)
                if not pr.get("ok"):
                    continue
                if best_pair is None or float(pr.get("pair_risk") or 0) > float(
                    best_pair.get("pair_risk") or 0
                ):
                    pr = dict(pr)
                    pr["asset_norad"] = aid
                    pr["asset_name"] = names.get(aid, str(aid))
                    best_pair = pr
            if best_pair:
                sc["pair"] = best_pair
                an = float(sc.get("anomaly_score") or 0)
                prisk = float(best_pair.get("pair_risk") or 0)
                sc["attention_score"] = float(np.clip(0.45 * an + 0.55 * prisk, 0, 1))
            results_by_norad[str(nid)] = sc

        folds.append(
            {
                "asof": str(fold_t.date()),
                "cutoff": str(cutoff.date()),
                "n_train_ok": True,
                "targets": results_by_norad,
            }
        )
        fold_t = fold_t + timedelta(days=step_days)

    # Metrics per target
    metrics = {}
    for nid in norads:
        series = []
        for f in folds:
            t = f.get("targets") or {}
            r = t.get(str(nid)) or {}
            if not r.get("ok"):
                continue
            series.append(
                {
                    "asof": f["asof"],
                    "anomaly_score": r.get("anomaly_score"),
                    "is_hit": r.get("is_hit"),
                    "features": r.get("features"),
                    "pair": r.get("pair"),
                }
            )

        scores = [float(s["anomaly_score"]) for s in series if s.get("anomaly_score") is not None]
        peak = t_peak
        hit_lo = peak - timedelta(days=hit_window_days)
        hit_hi = peak + timedelta(days=hit_window_days)

        hits_in_window = []
        first_hit_before_peak = None
        first_hit_asof = None
        for s in series:
            asof = _ts(s["asof"])
            if s.get("is_hit") and hit_lo <= asof <= hit_hi:
                hits_in_window.append(s)
            if s.get("is_hit") and asof <= peak and first_hit_before_peak is None:
                first_hit_before_peak = asof
                first_hit_asof = asof

        # Soft hit: score above train-ish elevated (0.45) in window
        soft_hits = [
            s
            for s in series
            if s.get("anomaly_score") is not None
            and float(s["anomaly_score"]) >= max(0.45, anomaly_threshold - 0.1)
            and hit_lo <= _ts(s["asof"]) <= hit_hi
        ]

        # First scorable fold in the event window (for first_fold_hit honesty)
        first_scorable_asof = _ts(series[0]["asof"]) if series else None
        first_fold_hit = bool(
            first_hit_asof is not None
            and first_scorable_asof is not None
            and first_hit_asof == first_scorable_asof
        )
        pre_peak_series = [s for s in series if _ts(s["asof"]) < peak]
        n_folds_above_thr_pre_peak = sum(
            1
            for s in pre_peak_series
            if s.get("anomaly_score") is not None
            and float(s["anomaly_score"]) >= anomaly_threshold
        )

        # lead_time_days = days from first thr cross in window to t_peak.
        # When first_fold_hit, this is "already elevated at window open", not onset detection.
        lead_days = None
        if first_hit_before_peak is not None:
            lead_days = float((peak - first_hit_before_peak).total_seconds() / 86400.0)

        # Feature means in pre-peak vs early train-ish
        feat_keys = [
            "shannon_entropy_sma_30d",
            "shannon_entropy_sma_short",
            "hurst_exponent_sma",
            "hurst_exponent_sma_short",
            "persistence_hurst_gap",
            "l1_cusum_sma",
            "kolmogorov_proxy_7d",
        ]
        pre = [s for s in series if _ts(s["asof"]) <= peak]
        early = pre[: max(1, len(pre) // 3)] if pre else []
        late = pre[-max(1, len(pre) // 3) :] if pre else []

        def _feat_mean(rows: List[Dict], key: str) -> Optional[float]:
            vals = []
            for r in rows:
                f = r.get("features") or {}
                if key in f:
                    vals.append(float(f[key]))
            return float(np.mean(vals)) if vals else None

        feat_delta = {
            k: {
                "early_mean": _feat_mean(early, k),
                "late_mean": _feat_mean(late, k),
            }
            for k in feat_keys
        }

        # Pair risk peak
        pair_risks = []
        for s in series:
            pr = (s.get("pair") or {})
            if pr.get("ok") and pr.get("pair_risk") is not None:
                pair_risks.append(float(pr["pair_risk"]))

        # --- Pre-peak noise analysis (core of walk-forward philosophy) ---
        pre_peak = [s for s in series if _ts(s["asof"]) < peak]
        pre_scores = [float(s["anomaly_score"]) for s in pre_peak if s.get("anomaly_score") is not None]
        pre_third = max(1, len(pre_peak) // 3)
        early_pre = pre_peak[:pre_third]
        late_pre = pre_peak[-pre_third:] if pre_peak else []
        early_s = [float(s["anomaly_score"]) for s in early_pre if s.get("anomaly_score") is not None]
        late_s = [float(s["anomaly_score"]) for s in late_pre if s.get("anomaly_score") is not None]
        pre_pair = [
            float((s.get("pair") or {}).get("pair_risk"))
            for s in pre_peak
            if (s.get("pair") or {}).get("ok") and (s.get("pair") or {}).get("pair_risk") is not None
        ]

        pre_peak_noise = {
            "description": (
                "Scores computed ONLY with models trained on data strictly before each fold "
                "(no peeking past asof). Compares early vs late noise before public t_peak."
            ),
            "n_pre_peak_folds": len(pre_peak),
            "pre_peak_anomaly_mean": float(np.mean(pre_scores)) if pre_scores else None,
            "pre_peak_anomaly_max": float(np.max(pre_scores)) if pre_scores else None,
            "early_pre_peak_mean": float(np.mean(early_s)) if early_s else None,
            "late_pre_peak_mean": float(np.mean(late_s)) if late_s else None,
            "noise_ramp": (
                float(np.mean(late_s) - np.mean(early_s))
                if early_s and late_s
                else None
            ),
            "pre_peak_pair_risk_max": float(np.max(pre_pair)) if pre_pair else None,
            "elevated_noise_before_peak": bool(
                (late_s and float(np.mean(late_s)) >= max(0.42, anomaly_threshold - 0.12))
                or (pre_scores and float(np.max(pre_scores)) >= anomaly_threshold)
            ),
        }

        metrics[str(nid)] = {
            "norad_id": nid,
            "object_name": names.get(nid, str(nid)),
            "n_folds_scored": len(series),
            "anomaly_score_mean": float(np.mean(scores)) if scores else None,
            "anomaly_score_max": float(np.max(scores)) if scores else None,
            "anomaly_score_at_nearest_peak": _nearest_score(series, t_peak),
            "hit_at_event": len(hits_in_window) > 0,
            "soft_hit_at_event": len(soft_hits) > 0,
            "n_hits_in_window": len(hits_in_window),
            "first_fold_hit": first_fold_hit,
            "first_hit_asof": str(first_hit_asof.date()) if first_hit_asof is not None else None,
            "first_scorable_asof": (
                str(first_scorable_asof.date()) if first_scorable_asof is not None else None
            ),
            "n_folds_above_thr_pre_peak": int(n_folds_above_thr_pre_peak),
            "lead_time_days": lead_days,
            "lead_time_note": (
                "already_elevated_at_window_open"
                if first_fold_hit
                else ("days_from_first_thr_cross_to_t_peak" if lead_days is not None else None)
            ),
            "feature_early_vs_late": feat_delta,
            "pair_risk_max": float(np.max(pair_risks)) if pair_risks else None,
            "pre_peak_noise": pre_peak_noise,
            "is_placebo": str(event.get("type", "")).startswith("placebo"),
        }

    return {
        "event_id": event.get("id"),
        "type": event.get("type"),
        "methodology": (
            "Walk-forward expanding window: at each asof, Isolation Forest is fit only on "
            "feature windows with window_end < asof-holdout (past-only). Target is scored at asof. "
            "Public report anchors (t_peak) are CASE STUDIES to read how quant noise features "
            "(Hurst, Shannon, CUSUM, IF score) behave — not prediction targets. "
            "Primary claim: continuous normality-vs-deviation monitoring. "
            "first_fold_hit=true means elevated from first scorable fold (regime level), "
            "not necessarily a rising ramp into t_peak. Not a classified ground-truth claim."
        ),
        "t_start": event.get("t_start"),
        "t_peak": event.get("t_peak"),
        "t_end": event.get("t_end"),
        "norad_ids": norads,
        "pair_with": pair_with,
        "sources": event.get("sources"),
        "notes": event.get("notes"),
        "params": {
            "step_days": step_days,
            "holdout_days": holdout_days,
            "anomaly_threshold": anomaly_threshold,
            "hit_window_days": hit_window_days,
            "contamination": contamination,
        },
        "n_folds": len(folds),
        "folds": folds,
        "metrics": metrics,
    }


def _nearest_score(series: List[Dict], peak: pd.Timestamp) -> Optional[float]:
    if not series:
        return None
    best = None
    best_dt = None
    for s in series:
        if s.get("anomaly_score") is None:
            continue
        dt = abs((_ts(s["asof"]) - peak).total_seconds())
        if best_dt is None or dt < best_dt:
            best_dt = dt
            best = float(s["anomaly_score"])
    return best


def run_all_walkforward(
    *,
    event_ids: Optional[Sequence[str]] = None,
    step_days: int = 14,
    holdout_days: int = 3,
    anomaly_threshold: float = 0.55,
    hit_window_days: int = 45,
) -> Dict[str, Any]:
    ensure_dirs()
    WF_DIR.mkdir(parents=True, exist_ok=True)

    events = load_events()
    if event_ids:
        want = set(event_ids)
        events = [e for e in events if e.get("id") in want]

    print(f"Walk-forward: {len(events)} events, step={step_days}d thr={anomaly_threshold}")
    hists = history_as_sat_histories(min_epochs=WINDOW)
    if not hists:
        raise RuntimeError("Insufficient history. Run seed-history before walk-forward.")

    results = []
    for ev in events:
        print(f"\n=== event {ev.get('id')} ===")
        rep = run_event_walkforward(
            ev,
            hists=hists,
            step_days=step_days,
            holdout_days=holdout_days,
            anomaly_threshold=anomaly_threshold,
            hit_window_days=hit_window_days,
        )
        results.append(rep)
        # per-event file
        eid = ev.get("id", "event")
        path = WF_DIR / f"wf_{eid}.json"
        # lighter save: drop heavy folds features optional — keep folds for audit
        path.write_text(json.dumps(rep, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
        print(f"  saved {path}")
        for nid, m in (rep.get("metrics") or {}).items():
            print(
                f"  #{nid} hit={m.get('hit_at_event')} soft={m.get('soft_hit_at_event')} "
                f"lead={m.get('lead_time_days')} max_anom={m.get('anomaly_score_max')} "
                f"placebo={m.get('is_placebo')}"
            )

    summary = _summarize(results, anomaly_threshold=anomaly_threshold)
    out = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "n_events": len(results),
        "params": {
            "step_days": step_days,
            "holdout_days": holdout_days,
            "anomaly_threshold": anomaly_threshold,
            "hit_window_days": hit_window_days,
        },
        "summary": summary,
        "events": results,
    }
    latest = WF_DIR / "walkforward_latest.json"
    # compact latest: metrics only + summary (full events on disk per file)
    compact = {
        "generated_at": out["generated_at"],
        "params": out["params"],
        "summary": summary,
        "events": [
            {
                "event_id": r.get("event_id"),
                "type": r.get("type"),
                "t_peak": r.get("t_peak"),
                "metrics": r.get("metrics"),
                "n_folds": r.get("n_folds"),
                "sources": r.get("sources"),
            }
            for r in results
        ],
    }
    latest.write_text(json.dumps(compact, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    (ALERTS_DIR / "walkforward_summary.json").write_text(
        json.dumps(compact, indent=2, ensure_ascii=False, default=str), encoding="utf-8"
    )
    print(f"\nSummary → {latest}")
    return out


def _summarize(results: List[Dict[str, Any]], anomaly_threshold: float) -> Dict[str, Any]:
    interest = []
    placebo = []
    for r in results:
        for m in (r.get("metrics") or {}).values():
            row = {**m, "event_id": r.get("event_id"), "type": r.get("type")}
            if m.get("is_placebo"):
                placebo.append(row)
            else:
                interest.append(row)

    def rate(rows: List[Dict], key: str) -> Optional[float]:
        if not rows:
            return None
        return float(np.mean([1.0 if x.get(key) else 0.0 for x in rows]))

    leads = [x["lead_time_days"] for x in interest if x.get("lead_time_days") is not None]
    noise_ramp_i = [
        (x.get("pre_peak_noise") or {}).get("noise_ramp")
        for x in interest
        if (x.get("pre_peak_noise") or {}).get("noise_ramp") is not None
    ]
    noise_ramp_p = [
        (x.get("pre_peak_noise") or {}).get("noise_ramp")
        for x in placebo
        if (x.get("pre_peak_noise") or {}).get("noise_ramp") is not None
    ]
    pre_mean_i = [
        (x.get("pre_peak_noise") or {}).get("pre_peak_anomaly_mean")
        for x in interest
        if (x.get("pre_peak_noise") or {}).get("pre_peak_anomaly_mean") is not None
    ]
    pre_mean_p = [
        (x.get("pre_peak_noise") or {}).get("pre_peak_anomaly_mean")
        for x in placebo
        if (x.get("pre_peak_noise") or {}).get("pre_peak_anomaly_mean") is not None
    ]
    elev_pre_i = float(
        np.mean(
            [
                1.0 if (x.get("pre_peak_noise") or {}).get("elevated_noise_before_peak") else 0.0
                for x in interest
            ]
        )
    ) if interest else None
    elev_pre_p = float(
        np.mean(
            [
                1.0 if (x.get("pre_peak_noise") or {}).get("elevated_noise_before_peak") else 0.0
                for x in placebo
            ]
        )
    ) if placebo else None
    first_fold_rate = rate(interest, "first_fold_hit")
    max_i = [x["anomaly_score_max"] for x in interest if x.get("anomaly_score_max") is not None]
    max_p = [x["anomaly_score_max"] for x in placebo if x.get("anomaly_score_max") is not None]
    p95_placebo = float(np.percentile(max_p, 95)) if max_p else None

    n_unique_interest = len({int(x["norad_id"]) for x in interest if x.get("norad_id") is not None})
    n_unique_placebo = len({int(x["norad_id"]) for x in placebo if x.get("norad_id") is not None})

    geo_ids = {
        "luch1_intelsat_2015",
        "luch1_intelsat_mid2015",
        "luch1_athena_fidus_2018",
        "sy12_geo_rpo_2021_22",
        "luch2_trailing_2023",
    }
    civil_eo_placebo = {
        "placebo_terra_2015",
        "placebo_terra_2018",
        "placebo_aqua_2015",
        "placebo_landsat8_2018",
        "placebo_noaa20_2023",
        "placebo_noaa18_2021",
        "placebo_aqua_2020",
    }
    geo_i = [x for x in interest if x.get("event_id") in geo_ids]
    eo_p = [x for x in placebo if x.get("event_id") in civil_eo_placebo]
    max_geo = [x["anomaly_score_max"] for x in geo_i if x.get("anomaly_score_max") is not None]
    max_eo = [x["anomaly_score_max"] for x in eo_p if x.get("anomaly_score_max") is not None]

    def _mean(xs):
        return float(np.mean(xs)) if xs else None

    return {
        "n_interest_targets": len(interest),
        "n_placebo_targets": len(placebo),
        "n_unique_interest_norads": n_unique_interest,
        "n_unique_placebo_norads": n_unique_placebo,
        "hit_rate_interest": rate(interest, "hit_at_event"),
        "soft_hit_rate_interest": rate(interest, "soft_hit_at_event"),
        "hit_rate_placebo": rate(placebo, "hit_at_event"),
        "soft_hit_rate_placebo": rate(placebo, "soft_hit_at_event"),
        "first_fold_hit_rate_interest": first_fold_rate,
        "elevated_pre_peak_noise_rate_interest": elev_pre_i,
        "elevated_pre_peak_noise_rate_placebo": elev_pre_p,
        "mean_noise_ramp_interest": float(np.mean(noise_ramp_i)) if noise_ramp_i else None,
        "mean_noise_ramp_placebo": float(np.mean(noise_ramp_p)) if noise_ramp_p else None,
        "mean_pre_peak_anomaly_interest": float(np.mean(pre_mean_i)) if pre_mean_i else None,
        "mean_pre_peak_anomaly_placebo": float(np.mean(pre_mean_p)) if pre_mean_p else None,
        "mean_lead_time_days_interest": float(np.mean(leads)) if leads else None,
        "median_lead_time_days_interest": float(np.median(leads)) if leads else None,
        "mean_max_anomaly_interest": float(np.mean(max_i)) if max_i else None,
        "mean_max_anomaly_placebo": float(np.mean(max_p)) if max_p else None,
        "p95_max_anomaly_placebo": p95_placebo,
        "subgroup_geo_interest_vs_civil_eo_placebo": {
            "n_geo_interest": len(geo_i),
            "n_civil_eo_placebo": len(eo_p),
            "hit_rate_geo_interest": rate(geo_i, "hit_at_event"),
            "hit_rate_civil_eo_placebo": rate(eo_p, "hit_at_event"),
            "mean_max_geo_interest": _mean(max_geo),
            "mean_max_civil_eo_placebo": _mean(max_eo),
            "p95_max_civil_eo_placebo": float(np.percentile(max_eo, 95)) if max_eo else None,
            "note": (
                "Starlink/GPS placebos can hard-hit (station-keeping). "
                "Civil EO placebos are quieter controls for the GEO Luch/SY-12 narrative."
            ),
        },
        "anomaly_threshold": anomaly_threshold,
        "interpretation": (
            "Past-only IF at each asof. Public t_peak anchors are case studies — not forecast targets. "
            "Full panel includes active-constellation placebos (may hard-hit). "
            "Use subgroup_geo_interest_vs_civil_eo_placebo for civil EO controls. "
            "first_fold_hit + noise_ramp~0 => persistent elevated level, not ramp onset. "
            "XGB accuracy is not used here."
        ),
    }
