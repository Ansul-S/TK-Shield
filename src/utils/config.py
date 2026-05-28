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

    # API endpoints
    USPTO_API_BASE   = os.getenv("USPTO_API_BASE", "https://search.patentsview.org/api/v1")
    EPO_API_BASE     = os.getenv("EPO_API_BASE", "https://ops.epo.org/3.2/rest-services")
    GBIF_API_BASE    = os.getenv("GBIF_API_BASE", "https://api.gbif.org/v1")

    # ChromaDB
    CHROMA_DB_PATH   = os.getenv("CHROMA_DB_PATH", "./chroma_db")

    # Search
    EMBEDDING_MODEL  = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
    SEMANTIC_WEIGHT  = float(os.getenv("SEMANTIC_WEIGHT", "0.7"))
    KEYWORD_WEIGHT   = float(os.getenv("KEYWORD_WEIGHT", "0.3"))

    # Ingestion
    BATCH_SIZE       = int(os.getenv("BATCH_SIZE", "50"))
    MAX_RETRIES      = int(os.getenv("MAX_RETRIES", "3"))
    REQUEST_DELAY    = float(os.getenv("REQUEST_DELAY", "0.5"))

    # IPC codes for TK-relevant patents
    # These are the categories where bio-piracy most commonly occurs
    TK_IPC_CODES = [
        "A61K36",   # Medicinal plants
        "A01H5",    # Plant varieties
        "C12N15",   # Genetic sequences
        "A23L33",   # Nutritional additives
        "A61K31",   # Organic chemistry medicines
    ]

    # Paths
    DATA_RAW_PATH       = Path("data/raw")
    DATA_PROCESSED_PATH = Path("data/processed")


config = Config()