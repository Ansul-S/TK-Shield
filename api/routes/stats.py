# api/routes/stats.py — Researcher persona: aggregate stats over the TK
# registry and the patent corpus (counts, domains, geography, assignees).

from collections import Counter

from fastapi import APIRouter, Request

from api.deps import limiter
from src.classifier.domain import infer_domain
from src.ingestion.tk_sources.duke_importer import DUKE_PROVENANCE
from src.registry import tk_store
from src.search import vector_store
from src.utils.config import config

router = APIRouter(prefix="/api/stats", tags=["researcher"])


@router.get("")
@limiter.limit(config.RATE_LIMIT_DEFAULT)
def stats(request: Request) -> dict:
    # --- TK registry (from SQLite source of truth) ---
    entries = tk_store.list_entries()
    tk_by_domain = Counter((e.get("domain") or "unknown") for e in entries)
    tk_by_country = Counter((e.get("country") or "—") for e in entries)
    # Documented holder communities/peoples (Nagoya/WIPO-IGC attribution). Drop
    # the generic Duke provenance placeholder and empties so only real groups show.
    tk_by_community = Counter(
        c for e in entries
        if (c := (e.get("community") or "").strip())
        and c != DUKE_PROVENANCE
    )

    # --- Patent corpus (from ChromaDB) ---
    patent_total = 0
    sampled = 0
    by_assignee: Counter = Counter()
    by_source: Counter = Counter()
    patent_by_domain: Counter = Counter()
    try:
        # Reuse the shared persistent client (C6): opening a second
        # PersistentClient on the same path per request is wasteful and risks
        # ChromaDB state/lock contention under concurrent calls.
        col = vector_store.get_or_create_collection(config.PATENTS_COLLECTION)
        patent_total = col.count()
        metas = col.get(include=["metadatas"], limit=config.STATS_PATENT_SAMPLE).get("metadatas", [])
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
            "top_communities": tk_by_community.most_common(10),
        },
        "patents": {
            "total": patent_total,
            "sampled": sampled,
            "by_domain": dict(patent_by_domain),
            "by_source": dict(by_source),
            "top_assignees": by_assignee.most_common(10),
        },
    }
