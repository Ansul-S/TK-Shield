# src/ingestion/tk_sources/ — pluggable sources for building the TK registry.
#
# Each module exposes:  iter_tk_entries(limit) -> Iterator[dict]
# yielding TK-entry dicts ({practice_name, description, plants[], uses[],
# country, domain, aliases[], ...}) ready for tk_store.register_bulk.

from importlib import import_module
from typing import Callable, Iterator

_SOURCES = {
    "duke": "src.ingestion.tk_sources.duke_importer",
    "wikidata": "src.ingestion.tk_sources.wikidata_harvester",
}


def get_tk_source(name: str) -> Callable[[int], Iterator[dict]]:
    if name not in _SOURCES:
        raise ValueError(f"Unknown TK_SOURCE '{name}'. Options: {list(_SOURCES)}")
    return import_module(_SOURCES[name]).iter_tk_entries
