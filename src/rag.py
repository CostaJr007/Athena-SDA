"""
Tiny local RAG over docs/ — keyword retrieval with file:heading citations.

Bob / Granite must cite these chunks. They must never invent or rewrite scores.
No embeddings, no network: deterministic token overlap so CI stays offline.
"""
from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from typing import Dict, List

from src.config import DOCS_DIR, ROOT

_STOP = frozenset(
    "the a an of to and or for in on at is are was be this that with from by as it "
    "not no we you our their if then than into over under its an".split()
)
_TOKEN = re.compile(r"[a-z0-9]{3,}")
_HEADING = re.compile(r"^(#{1,4})\s+(.+)$")


def _iter_doc_files() -> List[Path]:
    roots = [DOCS_DIR, ROOT / "README.md"]
    out: List[Path] = []
    if DOCS_DIR.exists():
        for p in DOCS_DIR.rglob("*.md"):
            if "sessions" in p.parts or p.name.startswith("."):
                continue
            out.append(p)
    readme = ROOT / "README.md"
    if readme.exists():
        out.append(readme)
    return out


def _chunks_from_markdown(path: Path) -> List[Dict[str, str]]:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    rel = str(path.relative_to(ROOT)).replace("\\", "/")
    heading = path.stem
    buf: List[str] = []
    chunks: List[Dict[str, str]] = []

    def flush() -> None:
        body = "\n".join(buf).strip()
        if len(body) < 40:
            return
        chunks.append({"path": rel, "heading": heading, "text": body[:1800]})

    for line in text.splitlines():
        m = _HEADING.match(line.strip())
        if m:
            flush()
            buf = []
            heading = m.group(2).strip()
            continue
        buf.append(line)
    flush()
    return chunks


@lru_cache(maxsize=1)
def _index() -> List[Dict[str, str]]:
    chunks: List[Dict[str, str]] = []
    for p in _iter_doc_files():
        chunks.extend(_chunks_from_markdown(p))
    return chunks


def clear_rag_cache() -> None:
    _index.cache_clear()


def _tokens(text: str) -> List[str]:
    return [t for t in _TOKEN.findall(text.lower()) if t not in _STOP]


def retrieve(query: str, k: int = 4) -> List[Dict[str, str]]:
    """Return top-k chunks with a citation key `path#heading`."""
    q = _tokens(query or "")
    if not q:
        return []
    qset = set(q)
    scored: List[tuple] = []
    for ch in _index():
        toks = _tokens(ch["heading"] + " " + ch["text"])
        if not toks:
            continue
        overlap = len(qset.intersection(toks))
        if overlap <= 0:
            continue
        # Prefer heading hits
        head_hit = 1 if qset.intersection(_tokens(ch["heading"])) else 0
        scored.append((overlap + 2 * head_hit, ch))
    scored.sort(key=lambda x: -x[0])
    out: List[Dict[str, str]] = []
    for _score, ch in scored[:k]:
        cite = f"{ch['path']}#{ch['heading']}"
        out.append(
            {
                "path": ch["path"],
                "heading": ch["heading"],
                "citation": cite,
                "excerpt": ch["text"][:400].strip(),
            }
        )
    return out


def format_citations(hits: List[Dict[str, str]]) -> str:
    if not hits:
        return ""
    lines = ["SOURCES (cite these; do not invent scores):"]
    for h in hits:
        lines.append(f"- [{h['citation']}] {h['excerpt'][:180].replace(chr(10), ' ')}")
    return "\n".join(lines)
