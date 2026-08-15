"""
Pair scoring: suspect × protected asset.

Military narrative layer (shadowing / RPO proxy):
  - approximate orbital proximity (geometry)
  - cointegration of aligned SMA series (temporal coupling, Engle-Granger)
  - DCCA cross-correlation (Podobnik & Stanley 2008) + persistence coherence
  - evidential-style coherence: cointegrated AND persistent = shadowing-like

Outputs JSON under data/alerts/ for merge into daily risk report.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

from src.engine import (
    calculate_cointegration_pvalue,
    calculate_dcca_rho,
    calculate_dfa_hurst,
)
from src.orbital import min_distance_to_assets, orbit_class_from_sma
from src.tle_store import ALERTS_DIR, DEFAULT_WATCHLIST, ensure_dirs, history_as_sat_histories


def _catalog_roles() -> Tuple[List[int], List[int], Dict[int, Dict[str, Any]]]:
    try:
        from src.catalog import asset_ids, get_meta, suspect_ids

        assets = sorted(asset_ids())
        suspects = sorted(suspect_ids())
        meta = {}
        for nid in set(assets) | set(suspects):
            meta[nid] = get_meta(nid)
        return assets, suspects, meta
    except Exception:
        # fallback: treat DEFAULT_WATCHLIST keys without roles as mixed
        ids = list(DEFAULT_WATCHLIST.keys())
        meta = {
            i: {
                "norad_id": i,
                "name": DEFAULT_WATCHLIST.get(i, str(i)),
                "role": "unknown",
                "country": "UNKNOWN",
                "purpose": "unknown",
            }
            for i in ids
        }
        return ids[: max(1, len(ids) // 3)], ids, meta


def _align_series(
    a: pd.DataFrame,
    b: pd.DataFrame,
    col: str = "semi_major_axis_km",
    max_points: int = 120,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Align two epoch series by timestamp (merge_asof ±12h) then take last max_points.
    Prevents Engle-Granger on misaligned calendar epochs.
    """
    if a is None or b is None or len(a) == 0 or len(b) == 0:
        return np.array([]), np.array([])
    if col not in a.columns or col not in b.columns or "timestamp" not in a.columns:
        return np.array([]), np.array([])

    a_sorted = a[["timestamp", col]].copy()
    b_sorted = b[["timestamp", col]].copy()
    a_sorted["timestamp"] = pd.to_datetime(a_sorted["timestamp"], utc=True, errors="coerce")
    b_sorted["timestamp"] = pd.to_datetime(b_sorted["timestamp"], utc=True, errors="coerce")
    a_sorted = a_sorted.dropna(subset=["timestamp", col]).sort_values("timestamp").tail(max_points * 2)
    b_sorted = b_sorted.dropna(subset=["timestamp", col]).sort_values("timestamp").tail(max_points * 2)

    if len(a_sorted) == 0 or len(b_sorted) == 0:
        return np.array([]), np.array([])

    # rename value cols before merge so suffixes are unambiguous
    a_sorted = a_sorted.rename(columns={col: f"{col}_a"})
    b_sorted = b_sorted.rename(columns={col: f"{col}_b"})

    merged = pd.merge_asof(
        a_sorted,
        b_sorted,
        on="timestamp",
        direction="nearest",
        tolerance=pd.Timedelta("12h"),
    ).dropna(subset=[f"{col}_a", f"{col}_b"])

    sa = merged[f"{col}_a"].astype(float).values
    sb = merged[f"{col}_b"].astype(float).values

    n = min(len(sa), len(sb), max_points)
    if n < 20:
        return sa[-n:] if n else sa, sb[-n:] if n else sb
    return sa[-n:], sb[-n:]


