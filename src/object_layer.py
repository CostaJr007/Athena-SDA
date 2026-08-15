"""
Gotham-lite object layer (OMS/OSS inspiration).

Does not recompute Isolation Forest / XGB scores. It *indexes* risk_report
rows + walk-forward cases into typed objects and links so the investigation
UI can search-around without joining CSVs.

Theory
------
- Foundry Object Set Service: apps query objects, not tables
  (https://www.palantir.com/docs/foundry/object-backend/overview/).
- US 12,374,011 B2: object map + category filters.
- US 12,657,514 B2: Open API contract for downstream consumers.
- Search-around: Gotham Graph expand-neighbors (same-asset suspects;
  same-t_peak placebos). Not conjunction geometry.

Hit rule (immutable): past-only IF hard hit at public t_peak. Pattern-of-life
≠ intent.
"""
from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.config import ALERTS_DIR, DATA_DIR
from src.contracts import validate_investigation
from src.logging_setup import get_logger
from src.ontology import load_ontology

logger = get_logger(__name__)

SCHEMA = "athena.investigation.v1"
HIT_RULE = "past-only Isolation Forest · hard hit iff score>=thr near public t_peak · Claims A+B"


def sat_id(norad: int) -> str:
    return f"sat:{int(norad)}"


def _pair_link_label(pair: Dict[str, Any]) -> str:
    name = pair.get("asset_name") or pair.get("asset_norad") or "asset"
    dist = pair.get("min_distance_km")
    bits = [str(name)]
    if dist is not None:
        bits.append(f"{dist} km")
    if pair.get("tca_utc"):
        bits.append(f"TCA {str(pair['tca_utc'])[11:16]}Z")
    if pair.get("pc") is not None:
        bits.append(f"Pc {pair['pc']}")
    return " · ".join(bits)


def _ot_category(name: str) -> str:
    ot = (load_ontology().get("objectTypes") or {}).get(name) or {}
    return str(ot.get("gothamCategory") or "Entity")


def _wf_events(summary: Dict[str, Any]) -> List[Dict[str, Any]]:
    return list(summary.get("events") or [])


def _cases_for_norad(summary: Dict[str, Any], norad: int) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for ev in _wf_events(summary):
        metrics = ev.get("metrics") or {}
        m = metrics.get(str(norad)) or {}
        if not m and isinstance(metrics, dict):
            for v in metrics.values():
                if isinstance(v, dict) and int(v.get("norad_id") or 0) == norad:
                    m = v
                    break
        if not m:
            continue
        out.append(
            {
                "event_id": ev.get("event_id"),
                "t_peak": ev.get("t_peak"),
                "type": ev.get("type"),
                "norad": norad,
                "hit": bool(m.get("hit_at_event")),
                "is_placebo": bool(m.get("is_placebo")),
                "lead_days": m.get("lead_time_days"),
                "max_score": m.get("anomaly_score_max"),
                "name": m.get("object_name"),
            }
        )
    return out


def _placebos_same_peak(summary: Dict[str, Any], event_ids: List[str]) -> List[Dict[str, Any]]:
    peaks = set()
    for ev in _wf_events(summary):
        if ev.get("event_id") in event_ids and ev.get("t_peak"):
            peaks.add(str(ev["t_peak"])[:10])
    out: List[Dict[str, Any]] = []
    for ev in _wf_events(summary):
        if str(ev.get("t_peak") or "")[:10] not in peaks:
            continue
        for m in (ev.get("metrics") or {}).values():
            if not isinstance(m, dict) or not m.get("is_placebo"):
                continue
            nid = m.get("norad_id")
            if nid is None:
                continue
            out.append(
                {
                    "event_id": ev.get("event_id"),
                    "t_peak": ev.get("t_peak"),
                    "norad": int(nid),
                    "name": m.get("object_name"),
                    "hit": bool(m.get("hit_at_event")),
                    "max_score": m.get("anomaly_score_max"),
                }
            )
    return out


