# src/ingestion/sources/ccdv_source.py
#
# Keyless patent source: the ccdv/patent-classification HuggingFace corpus.
# This is the offline default — no API key — but its metadata is low-fidelity
# (synthetic IDs, no real assignee/date). Reuses the existing scraper's filter
# + normalization (src/ingestion/patent_scraper.py) so logic isn't duplicated.

from typing import Iterator

from loguru import logger

from src.ingestion.patent_scraper import clean_patent


def iter_patents(limit: int) -> Iterator[dict]:
    from datasets import load_dataset  # local import: heavy, only when used

    logger.info(f"ccdv source: loading dataset (target {limit} TK-relevant)...")
    dataset = load_dataset(
        "ccdv/patent-classification", "abstract", split="train", trust_remote_code=False
    )

    kept = 0
    for idx, raw in enumerate(dataset):
        patent = clean_patent(raw, idx)  # applies section A/C + keyword filter
        if not patent:
            continue
        yield patent
        kept += 1
        if kept >= limit:
            break
    logger.success(f"ccdv source: yielded {kept} TK-relevant patents")
