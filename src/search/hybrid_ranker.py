# src/search/hybrid_ranker.py

from src.search.vector_store import search as semantic_search
from src.search.keyword_search import KeywordSearchEngine


def reciprocal_rank_fusion(
    semantic_results: list,
    keyword_results: list,
    k: int = 60,
    semantic_weight: float = 0.7,
    keyword_weight: float = 0.3
) -> list:
    """
    Reciprocal Rank Fusion (RRF) — combines two ranked lists into one

    The formula: score = weight / (k + rank)

    Why this works:
    - A document ranked #1 by both systems gets a very high combined score
    - A document ranked #1 by one and missing from the other still scores well
    - k=60 prevents the top rank from completely dominating

    semantic_weight=0.7 because semantic catches meaning
    keyword_weight=0.3 because keywords catch exact matches
    """
    scores = {}
    document_map = {}

    # Score semantic results
    for rank, result in enumerate(semantic_results):
        doc_id = result["metadata"]["patent_id"]
        rrf_score = semantic_weight / (k + rank + 1)
        scores[doc_id] = scores.get(doc_id, 0) + rrf_score
        document_map[doc_id] = result

    # Score keyword results
    for rank, result in enumerate(keyword_results):
        doc_id = result["id"]
        rrf_score = keyword_weight / (k + rank + 1)
        scores[doc_id] = scores.get(doc_id, 0) + rrf_score

        # If not already in map, add basic info
        if doc_id not in document_map:
            document_map[doc_id] = {
                "document": result["document"],
                "metadata": {"patent_id": doc_id},
                "similarity_score": 0
            }

    # Sort by combined RRF score
    ranked_ids = sorted(scores.items(), key=lambda x: x[1], reverse=True)

    # Build final results list
    final_results = []
    for doc_id, rrf_score in ranked_ids:
        result = document_map[doc_id]
        result["rrf_score"] = round(rrf_score, 6)
        final_results.append(result)

    return final_results


class HybridSearchEngine:
    """
    Combines semantic search (ChromaDB) and keyword search (BM25)
    This is the main search engine TK-Shield uses
    """

    def __init__(self, patents: list):
        """
        Build both search indexes from the same patent list
        """
        # Build BM25 index
        self.keyword_engine = KeywordSearchEngine(
            documents=[p["text"] for p in patents],
            ids=[p["id"] for p in patents]
        )

        # ChromaDB is already built (persistent on disk)
        self.patents = patents
        print("✅ Hybrid search engine ready")

    def search(self, query: str, n_results: int = 5) -> list:
        """
        Run both searches and fuse results
        """
        # Run semantic search
        sem_results = semantic_search("patents", query, n_results=n_results)

        # Run keyword search
        kw_results = self.keyword_engine.search(query, n_results=n_results)

        # Fuse with RRF
        hybrid_results = reciprocal_rank_fusion(sem_results, kw_results)

        return hybrid_results[:n_results]


# ── Quick test ──────────────────────────────────────────────
if __name__ == "__main__":

    patents = [
        {"id": "US5401504A",
         "text": "Method of using turmeric for wound healing and anti-inflammatory treatment"},
        {"id": "EP0436257B1",
         "text": "Antifungal properties of Azadirachta indica neem oil extract for agricultural use"},
        {"id": "US5663484A",
         "text": "Basmati rice lines and grains with specific aroma and cooking properties"},
        {"id": "US6890546B1",
         "text": "Ashwagandha root extract Withania somnifera for stress relief and adaptogenic use"},
        {"id": "US7344736B1",
         "text": "Ocimum sanctum tulsi leaf extract for respiratory infections and immunity"}
    ]

    engine = HybridSearchEngine(patents)

    # These are the interesting test cases
    # First two were failures for BM25 — let's see hybrid results
    queries = [
        ("Haldi paste for cuts and abrasions",
         "Hindi synonym — BM25 fails, semantic should save it"),

        ("curcumin tissue repair lacerations",
         "Scientific synonym — BM25 fails, semantic should save it"),

        ("turmeric wound healing",
         "Exact match — both should agree, score should be highest"),

        ("neem antifungal skin disease",
         "Partial match — tests combination strength"),
    ]

    print("=" * 60)
    print("TK-SHIELD — HYBRID SEARCH TEST")
    print("=" * 60)

    for query, description in queries:
        print(f"\nQUERY : '{query}'")
        print(f"TEST  : {description}")
        print("-" * 50)

        results = engine.search(query, n_results=2)

        for rank, result in enumerate(results, 1):
            patent_id = result.get("metadata", {}).get("patent_id", result.get("id", "?"))
            sem_score = result.get("similarity_score", 0)
            rrf_score = result.get("rrf_score", 0)

            print(f"  Rank {rank} | RRF: {rrf_score} | Semantic: {sem_score}")
            print(f"  Patent : {patent_id}")
            print(f"  Text   : {result['document'][:70]}...")