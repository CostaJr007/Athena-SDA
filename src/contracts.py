"""
Formal API contracts (Palantir US 12,657,514 B2 — Data/Inference/Open API).

  - Data API      -> src.tle_store (canonical epoch store)
  - Inference API -> models/registry.json (micro-model registry)
  - Open API      -> schemas/risk_report.v1.schema.json (downstream format)

This module validates artifacts against the Open API contract at write time
so the mission board never receives a schema-drifted report. Uses `jsonschema`
when installed; falls back to a structural subset check (dependency-free).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

_SCHEMA_DIR = Path(__file__).resolve().parent.parent / "schemas"


def _load_schema(name: str) -> Optional[Dict[str, Any]]:
    p = _SCHEMA_DIR / name
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def validate_risk_report(report: Dict[str, Any]) -> List[str]:
    """Validate a risk report dict against schemas/risk_report.v1.schema.json.

    Returns a list of violations (empty = valid). Best-effort: if jsonschema
    is unavailable, runs a minimal structural check.
    """
    violations: List[str] = []
    try:
        import jsonschema  # type: ignore

        schema = _load_schema("risk_report.v1.schema.json")
        if schema is None:
            return ["risk_report schema file missing"]
        try:
            jsonschema.validate(report, schema)
            return []
        except jsonschema.ValidationError as e:
            return [f"risk_report schema violation: {e.message}"]
    except ImportError:
        pass
    except Exception as e:  # pragma: no cover - defensive
        violations.append(f"schema validation error: {e}")
        return violations

    # Dependency-free fallback: structural subset
    if report.get("schema") != "athena.risk_report.v1":
        violations.append("missing schema='athena.risk_report.v1'")
    for key in ("generated_at", "day", "summary", "board"):
        if key not in report:
            violations.append(f"missing top-level key '{key}'")
    board = report.get("board")
    if board is not None and not isinstance(board, list):
        violations.append("board must be a list")
    for entry in board or []:
        for key in ("norad_id", "anomaly_score", "attention_score"):
            if key not in entry:
                violations.append(f"board entry missing '{key}'")
    return violations


def validate_investigation(bundle: Dict[str, Any]) -> List[str]:
    """Validate athena.investigation.v1 (object layer, not scores)."""
    violations: List[str] = []
    try:
        import jsonschema  # type: ignore

        schema = _load_schema("investigation.v1.schema.json")
        if schema is None:
            return ["investigation schema file missing"]
        try:
            jsonschema.validate(bundle, schema)
            return []
        except jsonschema.ValidationError as e:
            return [f"investigation schema violation: {e.message}"]
    except ImportError:
        pass
    except Exception as e:  # pragma: no cover
        violations.append(f"investigation schema error: {e}")
        return violations

    if bundle.get("schema") != "athena.investigation.v1":
        violations.append("missing schema='athena.investigation.v1'")
    if "objects" not in bundle or not isinstance(bundle.get("objects"), list):
        violations.append("objects must be a list")
    return violations
