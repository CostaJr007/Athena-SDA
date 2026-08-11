"""
Model registry — versioned micro-models (Palantir-inspired hot-swap / US patent 070 pattern).

Stores metadata for Isolation Forest (monitor + priority pipeline) and XGBoost
without overwriting roles silently.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from src.config import MODELS_DIR

REGISTRY_PATH = MODELS_DIR / "registry.json"


def feature_schema_hash(columns: Sequence[str]) -> str:
    payload = "|".join(columns)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def load_registry() -> Dict[str, Any]:
    if not REGISTRY_PATH.exists():
        return {"version": 1, "updated": None, "models": {}}
    try:
        return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {"version": 1, "updated": None, "models": {}}


def register_model(
    role: str,
    *,
    path: str | Path,
    feature_columns: Sequence[str],
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Register or update a model role: monitor_if | pipeline_if | xgboost | rkhs_reference.
    """
    reg = load_registry()
    models = reg.setdefault("models", {})
    # Store repo-relative paths (models/<file>) so metadata is portable across
    # machines — the old registry carried Windows "D:\\Athena-SDA\\models\\..." paths.
    try:
        rel = Path(path).resolve().relative_to(MODELS_DIR.resolve())
        path_str = str(rel)
    except Exception:
        path_str = str(path)
    entry: Dict[str, Any] = {
        "role": role,
        "path": path_str,
        "feature_columns": list(feature_columns),
        "feature_schema_hash": feature_schema_hash(feature_columns),
        "registered_at": datetime.now(timezone.utc).isoformat(),
    }
    if extra:
        entry.update(extra)
    models[role] = entry
    reg["version"] = 1
    reg["updated"] = entry["registered_at"]
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    REGISTRY_PATH.write_text(json.dumps(reg, indent=2, ensure_ascii=False), encoding="utf-8")
    return entry


def get_model_entry(role: str) -> Optional[Dict[str, Any]]:
    return load_registry().get("models", {}).get(role)
