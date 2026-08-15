"""
Military-first object catalog for Athena-SDA.

Loads data/catalog/watchlist.json and exposes:
  - roles: asset | suspect | baseline
  - name / country / purpose / orbit_class per NORAD
  - helpers for pipeline proximity (protected assets) and monitor watchlist
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set

from src.config import DATA_DIR

CATALOG_DIR = DATA_DIR / "catalog"
WATCHLIST_PATH = CATALOG_DIR / "watchlist.json"

VALID_ROLES = frozenset({"asset", "suspect", "baseline"})

# Fallback if JSON missing (keeps system bootable)
_FALLBACK_OBJECTS: List[Dict[str, Any]] = [
    {"norad_id": 25544, "name": "ISS (ZARYA)", "role": "asset", "country": "INTL", "purpose": "crewed_station", "orbit_class": "LEO"},
    {"norad_id": 39166, "name": "NAVSTAR 68 (USA 242)", "role": "asset", "country": "US", "purpose": "navigation", "orbit_class": "MEO"},
    {"norad_id": 41038, "name": "YAOGAN-29", "role": "suspect", "country": "CN", "purpose": "reconnaissance", "orbit_class": "LEO"},
    {"norad_id": 40258, "name": "LUCH (OLYMP-K 1)", "role": "suspect", "country": "RU", "purpose": "sigint", "orbit_class": "GEO"},
    {"norad_id": 25994, "name": "TERRA", "role": "baseline", "country": "US", "purpose": "scientific", "orbit_class": "LEO"},
    {"norad_id": 43013, "name": "NOAA 20 (JPSS-1)", "role": "baseline", "country": "US", "purpose": "earth obs", "orbit_class": "LEO"},
]


def _normalize_object(raw: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    try:
        nid = int(raw["norad_id"])
    except (KeyError, TypeError, ValueError):
        return None
    role = str(raw.get("role", "baseline")).lower().strip()
    if role not in VALID_ROLES:
        role = "baseline"
    return {
        "norad_id": nid,
        "name": str(raw.get("name") or f"NORAD-{nid}"),
        "role": role,
        "country": str(raw.get("country") or "UNKNOWN"),
        "purpose": str(raw.get("purpose") or "unknown"),
        "orbit_class": str(raw.get("orbit_class") or "LEO"),
        "notes": str(raw.get("notes") or ""),
    }


@lru_cache(maxsize=1)
def load_watchlist(path: Optional[str] = None) -> Dict[str, Any]:
    """
    Load watchlist JSON. Cached. Call clear_watchlist_cache() after edits.
    Returns dict with keys: version, objects (list), by_id (dict[int, obj]), ...
    """
    p = Path(path) if path else WATCHLIST_PATH
    objects: List[Dict[str, Any]] = []
    meta: Dict[str, Any] = {"version": 0, "source": "fallback"}

    if p.exists():
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            meta = {
                "version": data.get("version", 1),
                "updated": data.get("updated"),
                "description": data.get("description"),
                "doctrine": data.get("doctrine"),
                "source": str(p),
            }
            for raw in data.get("objects") or []:
                obj = _normalize_object(raw)
                if obj:
                    objects.append(obj)
        except Exception as e:
            meta["error"] = str(e)

    if not objects:
        objects = [o for r in _FALLBACK_OBJECTS if (o := _normalize_object(r))]
        meta["source"] = "fallback"

    by_id: Dict[int, Dict[str, Any]] = {o["norad_id"]: o for o in objects}
    return {
        **meta,
        "objects": objects,
        "by_id": by_id,
        "n_objects": len(objects),
    }


def clear_watchlist_cache() -> None:
    load_watchlist.cache_clear()


def all_norad_ids() -> List[int]:
    return [o["norad_id"] for o in load_watchlist()["objects"]]


def name_map() -> Dict[int, str]:
    """norad_id → display name (compatible with old DEFAULT_WATCHLIST)."""
    return {o["norad_id"]: o["name"] for o in load_watchlist()["objects"]}


def role_map() -> Dict[int, str]:
    return {o["norad_id"]: o["role"] for o in load_watchlist()["objects"]}


def ids_by_role(role: str) -> List[int]:
    role = role.lower().strip()
    return [o["norad_id"] for o in load_watchlist()["objects"] if o["role"] == role]


def asset_ids() -> Set[int]:
    return set(ids_by_role("asset"))


def suspect_ids() -> Set[int]:
    return set(ids_by_role("suspect"))


def baseline_ids() -> Set[int]:
    return set(ids_by_role("baseline"))


def get_object(norad_id: int) -> Optional[Dict[str, Any]]:
    return load_watchlist()["by_id"].get(int(norad_id))


def get_name(norad_id: int, default: Optional[str] = None) -> str:
    obj = get_object(norad_id)
    if obj:
        return obj["name"]
    return default if default is not None else str(norad_id)


def get_meta(norad_id: int) -> Dict[str, Any]:
    """country / purpose / orbit_class / role for feature extraction."""
    obj = get_object(norad_id)
    if not obj:
        return {
            "norad_id": int(norad_id),
            "name": str(norad_id),
            "role": "unknown",
            "country": "UNKNOWN",
            "purpose": "unknown",
            "orbit_class": "LEO",
        }
    return {
        "norad_id": obj["norad_id"],
        "name": obj["name"],
        "role": obj["role"],
        "country": obj["country"],
        "purpose": obj["purpose"],
        "orbit_class": obj["orbit_class"],
        "notes": obj.get("notes", ""),
    }


def summary() -> Dict[str, Any]:
    wl = load_watchlist()
    counts = {"asset": 0, "suspect": 0, "baseline": 0}
    for o in wl["objects"]:
        counts[o["role"]] = counts.get(o["role"], 0) + 1
    return {
        "source": wl.get("source"),
        "version": wl.get("version"),
        "updated": wl.get("updated"),
        "n_objects": wl["n_objects"],
        "counts": counts,
        "norad_ids": all_norad_ids(),
    }


def _atomic_write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(path)


def _assert_persist_allowed(obj: Dict[str, Any]) -> None:
    """Block commercial mega-constellations from becoming IF normality anchors."""
    name = str(obj.get("name") or "").upper()
    purpose = str(obj.get("purpose") or "").lower()
    role = str(obj.get("role") or "")
    if "STARLINK" in name:
        raise ValueError("Starlink cannot be added to the military watchlist")
    if purpose == "commercial" and role in ("baseline", "asset"):
        raise ValueError("commercial constellation cannot be a baseline/asset IF anchor")


def upsert_watchlist_object(raw: Dict[str, Any], path: Optional[Path] = None) -> Dict[str, Any]:
    """Add or replace a NORAD on the curated watchlist. Does not retrain."""
    obj = _normalize_object(raw)
    if obj is None:
        raise ValueError("invalid watchlist object (need integer norad_id)")
    _assert_persist_allowed(obj)
    p = Path(path) if path else WATCHLIST_PATH
    data: Dict[str, Any] = {"version": 1, "objects": []}
    if p.exists():
        try:
            loaded = json.loads(p.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                data = loaded
        except json.JSONDecodeError as exc:
            raise ValueError(f"watchlist JSON corrupt: {exc}") from exc
    objects = [o for o in (data.get("objects") or []) if int(o.get("norad_id") or -1) != obj["norad_id"]]
    objects.append(
        {
            "norad_id": obj["norad_id"],
            "name": obj["name"],
            "role": obj["role"],
            "country": obj["country"],
            "purpose": obj["purpose"],
            "orbit_class": obj["orbit_class"],
            "notes": obj.get("notes") or "",
        }
    )
    objects.sort(key=lambda o: int(o["norad_id"]))
    data["objects"] = objects
    data["updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    _atomic_write_json(p, data)
    clear_watchlist_cache()
    return obj


def remove_watchlist_object(norad_id: int, path: Optional[Path] = None) -> bool:
    """Remove a NORAD from the watchlist JSON. Returns True if it was present."""
    p = Path(path) if path else WATCHLIST_PATH
    if not p.exists():
        return False
    data = json.loads(p.read_text(encoding="utf-8"))
    before = list(data.get("objects") or [])
    after = [o for o in before if int(o.get("norad_id") or -1) != int(norad_id)]
    if len(after) == len(before):
        return False
    data["objects"] = after
    data["updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    _atomic_write_json(p, data)
    clear_watchlist_cache()
    return True


def persist_watchlist_role(norad_id: int, role: str, path: Optional[Path] = None) -> Dict[str, Any]:
    role = str(role or "").lower().strip()
    if role not in VALID_ROLES:
        raise ValueError(f"role must be one of {sorted(VALID_ROLES)}")
    existing = get_object(int(norad_id)) or {"norad_id": int(norad_id), "name": f"NORAD-{int(norad_id)}"}
    existing["role"] = role
    return upsert_watchlist_object(existing, path=path)


def filter_ids(
    norad_ids: Optional[Sequence[int]] = None,
    roles: Optional[Iterable[str]] = None,
) -> List[int]:
    """Intersect optional id list with optional role filter (order preserved from catalog)."""
    allowed_roles = {r.lower() for r in roles} if roles else None
    ids = set(int(x) for x in norad_ids) if norad_ids is not None else None
    out: List[int] = []
    for o in load_watchlist()["objects"]:
        if ids is not None and o["norad_id"] not in ids:
            continue
        if allowed_roles is not None and o["role"] not in allowed_roles:
            continue
        out.append(o["norad_id"])
    return out
