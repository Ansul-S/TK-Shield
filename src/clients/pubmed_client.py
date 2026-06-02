# src/clients/pubmed_client.py
#
# NCBI PubMed via E-utilities (keyless, verified live 2026).
# Supplies peer-reviewed ethnobotanical literature as citable prior-art
# evidence — e.g. papers documenting turmeric for wound healing that
# predate a patent's filing date.

from loguru import logger

from src.clients._http import get_json
from src.utils.config import config


def _common_params() -> dict:
    """Email + api_key are optional; they only raise NCBI's rate limit."""
    params = {"db": "pubmed", "retmode": "json"}
    if config.NCBI_EMAIL:
        params["email"] = config.NCBI_EMAIL
        params["tool"] = "tk-shield"
    if config.PUBMED_API_KEY:
        params["api_key"] = config.PUBMED_API_KEY
    return params


def search_literature(term: str, retmax: int = 5) -> list[dict]:
    """
    Search PubMed for `term` and return normalized, citation-tagged evidence.
    Each item: {source, ref_id (PMID), title, detail (journal), year, url}.
    Returns [] on any failure — never raises.
    """
    if not config.ENABLE_PUBMED or not term.strip():
        return []

    # Step 1: esearch → list of PMIDs
    search = get_json(
        f"{config.PUBMED_API_BASE}/esearch.fcgi",
        params={**_common_params(), "term": term, "retmax": retmax},
    )
    try:
        pmids = search["esearchresult"]["idlist"]
    except (TypeError, KeyError):
        return []
    if not pmids:
        return []

    # Step 2: esummary → titles, journals, dates
    summary = get_json(
        f"{config.PUBMED_API_BASE}/esummary.fcgi",
        params={**_common_params(), "id": ",".join(pmids)},
    )
    try:
        result = summary["result"]
    except (TypeError, KeyError):
        return []

    evidence = []
    for pmid in pmids:
        rec = result.get(pmid)
        if not rec:
            continue
        pubdate = str(rec.get("pubdate", ""))
        year = pubdate[:4] if pubdate[:4].isdigit() else None
        evidence.append({
            "source": "pubmed",
            "ref_id": pmid,
            "title": rec.get("title", "").rstrip("."),
            "detail": rec.get("fulljournalname", ""),
            "year": year,
            "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
        })
    logger.info(f"PubMed: {len(evidence)} records for '{term}'")
    return evidence


if __name__ == "__main__":
    for item in search_literature("turmeric wound healing", retmax=3):
        print(f"  [{item['year']}] {item['ref_id']}: {item['title'][:70]}")
