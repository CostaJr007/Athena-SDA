import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.graph_qa import build_graph_prompt, explain_graph, format_web_hits, local_graph_brief


def _payload():
    return {
        "norad": 40258,
        "object_name": "LUCH (OLYMP-K 1)",
        "role": "suspect",
        "status": "ANOMALY",
        "country": "RU",
        "orbit_class": "GEO",
        "scores": {"attention": 0.71, "anomaly": 0.42, "belief": 0.55},
        "nodes": [{"kind": "satellite", "label": "LUCH", "sub": "#40258"}],
        "links": [{"type": "threatens", "label": "ATHENA-FIDUS · 80 km"}],
        "question": "What does the pair link mean?",
    }


def test_prompt_forbids_score_rewrite() -> None:
    prompt = build_graph_prompt(_payload())
    assert "0.42" in prompt
    assert "Never invent or change numeric scores" in prompt
    assert "ATHENA-FIDUS" in prompt
    assert "threatens →" not in prompt


def test_local_brief_copies_scores() -> None:
    text = local_graph_brief(_payload())
    assert "0.42" in text
    assert "These scores are not recalculated here" in text
    assert "ATHENA-FIDUS" in text
    assert "fusedAs" not in text
    assert "Dempster" not in text


def test_explain_graph_returns_contract() -> None:
    out = explain_graph({**_payload(), "question": ""})
    assert out["source"] in ("deepseek", "groq", "fallback")
    assert out["text"]
    assert "citations" in out
    if out["source"] == "fallback":
        assert "0.42" in out["text"] or "anomaly=0.42" in out["text"].replace(" ", "")


def test_local_brief_is_plain_language() -> None:
    text = local_graph_brief(
        {
            "norad": 41727,
            "object_name": "GAOFEN-3",
            "role": "suspect",
            "status": "PAIR_ELEVATED",
            "country": "CN",
            "orbit_class": "LEO",
            "scores": {"attention": 0.12, "anomaly": 0.08, "belief": 0.006666710109401489},
            "links": [
                {"type": "threatens", "label": "DMSP 5D-3 F18 (USA 210) (#35951 · asset)"},
                {"type": "hasAlert", "label": "PAIR_ELEVATED · #41727 · alert"},
                {"type": "weather", "label": "F10.7 99.0 · #41727 · weather"},
                {"type": "fusedAs", "label": "Bel 0.006666710109401489 · #41727 · evidence"},
                {"type": "sameAsset", "label": "YAOGAN-29 · #41038 · suspect"},
            ],
        }
    )
    assert "GAOFEN-3" in text
    assert "DMSP" in text
    assert "0.006666710109401489" not in text
    assert "fusedAs" not in text
    assert "threatens" not in text
    assert "Dempster" not in text
    assert "Bottom line:" in text


def test_format_web_hits() -> None:
    block = format_web_hits(
        [{"title": "Luch", "url": "https://example.test/luch", "content": "GEO relay"}]
    )
    assert "example.test/luch" in block
    assert "do not invent scores" in block
