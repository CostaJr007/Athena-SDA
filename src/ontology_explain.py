"""
IBM Granite (watsonx.ai) — ontology + object-graph explainer.

This is not Bob. Scores stay immutable. The model only narrates typed
objects (Satellite, Alert, Case, Weather, Evidence) and their links.
"""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

load_dotenv()

# Reuse the watsonx client already wired for Granite.
from src.bob import get_watsonx_model
from src.rag import format_citations, retrieve

GRANITE_MODEL_LABEL = "ibm/granite-3-8b-instruct"

LINK_GLOSSARY = {
    "threatens": "suspect → protected asset (pair risk / shadowing proxy)",
    "hasAlert": "Satellite → Alert (elevated noise, pair, or health flag)",
    "validatedBy": "Satellite → walk-forward Case (public t_peak, past-only IF)",
    "weather": "Satellite → GFZ space-weather context (drag vs maneuver)",
    "fusedAs": "Satellite → Dempster–Shafer evidence (belief / conflict K)",
}


def local_ontology_brief(payload: Dict[str, Any]) -> str:
    """Deterministic fallback when watsonx is not configured."""
    name = payload.get("object_name") or "Unknown object"
    norad = payload.get("norad")
    role = payload.get("role") or "unknown"
    status = payload.get("status") or "—"
    links: List[Dict[str, Any]] = list(payload.get("links") or [])
    scores = payload.get("scores") or {}
    q = (payload.get("question") or "").strip()

    lines = [
        f"Ontology walk of {name} (NORAD {norad}).",
        f"Object type Satellite · role {role} · status {status}.",
        "Athena types: Satellite, Alert, Case, Weather, Evidence, TaskingOrder.",
    ]
    if links:
        lines.append("Links on this graph:")
        for lk in links:
            kind = str(lk.get("type") or "link")
            gloss = LINK_GLOSSARY.get(kind, kind)
            label = lk.get("label") or ""
            lines.append(f"- {kind}: {label} — {gloss}")
    else:
        lines.append("No ontology links on the current graph.")

    att = scores.get("attention")
    anom = scores.get("anomaly")
    bel = scores.get("belief")
    if att is not None or anom is not None:
        bits = []
        if att is not None:
            bits.append(f"attention={float(att):.3f}")
        if anom is not None:
            bits.append(f"anomaly={float(anom):.3f}")
        if bel is not None:
            bits.append(f"DS belief={float(bel):.3f}")
        lines.append("Immutable scores: " + " · ".join(bits) + ".")

    lines.append(
        "Granite must not invent threat or rewrite Isolation Forest scores. "
        "Pattern-of-life ≠ intent."
    )
    if q:
        lines.append(f"Operator question: {q}")
        lines.append(
            "Answer from the typed graph only: follow threatens / hasAlert / "
            "validatedBy / weather / fusedAs."
        )
    return " ".join(lines[:2]) + "\n" + "\n".join(lines[2:])


def build_prompt(payload: Dict[str, Any]) -> str:
    name = payload.get("object_name") or "Unknown"
    norad = payload.get("norad")
    role = payload.get("role") or "unknown"
    status = payload.get("status") or "—"
    orbit = payload.get("orbit_class") or "—"
    country = payload.get("country") or "—"
    links: List[Dict[str, Any]] = list(payload.get("links") or [])
    nodes: List[Dict[str, Any]] = list(payload.get("nodes") or [])
    scores = payload.get("scores") or {}
    q = (payload.get("question") or "").strip() or (
        "Explain this object's ontology types and graph links for an SDA operator."
    )
    rag_q = " ".join(
        [
            str(name),
            str(role),
            str(status),
            q,
            "space domain awareness ontology alert pair weather",
        ]
    )
    cites = format_citations(retrieve(rag_q, k=3))

    link_lines = []
    for lk in links:
        kind = str(lk.get("type") or "link")
        link_lines.append(
            f"- {kind} → {lk.get('label') or '?'}  ({LINK_GLOSSARY.get(kind, kind)})"
        )
    node_lines = [
        f"- {n.get('kind')}: {n.get('label')} ({n.get('sub') or ''})"
        for n in nodes
    ]

    return f"""[ATHENA-SDA · IBM GRANITE · ONTOLOGY EXPLAINER]
You are IBM Granite on watsonx.ai. You explain the Athena typed ontology and
the current object graph. You are not Bob and you do not write tactical orders.

ONTOLOGY ( Palantir-style object map, US 12,374,011 ):
- Satellite (primary key noradId): role asset|suspect|baseline, orbit, scores
- Alert: raised on a Satellite (hasAlert)
- Case: walk-forward validation window with public t_peak (validatedBy)
- Weather: GFZ F10.7/Ap/Kp context
- Evidence: Dempster–Shafer belief / plausibility / conflict K
- Action TaskSatellite: validate-only, never executes without approval

CURRENT OBJECT:
- {name} NORAD {norad} · role {role} · {country} · {orbit} · status {status}
- attention={scores.get('attention')} anomaly={scores.get('anomaly')} belief={scores.get('belief')}

GRAPH NODES:
{chr(10).join(node_lines) or '- (none)'}

GRAPH LINKS:
{chr(10).join(link_lines) or '- (none)'}

RULES:
- English, 120–180 words, operator tone.
- Explain what each node type is and what each link means for THIS object.
- Never invent or change numeric scores.
- Do not claim espionage or classified intent.
- If a Case link exists, say it is a public-anchor walk-forward, not ground truth.

OPERATOR QUESTION:
{q}

{cites}

EXPLANATION:"""


def explain_ontology_graph(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Return {text, model, source}."""
    model = get_watsonx_model()
    if model is not None:
        try:
            response = model.generate(prompt=build_prompt(payload))
            text = (response.get("results") or [{}])[0].get("generated_text") or ""
            text = text.strip()
            if text:
                return {
                    "text": text,
                    "model": os.environ.get("WATSONX_MODEL", GRANITE_MODEL_LABEL),
                    "source": "watsonx",
                }
        except Exception as exc:
            print(f"watsonx ontology explain error: {exc}")

    return {
        "text": local_ontology_brief(payload),
        "model": "local-ontology-fallback",
        "source": "fallback",
    }
