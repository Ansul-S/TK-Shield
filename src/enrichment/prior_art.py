# src/enrichment/prior_art.py
#
# Fan out to the keyless evidence sources (PubMed, Wikidata, GBIF) and
# assemble one normalized, deduplicated, citation-tagged bundle for a TK
# entry. Every item keeps its source + stable ID so downstream reports cite
# real references (PMID / QID / GBIF key) rather than LLM hand-waving.
#
# Each source degrades independently: if one returns nothing (disabled, no
# data, or down), it is recorded in `sources_skipped` and the rest proceed.

import concurrent.futures as cf

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

    # Fan out all independent network calls concurrently. Each client already
    # returns None/[] on failure (never raises), so graceful degradation is
    # preserved — concurrency only cuts wall-time (was sequential per plant).
    enrich_plants = plants[:config.ENRICH_MAX_PLANTS]
    wd_results: dict[str, dict | None] = {}
    gb_results: dict[str, dict | None] = {}
    lit_result: list = []
    with cf.ThreadPoolExecutor(max_workers=config.ENRICH_WORKERS) as ex:
        futs = {}
        for plant in enrich_plants:
            if config.ENABLE_WIKIDATA:
                futs[ex.submit(wikidata_client.search_plant, plant)] = ("wd", plant)
            if config.ENABLE_GBIF:
                futs[ex.submit(gbif_client.species_origin, plant)] = ("gb", plant)
        lit_fut = None
        if config.ENABLE_PUBMED:
            query = _build_query(plants, uses)
            if query.strip():
                lit_fut = ex.submit(pubmed_client.search_literature, query, max_literature)
        for fut, (kind, plant) in futs.items():
            try:
                res = fut.result()
            except Exception:  # noqa: BLE001 — never let one source break the bundle
                res = None
            (wd_results if kind == "wd" else gb_results)[plant] = res
        if lit_fut is not None:
            try:
                lit_result = lit_fut.result() or []
            except Exception:  # noqa: BLE001
                lit_result = []

    # Assemble deterministically in plant order (wikidata then gbif per plant).
    for plant in enrich_plants:
        wd = wd_results.get(plant)
        if wd:
            bundle["taxonomy"].append(wd)
            bundle["aliases"].extend(wd.get("aliases", []))
        gb = gb_results.get(plant)
        if gb:
            bundle["taxonomy"].append(gb)
            bundle["origin_countries"].extend(gb.get("native_countries", []))
    bundle["literature"] = lit_result

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
