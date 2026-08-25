"""Graph copilot: Groq (LLM) + Tavily (web) over the object graph.

Scores stay immutable. The model only narrates nodes/links already on the
board. Tavily adds public-web context; it never becomes a score source.
"""
from __future__ import annotations

import os
import re
from typing import Any, Dict, List, Optional, Tuple

import requests
from dotenv import load_dotenv

from src.config import ROOT
from src.logging_setup import get_logger
from src.rag import format_citations, retrieve

load_dotenv(ROOT / ".env", override=True)
logger = get_logger(__name__)

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"
TAVILY_URL = "https://api.tavily.com/search"
DEFAULT_GROQ_MODEL = "llama-3.1-8b-instant"
DEFAULT_DEEPSEEK_MODEL = "deepseek-chat"
TIMEOUT = 20

# Plain-language only. Keys stay stable for older imports.
LINK_GLOSSARY = {
    "threatens": "getting close to a satellite we protect",
    "hasAlert": "something on this object is flagged for a closer look",
    "validatedBy": "a past public event we already tested against",
    "weather": "how active the Sun is right now",
    "fusedAs": "how strong the combined evidence is",
    "sameAsset": "another watched satellite tied to the same protected one",
    "samePeak": "a quiet comparison case on the same date",
    "threatenedBy": "another satellite flagged near this protected one",
}

ROLE_PLAIN = {
    "suspect": "a satellite we watch because it may affect something we protect",
    "asset": "a satellite we protect",
    "baseline": "a quiet reference satellite, used to learn what normal looks like",
}

STATUS_PLAIN = {
    "NOMINAL": "nothing unusual right now",
    "ANOMALY": "its recent motion looks unusual",
    "PAIR_ELEVATED": "it is flagged for getting close to a satellite we protect",
    "UNRELIABLE_DATA": "the tracking data for this object is not trustworthy",
    "ASSET_REGIME_NOISE": "the protected satellite's own motion looks noisier than usual",
    "CALIBRATION_BASELINE": "this is a calibration / reference object",
    "CHANGE_RELEVANT": "a relevant change was flagged",
    "PAIR ↑": "it is flagged for getting close to a satellite we protect",
    "MIL DETECT": "it was flagged as a military-interest detection",
    "UNRELIABLE": "the tracking data for this object is not trustworthy",
    "REGIME": "the protected satellite's own motion looks noisier than usual",
}


def deepseek_api_key() -> str:
    return (os.environ.get("DEEPSEEK_API_KEY") or "").strip()


def deepseek_model() -> str:
    return (os.environ.get("DEEPSEEK_MODEL") or DEFAULT_DEEPSEEK_MODEL).strip()


def groq_api_key() -> str:
    return (os.environ.get("GROQ_API_KEY") or "").strip()


def tavily_api_key() -> str:
    return (os.environ.get("TAVILY_API_KEY") or "").strip()


def groq_model() -> str:
    return (os.environ.get("GROQ_MODEL") or DEFAULT_GROQ_MODEL).strip()


def _round_long_floats(text: str) -> str:
    def _repl(m: re.Match[str]) -> str:
        try:
            return f"{float(m.group(0)):.2f}"
        except ValueError:
            return m.group(0)

    return re.sub(r"\d+\.\d{3,}", _repl, text or "")


def _head_name(label: str) -> str:
    raw = _round_long_floats(label or "")
    return re.split(r"\s*[·|]\s*", raw, maxsplit=1)[0].strip() or raw.strip()


def _score_words(score: Any) -> Optional[str]:
    try:
        n = float(score)
    except (TypeError, ValueError):
        return None
    if n < 0.15:
        band = "very low"
    elif n < 0.35:
        band = "low"
    elif n < 0.55:
        band = "moderate"
    elif n < 0.75:
        band = "high"
    else:
        band = "very high"
    return f"{band} ({n:.2f})"


def _role_plain(role: Any) -> str:
    key = str(role or "").strip().lower()
    return ROLE_PLAIN.get(key, "a satellite on the watch list")


def _status_plain(status: Any) -> str:
    key = str(status or "").strip().upper()
    if key in STATUS_PLAIN:
        return STATUS_PLAIN[key]
    cleaned = key.replace("_", " ").strip().lower()
    return cleaned or "status not given"


def _weather_plain(label: str) -> str:
    text = label or ""
    m = re.search(r"F10\.7\s*([0-9.]+)", text, re.I)
    storm = "storm" in text.lower()
    if m:
        try:
            f107 = float(m.group(1))
        except ValueError:
            f107 = None
        if f107 is not None:
            if storm or f107 >= 180:
                mood = "very active (storm-level)"
            elif f107 >= 120:
                mood = "active"
            elif f107 >= 80:
                mood = "fairly quiet"
            else:
                mood = "quiet"
            return f"the Sun is {mood} (radio index F10.7 = {f107:.0f})"
    if "quiet" in text.lower():
        return "the Sun is quiet"
    if storm:
        return "there is a geomagnetic storm"
    return "space weather looks ordinary"


