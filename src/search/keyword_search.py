# src/search/keyword_search.py

from rank_bm25 import BM25Okapi
import re


def tokenize_for_bm25(text: str) -> list:
    """
    Simple tokenization for BM25
    Lowercase + split on whitespace and punctuation
    """
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    tokens = text.split()
    return tokens


class KeywordSearchEngine:
    """
    BM25 search engine — finds documents with matching keywords

    BM25 improves on simple word counting by:
    1. Penalizing common words that appear in every document
    2. Rewarding rare words that appear in few documents
    3. Normalizing for document length

    Example:
    Query: "neem antifungal"
    - Document with "neem" appearing 5 times scores higher
    - But not infinitely higher — BM25 has diminishing returns
    """

    def __init__(self, documents: list, ids: list):
        """
        Build the BM25 index from a list of documents
        documents → list of text strings
        ids       → unique identifier for each document
        """
        self.documents = documents
        self.ids = ids

        # Tokenize all documents
        tokenized = [tokenize_for_bm25(doc) for doc in documents]

        # Build the BM25 index
        self.bm25 = BM25Okapi(tokenized)
        print(f"✅ BM25 index built with {len(documents)} documents")

    def search(self, query: str, n_results: int = 5) -> list:
        """
        Search for documents matching the query keywords
        Returns top n_results sorted by BM25 score
        """
        # Tokenize the query the same way as documents
        tokenized_query = tokenize_for_bm25(query)

        # Get BM25 scores for all documents
        scores = self.bm25.get_scores(tokenized_query)

        # Pair each document with its score
        results = []
        for i, score in enumerate(scores):
            if score > 0:  # Only include documents with at least some match
                results.append({
                    "id": self.ids[i],
                    "document": self.documents[i],
                    "bm25_score": round(float(score), 4)
                })

        # Sort by score — highest first
        results.sort(key=lambda x: x["bm25_score"], reverse=True)

        return results[:n_results]


# ── Quick test ──────────────────────────────────────────────
if __name__ == "__main__":

    # Same 5 patents as before
    patents = [
        {
            "id": "US5401504A",
            "text": "Method of using turmeric for wound healing and anti-inflammatory treatment"
        },
        {
            "id": "EP0436257B1",
            "text": "Antifungal properties of Azadirachta indica neem oil extract for agricultural use"
        },
        {
            "id": "US5663484A",
            "text": "Basmati rice lines and grains with specific aroma and cooking properties"
        },
        {
            "id": "US6890546B1",
            "text": "Ashwagandha root extract Withania somnifera for stress relief and adaptogenic use"
        },
        {
            "id": "US7344736B1",
            "text": "Ocimum sanctum tulsi leaf extract for respiratory infections and immunity"
        }
    ]

    # Build the engine
    engine = KeywordSearchEngine(
        documents=[p["text"] for p in patents],
        ids=[p["id"] for p in patents]
    )

    # Test queries
    queries = [
        "turmeric wound healing",           # exact words match
        "neem antifungal azadirachta",       # scientific name match
        "basmati rice Punjab India",         # partial match
        "Haldi paste cuts abrasions",        # Hindi synonym — should FAIL
        "curcumin tissue repair lacerations" # semantic synonym — should FAIL
    ]

    print("\n" + "=" * 60)
    print("TK-SHIELD — BM25 KEYWORD SEARCH TEST")
    print("=" * 60)

    for query in queries:
        print(f"\nQUERY: '{query}'")
        print("-" * 50)

        results = engine.search(query, n_results=3)

        if not results:
            print("  ❌ No keyword matches found")
        else:
            for rank, result in enumerate(results, 1):
                print(f"  Rank {rank} | BM25 Score: {result['bm25_score']}")
                print(f"  ID   : {result['id']}")
                print(f"  Text : {result['document']}")