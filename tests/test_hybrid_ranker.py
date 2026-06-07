# Tests for Reciprocal Rank Fusion — no network, no models.

from src.search import hybrid_ranker
from src.search.hybrid_ranker import HybridSearchEngine, reciprocal_rank_fusion


def _sem(pid, doc="d"):
    return {"metadata": {"patent_id": pid}, "document": doc, "similarity_score": 0.9}


def _kw(pid, doc="d"):
    return {"id": pid, "document": doc, "bm25_score": 5.0}


def test_doc_ranked_first_by_both_wins():
    semantic = [_sem("A"), _sem("B"), _sem("C")]
    keyword = [_kw("A"), _kw("B")]
    fused = reciprocal_rank_fusion(semantic, keyword)
    assert fused[0]["metadata"]["patent_id"] == "A"
    assert all("rrf_score" in r for r in fused)
    # Scores must be monotonically non-increasing.
    scores = [r["rrf_score"] for r in fused]
    assert scores == sorted(scores, reverse=True)


def test_keyword_only_doc_is_included():
    semantic = [_sem("A")]
    keyword = [_kw("Z")]  # only in keyword results
    ids = {r["metadata"]["patent_id"] for r in reciprocal_rank_fusion(semantic, keyword)}
    assert {"A", "Z"} <= ids


def test_semantic_weight_dominates_when_higher():
    # Same single doc from each side; with default 0.7/0.3 the doc appears once,
    # combining both contributions.
    fused = reciprocal_rank_fusion([_sem("A")], [_kw("A")])
    assert len(fused) == 1
    # 0.7/(60+1) + 0.3/(60+1) = 1.0/61
    assert abs(fused[0]["rrf_score"] - (1.0 / 61)) < 1e-6


def test_search_dedupes_kind_code_variants(monkeypatch):
    # The seeded 'US5401504A' and bulk 'US5401504' are the same patent; hybrid
    # search must return it once, keeping the higher-ranked. (M4)
    engine = HybridSearchEngine([
        {"id": "US5401504A", "text": "turmeric wound healing"},
        {"id": "US5401504", "text": "turmeric wound healing bulk"},
    ])
    monkeypatch.setattr(hybrid_ranker, "semantic_search", lambda *a, **k: [
        {"metadata": {"patent_id": "US5401504A"}, "document": "turmeric", "similarity_score": 0.9},
        {"metadata": {"patent_id": "US5401504"}, "document": "turmeric bulk", "similarity_score": 0.85},
    ])
    out = engine.search("turmeric wound healing", n_results=10)
    ids = [r["metadata"]["patent_id"] for r in out]
    assert ids == ["US5401504A"]  # collapsed to the higher-ranked variant
