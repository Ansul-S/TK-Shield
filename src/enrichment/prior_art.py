# src/enrichment/prior_art.py
#
# Fan out to the keyless evidence sources (PubMed, Wikidata, GBIF) and
# assemble one normalized, deduplicated, citation-tagged bundle for a TK
# entry. Every item keeps its source + stable ID so downstream reports cite
# real references (PMID / QID / GBIF key) rather than LLM hand-waving.
#
# Each source degrades independently: if one returns nothing (disabled, no
# data, or down), it is recorded in `sources_skipped` and the rest proceed.

from loguru import logger

from src.clients import pubmed_client, wikidata_client, gbif_client
from src.utils.config import config


def _build_query(plants: list[str], uses: list[str]) -> str:
    """Combine plant + use terms into a PubMed-friendly query string."""
    terms = [t for t in (plants[:3] + uses[:3]) if t]
    return " ".join(terms)


def gather_evidence(plants: list[str], uses: list[str],
                    max_literature: int = 5) -> dict:
    """
    Collect prior-art evidence for a TK practice.

    Returns:
      {
        "literature":       [pubmed evidence dicts],
        "taxonomy":         [wikidata + gbif evidence dicts],
        "origin_countries": [ISO codes from GBIF native ranges],
        "aliases":          [synonyms from Wikidata, for query expansion],
        "sources_used":     ["pubmed", ...],
        "sources_skipped":  ["gbif", ...],
      }
    """
    plants = [p for p in (plants or []) if p]
    uses = [u for u in (uses or []) if u]

    bundle = {
        "literature": [],
        "taxonomy": [],
        "origin_countries": [],
        "aliases": [],
        "sources_used": [],
        "sources_skipped": [],
    }

    # --- Wikidata + GBIF, per plant ---
    for plant in plants:
        if config.ENABLE_WIKIDATA:
            wd = wikidata_client.search_plant(plant)
            if wd:
                bundle["taxonomy"].append(wd)
                bundle["aliases"].extend(wd.get("aliases", []))
        if config.ENABLE_GBIF:
            gb = gbif_client.species_origin(plant)
            if gb:
                bundle["taxonomy"].append(gb)
                bundle["origin_countries"].extend(gb.get("native_countries", []))

    # --- PubMed literature for the plant+use combination ---
    if config.ENABLE_PUBMED:
        query = _build_query(plants, uses)
        bundle["literature"] = pubmed_client.search_literature(query, retmax=max_literature)

    # Dedupe taxonomy by (source, ref_id) — the same entity is often reached
    # via both the common and scientific name.
    seen = set()
    deduped = []
    for t in bundle["taxonomy"]:
        key = (t["source"], t["ref_id"])
        if key not in seen:
            seen.add(key)
            deduped.append(t)
    bundle["taxonomy"] = deduped

    # Dedupe list fields while preserving order.
    bundle["origin_countries"] = sorted(set(bundle["origin_countries"]))
    bundle["aliases"] = list(dict.fromkeys(bundle["aliases"]))

    # Record which sources actually contributed (for transparent reports).
    if bundle["literature"]:
        bundle["sources_used"].append("pubmed")
    elif config.ENABLE_PUBMED:
        bundle["sources_skipped"].append("pubmed")

    for source, enabled in (("wikidata", config.ENABLE_WIKIDATA), ("gbif", config.ENABLE_GBIF)):
        if not enabled:
            continue
        used = any(t["source"] == source for t in bundle["taxonomy"])
        (bundle["sources_used"] if used else bundle["sources_skipped"]).append(source)

    logger.info(
        f"Evidence: {len(bundle['literature'])} papers, "
        f"{len(bundle['taxonomy'])} taxonomy records, "
        f"origin={bundle['origin_countries']}"
    )
    return bundle


def all_citations(bundle: dict) -> list[dict]:
    """Flatten a bundle into a single list of {source, ref_id, title, url}."""
    cites = []
    for item in bundle.get("literature", []) + bundle.get("taxonomy", []):
        cites.append({k: item.get(k) for k in ("source", "ref_id", "title", "url")})
    return cites


if __name__ == "__main__":
    b = gather_evidence(["turmeric", "Curcuma longa"], ["wound healing"], max_literature=3)
    print("Sources used:", b["sources_used"], "| skipped:", b["sources_skipped"])
    print("Origin countries:", b["origin_countries"])
    for c in all_citations(b):
        print(f"  [{c['source']}] {c['ref_id']}: {c['title'][:60]}")
