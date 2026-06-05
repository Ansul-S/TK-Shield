# src/ingestion/sources/ — pluggable patent corpus sources.
#
# Each source module exposes:  iter_patents(limit) -> Iterator[dict]
# yielding canonical patent dicts {id, text, metadata{...}} (the shape used
# everywhere else). build_corpus.py drives whichever source config selects.

from importlib import import_module
from typing import Callable, Iterator

_SOURCES = {
    "ccdv": "src.ingestion.sources.ccdv_source",
    "patentsview_bulk": "src.ingestion.sources.patentsview_bulk_source",  # keyless, real metadata
    "patentsview": "src.ingestion.sources.patentsview_harvest",           # live API (needs key)
}


def get_patent_source(name: str) -> Callable[[int], Iterator[dict]]:
    """Return the iter_patents callable for a source name (raises if unknown)."""
    if name not in _SOURCES:
        raise ValueError(f"Unknown PATENT_SOURCE '{name}'. Options: {list(_SOURCES)}")
    return import_module(_SOURCES[name]).iter_patents