def _peers_on_asset(
    report: Dict[str, Any], norad: int, pair_asset: Optional[int]
) -> List[Dict[str, Any]]:
    """Other suspects sharing the same protected asset (Graph search-around)."""
    asset = pair_asset
    if asset is None:
        # If this row is itself an asset, expand inbound threatens.
        board = {int(b["norad_id"]): b for b in report.get("board") or [] if "norad_id" in b}
        row = board.get(norad)
        if row and row.get("role") == "asset":
            asset = norad
    if asset is None:
        return []
    peers: List[Dict[str, Any]] = []
    seen = set()
    for p in report.get("top_pairs") or []:
        if int(p.get("asset_norad") or 0) != int(asset):
            continue
        sn = int(p.get("suspect_norad") or 0)
        if not sn or sn == norad or sn in seen:
            continue
        seen.add(sn)
        peers.append(
            {
                "norad": sn,
                "name": p.get("suspect_name") or f"#{sn}",
                "pair_risk": p.get("pair_risk"),
                "min_distance_km": p.get("min_distance_km"),
            }
        )
    return peers[:4]


def _model_provenance() -> Dict[str, Any]:
    """Attach model provenance (versions, schema hashes, trained_at) to the
    investigation bundle so every derived object is traceable to the exact
    artifacts that produced it (Foundry Data Lineage)."""
    prov: Dict[str, Any] = {"registry": None, "monitor_meta": None, "models": {}}
    reg_path = ALERTS_DIR.parent.parent / "models" / "registry.json"
    try:
        if reg_path.exists():
            reg = json.loads(reg_path.read_text(encoding="utf-8"))
            prov["registry"] = {
                "updated": reg.get("updated"),
                "version": reg.get("version"),
            }
            for name, meta in (reg.get("models") or {}).items():
                prov["models"][name] = {
                    "path": meta.get("path"),
                    "feature_schema_hash": meta.get("feature_schema_hash"),
                    "registered_at": meta.get("registered_at"),
                    "n_samples": meta.get("n_samples"),
                    "contamination": meta.get("contamination"),
                    "cutoff_utc": meta.get("cutoff_utc"),
                }
    except Exception as exc:
        logger.warning("model registry provenance skipped: %s", exc)

    meta_path = ALERTS_DIR.parent.parent / "models" / "anomaly_monitor_meta.json"
    try:
        if meta_path.exists():
            mm = json.loads(meta_path.read_text(encoding="utf-8"))
            prov["monitor_meta"] = {
                "trained_at": mm.get("trained_at"),
                "n_windows": mm.get("n_windows"),
                "n_sats": mm.get("n_sats"),
                "train_roles": mm.get("train_roles"),
                "holdout_days": mm.get("holdout_days"),
                "contamination": mm.get("contamination"),
                "versioned_model": mm.get("versioned_model"),
                "recommended_anomaly_threshold": mm.get("recommended_anomaly_threshold"),
            }
    except Exception as exc:
        logger.warning("monitor meta provenance skipped: %s", exc)
    return prov


