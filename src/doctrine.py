"""
Military-first SDA doctrine for Athena-SDA (Palantir-inspired DAG roles).

Watchlist roles (data/catalog/watchlist.json):
  - baseline  → normality anchors for Isolation Forest ("quiet orbit")
  - asset     → high-value platforms to protect (priority when threatened)
  - suspect   → platforms of military interest (recon / SIGINT / dual-use)

Detection layer (quant + IF):
  Train IF on baseline (+ assets as secondary quiet anchors).
  Score everyone for calibration; **military alerts** focus on suspects
  (and elevated pair risk suspect→asset). Baseline is not a threat narrative.

Priority layer (XGB / fuzzy / Kelly / pairs):
  Ranks operator attention; does not redefine ground truth of intent.

Globe tracks (Starlink, decorative GPS, etc.) may appear in the UI only —
they are not the training objective.
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Sequence, Set

# --- Role policy -------------------------------------------------------------

# IF learns "normal orbital behavior" from these roles
IF_TRAIN_ROLES: frozenset = frozenset({"baseline", "asset"})

# Primary military detection / alert narrative
IF_ALERT_ROLES: frozenset = frozenset({"suspect"})

# Also surface platform health on protected assets (not "hostile")
IF_PLATFORM_HEALTH_ROLES: frozenset = frozenset({"asset"})

# Never treat as threat-class anomaly in the board narrative
IF_CALIBRATION_ONLY_ROLES: frozenset = frozenset({"baseline"})


def role_of(norad_id: int) -> str:
    try:
        from src.catalog import get_meta

        return str(get_meta(int(norad_id)).get("role") or "unknown")
    except Exception:
        return "unknown"


def ids_for_if_training(
    available: Optional[Sequence[int]] = None,
    *,
    min_ids: int = 4,
    exclude_commercial_constellations: bool = True,
) -> List[int]:
    """
    NORADs used to fit the Isolation Forest baseline (military doctrine).
    Prefer baseline + asset; drop commercial constellation anchors (e.g. Starlink)
    so station-keeping mega-constellations do not define "normal" for SDA suspects.
    """
    try:
        from src.catalog import asset_ids, baseline_ids, all_norad_ids, get_meta

        train_set = set(baseline_ids()) | set(asset_ids())
        if exclude_commercial_constellations:
            cleaned = set()
            for nid in train_set:
                meta = get_meta(int(nid))
                purpose = str(meta.get("purpose") or "").lower()
                name = str(meta.get("name") or "").upper()
                if purpose == "commercial" or "STARLINK" in name:
                    continue
                cleaned.add(int(nid))
            if len(cleaned) >= min_ids:
                train_set = cleaned
        if available is not None:
            avail = set(int(x) for x in available)
            train_set &= avail
        ids = sorted(train_set)
        if len(ids) >= min_ids:
            return ids
        if available is not None:
            return sorted(set(int(x) for x in available))
        return sorted(all_norad_ids())
    except Exception:
        if available is not None:
            return sorted(set(int(x) for x in available))
        return []


def is_alert_role(role: str) -> bool:
    return str(role or "").lower() in IF_ALERT_ROLES


def is_platform_health_role(role: str) -> bool:
    return str(role or "").lower() in IF_PLATFORM_HEALTH_ROLES


def is_calibration_role(role: str) -> bool:
    return str(role or "").lower() in IF_CALIBRATION_ONLY_ROLES


def military_alert_eligible(role: str) -> bool:
    """Suspects (detection) + assets (protect) can raise operational flags."""
    r = str(role or "").lower()
    return r in IF_ALERT_ROLES or r in IF_PLATFORM_HEALTH_ROLES


def classify_military_status(
    *,
    role: str,
    reliable: bool,
    series_outlier: bool,
    day_over_day_relevant: bool,
    pair_elevated: bool = False,
) -> Dict[str, Any]:
    """
    Map quant state → military board status without rewriting scores.

    Returns flags for risk board / anomalies JSON.
    """
    role = str(role or "unknown").lower()
    out: Dict[str, Any] = {
        "role": role,
        "military_alert_eligible": military_alert_eligible(role),
        "is_calibration_object": is_calibration_role(role),
        "is_military_detection": False,
        "is_platform_health_flag": False,
        "is_anomaly": False,
        "status": "NOMINAL",
        "doctrine_note": (
            "baseline=IF normality anchor; suspect=detection; asset=protect/priority"
        ),
    }
    if not reliable:
        out["status"] = "UNRELIABLE_DATA"
        return out

    if is_calibration_role(role):
        # Score still computed; never escalates military anomaly narrative
        out["status"] = "CALIBRATION_BASELINE"
        out["is_anomaly"] = False
        return out

    noise = bool(series_outlier or day_over_day_relevant)
    if is_alert_role(role):
        if noise or pair_elevated:
            out["is_military_detection"] = True
            out["is_anomaly"] = True
            if pair_elevated and not series_outlier:
                out["status"] = "PAIR_ELEVATED"
            elif series_outlier:
                out["status"] = "ANOMALY"
            else:
                out["status"] = "CHANGE_RELEVANT"
        else:
            out["status"] = "NOMINAL"
        return out

    if is_platform_health_role(role):
        if noise:
            out["is_platform_health_flag"] = True
            out["is_anomaly"] = True  # attention on protected platform
            out["status"] = "ASSET_REGIME_NOISE"
        else:
            out["status"] = "NOMINAL"
        return out

    # unknown roles: score only
    if noise:
        out["status"] = "ANOMALY"
        out["is_anomaly"] = True
    return out


def doctrine_summary() -> Dict[str, Any]:
    try:
        from src.catalog import asset_ids, baseline_ids, suspect_ids, summary

        cat = summary()
    except Exception:
        cat = {}
        asset_ids = baseline_ids = suspect_ids = lambda: set()  # type: ignore
    return {
        "doctrine": "military_first_sda",
        "if_train_roles": sorted(IF_TRAIN_ROLES),
        "if_alert_roles": sorted(IF_ALERT_ROLES),
        "if_platform_health_roles": sorted(IF_PLATFORM_HEALTH_ROLES),
        "n_assets": len(asset_ids()),
        "n_suspects": len(suspect_ids()),
        "n_baselines": len(baseline_ids()),
        "catalog": cat,
        "architecture": {
            "data": "public TLE + GFZ space weather",
            "quant": "engine features (Hurst, Shannon, CUSUM, …)",
            "inference": "Isolation Forest past-only (normality)",
            "priority": "XGB weak labels + fuzzy + pair_risk + Kelly",
            "llm": "Bob explains; never rewrites quant scores",
            "ontology": "asset | suspect | baseline board roles",
        },
        "ui_note": (
            "Globe decorative tracks (e.g. commercial constellations) are not the ML objective; "
            "models train/score the military-first watchlist."
        ),
    }
