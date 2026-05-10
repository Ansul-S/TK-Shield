# src/search/vector_store.py

import chromadb
from chromadb.config import Settings
from src.embeddings.embed_pipeline import embed_text, embed_batch

# Initialize ChromaDB — stores data locally in a folder called chroma_db
client = chromadb.PersistentClient(path="./chroma_db")


def get_or_create_collection(name: str):
    """
    Get an existing collection or create a new one
    Think of a collection like a table in a regular database
    We'll have two: one for patents, one for TK entries
    """
    collection = client.get_or_create_collection(
        name=name,
        metadata={"hnsw:space": "cosine"}  # Use cosine similarity for comparisons
    )
    return collection


def add_documents(collection_name: str, documents: list, metadatas: list, ids: list):
    """
    Add documents to a collection
    ChromaDB automatically generates and stores embeddings

    documents  → the actual text
    metadatas  → extra info (patent_id, date, country, etc.)
    ids        → unique identifier for each document
    """
    collection = get_or_create_collection(collection_name)

    # Generate embeddings for all documents
    print(f"Generating embeddings for {len(documents)} documents...")
    embeddings = embed_batch(documents)

    # Store in ChromaDB
    collection.add(
        documents=documents,
        embeddings=embeddings,
        metadatas=metadatas,
        ids=ids
    )

    print(f"✅ Added {len(documents)} documents to '{collection_name}' collection")


def search(collection_name: str, query: str, n_results: int = 5) -> list:
    """
    Search a collection for documents similar to the query
    Returns top n_results matches with similarity scores
    """
    collection = get_or_create_collection(collection_name)

    # Embed the query
    query_embedding = embed_text(query)

    # Search ChromaDB — this is instant even with millions of documents
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results,
        include=["documents", "metadatas", "distances"]
    )

    # Format results nicely
    formatted = []
    for i in range(len(results["documents"][0])):
        # ChromaDB returns distance (lower = more similar)
        # We convert to similarity score (higher = more similar)
        similarity = round(1 - results["distances"][0][i], 4)

        formatted.append({
            "document": results["documents"][0][i],
            "metadata": results["metadatas"][0][i],
            "similarity_score": similarity
        })

    return formatted


def get_collection_count(collection_name: str) -> int:
    """
    How many documents are stored in a collection
    """
    collection = get_or_create_collection(collection_name)
    return collection.count()


# ── Quick test ──────────────────────────────────────────────
if __name__ == "__main__":

    # Simulate a small patent database
    # In real TK-Shield this will be 120,000+ patents
    sample_patents = [
        {
            "id": "US5401504A",
            "text": "Method of using turmeric for wound healing and anti-inflammatory treatment",
            "metadata": {
                "patent_id": "US5401504A",
                "title": "Use of turmeric in wound healing",
                "assignee": "University of Mississippi",
                "filing_date": "1993-01-04",
                "country": "US",
                "status": "REVOKED"
            }
        },
        {
            "id": "EP0436257B1",
            "text": "Antifungal properties of Azadirachta indica neem oil extract for agricultural use",
            "metadata": {
                "patent_id": "EP0436257B1",
                "title": "Neem oil antifungal agent",
                "assignee": "W.R. Grace & Co.",
                "filing_date": "1990-06-12",
                "country": "EP",
                "status": "CANCELLED"
            }
        },
        {
            "id": "US5663484A",
            "text": "Basmati rice lines and grains with specific aroma and cooking properties",
            "metadata": {
                "patent_id": "US5663484A",
                "title": "Basmati rice varieties",
                "assignee": "RiceTec Inc.",
                "filing_date": "1994-08-25",
                "country": "US",
                "status": "PARTIALLY_REVOKED"
            }
        },
        {
            "id": "US6890546B1",
            "text": "Ashwagandha root extract Withania somnifera for stress relief and adaptogenic use",
            "metadata": {
                "patent_id": "US6890546B1",
                "title": "Ashwagandha adaptogen supplement",
                "assignee": "NutraCorp Ltd.",
                "filing_date": "2001-11-30",
                "country": "US",
                "status": "ACTIVE"
            }
        },
        {
            "id": "US7344736B1",
            "text": "Ocimum sanctum tulsi leaf extract for respiratory infections and immunity",
            "metadata": {
                "patent_id": "US7344736B1",
                "title": "Holy basil extract for immunity",
                "assignee": "HerbalTech Inc.",
                "filing_date": "2003-05-10",
                "country": "US",
                "status": "ACTIVE"
            }
        }
    ]

    # Add patents to ChromaDB
    print("=" * 60)
    print("TK-SHIELD — VECTOR STORE TEST")
    print("=" * 60)

    add_documents(
        collection_name="patents",
        documents=[p["text"] for p in sample_patents],
        metadatas=[p["metadata"] for p in sample_patents],
        ids=[p["id"] for p in sample_patents]
    )

    print(f"\nTotal patents in database: {get_collection_count('patents')}")

    # Now search — this is what happens when a user types a TK query
    queries = [
        "turmeric paste used for wound healing in Ayurveda",
        "neem leaves for skin infection and antifungal treatment",
        "traditional basmati rice from Punjab India"
    ]

    print("\n" + "=" * 60)
    print("SEARCH RESULTS")
    print("=" * 60)

    for query in queries:
        print(f"\nQUERY: '{query}'")
        print("-" * 50)

        results = search("patents", query, n_results=2)

        for rank, result in enumerate(results, 1):
            print(f"  Rank {rank} | Score: {result['similarity_score']}")
            print(f"  Patent : {result['metadata']['patent_id']}")
            print(f"  Title  : {result['metadata']['title']}")
            print(f"  Status : {result['metadata']['status']}")
            print(f"  Match  : {result['document']}")
            print()