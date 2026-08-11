"""
Typed ontology layer for Athena-SDA (Palantir Ontology-inspired).

The ontology is a declarative, typed schema (src/ontology.json, OSDK-style)
declaring object types (Satellite, Alert, Sensor, TaskingOrder), property
types, link types and action types. All UI/API surfaces should read from
this model rather than ad-hoc dicts.

References:
  - Palantir Ontology core concepts (object type / property / link / action)
  - US 12,374,011 B2 "Interactive data object map" (Palantir) — inspiration
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

_ONTOLOGY_PATH = Path(__file__).resolve().parent / "ontology.json"

_ONTOLOGY_CACHE: Optional[Dict[str, Any]] = None


def load_ontology() -> Dict[str, Any]:
    """Load and cache the ontology definition (src/ontology.json)."""
    global _ONTOLOGY_CACHE
    if _ONTOLOGY_CACHE is None:
        _ONTOLOGY_CACHE = json.loads(_ONTOLOGY_PATH.read_text(encoding="utf-8"))
    return _ONTOLOGY_CACHE


def object_types() -> Dict[str, Any]:
    return (load_ontology().get("objectTypes") or {})


def object_type(name: str) -> Dict[str, Any]:
    ot = object_types().get(name)
    if ot is None:
        raise KeyError(f"unknown object type: {name}")
    return ot


def property_type(object_name: str, prop: str) -> Optional[Dict[str, Any]]:
    ot = object_types().get(object_name)
    if ot is None:
        return None
    return (ot.get("properties") or {}).get(prop)


def role_enum() -> List[str]:
    """Valid Satellite roles from the ontology (asset / suspect / baseline / unknown)."""
    p = property_type("Satellite", "role")
    if p is None:
        return ["asset", "suspect", "baseline", "unknown"]
    return list(p.get("enum") or ["asset", "suspect", "baseline", "unknown"])


def status_enum() -> List[str]:
    p = property_type("Satellite", "status")
    if p is None:
        return []
    return list(p.get("enum") or [])


def action_types() -> Dict[str, Any]:
    return load_ontology().get("actionTypes") or {}


def validate_satellite_properties(obj: Dict[str, Any]) -> List[str]:
    """
    Lightweight ontology validation of a Satellite object.

    Returns a list of violations (empty = valid). Kept dependency-free;
    deep validation lives in src/contracts.py for the risk_report contract.
    """
    violations: List[str] = []
    props = property_type("Satellite", "noradId")
    if props is not None and props.get("required") and "noradId" not in obj:
        violations.append("Satellite missing required property noradId")
    role = obj.get("role")
    if role is not None and role not in role_enum():
        violations.append(f"invalid role '{role}' (ontology: {role_enum()})")
    status = obj.get("status")
    if status is not None and status not in status_enum():
        violations.append(f"invalid status '{status}'")
    return violations
