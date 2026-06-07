# src/ingestion/seed_landmark_cases.py
#
# Seeds the three landmark bio-piracy patents into the corpus so TK-Shield
# demonstrates the real cases it was built around. All three were actually
# challenged and revoked/cancelled/partially-revoked using prior-art evidence
# of traditional knowledge — exactly what this tool helps assemble.
#
# These rows are appended to the patents CSV (so BM25 includes them) and added
# to the ChromaDB `patents` collection (so semantic search includes them).
# Idempotent: re-running de-duplicates by patent id.

import chromadb
import pandas as pd
from loguru import logger

from src.embeddings.embed_pipeline import embed_batch
from src.utils.config import config

LANDMARK_CASES = [
    {
        "id": "US5401504A",
        "text": ("Use of turmeric in wound healing. Method of promoting healing of a wound "
                 "by administering turmeric (Curcuma longa) to a patient afflicted with the wound."),
        "metadata": {
            "patent_id": "US5401504A",
            "title": "Use of turmeric in wound healing",
            "abstract": "Method of promoting healing of a wound by administering turmeric.",
            "assignee": "University of Mississippi Medical Center",
            "filing_date": "1993-01-04",
            "country": "US",
            "ipc_code": "A61K36/906",
            "source": "landmark-biopiracy",
            "status": "REVOKED",
        },
    },
    {
        "id": "EP0436257B1",
        "text": ("Method for controlling fungi on plants by the aid of a hydrophobic extracted "
                 "neem oil. Antifungal properties of Azadirachta indica neem oil extract."),
        "metadata": {
            "patent_id": "EP0436257B1",
            "title": "Method for controlling fungi on plants using neem oil",
            "abstract": "Hydrophobic extracted neem oil (Azadirachta indica) as an antifungal agent.",
            "assignee": "W.R. Grace & Co.",
            "filing_date": "1990-06-12",
            "country": "EP",
            "ipc_code": "A01N65/00",
            "source": "landmark-biopiracy",
            "status": "REVOKED",
        },
    },
    {
        "id": "US5663484A",
        "text": ("Basmati rice lines and grains. Novel rice lines whose plants are "
                 "semi-dwarf in stature and produce rice grains having characteristics "
                 "similar or superior to those of good quality basmati rice."),
        "metadata": {
            "patent_id": "US5663484A",
            "title": "Basmati rice lines and grains",
            "abstract": "Novel basmati-type rice lines and grains.",
            "assignee": "RiceTec Inc.",
            "filing_date": "1994-08-25",
            "country": "US",
            "ipc_code": "A01H5/00",
            "source": "landmark-biopiracy",
            "status": "PARTIALLY_REVOKED",
        },
    },
]


def _append_to_csv() -> None:
    rows = [{"id": c["id"], "text": c["text"], **c["metadata"]} for c in LANDMARK_CASES]
    new_df = pd.DataFrame(rows)
    if config.PATENTS_CSV.exists():
        existing = pd.read_csv(config.PATENTS_CSV)
        combined = pd.concat([existing, new_df], ignore_index=True)
        combined = combined.drop_duplicates(subset="id", keep="last")
    else:
        config.PATENTS_CSV.parent.mkdir(parents=True, exist_ok=True)
        combined = new_df
    combined.to_csv(config.PATENTS_CSV, index=False)
    logger.success(f"CSV now has {len(combined)} patents (incl. {len(rows)} landmark cases)")


def _add_to_chroma() -> None:
    client = chromadb.PersistentClient(path=config.CHROMA_DB_PATH)
    collection = client.get_or_create_collection(
        name=config.PATENTS_COLLECTION, metadata={"hnsw:space": config.CHROMA_DISTANCE}
    )
    docs = [c["text"] for c in LANDMARK_CASES]
    collection.upsert(
        documents=docs,
        embeddings=embed_batch(docs),
        metadatas=[c["metadata"] for c in LANDMARK_CASES],
        ids=[c["id"] for c in LANDMARK_CASES],
    )
    logger.success(f"Upserted {len(docs)} landmark cases into '{config.PATENTS_COLLECTION}'")


def seed() -> None:
    _append_to_csv()
    _add_to_chroma()


if __name__ == "__main__":
    seed()
