# Tests for the examiner novelty assessment — mocked vector store + LLM.

from src.rag import novelty


class _FakeLLM:
    def __init__(self, available): self._a = available
    def is_available(self): return self._a
    def generate(self, prompt, system=None): return "LLM examiner note."


def _matches(top_sim):
    return [{
        "document": "neem oil antifungal traditional use",
        "metadata": {"tk_id": "TK-1", "practice_name": "Neem antifungal",
                     "domain": "agricultural", "country": "IN"},
        "similarity_score": top_sim,
    }]


def test_verdict_not_novel_high_similarity(monkeypatch):
    monkeypatch.setattr(novelty.vector_store, "search", lambda *a, **k: _matches(0.78))
    r = novelty.assess_novelty("neem oil as antifungal", llm=_FakeLLM(False))
    assert r["verdict"] == "LIKELY NOT NOVEL"
    assert r["confidence"] == "high"
    assert r["matches"][0]["tk_id"] == "TK-1"
    assert r["llm_used"] is False
    assert "TK-1" in r["assessment"]            # deterministic narrative names the match


def test_verdict_possible_mid_similarity(monkeypatch):
    monkeypatch.setattr(novelty.vector_store, "search", lambda *a, **k: _matches(0.50))
    assert novelty.assess_novelty("x", llm=_FakeLLM(False))["verdict"] == "POSSIBLE PRIOR ART"


def test_verdict_novel_low_similarity(monkeypatch):
    monkeypatch.setattr(novelty.vector_store, "search", lambda *a, **k: _matches(0.20))
    r = novelty.assess_novelty("unrelated widget", llm=_FakeLLM(False))
    assert r["verdict"] == "LIKELY NOVEL"


def test_uses_llm_when_available(monkeypatch):
    monkeypatch.setattr(novelty.vector_store, "search", lambda *a, **k: _matches(0.8))
    r = novelty.assess_novelty("neem oil", llm=_FakeLLM(True))
    assert r["llm_used"] is True
    assert r["assessment"] == "LLM examiner note."
