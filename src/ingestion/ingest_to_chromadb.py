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

    def _s(val, default=""):
        # NaN/empty cells must not become the literal string "nan".
        if val is None or (isinstance(val, float) and pd.isna(val)):
            return default
        s = str(val).strip()
        return default if s.lower() == "nan" else s

    patents = []
    excluded_sources = 0
    for _, row in df.iterrows():
        text = _s(row.get("text", ""))

        # Drop synthetic/low-fidelity sources so the corpus is genuinely real
        # patent metadata (e.g. the ccdv HF fallback). Configurable via
        # config.EXCLUDE_PATENT_SOURCES; landmark/bulk rows are unaffected.
        src = _s(row.get("source", "")).lower()
        if src and any(bad in src for bad in config.EXCLUDE_PATENT_SOURCES):
            excluded_sources += 1
            continue

        # Apply strict filter
        if not is_strictly_tk_relevant(text):
            continue

        patents.append({
            "id":   _s(row["id"]),
            "text": text,
            "metadata": {
                "patent_id":   _s(row.get("patent_id", "")),
                "title":       _s(row.get("title", ""))[:config.TITLE_MAX_CHARS],
                "abstract":    _s(row.get("abstract", ""))[:config.ABSTRACT_MAX_CHARS],
                "assignee":    _s(row.get("assignee", "Unknown")) or "Unknown",
                "filing_date": _s(row.get("filing_date", "")),
                "country":     _s(row.get("country", "US")) or "US",
                "ipc_code":    _s(row.get("ipc_code", "")),
                "source":      _s(row.get("source", "")),
                "status":      _s(row.get("status", "UNKNOWN")) or "UNKNOWN",
            }
        })

    logger.success(
        f"After strict TK filter: {len(patents)} patents kept "
        f"({excluded_sources} excluded by source filter)"
    )
    return patents


def embed_and_store(patents: list[dict], batch_size: int | None = None,
                    rebuild: bool = True):
    """
    Generate embeddings and store in ChromaDB, in batches.

    rebuild=True  → drop and recreate the collection (deterministic full build).
    rebuild=False → resume: skip ids already present, only embed the rest. Lets
                    a large (tens of thousands) run recover after an interrupt.
    """
    batch_size = batch_size or config.EMBED_BATCH_SIZE
    collection_name = config.PATENTS_COLLECTION
    client = chromadb.PersistentClient(path=config.CHROMA_DB_PATH)

    if rebuild:
        try:
            client.delete_collection(collection_name)
            logger.info(f"Deleted existing '{collection_name}' collection")
        except Exception:
            pass

    collection = client.get_or_create_collection(
        name=collection_name, metadata={"hnsw:space": config.CHROMA_DISTANCE}
    )

    if not rebuild:
        existing = set(collection.get(include=[])["ids"])
        before = len(patents)
        patents = [p for p in patents if p["id"] not in existing]
        logger.info(f"Resume: {len(existing)} already indexed, {len(patents)}/{before} to add")

    logger.info(f"Loading embedding model: {config.EMBEDDING_MODEL}")
    model = SentenceTransformer(config.EMBEDDING_MODEL)

    total = len(patents)
    inserted = 0
    logger.info(f"Embedding and storing {total} patents in batches of {batch_size}...")

    for i in tqdm(range(0, total, batch_size), desc="Indexing patents"):
        batch = patents[i : i + batch_size]
        texts = [p["text"] for p in batch]
        embeddings = model.encode(texts, normalize_embeddings=True, show_progress_bar=False).tolist()
        collection.add(
            documents=texts,
            embeddings=embeddings,
            metadatas=[p["metadata"] for p in batch],
            ids=[p["id"] for p in batch],
        )
        inserted += len(batch)

    logger.success(f"Stored {inserted} patents in '{collection_name}' ({config.CHROMA_DB_PATH})")
    return inserted


def verify_search(collection_name: str = None):
    collection_name = collection_name or config.PATENTS_COLLECTION
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

    csv_path = str(config.PATENTS_CSV)

    if not Path(csv_path).exists():
        logger.error(f"CSV not found at {csv_path}")
        logger.error("Run `python -m src.ingestion.build_corpus` first")
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