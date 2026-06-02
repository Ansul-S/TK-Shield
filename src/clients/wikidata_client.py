# src/clients/wikidata_client.py
#
# Wikidata API (keyless, verified live 2026).
# Resolves a folk/common plant name to its canonical entity: scientific
# name, description, and aliases. Useful both as citable evidence (a stable
# QID) and to expand a query with synonyms the semantic search can use.

from loguru import logger

from src.clients._http import get_json
from src.utils.config import config


def search_plant(name: str) -> dict | None:
    """
    Resolve `name` to a Wikidata entity. Returns a citation-tagged dict:
    {source, ref_id (QID), title (label), detail (description), aliases, url}
    or None if nothing matched / on failure.
    """
    if not config.ENABLE_WIKIDATA or not name.strip():
        return None

    hits = get_json(
        f"{config.WIKIDATA_API_BASE}/api.php",
        params={
            "action": "wbsearchentities",
            "search": name,
            "language": "en",
            "format": "json",
            "limit": 1,
        },
    )
    try:
        top = hits["search"][0]
    except (TypeError, KeyError, IndexError):
        return None

    qid = top.get("id", "")
    aliases = top.get("aliases", []) or []
    logger.info(f"Wikidata: '{name}' → {qid} ({top.get('label')})")
    return {
        "source": "wikidata",
        "ref_id": qid,
        "title": top.get("label", name),
        "detail": top.get("description", ""),
        "aliases": aliases,
        "url": top.get("concepturi", f"https://www.wikidata.org/wiki/{qid}"),
    }


if __name__ == "__main__":
    print(search_plant("turmeric"))
    print(search_plant("neem"))
