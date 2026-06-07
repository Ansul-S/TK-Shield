# src/ingestion/build_corpus.py
#
# Source-driven patent corpus builder. Picks the source from config
# (PATENT_SOURCE), pulls up to MAX_PATENTS canonical patent dicts, and
# appends them to the canonical CSV (config.PATENTS_CSV), de-duplicating by id.
# Then run `python -m src.ingestion.ingest_to_chromadb` to (re)build the
# vector index from the CSV — keeping CSV ↔ ChromaDB ↔ BM25 consistent.
#
#   PATENT_SOURCE=ccdv        MAX_PATENTS=5000  python -m src.ingestion.build_corpus
#   PATENT_SOURCE=patentsview MAX_PATENTS=50000 python -m src.ingestion.build_corpus

import pandas as pd
from loguru import logger

from src.ingestion.sources import get_patent_source
from src.utils.config import config

_COLUMNS = ["id", "text", "patent_id", "title", "abstract", "assignee",
            "filing_date", "country", "ipc_code", "source", "status"]


def _flatten(patent: dict) -> dict:
    m = patent["metadata"]
    return {"id": patent["id"], "text": patent["text"], **{c: m.get(c, "") for c in _COLUMNS[2:]}}


def build_corpus(source_name: str | None = None, limit: int | None = None) -> pd.DataFrame:
    source_name = source_name or config.PATENT_SOURCE
    limit = limit or config.MAX_PATENTS
    # Fail fast: a source that is excluded at index time would build a corpus
    # that ingest_to_chromadb then drops entirely (empty index footgun, A1).
    config.validate_corpus_config(source_name)
    iter_patents = get_patent_source(source_name)

    rows = [_flatten(p) for p in iter_patents(limit)]
    if not rows:
        logger.warning(f"Source '{source_name}' produced no patents.")
        return pd.DataFrame(columns=_COLUMNS)

    new_df = pd.DataFrame(rows, columns=_COLUMNS)
    if config.PATENTS_CSV.exists():
        existing = pd.read_csv(config.PATENTS_CSV)
        combined = pd.concat([existing, new_df], ignore_index=True).drop_duplicates(
            subset="id", keep="last"
        )
    else:
        config.PATENTS_CSV.parent.mkdir(parents=True, exist_ok=True)
        combined = new_df

    combined.to_csv(config.PATENTS_CSV, index=False)
    logger.success(
        f"Corpus: +{len(new_df)} from '{source_name}' → {len(combined)} total "
        f"patents at {config.PATENTS_CSV}"
    )
    return combined


if __name__ == "__main__":
    build_corpus()
    print("\nNext: python -m src.ingestion.ingest_to_chromadb   (rebuild the index)")