def score_pair(
    suspect_id: int,
    asset_id: int,
    hist_s: pd.DataFrame,
    hist_a: pd.DataFrame,
    *,
    names: Optional[Dict[int, str]] = None,
    meta_s: Optional[Dict[str, Any]] = None,
    meta_a: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Score one suspect–asset pair."""
    names = names or {}
    meta_s = meta_s or {}
    meta_a = meta_a or {}

    dist_km, _ = min_distance_to_assets(hist_s, {asset_id: hist_a}, cap_km=2000.0)

    sa, aa = _align_series(hist_s, hist_a)
    coint_p = calculate_cointegration_pvalue(sa, aa) if len(sa) >= 20 and len(aa) >= 20 else 1.0
    # DCCA coupling coefficient on aligned series (Podobnik & Stanley 2008)
    dcca = calculate_dcca_rho(sa, aa) if len(sa) >= 12 and len(aa) >= 12 else 0.0

    # Persistence of the suspect (DFA on drag-detrended SMA)
    try:
        dfa = float(calculate_dfa_hurst(hist_s["semi_major_axis_km"].astype(float).values))
    except Exception:
        dfa = 0.5
    p_coint = 1.0 if coint_p < 0.05 else 0.0
    q_persist = 1.0 if dfa > 0.65 else 0.0
    # Evidential-style coherence: cointegrated AND persistent = shadowing-like
    coherence = float(min(p_coint, q_persist))

    # Geometric closeness score (0 far → 1 very close)
    # 0 km → 1.0; 500 km → ~0.37; 2000+ → ~0
    prox_score = float(np.exp(-float(dist_km) / 400.0))
    # Cointegration strength: lower p → higher score
    coint_score = float(np.clip(1.0 - coint_p, 0.0, 1.0))
    if coint_p < 0.05:
        coint_score = float(np.clip(coint_score + 0.25, 0.0, 1.0))

    # Combined pair risk (geometry + temporal coupling + DCCA cross-correlation)
    pair_risk = float(np.clip(0.50 * prox_score + 0.30 * coint_score + 0.10 * max(dcca, 0.0) + 0.10 * coherence, 0.0, 1.0))
    # Boost if both close and cointegrated
    if dist_km < 150 and coint_p < 0.1:
        pair_risk = float(np.clip(pair_risk + 0.15, 0.0, 1.0))
    if dist_km < 50 and coint_p < 0.05:
        pair_risk = float(np.clip(pair_risk + 0.1, 0.0, 1.0))

    # CRITICAL only if geometry is tight AND temporal coupling supports (avoids
    # pure SSO false-friends from the coarse Kepler distance proxy).
    if pair_risk >= 0.75 and dist_km < 100 and coint_p < 0.10:
        level = "CRITICAL"
    elif pair_risk >= 0.55 or (dist_km < 120 and coint_p < 0.15):
        level = "ELEVATED"
    elif pair_risk >= 0.35 or dist_km < 250:
        level = "WATCH"
    else:
        level = "LOW"

    last_s = hist_s.iloc[-1]
    last_a = hist_a.iloc[-1]
    rec = {
        "suspect_norad": int(suspect_id),
        "suspect_name": names.get(suspect_id) or meta_s.get("name") or str(suspect_id),
        "suspect_country": meta_s.get("country", "UNKNOWN"),
        "suspect_purpose": meta_s.get("purpose", "unknown"),
        "asset_norad": int(asset_id),
        "asset_name": names.get(asset_id) or meta_a.get("name") or str(asset_id),
        "asset_country": meta_a.get("country", "UNKNOWN"),
        "min_distance_km": round(float(dist_km), 3),
        "cointegration_pvalue": round(float(coint_p), 6),
        "dfa_suspect": round(float(dfa), 4),
        "dcca_rho": round(float(dcca), 4),
        "coherence": round(coherence, 4),
        "proximity_score": round(prox_score, 4),
        "coint_score": round(coint_score, 4),
        "pair_risk": round(pair_risk, 4),
        "risk_level": level,
        "n_epochs_aligned": int(min(len(sa), len(aa))),
        "suspect_orbit": orbit_class_from_sma(float(last_s["semi_major_axis_km"])),
        "asset_orbit": orbit_class_from_sma(float(last_a["semi_major_axis_km"])),
        "suspect_window_end": str(last_s.get("timestamp", "")),
        "asset_window_end": str(last_a.get("timestamp", "")),
    }
    # Extra fields only — pair_risk stays the geometry+coint formula above.
    try:
        from src.conjunction import attach_conjunction, estimate_conjunction

        rec = attach_conjunction(rec, estimate_conjunction(hist_s, hist_a))
    except Exception:
        rec.setdefault("pc", None)
        rec.setdefault("tca_utc", None)
    return rec


def score_all_pairs(
    *,
    suspect_ids: Optional[Sequence[int]] = None,
    asset_ids: Optional[Sequence[int]] = None,
    min_epochs: int = 20,
    top_k_per_suspect: int = 3,
    max_pairs: int = 80,
) -> Dict[str, Any]:
    """
    Score all suspect×asset pairs present in history with enough epochs.
    Keeps top_k closest/riskiest assets per suspect, capped at max_pairs total.
    """
    ensure_dirs()
    cat_assets, cat_suspects, meta = _catalog_roles()
    assets = list(asset_ids) if asset_ids is not None else cat_assets
    suspects = list(suspect_ids) if suspect_ids is not None else cat_suspects

    all_ids = list(set(assets) | set(suspects))
    hists = history_as_sat_histories(norad_ids=all_ids, min_epochs=min_epochs)
    # also try without min for assets if short
    if not hists:
        hists = history_as_sat_histories(min_epochs=min_epochs)

    names = {i: meta.get(i, {}).get("name") or DEFAULT_WATCHLIST.get(i, str(i)) for i in all_ids}

    asset_h = {i: hists[i] for i in assets if i in hists}
    suspect_h = {i: hists[i] for i in suspects if i in hists}

    pairs: List[Dict[str, Any]] = []
    for sid, hs in suspect_h.items():
        scored = []
        for aid, ha in asset_h.items():
            if aid == sid:
                continue
            try:
                rec = score_pair(
                    sid,
                    aid,
                    hs,
                    ha,
                    names=names,
                    meta_s=meta.get(sid),
                    meta_a=meta.get(aid),
                )
                scored.append(rec)
            except Exception as e:
                scored.append(
                    {
                        "suspect_norad": int(sid),
                        "asset_norad": int(aid),
                        "error": str(e),
                        "pair_risk": 0.0,
                        "risk_level": "ERROR",
                    }
                )
        scored.sort(key=lambda r: (-float(r.get("pair_risk", 0)), float(r.get("min_distance_km", 1e9))))
        pairs.extend(scored[:top_k_per_suspect])

    pairs.sort(key=lambda r: (-float(r.get("pair_risk", 0)), float(r.get("min_distance_km", 1e9))))
    pairs = pairs[:max_pairs]

    # Best pair per suspect (for merge into single-sat alerts)
    best_by_suspect: Dict[int, Dict[str, Any]] = {}
    for p in pairs:
        sid = int(p.get("suspect_norad", -1))
        if sid < 0 or p.get("error"):
            continue
        if sid not in best_by_suspect or float(p["pair_risk"]) > float(best_by_suspect[sid]["pair_risk"]):
            best_by_suspect[sid] = p

    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "day": day,
        "n_assets": len(asset_h),
        "n_suspects": len(suspect_h),
        "n_pairs_scored": len(pairs),
        "n_elevated": sum(1 for p in pairs if p.get("risk_level") in ("ELEVATED", "CRITICAL")),
        "pairs": pairs,
        "best_by_suspect": {str(k): v for k, v in best_by_suspect.items()},
        "notes": (
            "pair_risk is geometry + cointegration/DCCA (unchanged). "
            "pc / tca_utc / miss_distance_km / covariance are extra conjunction fields "
            "(SGP4 when installed, else Kepler-circular fallback)."
        ),
    }

    path = ALERTS_DIR / f"proximity_{day}.json"
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    (ALERTS_DIR / "proximity_latest.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # flat CSV
    flat_cols = [
        "suspect_norad",
        "suspect_name",
        "asset_norad",
        "asset_name",
        "min_distance_km",
        "cointegration_pvalue",
        "pair_risk",
        "risk_level",
    ]
    rows = [{c: p.get(c) for c in flat_cols} for p in pairs if not p.get("error")]
    if rows:
        pd.DataFrame(rows).to_csv(ALERTS_DIR / f"proximity_{day}.csv", index=False)

    return report


def merge_pairs_into_alerts(
    anomaly_report: Dict[str, Any],
    pair_report: Dict[str, Any],
) -> Dict[str, Any]:
    """Attach best pair info to each alert; bump is_anomaly if pair CRITICAL/ELEVATED + anomaly mid."""
    best = pair_report.get("best_by_suspect") or {}
    # keys may be str
    best_i = {int(k): v for k, v in best.items()}

    for a in anomaly_report.get("alerts") or []:
        nid = int(a.get("norad_id", -1))
        pair = best_i.get(nid)
        if not pair:
            # assets/baseline: surface if they appear as asset side in any high pair
            a["pair"] = None
            continue
        a["pair"] = {
            "asset_norad": pair.get("asset_norad"),
            "asset_name": pair.get("asset_name"),
            "min_distance_km": pair.get("min_distance_km"),
            "cointegration_pvalue": pair.get("cointegration_pvalue"),
            "pair_risk": pair.get("pair_risk"),
            "risk_level": pair.get("risk_level"),
            "pc": pair.get("pc"),
            "tca_utc": pair.get("tca_utc"),
            "miss_distance_km": pair.get("miss_distance_km"),
        }
        # Operational fuse: strong pair elevates military attention (suspects only)
        pr = float(pair.get("pair_risk") or 0)
        an = float(a.get("anomaly_score") or 0)
        role = str(a.get("role") or "").lower()
        if a.get("data_quality", {}).get("reliable", True):
            pair_hot = pair.get("risk_level") == "CRITICAL" or (
                pair.get("risk_level") == "ELEVATED" and pr >= 0.65 and an >= 0.35
            )
            if pair_hot and role == "suspect":
                a["is_anomaly"] = True
                a["is_military_detection"] = True
                if a.get("status") in (None, "NOMINAL", "CALIBRATION_BASELINE"):
                    a["status"] = "PAIR_ELEVATED"
            a["attention_score"] = round(float(np.clip(0.45 * an + 0.55 * pr, 0, 1)), 4)
        else:
            a["attention_score"] = an

    # Baselines: calibration scores only — never force anomaly via pairs
    for a in anomaly_report.get("alerts") or []:
        if str(a.get("role") or "").lower() == "baseline":
            a["is_anomaly"] = False
            a["is_military_detection"] = False
            if a.get("status") not in ("UNRELIABLE_DATA",):
                a["status"] = "CALIBRATION_BASELINE"
            if a.get("attention_score") is None:
                a["attention_score"] = float(a.get("anomaly_score") or 0) * 0.35

    # re-count
    anomaly_report["n_anomalies"] = sum(1 for a in anomaly_report.get("alerts") or [] if a.get("is_anomaly"))
    anomaly_report["n_military_detections"] = sum(
        1 for a in anomaly_report.get("alerts") or [] if a.get("is_military_detection")
    )
    anomaly_report["pairs_merged"] = True
    anomaly_report["n_pairs"] = pair_report.get("n_pairs_scored", 0)
    anomaly_report["n_pair_elevated"] = pair_report.get("n_elevated", 0)

    # sort: military detections, then attention
    anomaly_report["alerts"].sort(
        key=lambda x: (
            -int(bool(x.get("is_military_detection"))),
            -float(x.get("attention_score") or x.get("anomaly_score") or 0),
            -float(x.get("anomaly_score") or 0),
        )
    )
    return anomaly_report


def build_risk_report(
    anomaly_report: Dict[str, Any],
    pair_report: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Unified contract for UI / Bob (insight-first)."""
    from src.config import PURPOSE_SEVERITY
    from src.engine import calculate_kelly_allocation

    day = anomaly_report.get("day") or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    pairs = (pair_report or {}).get("pairs") or []
    top_pairs = pairs[:10]
    alerts = anomaly_report.get("alerts") or []

    board = []
    for a in alerts:
        # Kelly attention budget (patent 070 — Meta-Constellation tasking):
        # f* = (p*b - q)/b, half-Kelly damped; p = attention probability,
        # b = purpose severity multiplier (doctrine, config.PURPOSE_SEVERITY).
        p_kelly = float(a.get("attention_score") or a.get("anomaly_score") or 0.0)
        b_kelly = float(PURPOSE_SEVERITY.get(str(a.get("purpose") or "unknown").lower(), 25.0))
        kelly = calculate_kelly_allocation(p_kelly, b_kelly)
        board.append(
            {
                "norad_id": a.get("norad_id"),
                "object_name": a.get("object_name"),
                "role": a.get("role"),
                "country": a.get("country"),
                "purpose": a.get("purpose"),
                "orbit_class": a.get("orbit_class"),
                "anomaly_score": a.get("anomaly_score"),
                "attention_score": a.get("attention_score", a.get("anomaly_score")),
                "kelly_allocation": kelly,
                "is_anomaly": a.get("is_anomaly"),
                "is_military_detection": a.get("is_military_detection"),
                "is_platform_health_flag": a.get("is_platform_health_flag"),
                "is_calibration_object": a.get("is_calibration_object"),
                "status": a.get("status"),
                "xgb_class": a.get("xgb_class"),
                "data_quality": a.get("data_quality"),
                "evidence": a.get("evidence"),
                "features_snapshot": a.get("features_snapshot"),
                "pair": a.get("pair"),
                "anomaly_onset": a.get("anomaly_onset"),
                "window_end": a.get("window_end"),
                "score_delta_1d": a.get("score_delta_1d"),
            }
        )

    report = {
        "schema": "athena.risk_report.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "day": day,
        "doctrine": anomaly_report.get("doctrine") or "military_first_sda",
        "protocol": anomaly_report.get("protocol"),
        "summary": {
            "n_scored": anomaly_report.get("n_scored"),
            "n_anomalies": anomaly_report.get("n_anomalies"),
            "n_military_detections": anomaly_report.get("n_military_detections")
            or sum(1 for b in board if b.get("is_military_detection")),
            "n_platform_health_flags": sum(1 for b in board if b.get("is_platform_health_flag")),
            "n_pairs": (pair_report or {}).get("n_pairs_scored", 0),
            "n_pair_elevated": (pair_report or {}).get("n_elevated", 0),
            "threshold": anomaly_report.get("threshold"),
            "focus": "suspect detection + asset protect; baseline = IF normality only",
            "kelly_attention_budget": round(
                sum(float(b.get("kelly_allocation") or 0.0) for b in board), 4
            ),
        },
        "board": board,
        "top_pairs": top_pairs,
        "model": anomaly_report.get("model"),
        "train_meta": anomaly_report.get("train_meta"),
        "doctrine_summary": anomaly_report.get("doctrine_summary"),
    }

    ensure_dirs()
    (ALERTS_DIR / f"risk_report_{day}.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (ALERTS_DIR / "risk_report_latest.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    # HTML quant rationale (new tab) for every board entry
    try:
        from src.quant_report import write_all_quant_reports

        write_all_quant_reports(also_public=True)
    except Exception as e:
        print(f"Quant HTML reports skipped: {e}")
    return report