def _belief_from_label(label: str) -> Optional[str]:
    m = re.search(r"Bel(?:ief)?\s*([0-9.]+)", label or "", re.I)
    if not m:
        return None
    return _score_words(m.group(1))


def _plain_fact(kind: str, label: str) -> str:
    name = _head_name(label)
    km = re.search(r"(\d+(?:\.\d+)?)\s*km", label or "", re.I)
    dist = ""
    if km:
        try:
            dist = f" about {int(round(float(km.group(1))))} km away"
        except ValueError:
            dist = ""
    if kind == "threatens":
        return (
            f"It is flagged near {name}{dist}, a satellite we protect. "
            "That is a close-approach watch, not proof of an attack."
        )
    if kind == "threatenedBy":
        return f"{name} is flagged near this protected satellite{dist}."
    if kind == "hasAlert":
        return f"There is an alert: {_status_plain(name)}."
    if kind == "weather":
        return (
            f"Space weather: {_weather_plain(label)}. "
            "Use this to tell solar drag apart from a real maneuver."
        )
    if kind == "fusedAs":
        bel = _belief_from_label(label)
        if bel is None:
            raw = re.search(r"([0-9]*\.?[0-9]+)", label or "")
            bel = _score_words(raw.group(1) if raw else None)
        if bel:
            return (
                f"Combined evidence that something is wrong is {bel}. "
                "A very low number means do not treat this as confirmed."
            )
        return "Combined evidence is weak — not a confirmed problem."
    if kind == "sameAsset":
        return f"{name} is another watched satellite tied to the same protected one."
    if kind == "validatedBy":
        return f"There is a past public case on file: {name}."
    if kind == "samePeak":
        return f"A quiet comparison case on the same date: {name}."
    return _round_long_floats(name or label)


def _facts(payload: Dict[str, Any]) -> Tuple[str, List[str], List[str]]:
    name = str(payload.get("object_name") or "This object")
    norad = payload.get("norad")
    role = payload.get("role") or "unknown"
    status = payload.get("status") or "—"
    orbit = payload.get("orbit_class") or ""
    country = payload.get("country") or ""
    scores = payload.get("scores") or {}
    who = f"{name}" + (f" (catalog #{norad})" if norad is not None else "")
    where = " · ".join(p for p in (str(country).strip(), str(orbit).strip()) if p and p != "—")
    header = f"{who} is {_role_plain(role)}" + (f" · {where}" if where else "") + "."
    header += f" Right now: {_status_plain(status)}."

    score_lines: List[str] = []
    att = _score_words(scores.get("attention"))
    anom = _score_words(scores.get("anomaly"))
    bel = _score_words(scores.get("belief"))
    if att:
        score_lines.append(f"attention needed: {att}")
    if anom:
        score_lines.append(f"how unusual the orbit looks: {anom}")
    if bel:
        score_lines.append(f"combined evidence: {bel}")

    facts: List[str] = []
    seen: set[str] = set()
    for lk in payload.get("links") or []:
        kind = str(lk.get("type") or "link")
        line = _plain_fact(kind, str(lk.get("label") or ""))
        if line and line not in seen:
            seen.add(line)
            facts.append(line)
    return header, score_lines, facts


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
    header, score_lines, facts = _facts(payload)
    q = (payload.get("question") or "").strip()
    lines = [header, ""]
    if facts:
        lines.append("What matters now:")
        for fact in facts[:6]:
            lines.append(f"• {fact}")
        lines.append("")
    if score_lines:
        lines.append("Scores (unchanged copies of the risk report): " + "; ".join(score_lines) + ".")
    if web_hits:
        lines.append("Public pages:")
        for h in web_hits[:3]:
            lines.append(f"• {h.get('title')} ({h.get('url')})")
    bottom = "Unusual motion is not the same as hostile intent."
    if score_lines:
        bottom += " These scores are not recalculated here."
    if facts and any("close" in f.lower() or "protect" in f.lower() for f in facts):
        lines.append(f"Bottom line: watch the close-approach pair. {bottom}")
    else:
        lines.append(f"Bottom line: {bottom}")
    if q:
        lines.append(f"Your question: {q}")
    return "\n".join(lines).strip()


