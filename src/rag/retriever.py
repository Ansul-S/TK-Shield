# src/rag/retriever.py
#
# Assembles everything the report generator needs for one TK entry:
#   - candidate patents (hybrid semantic + BM25 search over the corpus)
#   - the 5-factor bio-piracy risk score
#   - external prior-art evidence (PubMed / Wikidata / GBIF)
#
# Reuses the existing engines: HybridSearchEngine, score_risk, gather_evidence.

from loguru import logger

from src.classifier.ip_risk_scorer import score_risk
from src.enrichment import prior_art
from src.nlp.ner_extractor import extract_all
from src.utils.config import config


def build_query(tk_entry: dict) -> str:
    """
    Build the search query from practice name + description + any aliases
    (folk / multilingual names). Including aliases broadens matching across
    languages and synonyms — part of the coverage-breadth goal.
    """
    parts = [tk_entry.get("practice_name", ""), tk_entry.get("description", "")]
    parts += tk_entry.get("aliases", []) or []
    return ". ".join(p for p in parts if p).strip()


# Backwards-compatible alias for internal callers.
_entry_query = build_query


def _ensure_entities(tk_entry: dict, query: str) -> tuple[list[str], list[str]]:
    """
    Use the TK entry's stored plants/uses if present; otherwise derive them
    from the text via the existing dictionary NER. This lets the retriever
    work for both registered entries and ad-hoc free-text analysis.
    """
    plants = tk_entry.get("plants") or []
    uses = tk_entry.get("uses") or []
    if not plants or not uses:
        extracted = extract_all(query)["tk_entities"]
        plants = plants or extracted["plants"]
        uses = uses or extracted["medical_uses"]
    return plants, uses


def build_context(tk_entry: dict, engine, n_results: int | None = None) -> dict:
    """
    Run retrieval + scoring + enrichment for `tk_entry`.

    `engine` is a built HybridSearchEngine. Returns a context dict consumed
    by report_generator.generate_report().
    """
    n_results = n_results or config.DEFAULT_N_RESULTS
    query = _entry_query(tk_entry)

    patents = engine.search(query, n_results=n_results) if query else []
    risk = score_risk(tk_entry, patents)

    plants, uses = _ensure_entities(tk_entry, query)
    evidence = prior_art.gather_evidence(plants, uses)

    logger.info(
        f"Context for '{tk_entry.get('practice_name', '?')}': "
        f"{len(patents)} patents, risk={risk['risk_level']}, "
        f"{len(evidence['literature'])} papers"
    )
    return {
        "query": query,
        "plants": plants,
        "uses": uses,
        "patents": patents,
        "risk": risk,
        "evidence": evidence,
    }