def materialize_investigation(
    report: Optional[Dict[str, Any]] = None,
    wf_summary: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Index board + walk-forward into athena.investigation.v1."""
    if report is None:
        p = ALERTS_DIR / "risk_report_latest.json"
        report = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    if wf_summary is None:
        p = ALERTS_DIR / "walkforward_summary.json"
        wf_summary = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}

    summary = report.get("summary") or {}
    objects: List[Dict[str, Any]] = []
    set_suspect: List[str] = []
    set_asset: List[str] = []
    set_alert: List[str] = []

    for row in report.get("board") or []:
        norad = int(row["norad_id"])
        oid = sat_id(norad)
        role = row.get("role") or "unknown"
        pair = row.get("pair") or {}
        asset_norad = pair.get("asset_norad")
        cases = _cases_for_norad(wf_summary, norad)
        peers = _peers_on_asset(report, norad, int(asset_norad) if asset_norad else None)
        placebos = _placebos_same_peak(
            wf_summary, [c["event_id"] for c in cases if c.get("event_id")]
        )

        links: List[Dict[str, Any]] = []
        if asset_norad:
            links.append(
                {
                    "type": "threatens",
                    "target": sat_id(int(asset_norad)),
                    "norad": int(asset_norad),
                    "label": _pair_link_label(pair),
                    "pc": pair.get("pc"),
                    "tca_utc": pair.get("tca_utc"),
                    "miss_distance_km": pair.get("miss_distance_km"),
                }
            )
        if row.get("is_anomaly") or row.get("is_military_detection") or row.get("status") != "NOMINAL":
            links.append(
                {
                    "type": "hasAlert",
                    "target": f"alert:{norad}",
                    "label": row.get("status"),
                }
            )
        for c in cases[:3]:
            links.append(
                {
                    "type": "validatedBy",
                    "target": f"case:{c['event_id']}",
                    "event_id": c["event_id"],
                    "label": c["event_id"],
                    "is_placebo": c.get("is_placebo"),
                    "hit": c.get("hit"),
                    "t_peak": c.get("t_peak"),
                    "lead_days": c.get("lead_days"),
                }
            )
        fs = row.get("features_snapshot") or {}
        links.append(
            {
                "type": "weather",
                "target": f"wx:{norad}",
                "label": f"F10.7 {fs.get('f10_7', '—')} · Ap {fs.get('ap_index', '—')}",
            }
        )
        ev = row.get("evidence") or {}
        if ev:
            links.append(
                {
                    "type": "fusedAs",
                    "target": f"ev:{norad}",
                    "label": f"Bel {ev.get('belief_anomalous')} · K {ev.get('conflict_K')}",
                }
            )
        for peer in peers:
            links.append(
                {
                    "type": "threatenedBy" if role == "asset" else "sameAsset",
                    "target": sat_id(peer["norad"]),
                    "norad": peer["norad"],
                    "label": peer["name"],
                    "pair_risk": peer.get("pair_risk"),
                }
            )
        for pl in placebos[:3]:
            if pl.get("norad") == norad:
                continue
            links.append(
                {
                    "type": "samePeak",
                    "target": f"case:{pl['event_id']}",
                    "event_id": pl["event_id"],
                    "norad": pl["norad"],
                    "label": pl.get("name") or pl["event_id"],
                    "is_placebo": True,
                }
            )

        triage = get_alert_state(norad)
        obj = {
            "id": oid,
            "kind": "satellite",
            "gotham_category": _ot_category("Satellite"),
            "norad": norad,
            "label": row.get("object_name") or f"#{norad}",
            "role": role,
            "status": row.get("status"),
            "triage": {
                "status": triage.get("status") or "OPEN",
                "updated_at": triage.get("updated_at"),
                "operator": triage.get("operator"),
            },
            "country": row.get("country"),
            "orbit_class": row.get("orbit_class"),
            "scores": {
                "attention": row.get("attention_score"),
                "anomaly": row.get("anomaly_score"),
                "belief": ev.get("belief_anomalous"),
            },
            "links": links,
        }
        objects.append(obj)
        if role == "suspect":
            set_suspect.append(oid)
        if role == "asset":
            set_asset.append(oid)
        if row.get("is_military_detection") or row.get("is_anomaly"):
            set_alert.append(oid)

        if row.get("is_anomaly") or row.get("is_military_detection") or row.get("status") != "NOMINAL":
            objects.append(
                {
                    "id": f"alert:{norad}",
                    "kind": "alert",
                    "gotham_category": _ot_category("Alert"),
                    "norad": norad,
                    "label": row.get("status") or "ALERT",
                    "status": row.get("status"),
                    "links": [{"type": "source", "target": oid, "label": obj["label"]}],
                }
            )
        if ev:
            objects.append(
                {
                    "id": f"ev:{norad}",
                    "kind": "evidence",
                    "gotham_category": _ot_category("Evidence"),
                    "norad": norad,
                    "label": f"Bel {ev.get('belief_anomalous')}",
                    "links": [{"type": "about", "target": oid, "label": obj["label"]}],
                }
            )
        objects.append(
            {
                "id": f"wx:{norad}",
                "kind": "weather",
                "gotham_category": _ot_category("Weather"),
                "norad": norad,
                "label": f"F10.7 {fs.get('f10_7', '—')}",
                "links": [{"type": "windowOf", "target": oid, "label": obj["label"]}],
            }
        )

    objects.extend(_case_and_document_objects(wf_summary, objects))

    bundle = {
        "schema": SCHEMA,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "day": report.get("day"),
        "lineage": {
            "risk_report_schema": report.get("schema") or "athena.risk_report.v1",
            "doctrine": report.get("doctrine") or "military_first_sda",
            "protocol": report.get("protocol") or "past-only",
            "threshold": summary.get("threshold"),
            "hit_rule": HIT_RULE,
        },
        "provenance": _model_provenance(),
        "object_sets": [
            {"id": "suspects", "label": "Watchlist suspects", "ids": set_suspect},
            {"id": "assets", "label": "Protected assets", "ids": set_asset},
            {"id": "alerts", "label": "Elevated / mil-detect", "ids": set_alert},
        ],
        "objects": objects,
    }
    return bundle


def _case_and_document_objects(
    wf_summary: Dict[str, Any],
    existing: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """First-class Case + Document objects (T4). Scores stay on Satellite."""
    have = {o.get("id") for o in existing}
    extra: List[Dict[str, Any]] = []
    catalog_events = _load_walkforward_catalog()
    for ev in _wf_events(wf_summary):
        eid = ev.get("event_id") or ev.get("id")
        if not eid:
            continue
        cid = f"case:{eid}"
        if cid not in have:
            extra.append(
                {
                    "id": cid,
                    "kind": "case",
                    "gotham_category": _ot_category("Case"),
                    "label": str(eid),
                    "t_peak": ev.get("t_peak"),
                    "links": [],
                }
            )
            have.add(cid)
        cat = catalog_events.get(str(eid)) or {}
        for src in (cat.get("sources") or ev.get("sources") or [])[:3]:
            did = f"doc:{_slug(str(src))[:48]}"
            if did in have:
                continue
            extra.append(
                {
                    "id": did,
                    "kind": "document",
                    "gotham_category": "Document",
                    "label": str(src)[:160],
                    "links": [
                        {"type": "mentions", "target": cid, "label": str(eid)},
                    ],
                }
            )
            have.add(did)
            extra[-1]["links"].append({"type": "validatedBy", "target": cid, "label": str(eid)})
    return extra


def _load_walkforward_catalog() -> Dict[str, Any]:
    p = DATA_DIR / "catalog" / "events_walkforward.json"
    if not p.exists():
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning("events_walkforward.json unreadable: %s", exc)
        return {}
    out: Dict[str, Any] = {}
    for ev in data.get("events") or []:
        eid = ev.get("id")
        if eid:
            out[str(eid)] = ev
    return out


def _slug(text: str) -> str:
    return "".join(ch.lower() if ch.isalnum() else "-" for ch in text).strip("-")


def expand_neighbors(
    bundle: Dict[str, Any],
    object_id: str,
    hops: int = 2,
) -> Dict[str, Any]:
    """BFS over investigation links. hops is depth from the start node (1–3)."""
    hops = max(1, min(int(hops), 3))
    by_id: Dict[str, Dict[str, Any]] = {str(o.get("id")): o for o in bundle.get("objects") or []}
    if object_id not in by_id:
        return {"start": object_id, "hops": hops, "nodes": [], "edges": []}
    seen = {object_id}
    frontier = [object_id]
    nodes = [by_id[object_id]]
    edges: List[Dict[str, Any]] = []
    for _ in range(hops):
        nxt: List[str] = []
        for oid in frontier:
            obj = by_id.get(oid) or {}
            for link in obj.get("links") or []:
                tid = str(link.get("target") or "")
                if not tid:
                    continue
                edges.append({"from": oid, "to": tid, "type": link.get("type"), "label": link.get("label")})
                if tid in seen:
                    continue
                seen.add(tid)
                if tid in by_id:
                    nodes.append(by_id[tid])
                    nxt.append(tid)
        frontier = nxt
        if not frontier:
            break
    return {"start": object_id, "hops": hops, "nodes": nodes, "edges": edges}


def write_investigation(bundle: Optional[Dict[str, Any]] = None) -> Path:
    if bundle is None:
        bundle = materialize_investigation()
    violations = validate_investigation(bundle)
    if violations:
        raise ValueError("investigation.v1 invalid: " + "; ".join(violations[:6]))
    ALERTS_DIR.mkdir(parents=True, exist_ok=True)
    out = ALERTS_DIR / "investigation_latest.json"
    out.write_text(json.dumps(bundle, indent=2, default=str), encoding="utf-8")
    return out


# --- Actions log (Foundry Actions service: validate + historical log) ------

ACTIONS_PATH = ALERTS_DIR / "actions.jsonl"
ALLOWED_ACTIONS = frozenset(
    {"AcknowledgeAlert", "OpenCase", "TaskSatellite", "ResolveAlert", "SuppressAlert"}
)
ACTION_FOR_STATUS = {
    "ACKNOWLEDGED": "AcknowledgeAlert",
    "RESOLVED": "ResolveAlert",
    "SUPPRESSED": "SuppressAlert",
    "OPEN": "OpenCase",
}


def append_action(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Append a validate-only action. Never mutates scores."""
    action = str(payload.get("action") or "")
    if action not in ALLOWED_ACTIONS:
        raise ValueError(f"unknown action '{action}'")
    norad = payload.get("norad")
    if norad is None:
        raise ValueError("norad required")
    rec = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "action": action,
        "norad": int(norad),
        "operator": payload.get("operator") or "local",
        "validate_only": True,
        "params": payload.get("params") or {},
        "note": "Action log only — scores immutable (US 12,657,514; US 2024/0394296).",
    }
    ALERTS_DIR.mkdir(parents=True, exist_ok=True)
    with ACTIONS_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec) + "\n")
    return rec


