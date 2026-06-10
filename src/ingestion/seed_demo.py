# src/ingestion/seed_demo.py
#
# One-shot "instant demo" seeder for the Docker image (C4). It makes TK-Shield
# fully usable on the three landmark cases WITHOUT the ~219MB PatentsView bulk
# download, so `docker compose up` yields a working Defender / Examiner /
# Researcher demo in seconds.
#
# It reuses existing code rather than duplicating data:
#   1. seed_landmark_cases.seed() — writes the 3 real bio-piracy patents to the
#      patents CSV (source of truth for BM25) and the ChromaDB `patents`
#      collection (semantic search).
#   2. tk_store.register_bulk(...) — registers the matching documented TK
#      practices so the registry/examiner/researcher views have content.
#
# Idempotent: landmark seeding de-dupes by patent id; TK ids are fixed so
# re-running upserts the same rows. Safe to run on every container start.

from loguru import logger

from src.ingestion import seed_landmark_cases
from src.registry import tk_store

# Documented TK practices for the three landmark disputes. Documentation dates
# predate the patents (turmeric 1993, neem 1990, basmati 1994) so the temporal
# risk factor fires and turmeric scores CRITICAL — the canonical demo result.
DEMO_TK_ENTRIES = [
    {
        "tk_id": "TK-TURMERIC",
        "practice_name": "Turmeric paste for wound healing",
        "description": (
            "Application of turmeric (Curcuma longa, 'haldi') paste to cuts, "
            "wounds and abrasions to promote healing and prevent infection, "
            "documented in Ayurveda and Indian household practice for centuries."
        ),
        "community": "Traditional Ayurvedic practitioners",
        "country": "IN",
        "documentation_date": "1900-01-01",
        "category": "Medicinal",
        "aliases": ["haldi", "curcuma longa", "curcumin"],
    },
    {
        "tk_id": "TK-NEEM",
        "practice_name": "Neem oil as antifungal and pesticide",
        "description": (
            "Use of neem (Azadirachta indica) oil and leaf extracts as a natural "
            "antifungal agent and crop pesticide, long practised in Indian "
            "agriculture and traditional medicine."
        ),
        "community": "Indian farming communities",
        "country": "IN",
        "documentation_date": "1900-01-01",
        "category": "Agricultural",
        "aliases": ["azadirachta indica", "nim", "margosa"],
    },
    {
        "tk_id": "TK-BASMATI",
        "practice_name": "Basmati aromatic rice landraces",
        "description": (
            "Traditional aromatic long-grain basmati rice landraces cultivated "
            "for generations across the Indian subcontinent, prized for aroma, "
            "grain elongation and cooking quality."
        ),
        "community": "Punjab and Himalayan-foothill rice farmers",
        "country": "IN",
        "documentation_date": "1900-01-01",
        "category": "Agricultural",
        "aliases": ["basmati rice", "aromatic rice"],
    },
]


def seed_demo() -> None:
    logger.info("Seeding landmark patents (CSV + ChromaDB)…")
    seed_landmark_cases.seed()
    logger.info("Registering landmark TK practices…")
    n = tk_store.register_bulk(DEMO_TK_ENTRIES)
    logger.success(f"Demo seed complete: 3 landmark patents + {n} TK entries.")


if __name__ == "__main__":
    seed_demo()
