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


# ── Claim-level assessment (Tier 2) ──────────────────────────────────────────

_MULTI_CLAIM_PATENT = """What is claimed is:
1. A method of controlling fungi on a plant comprising applying a hydrophobic
   extracted neem oil to the plant.
2. The method of claim 1, wherein the neem oil is storage stable.
"""


def test_claim_level_splits_and_aggregates(monkeypatch):
    # Both claims score high → both LIKELY NOT NOVEL → overall LIKELY NOT NOVEL.
    monkeypatch.setattr(novelty.vector_store, "search", lambda *a, **k: _matches(0.78))
    r = novelty.assess_novelty_by_claim(_MULTI_CLAIM_PATENT, llm=_FakeLLM(False))
    assert r["claim_level"] is True
    assert [c["number"] for c in r["claims"]] == [1, 2]
    assert r["claims"][1]["is_dependent"] is True and r["claims"][1]["depends_on"] == 1
    assert r["verdict"] == "LIKELY NOT NOVEL"
    assert r["claims"][0]["verdict"] == "LIKELY NOT NOVEL"


def test_overall_verdict_driven_by_independent_claim(monkeypatch):
    # Independent claim 1 weak, dependent claim 2 would score high — but the
    # overall verdict must follow the INDEPENDENT claim. Score by claim text.
    def _search(_collection, text, n_results=5):
        return _matches(0.78) if "storage stable" in text else _matches(0.20)
    monkeypatch.setattr(novelty.vector_store, "search", _search)
    r = novelty.assess_novelty_by_claim(_MULTI_CLAIM_PATENT, llm=_FakeLLM(False))
    assert r["claims"][0]["verdict"] == "LIKELY NOVEL"      # independent claim 1
    assert r["claims"][1]["verdict"] == "LIKELY NOT NOVEL"  # dependent claim 2
    assert r["verdict"] == "LIKELY NOVEL"                   # follows the independent claim


def test_no_claim_structure_falls_back(monkeypatch):
    monkeypatch.setattr(novelty.vector_store, "search", lambda *a, **k: _matches(0.78))
    abstract = "A method of promoting wound healing by administering turmeric."
    r = novelty.assess_novelty_by_claim(abstract, llm=_FakeLLM(False))
    assert r["claim_level"] is False
    assert r["claims"] == []
    # Output otherwise matches the whole-text path.
    base = novelty.assess_novelty(abstract, llm=_FakeLLM(False))
    assert r["verdict"] == base["verdict"]
    assert r["matches"] == base["matches"]
