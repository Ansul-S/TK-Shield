# src/ingestion/build_registry.py
#
# Populate the TK registry at scale from a pluggable source (config.TK_SOURCE),
# capped at config.TK_IMPORT_LIMIT, via the batched tk_store.register_bulk.
#
#   TK_SOURCE=duke     TK_IMPORT_LIMIT=2000 python -m src.ingestion.build_registry
#   TK_SOURCE=wikidata TK_IMPORT_LIMIT=50   python -m src.ingestion.build_registry

from loguru import logger

from src.ingestion.tk_sources import get_tk_source
from src.registry import tk_store
from src.utils.config import config


def build_registry(source_name: str | None = None, limit: int | None = None) -> int:
    source_name = source_name or config.TK_SOURCE
    limit = limit or config.TK_IMPORT_LIMIT
    iter_tk_entries = get_tk_source(source_name)

    entries = list(iter_tk_entries(limit))
    if not entries:
        logger.warning(f"TK source '{source_name}' produced no entries.")
        return 0
    count = tk_store.register_bulk(entries)
    logger.success(f"Registry: +{count} entries from '{source_name}'")
    return count


if __name__ == "__main__":
    build_registry()
