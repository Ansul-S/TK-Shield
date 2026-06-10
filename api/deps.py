# api/deps.py — cached singletons + small helpers shared by routes.

import threading
from contextlib import contextmanager
from functools import lru_cache

from loguru import logger
from slowapi import Limiter
from slowapi.util import get_remote_address

from src.ingestion.ingest_to_chromadb import load_patents_from_csv
from src.rag.llm_client import get_llm
from src.registry import tk_store
from src.search.hybrid_ranker import HybridSearchEngine
from src.utils.config import config

# Per-IP rate limiter (C7), shared by every route via `@limiter.limit(...)`.
# Keyed on the client address; in-memory (no external store, keyless). Disabled
# wholesale via RATE_LIMIT_ENABLED=false, in which case the decorators are
# no-ops. We attach explicit decorators per route rather than a global
# default-limits middleware so static assets, the SPA shell and /api/health
# polling are never throttled.
limiter = Limiter(key_func=get_remote_address, enabled=config.RATE_LIMIT_ENABLED)


class LLMBusy(RuntimeError):
    """Raised when the concurrent-LLM-request cap is reached (→ HTTP 503)."""


# Bound concurrent LLM-backed requests (/report, /novelty) so a burst of slow
# synchronous calls can't saturate the threadpool / pin the local model. Excess
# requests get a clean 503 instead of all stalling for minutes.
_llm_semaphore = threading.BoundedSemaphore(max(1, config.MAX_CONCURRENT_LLM))


@contextmanager
def llm_slot():
    """Acquire one of the limited LLM slots, or raise LLMBusy immediately."""
    if not _llm_semaphore.acquire(blocking=False):
        raise LLMBusy(
            f"Server busy: at most {config.MAX_CONCURRENT_LLM} report/novelty "
            "requests run concurrently. Please retry shortly."
        )
    try:
        yield
    finally:
        _llm_semaphore.release()


@lru_cache(maxsize=1)
def get_engine() -> HybridSearchEngine:
    """
    Build the hybrid search engine once. BM25 is built from the same CSV that
    seeded the ChromaDB `patents` collection, so the two stay consistent.
    """
    csv_path = str(config.PATENTS_CSV)
    if not config.PATENTS_CSV.exists():
        raise RuntimeError(
            f"Patent corpus not found at {csv_path}. Build it first: "
            "python -m src.ingestion.build_corpus && "
            "python -m src.ingestion.ingest_to_chromadb && "
            "python -m src.ingestion.seed_landmark_cases"
        )
    patents = load_patents_from_csv(csv_path)
    logger.info(f"Hybrid engine built from {len(patents)} patents")
    return HybridSearchEngine(patents)


@lru_cache(maxsize=1)
def get_llm_client():
    return get_llm()


def resolve_entry(*, tk_id: str | None = None, practice_name: str = "",
                  description: str = "", country: str = "",
                  documentation_date: str = "") -> dict:
    """
    Resolve a TK entry for analysis: load it from the registry by tk_id, or
    build an ad-hoc entry from the supplied fields. Raises ValueError if
    neither a known tk_id nor a practice_name is given.
    """
    if tk_id:
        entry = tk_store.get_entry(tk_id)
        if not entry:
            raise ValueError(f"TK entry '{tk_id}' not found")
        return entry
    if not practice_name:
        raise ValueError("Provide either tk_id or practice_name")
    return {
        "tk_id": None,
        "practice_name": practice_name,
        "description": description,
        "country": country.upper(),
        "documentation_date": documentation_date,
        "plants": [],
        "uses": [],
    }
