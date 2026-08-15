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


def test_local_brief_copies_scores() -> None:
    text = local_graph_brief(_payload())
    assert "0.420" in text or "0.42" in text
    assert "does not change Isolation Forest scores" in text


def test_explain_graph_returns_contract() -> None:
    out = explain_graph({**_payload(), "question": ""})
    assert out["source"] in ("groq", "fallback")
    assert out["text"]
    assert "citations" in out
    if out["source"] == "fallback":
        assert "0.42" in out["text"] or "anomaly=0.42" in out["text"].replace(" ", "")


def test_format_web_hits() -> None:
    block = format_web_hits(
        [{"title": "Luch", "url": "https://example.test/luch", "content": "GEO relay"}]
    )
    assert "example.test/luch" in block
    assert "do not invent scores" in block
