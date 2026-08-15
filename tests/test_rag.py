from src.rag import clear_rag_cache, retrieve


def test_retrieve_hits_docs() -> None:
    clear_rag_cache()
    hits = retrieve("past-only Isolation Forest military baseline doctrine", k=3)
    assert hits
    assert all("citation" in h and "path" in h for h in hits)
    assert any(h["path"].endswith(".md") for h in hits)


def test_retrieve_empty_query() -> None:
    assert retrieve("   ") == []
