# scripts/ingest_to_chromadb.py

import pandas as pd
import chromadb
from sentence_transformers import SentenceTransformer
from loguru import logger
from pathlib import Path
from tqdm import tqdm
from src.utils.config import config

# ── Better TK relevance filter ────────────────────────────────
# These are highly specific TK/bio-piracy terms
# Much stricter than the keyword list in scraper
STRICT_TK_KEYWORDS = [
    # Plants and botanicals
    "plant extract", "herbal", "botanical", "medicinal plant",
    "plant material", "plant species", "plant variety",
    "root extract", "leaf extract", "bark extract", "seed extract",
    "flower extract", "fruit extract",

    # Specific TK plants
    "turmeric", "curcumin", "neem", "azadirachta",
    "ashwagandha", "withania", "tulsi", "ocimum sanctum",
    "brahmi", "bacopa", "giloy", "tinospora",
    "aloe vera", "ginger", "zingiber", "garlic", "allium",
    "basmati", "ayahuasca", "banisteriopsis",

    # Traditional medicine systems
    "ayurved", "traditional medicine", "folk medicine",
    "indigenous", "ethnobotanic", "ethnopharmacolog",
    "traditional knowledge", "traditional use",

    # Bio-piracy relevant uses
    "wound healing", "antimalarial", "antifungal",
    "antibacterial", "anti-inflammatory", "antiviral",
    "traditional remedy", "natural remedy",

    # Agricultural TK
    "plant variety", "cultivar", "landrace",
    "traditional crop", "indigenous crop",
    "genetic resource", "biodiversity"
]


def is_strictly_tk_relevant(text: str) -> bool:
    """
    Stricter filter — requires more specific TK terminology
    Reduces noise from generic medical/tech patents
    """
    text_lower = text.lower()
    return any(kw in text_lower for kw in STRICT_TK_KEYWORDS)


def load_patents_from_csv(csv_path: str) -> list[dict]:
    """
    Load patents from CSV and apply strict TK filter
    """
    df = pd.read_csv(csv_path)
    logger.info(f"Loaded {len(df)} patents from CSV")

    patents = []
    for _, row in df.iterrows():
        text = str(row.get("text", ""))

        # Apply strict filter
        if not is_strictly_tk_relevant(text):
            continue

        patents.append({
            "id":   str(row["id"]),
            "text": text,
            "metadata": {
                "patent_id":   str(row.get("patent_id", "")),
                "title":       str(row.get("title", ""))[:200],
                "abstract":    str(row.get("abstract", ""))[:500],
                "assignee":    str(row.get("assignee", "Unknown")),
                "filing_date": str(row.get("filing_date", "")),
                "country":     str(row.get("country", "US")),
                "ipc_code":    str(row.get("ipc_code", "")),
                "source":      str(row.get("source", "")),
                "status":      str(row.get("status", "UNKNOWN"))
            }
        })

    logger.success(f"After strict TK filter: {len(patents)} patents kept")
    return patents


def embed_and_store(patents: list[dict], batch_size: int = 64):
    """
    Generate embeddings and store in ChromaDB
    Processes in batches to handle large datasets efficiently
    """
    # Initialize ChromaDB
    client     = chromadb.PersistentClient(path=config.CHROMA_DB_PATH)

    # Delete existing collection to start fresh
    try:
        client.delete_collection("patents")
        logger.info("Deleted existing patents collection")
    except Exception:
        pass

    collection = client.get_or_create_collection(
        name="patents",
        metadata={"hnsw:space": "cosine"}
    )

    # Load embedding model
    logger.info(f"Loading embedding model: {config.EMBEDDING_MODEL}")
    model = SentenceTransformer(config.EMBEDDING_MODEL)

    total    = len(patents)
    inserted = 0

    logger.info(f"Embedding and storing {total} patents in batches of {batch_size}...")

    for i in tqdm(range(0, total, batch_size), desc="Indexing patents"):
        batch = patents[i : i + batch_size]

        texts     = [p["text"] for p in batch]
        ids       = [p["id"] for p in batch]
        metadatas = [p["metadata"] for p in batch]

        # Generate embeddings
        embeddings = model.encode(
            texts,
            normalize_embeddings=True,
            show_progress_bar=False
        ).tolist()

        # Store in ChromaDB
        collection.add(
            documents=texts,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids
        )

        inserted += len(batch)

    logger.success(f"Stored {inserted} patents in ChromaDB")
    logger.success(f"ChromaDB path: {config.CHROMA_DB_PATH}")

    return inserted


def verify_search(collection_name: str = "patents"):
    """
    Run 3 test queries to verify everything works end-to-end
    """
    client     = chromadb.PersistentClient(path=config.CHROMA_DB_PATH)
    collection = client.get_collection(collection_name)
    model      = SentenceTransformer(config.EMBEDDING_MODEL)

    test_queries = [
        "turmeric used for wound healing in Ayurvedic medicine",
        "neem extract antifungal pesticide traditional use",
        "medicinal plant extract antibacterial treatment"
    ]

    print("\n" + "=" * 60)
    print("VERIFICATION — Search Test")
    print("=" * 60)

    for query in test_queries:
        embedding = model.encode(query, normalize_embeddings=True).tolist()

        results = collection.query(
            query_embeddings=[embedding],
            n_results=3,
            include=["documents", "metadatas", "distances"]
        )

        print(f"\nQuery: '{query}'")
        print("-" * 50)

        for j in range(len(results["documents"][0])):
            score = round(1 - results["distances"][0][j], 4)
            meta  = results["metadatas"][0][j]
            text  = results["documents"][0][j][:100]
            print(f"  Score: {score} | IPC: {meta['ipc_code']}")
            print(f"  Text : {text}...")
            print()


if __name__ == "__main__":
    logger.info("TK-SHIELD — ChromaDB Ingestion")
    logger.info("=" * 55)

    csv_path = "data/raw/patents_medicinal.csv"

    if not Path(csv_path).exists():
        logger.error(f"CSV not found at {csv_path}")
        logger.error("Run python src/ingestion/patent_scraper.py first")
        exit(1)

    # Step 1: Load and strictly filter
    patents = load_patents_from_csv(csv_path)

    if not patents:
        logger.error("No patents after strict filter")
        exit(1)

    # Step 2: Embed and store
    count = embed_and_store(patents, batch_size=64)

    # Step 3: Verify with real queries
    verify_search()

    print(f"\n✅ TK-Shield patent database ready")
    print(f"   {count} patents indexed and searchable")