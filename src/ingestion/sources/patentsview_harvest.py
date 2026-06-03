# src/ingestion/sources/patentsview_harvest.py
#
# Real-metadata patent source: pages the PatentsView PatentSearch API by
# TK-relevant CPC classes (config.PATENT_CPC_CLASSES) to build a corpus with
# real IDs / titles / abstracts / dates / assignees / CPC. Needs the free
# PATENTSVIEW_API_KEY; without it, yields nothing (graceful).
#
# Reuses src/clients/patentsview_client.search_by_cpc for the page + normalize.

import time
from typing import Iterator

from loguru import logger

from src.clients import patentsview_client
from src.utils.config import config

_PAGE_SIZE = 100


def iter_patents(limit: int) -> Iterator[dict]:
    if not patentsview_client.is_available():
        logger.warning(
            "patentsview source: no PATENTSVIEW_API_KEY — yielding nothing. "
            "Use PATENT_SOURCE=ccdv for the keyless corpus, or set a free key."
        )
        return

    cpc = config.PATENT_CPC_CLASSES
    logger.info(f"patentsview source: harvesting up to {limit} patents for CPC {cpc}")
    seen: set[str] = set()
    cursor = None
    yielded = 0

    while yielded < limit:
        patents, cursor = patentsview_client.search_by_cpc(cpc, after=cursor, size=_PAGE_SIZE)
        if not patents:
            break
        for p in patents:
            if p["id"] in seen:
                continue
            seen.add(p["id"])
            yield p
            yielded += 1
            if yielded >= limit:
                break
        if cursor is None:  # last page
            break
        time.sleep(config.REQUEST_DELAY)  # respect the 45 req/min limit

    logger.success(f"patentsview source: yielded {yielded} patents")
