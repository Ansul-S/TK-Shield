# api/routes/stats.py — Researcher persona: aggregate stats over the TK
# registry and the patent corpus (counts, domains, geography, assignees).

from collections import Counter

import chromadb
from fastapi import APIRouter

from src.classifier.domain import infer_domain
from src.registry import tk_store
from src.utils.config import config

router = APIRouter(prefix="/api/stats", tags=["researcher"])

_PATENT_SAMPLE = 5000  # cap metadata scan so it stays fast on large corpora


@router.get("")
def stats() -> dict:
    # --- TK registry (from SQLite source of truth) ---
    entries = tk_store.list_entries()
    tk_by_domain = Counter((e.get("domain") or "unknown") for e in entries)
    tk_by_country = Counter((e.get("country") or "—") for e in entries)

    # --- Patent corpus (from ChromaDB) ---
    patent_total = 0
    sampled = 0
    by_assignee: Counter = Counter()
    by_source: Counter = Counter()
    patent_by_domain: Counter = Counter()
    try:
        col = chromadb.PersistentClient(path=config.CHROMA_DB_PATH).get_collection(
            config.PATENTS_COLLECTION
        )
        patent_total = col.count()
        metas = col.get(include=["metadatas"], limit=_PATENT_SAMPLE).get("metadatas", [])
        sampled = len(metas)
        for m in metas:
            by_assignee[m.get("assignee", "Unknown") or "Unknown"] += 1
            by_source[m.get("source", "") or "unknown"] += 1
            patent_by_domain[infer_domain(m.get("title", ""), m.get("ipc_code", ""))] += 1
    except Exception:  # noqa: BLE001 — empty/missing collection is fine
        pass

    return {
        "registry": {
            "total": len(entries),
            "by_domain": dict(tk_by_domain),
            "top_countries": tk_by_country.most_common(10),
        },
        "patents": {
            "total": patent_total,
            "sampled": sampled,
            "by_domain": dict(patent_by_domain),
            "by_source": dict(by_source),
            "top_assignees": by_assignee.most_common(10),
        },
    }
