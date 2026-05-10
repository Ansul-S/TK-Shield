# src/embeddings/embed_pipeline.py

from sentence_transformers import SentenceTransformer
import numpy as np

# Load the model — this downloads ~90MB the first time
# all-MiniLM-L6-v2 converts any text into a 384-dimensional vector
model = SentenceTransformer('all-MiniLM-L6-v2')


def embed_text(text: str) -> list:
    """
    Convert a single piece of text into a vector (list of 384 numbers)
    These numbers capture the MEANING of the text
    """
    embedding = model.encode(text, normalize_embeddings=True)
    return embedding.tolist()


def embed_batch(texts: list) -> list:
    """
    Convert multiple texts into vectors at once
    Much faster than embedding one by one
    """
    embeddings = model.encode(texts, normalize_embeddings=True, show_progress_bar=True)
    return embeddings.tolist()


def cosine_similarity(vec1: list, vec2: list) -> float:
    """
    Measure how similar two vectors are
    Returns a score between 0 and 1:
      1.0 = identical meaning
      0.0 = completely unrelated

    Because we normalized embeddings above, similarity is just a dot product
    """
    v1 = np.array(vec1)
    v2 = np.array(vec2)
    return float(np.dot(v1, v2))


def find_most_similar(query: str, documents: list) -> list:
    """
    Given a query and a list of documents,
    rank documents by how similar they are to the query
    This is the core of semantic search
    """
    # Embed the query
    query_vector = embed_text(query)

    # Embed all documents
    doc_vectors = embed_batch(documents)

    # Calculate similarity between query and each document
    results = []
    for i, doc_vector in enumerate(doc_vectors):
        score = cosine_similarity(query_vector, doc_vector)
        results.append({
            "document": documents[i],
            "similarity_score": round(score, 4)
        })

    # Sort by similarity — highest first
    results.sort(key=lambda x: x["similarity_score"], reverse=True)

    return results


# ── Quick test ──────────────────────────────────────────────
if __name__ == "__main__":

    # This is the core problem TK-Shield solves
    # A TK entry uses folk language
    # A patent uses scientific/legal language
    # Can our embeddings see they mean the same thing?

    query = "turmeric used for wound healing"

    documents = [
        # Should match — same meaning, scientific language (patent style)
        "Curcuma longa rhizome extract applied to lacerations",

        # Should match — synonym + different phrasing
        "Haldi paste for cuts and skin abrasions",

        # Should match — related concept
        "Anti-inflammatory properties of Curcumin for tissue repair",

        # Should NOT match — completely different topic
        "Diesel engine lubrication using synthetic oil compounds",

        # Should NOT match — different plant, different use
        "Neem extract for antifungal treatment of crops",

        # Tricky — same plant, different use (should be low score)
        "Turmeric used as food coloring in industrial processing"
    ]

    print("=" * 60)
    print("TK-SHIELD — SEMANTIC SIMILARITY TEST")
    print(f"QUERY: '{query}'")
    print("=" * 60)

    results = find_most_similar(query, documents)

    for rank, result in enumerate(results, 1):
        score = result["similarity_score"]
        bar = "█" * int(score * 30)
        print(f"\nRank {rank} | Score: {score} | {bar}")
        print(f"         {result['document']}")