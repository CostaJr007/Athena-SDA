"""Object-graph explainer.

Primary path: Groq + Tavily (`src.graph_qa`). Scores stay immutable.
"""
from __future__ import annotations

from typing import Any, Dict

from src.graph_qa import (
    LINK_GLOSSARY,
    explain_graph,
    explain_graph_stream,
    local_graph_brief,
)

# Kept so older imports / tests do not break.
local_ontology_brief = local_graph_brief


def explain_ontology_graph(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Return {text, model, source, citations}."""
    return explain_graph(payload)


__all__ = [
    "LINK_GLOSSARY",
    "explain_graph_stream",
    "explain_ontology_graph",
    "local_ontology_brief",
]
