# src/utils/config.py

import os
from dotenv import load_dotenv
from pathlib import Path

# Load .env file
load_dotenv()

class Config:
    """
    Central configuration — all settings come from .env
    Nothing is hardcoded anywhere in the codebase
    """

    # ── External API endpoints ──────────────────────────────
    # Keyless & reliable (verified live 2026):
    GBIF_API_BASE    = os.getenv("GBIF_API_BASE", "https://api.gbif.org/v1")
    PUBMED_API_BASE  = os.getenv("PUBMED_API_BASE", "https://eutils.ncbi.nlm.nih.gov/entrez/eutils")
    WIKIDATA_API_BASE = os.getenv("WIKIDATA_API_BASE", "https://www.wikidata.org/w")
    # Live patents — free but requires a key (PatentsView PatentSearch).
    # The legacy keyless API was retired Feb 2025. Optional: absent a key,
    # live monitoring degrades gracefully and the core pipeline still runs.
    PATENTSVIEW_API_BASE = os.getenv("PATENTSVIEW_API_BASE", "https://search.patentsview.org/api/v1")
    PATENTSVIEW_API_KEY  = os.getenv("PATENTSVIEW_API_KEY", "")   # free key, optional
    # NCBI is keyless; supplying an email + key raises the rate limit (optional).
    NCBI_EMAIL       = os.getenv("NCBI_EMAIL", "")
    PUBMED_API_KEY   = os.getenv("PUBMED_API_KEY", "")

    # ── Enrichment toggles ──────────────────────────────────
    ENABLE_PUBMED      = os.getenv("ENABLE_PUBMED", "true").lower() == "true"
    ENABLE_WIKIDATA    = os.getenv("ENABLE_WIKIDATA", "true").lower() == "true"
    ENABLE_GBIF        = os.getenv("ENABLE_GBIF", "true").lower() == "true"
    ENABLE_PATENTSVIEW = os.getenv("ENABLE_PATENTSVIEW", "true").lower() == "true"

    # ── RAG / LLM (Ollama, local) ───────────────────────────
    OLLAMA_BASE_URL  = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL     = os.getenv("OLLAMA_MODEL", "llama3.2")
    LLM_TIMEOUT      = float(os.getenv("LLM_TIMEOUT", "120"))

    # ── ChromaDB ────────────────────────────────────────────
    CHROMA_DB_PATH   = os.getenv("CHROMA_DB_PATH", "./chroma_db")
    PATENTS_COLLECTION = os.getenv("PATENTS_COLLECTION", "patents")
    TK_COLLECTION      = os.getenv("TK_COLLECTION", "tk_entries")

    # ── Search ──────────────────────────────────────────────
    EMBEDDING_MODEL  = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
    SEMANTIC_WEIGHT  = float(os.getenv("SEMANTIC_WEIGHT", "0.7"))
    KEYWORD_WEIGHT   = float(os.getenv("KEYWORD_WEIGHT", "0.3"))
    RRF_K            = int(os.getenv("RRF_K", "60"))
    DEFAULT_N_RESULTS = int(os.getenv("DEFAULT_N_RESULTS", "5"))

    # ── Ingestion / HTTP resilience ─────────────────────────
    BATCH_SIZE       = int(os.getenv("BATCH_SIZE", "50"))
    EMBED_BATCH_SIZE = int(os.getenv("EMBED_BATCH_SIZE", "64"))
    MAX_RETRIES      = int(os.getenv("MAX_RETRIES", "3"))
    REQUEST_DELAY    = float(os.getenv("REQUEST_DELAY", "0.5"))
    HTTP_TIMEOUT     = float(os.getenv("HTTP_TIMEOUT", "15"))

    # ── Corpus scale-up ─────────────────────────────────────
    # Patent source for build_corpus:
    #   "ccdv"            — keyless HuggingFace corpus (no download; low-fidelity metadata)
    #   "patentsview_bulk"— keyless PatentsView bulk TSV (REAL metadata; ~219MB download) ← recommended
    #   "patentsview"     — PatentsView live API harvest (real metadata; needs a free key)
    PATENT_SOURCE    = os.getenv("PATENT_SOURCE", "ccdv")
    MAX_PATENTS      = int(os.getenv("MAX_PATENTS", "5000"))

    # PatentsView bulk (keyless public files; no API key/registration).
    PATENTSVIEW_BULK_BASE = os.getenv(
        "PATENTSVIEW_BULK_BASE", "https://s3.amazonaws.com/data.patentsview.org/download"
    )
    PATENTSVIEW_BULK_DIR  = os.getenv("PATENTSVIEW_BULK_DIR", "data/raw/bulk")
    BULK_ENRICH_ASSIGNEE  = os.getenv("BULK_ENRICH_ASSIGNEE", "true").lower() == "true"
    # CPC classes the PatentsView harvester pages through (bio-piracy-prone areas).
    PATENT_CPC_CLASSES = [
        c.strip() for c in os.getenv(
            "PATENT_CPC_CLASSES",
            "A61K36,A01H,A23L,A61K8,A61Q,C12N15"
        ).split(",") if c.strip()
    ]
    # Cap for TK-registry importers (Dr. Duke / Wikidata).
    TK_IMPORT_LIMIT  = int(os.getenv("TK_IMPORT_LIMIT", "500"))
    # TK registry source: "duke" (CC0 ethnobotany) or "wikidata" (SPARQL).
    TK_SOURCE        = os.getenv("TK_SOURCE", "duke")
    # Dr. Duke's CC0 data. Point DUKE_CSV_PATH at a locally-downloaded
    # ethnobotany CSV, or let the importer fetch the zip from DUKE_DATA_URL.
    DUKE_CSV_PATH    = os.getenv("DUKE_CSV_PATH", "data/raw/duke_ethnobotany.csv")
    DUKE_DATA_URL    = os.getenv(
        "DUKE_DATA_URL",
        "https://data.nal.usda.gov/system/files/Duke-Source-CSV.zip",
    )
    # Enrich imported plants with Wikidata multilingual aliases (slower; capped).
    ENRICH_MULTILINGUAL = os.getenv("ENRICH_MULTILINGUAL", "false").lower() == "true"

    # ── Registry persistence ────────────────────────────────
    TK_DB_PATH       = os.getenv("TK_DB_PATH", "data/tk_registry.sqlite3")

    # IPC codes for TK-relevant patents
    # These are the categories where bio-piracy most commonly occurs
    TK_IPC_CODES = [
        "A61K36",   # Medicinal plants
        "A01H5",    # Plant varieties
        "C12N15",   # Genetic sequences
        "A23L33",   # Nutritional additives
        "A61K31",   # Organic chemistry medicines
    ]

    # Domain → IPC/CPC prefixes, for tagging TK entries & patents across the
    # broadened coverage (medicinal / agricultural / food / cosmetic).
    DOMAIN_IPC_GROUPS = {
        "medicinal":    ["A61K36", "A61K31", "A61P"],
        "agricultural": ["A01H", "C12N15", "A01N"],
        "food":         ["A23L", "A23F", "A21D"],
        "cosmetic":     ["A61K8", "A61Q"],
    }

    # Paths
    DATA_RAW_PATH       = Path("data/raw")
    DATA_PROCESSED_PATH = Path("data/processed")
    PATENTS_CSV         = Path(os.getenv("PATENTS_CSV", "data/raw/patents_medicinal.csv"))


config = Config()