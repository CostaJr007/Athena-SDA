"""Graph copilot: Groq (LLM) + Tavily (web) over the object graph.

Scores stay immutable. The model only narrates nodes/links already on the
board. Tavily adds public-web context; it never becomes a score source.
"""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

import requests
from dotenv import load_dotenv

from src.config import ROOT
from src.logging_setup import get_logger
from src.rag import format_citations, retrieve

load_dotenv(ROOT / ".env", override=True)
logger = get_logger(__name__)

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
TAVILY_URL = "https://api.tavily.com/search"
DEFAULT_GROQ_MODEL = "llama-3.1-8b-instant"
TIMEOUT = 20

LINK_GLOSSARY = {
    "threatens": "suspect → protected asset (pair risk / shadowing proxy)",
    "hasAlert": "Satellite → Alert (elevated noise, pair, or health flag)",
    "validatedBy": "Satellite → walk-forward Case (public t_peak, past-only IF)",
    "weather": "Satellite → GFZ space-weather context (drag vs maneuver)",
    "fusedAs": "Satellite → Dempster–Shafer evidence (belief / conflict K)",
    "sameAsset": "peer suspect sharing the same protected asset",
    "samePeak": "placebo / peer case on the same public t_peak",
    "threatenedBy": "inbound pair link onto a protected asset",
}


def groq_api_key() -> str:
    return (os.environ.get("GROQ_API_KEY") or "").strip()


def tavily_api_key() -> str:
    return (os.environ.get("TAVILY_API_KEY") or "").strip()


def groq_model() -> str:
    return (os.environ.get("GROQ_MODEL") or DEFAULT_GROQ_MODEL).strip()


def tavily_search(query: str, *, max_results: int = 3) -> List[Dict[str, str]]:
    """Public-web snippets. Empty list if key missing or the call fails."""
    key = tavily_api_key()
    q = (query or "").strip()
    if not key or not q:
        return []
    try:
        res = requests.post(
            TAVILY_URL,
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            },
            json={
                "query": q[:400],
                "max_results": int(max_results),
                "search_depth": "basic",
                "include_answer": False,
            },
            timeout=TIMEOUT,
        )
        res.raise_for_status()
        payload = res.json()
    except Exception:
        return []
    out: List[Dict[str, str]] = []
    for hit in payload.get("results") or []:
        url = str(hit.get("url") or "").strip()
        title = str(hit.get("title") or url or "source").strip()
        content = str(hit.get("content") or "").strip()
        if not url and not content:
            continue
        out.append({"title": title[:160], "url": url, "content": content[:400]})
    return out[:max_results]


def format_web_hits(hits: List[Dict[str, str]]) -> str:
    if not hits:
        return ""
    lines = ["WEB CONTEXT (public pages only; do not invent scores from these):"]
    for h in hits:
        lines.append(f"- {h.get('title')} — {h.get('url')}")
        if h.get("content"):
            lines.append(f"  {h['content'][:220]}")
    return "\n".join(lines)


def local_graph_brief(payload: Dict[str, Any], web_hits: Optional[List[Dict[str, str]]] = None) -> str:
    name = payload.get("object_name") or "Unknown object"
    norad = payload.get("norad")
    role = payload.get("role") or "unknown"
    status = payload.get("status") or "—"
    links: List[Dict[str, Any]] = list(payload.get("links") or [])
    scores = payload.get("scores") or {}
    q = (payload.get("question") or "").strip()

    lines = [
        f"{name} (NORAD {norad}) · role {role} · status {status}.",
        "This is the typed object graph. Scores below are copies of the risk report.",
    ]
    if links:
        lines.append("Links:")
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
    bits = []
    if att is not None:
        bits.append(f"attention={float(att):.3f}")
    if anom is not None:
        bits.append(f"anomaly={float(anom):.3f}")
    if bel is not None:
        bits.append(f"DS belief={float(bel):.3f}")
    if bits:
        lines.append("Immutable scores: " + " · ".join(bits) + ".")
    if web_hits:
        lines.append("Public web context:")
        for h in web_hits[:3]:
            lines.append(f"- {h.get('title')} ({h.get('url')})")
    lines.append("Pattern-of-life is not intent. The copilot does not change Isolation Forest scores.")
    if q:
        lines.append(f"Operator question: {q}")
    return "\n".join(lines)


def build_graph_prompt(
    payload: Dict[str, Any],
    *,
    web_hits: Optional[List[Dict[str, str]]] = None,
) -> str:
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
        "Explain this object's graph links for an SDA operator."
    )
    rag_q = " ".join([str(name), str(role), str(status), q, "space domain awareness"])
    cites = format_citations(retrieve(rag_q, k=3))
    web = format_web_hits(web_hits or [])

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

    return f"""You are the Athena-SDA graph copilot. Explain the current object graph.
You never invent or change numeric scores. Pattern-of-life is not intent.

CURRENT OBJECT:
- {name} NORAD {norad} · role {role} · {country} · {orbit} · status {status}
- attention={scores.get('attention')} anomaly={scores.get('anomaly')} belief={scores.get('belief')}

GRAPH NODES:
{chr(10).join(node_lines) or '- (none)'}

GRAPH LINKS:
{chr(10).join(link_lines) or '- (none)'}

RULES:
- English, 80–140 words, operator tone.
- Answer from THIS graph first. Use WEB CONTEXT only for public identity / history.
- Never invent or change numeric scores.
- Do not claim espionage or classified intent.
- If a Case link exists, say it is a public-anchor walk-forward, not ground truth.

OPERATOR QUESTION:
{q}

{cites}

{web}

ANSWER:"""


def groq_complete(prompt: str) -> Optional[str]:
    key = groq_api_key()
    if not key:
        return None
    try:
        res = requests.post(
            GROQ_URL,
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            },
            json={
                "model": groq_model(),
                "temperature": 0.2,
                "max_tokens": 420,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You explain an SDA object graph. "
                            "Never invent or rewrite anomaly/attention/belief scores."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
            },
            timeout=TIMEOUT,
        )
        res.raise_for_status()
        data = res.json()
        text = (
            ((data.get("choices") or [{}])[0].get("message") or {}).get("content") or ""
        ).strip()
        return text or None
    except Exception as exc:
        logger.warning("groq complete failed: %s", exc)
        return None


def _web_query(payload: Dict[str, Any]) -> str:
    name = str(payload.get("object_name") or "").strip()
    norad = payload.get("norad")
    q = str(payload.get("question") or "").strip()
    bits = [name, f"NORAD {norad}" if norad is not None else "", "satellite"]
    if q:
        bits.append(q)
    return " ".join(b for b in bits if b)


def explain_graph(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Return {text, model, source, citations}. source is groq or fallback."""
    question = str(payload.get("question") or "").strip()
    web_hits: List[Dict[str, str]] = []
    if question and tavily_api_key():
        web_hits = tavily_search(_web_query(payload))

    prompt = build_graph_prompt(payload, web_hits=web_hits)
    text = groq_complete(prompt)
    if text:
        return {
            "text": text,
            "model": groq_model(),
            "source": "groq",
            "citations": web_hits,
        }
    return {
        "text": local_graph_brief(payload, web_hits),
        "model": "local-graph",
        "source": "fallback",
        "citations": web_hits,
    }