def read_actions(limit: int = 80) -> List[Dict[str, Any]]:
    if not ACTIONS_PATH.exists():
        return []
    lines = ACTIONS_PATH.read_text(encoding="utf-8").splitlines()
    out: List[Dict[str, Any]] = []
    for line in lines[-limit:]:
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


# --- Alert lifecycle (operator triage workflow) -----------------------------
#
# Scores are immutable (quant ground truth). Alert *state* is operational
# bookkeeping: OPEN → ACKNOWLEDGED → RESOLVED / SUPPRESSED. Each transition is
# audited in actions.jsonl (validate-only action log) + alert_state.json.
# Gotham: alert workflow + Actions service, without mutating the analytic.

ALERT_STATE_PATH = ALERTS_DIR / "alert_state.json"
ALERT_STATUSES = ("OPEN", "ACKNOWLEDGED", "RESOLVED", "SUPPRESSED")
_ALERT_LOCK = threading.Lock()

# Valid transitions (deterministic finite state machine).
_STATUS_TRANSITIONS = {
    "OPEN": {"ACKNOWLEDGED", "RESOLVED", "SUPPRESSED"},
    "ACKNOWLEDGED": {"RESOLVED", "SUPPRESSED", "OPEN"},
    "RESOLVED": {"OPEN"},
    "SUPPRESSED": {"OPEN"},
}