def build_graph_prompt(
    payload: Dict[str, Any],
    *,
    web_hits: Optional[List[Dict[str, str]]] = None,
) -> str:
    name = payload.get("object_name") or "Unknown"
    q = (payload.get("question") or "").strip() or (
        "Give a complete briefing: what is this object, characteristics, launch history, and what does the graph & risk show?"
    )
    rag_q = " ".join([str(name), str(payload.get("role") or ""), q, "satellite"])
    cites = format_citations(retrieve(rag_q, k=3))
    web = format_web_hits(web_hits or [])
    header, score_lines, facts = _facts(payload)
    fact_block = "\n".join(f"- {f}" for f in facts) or "- No extra facts on the board."
    score_block = "\n".join(f"- {s}" for s in score_lines) or "- no scores attached"

    return f"""You are Athena's Space Domain Awareness (SDA) Expert Copilot.
You assist satellite operators, intelligence analysts, and domain experts.

SATELLITE UNDER INVESTIGATION:
- Name: {name}
- Catalog/NORAD ID: {payload.get('norad')}
- Country / Operator: {payload.get('country') or 'Unknown'}
- Orbit Regime: {payload.get('orbit_class') or 'Unknown'}
- Operational Role: {payload.get('role') or 'Unknown'}
- Current Alert Status: {payload.get('status') or 'NOMINAL'}

COMPUTED SCORES (Immutable from ML pipeline - copy exactly, never invent):
{score_block}

OBJECT ONTOLOGY GRAPH & LIVE CONTACTS:
{header}
{fact_block}

TIMEOUT = 35

INSTRUCTIONS:
1. Language: Answer in the same language as the user's question (if asked in Portuguese, answer in fluent Portuguese; if asked in English, answer in English).
2. Completeness: Always complete all sentences and sections thoroughly. Do not leave thoughts unfinished.
3. Structure your response into clear, well-formatted Markdown sections:
   - **1. Contexto & Ficha Técnica do Satélite:** Identificação, NORAD, Operador, Data e local de lançamento, Veículo lançador, Regime orbital e Capacidade/Propósito da missão.
   - **2. Análise do Grafo de Ontologia:** Interpretação detalhada das conexões (ativos protegidos sob vigilância, alertas ativos, satélites relacionados da mesma constelação/operador e influência do clima espacial F10.7 na discriminação de arrasto vs manobra).
   - **3. Scores Matemáticos do Modelo (Imutáveis):** Explicação contextualizada de Atenção, Anomalia e Evidência Combinada (Dempster-Shafer).
   - **4. Implicações Operacionais & Riscos Orbitais:** Detalhar o que o alerta indica e o que NÃO indica (ex: aproximação vs ataque hostil; probabilidade de manobra vs ruído).
   - **5. Conclusão & Recomendação Tática.**
4. Score Integrity: Never invent or recalculate numerical scores; reference the computed anomaly, attention, and evidence scores given above.

USER QUESTION:
{q}

{cites}

{web}

EXPERT BRIEFING:"""


def deepseek_complete(prompt: str) -> Optional[str]:
    key = deepseek_api_key()
    if not key:
        return None
    try:
        res = requests.post(
            DEEPSEEK_URL,
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            },
            json={
                "model": deepseek_model(),
                "temperature": 0.3,
                "max_tokens": 2500,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are Athena-SDA Copilot, a senior military and space domain awareness analyst AI. "
                            "You provide elaborate, complete, highly organized, and professionally formatted briefings "
                            "in the operator's language. Never leave an analysis cut off or incomplete."
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
        logger.warning("deepseek complete failed: %s", exc)
        return None


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
                "max_tokens": 1500,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are Athena-SDA Copilot, an expert AI in Space Domain Awareness. "
                            "Answer accurately in the user's language with complete structured sections without altering mathematical scores."
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
    """Return {text, model, source, citations}. source is deepseek, groq or fallback."""
    question = str(payload.get("question") or "").strip()
    web_hits: List[Dict[str, str]] = []
    if question and tavily_api_key():
        web_hits = tavily_search(_web_query(payload))

    prompt = build_graph_prompt(payload, web_hits=web_hits)

    # 1. Try DeepSeek (High intelligence / knowledge)
    if deepseek_api_key():
        text = deepseek_complete(prompt)
        if text:
            return {
                "text": text,
                "model": deepseek_model(),
                "source": "deepseek",
                "citations": web_hits,
            }

    # 2. Try Groq
    if groq_api_key():
        text = groq_complete(prompt)
        if text:
            return {
                "text": text,
                "model": groq_model(),
                "source": "groq",
                "citations": web_hits,
            }

    # 3. Deterministic Local Fallback
    return {
        "text": local_graph_brief(payload, web_hits),
        "model": "local-graph",
        "source": "fallback",
        "citations": web_hits,
    }