def _load_alert_state() -> Dict[str, Any]:
    if not ALERT_STATE_PATH.exists():
        return {"schema": "athena.alert_state.v1", "alerts": {}}
    try:
        data = json.loads(ALERT_STATE_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(
            "alert_state.json corrupt — refusing to reset triage"
        ) from exc
    if not isinstance(data, dict):
        raise ValueError("alert_state.json corrupt — refusing to reset triage")
    data.setdefault("schema", "athena.alert_state.v1")
    data.setdefault("alerts", {})
    return data


def _save_alert_state(state: Dict[str, Any]) -> None:
    ALERTS_DIR.mkdir(parents=True, exist_ok=True)
    tmp = ALERT_STATE_PATH.with_suffix(ALERT_STATE_PATH.suffix + ".tmp")
    tmp.write_text(json.dumps(state, indent=2, default=str), encoding="utf-8")
    tmp.replace(ALERT_STATE_PATH)


def get_alert_state(norad: Optional[int] = None) -> Dict[str, Any]:
    """Return the full state map, or the state for a single NORAD."""
    with _ALERT_LOCK:
        state = _load_alert_state()
    if norad is None:
        return state
    return state.get("alerts", {}).get(str(int(norad)), {"norad": int(norad), "status": "OPEN"})


def update_alert_state(
    norad: int,
    status: str,
    *,
    operator: str = "local",
    note: str = "",
) -> Dict[str, Any]:
    """Transition an alert's triage state, validating the FSM and auditing it.

    Does NOT touch scores — only the operational `status` field.
    """
    status = str(status or "").upper()
    if status not in ALERT_STATUSES:
        raise ValueError(f"unknown status '{status}' (allowed: {ALERT_STATUSES})")

    with _ALERT_LOCK:
        state = _load_alert_state()
        alerts = state.setdefault("alerts", {})
        key = str(int(norad))
        current = alerts.get(key, {"norad": int(norad), "status": "OPEN"})
        prev = str(current.get("status") or "OPEN").upper()
        if prev != status:
            allowed = _STATUS_TRANSITIONS.get(prev, set())
            if status not in allowed:
                raise ValueError(f"invalid transition {prev} -> {status} (allowed: {sorted(allowed)})")

        rec = {
            "norad": int(norad),
            "status": status,
            "previous_status": prev,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "operator": operator,
            "note": note,
        }
        alerts[key] = rec
        state["updated"] = datetime.now(timezone.utc).isoformat()
        _save_alert_state(state)

    # Audit trail (validate-only action log; scores immutable).
    try:
        append_action(
            {
                "action": ACTION_FOR_STATUS.get(status, "OpenCase"),
                "norad": int(norad),
                "operator": operator,
                "params": {"status": status, "previous_status": prev, "note": note},
            }
        )
    except Exception as exc:
        logger.warning("alert-state audit log failed for #%s: %s", norad, exc)
    return rec
