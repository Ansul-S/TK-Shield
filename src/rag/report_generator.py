# src/rag/report_generator.py
#
# Turns a retrieval context into a structured, citation-backed bio-piracy
# report. Uses the local LLM when available; otherwise falls back to a
# deterministic template so the tool still produces a usable report fully
# offline (no Ollama running) — offline-first by design.

from loguru import logger

from src.enrichment.prior_art import all_citations
from src.rag.llm_client import get_llm, LLMUnavailable

_SYSTEM = (
    "You are a defensive intellectual-property analyst specializing in "
    "traditional-knowledge (TK) protection and bio-piracy, in the tradition "
    "of India's TKDL and WIPO IGC. You analyze whether a patent improperly "
    "claims pre-existing traditional knowledge. You ONLY use the facts "
    "provided. You cite every claim using the given reference IDs "
    "(PMID, Wikidata QID, GBIF key, or patent number). You never invent "
    "patents, citations, or dates."
)


def _format_patents(patents: list[dict]) -> str:
    lines = []
    for p in patents[:5]:
        m = p.get("metadata", {})
        lines.append(
            f"- {m.get('patent_id', p.get('id', '?'))}: \"{m.get('title', '')}\" "
            f"| assignee={m.get('assignee', 'Unknown')} "
            f"| filed={m.get('filing_date', '?')} | country={m.get('country', '?')} "
            f"| similarity={p.get('similarity_score', 0)}"
        )
    return "\n".join(lines) or "(no candidate patents found)"


def _format_evidence(evidence: dict) -> str:
    lines = []
    for lit in evidence.get("literature", []):
        lines.append(f"- [PMID {lit['ref_id']}] ({lit.get('year', '?')}) {lit['title']}")
    for tax in evidence.get("taxonomy", []):
        tag = "QID" if tax["source"] == "wikidata" else "GBIF"
        lines.append(f"- [{tag} {tax['ref_id']}] {tax['title']} — {tax.get('detail', '')}")
    if evidence.get("origin_countries"):
        lines.append(f"- Native origin (GBIF): {', '.join(evidence['origin_countries'])}")
    return "\n".join(lines) or "(no external prior-art evidence found)"


def _build_prompt(tk_entry: dict, context: dict) -> str:
    risk = context["risk"]
    factors = "\n".join(f"  - {k}: {v}" for k, v in risk["factors"].items())
    return f"""TRADITIONAL KNOWLEDGE ENTRY
Practice: {tk_entry.get('practice_name', '')}
Description: {tk_entry.get('description', '')}
Community: {tk_entry.get('community', 'unknown')}
Origin country: {tk_entry.get('country', 'unknown')}
Documented: {tk_entry.get('documentation_date', 'unknown')}

COMPUTED BIO-PIRACY RISK: {risk['risk_level']} ({risk['total_score']}/100)
Factor breakdown:
{factors}

CANDIDATE PATENTS (from hybrid search of the corpus):
{_format_patents(context['patents'])}

EXTERNAL PRIOR-ART EVIDENCE:
{_format_evidence(context['evidence'])}

TASK: Return a JSON object with exactly two string fields:
- "assessment": a markdown analysis (3-5 short paragraphs) explaining the
  bio-piracy risk, the overlap between the patent claims and the documented
  traditional knowledge / prior art, and the significance of the risk
  factors. Cite supporting references inline by their IDs.
- "opposition_draft": a short formal paragraph the community could submit to
  a patent office asserting the prior art, naming the patent(s) and citing
  the prior-art references by ID.
"""


def _as_text(value) -> str:
    """
    Coerce an LLM JSON field to a string. JSON-mode models sometimes return a
    list (of paragraphs/points) or a dict instead of a string; flatten those
    rather than letting a non-str leak into the renderer.
    """
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list):
        return "\n\n".join(_as_text(v) for v in value).strip()
    if isinstance(value, dict):
        return "\n\n".join(f"**{k}:** {_as_text(v)}" for k, v in value.items()).strip()
    return "" if value is None else str(value)


def _deterministic_report(tk_entry: dict, context: dict) -> tuple[str, str]:
    """Template fallback used when the LLM is unavailable (fully offline)."""
    risk = context["risk"]
    patents = context["patents"]
    top = patents[0]["metadata"] if patents else {}
    cites = all_citations(context["evidence"])
    cite_str = ", ".join(f"{c['source']}:{c['ref_id']}" for c in cites) or "none on record"

    assessment = (
        f"## Bio-piracy risk: {risk['risk_level']} ({risk['total_score']}/100)\n\n"
        f"The traditional practice **{tk_entry.get('practice_name', '')}** "
        f"(community: {tk_entry.get('community', 'unknown')}, origin: "
        f"{tk_entry.get('country', 'unknown')}, documented "
        f"{tk_entry.get('documentation_date', 'unknown')}) was matched against "
        f"the patent corpus.\n\n"
        + (
            f"The closest patent is **{top.get('patent_id', '?')}** — "
            f"\"{top.get('title', '')}\" (assignee {top.get('assignee', 'Unknown')}, "
            f"filed {top.get('filing_date', '?')}, {top.get('country', '?')}).\n\n"
            if top else "No candidate patents were found in the corpus.\n\n"
        )
        + "Risk factor breakdown: "
        + "; ".join(f"{k}={v}" for k, v in risk["factors"].items())
        + f".\n\nSupporting prior-art references: {cite_str}.\n\n"
        f"_(Generated without the LLM — Ollama was unavailable. Numbers and "
        f"citations are exact; narrative is templated.)_"
    )
    opposition = (
        f"We submit that patent {top.get('patent_id', '[patent no.]')} lacks "
        f"novelty. The claimed subject matter corresponds to the traditional "
        f"practice '{tk_entry.get('practice_name', '')}', documented by "
        f"{tk_entry.get('community', 'the originating community')} since "
        f"{tk_entry.get('documentation_date', '[date]')}. Prior art is "
        f"evidenced by: {cite_str}. We request rejection/revocation on grounds "
        f"of pre-existing traditional knowledge."
    )
    return assessment, opposition


def generate_report(tk_entry: dict, context: dict, llm=None) -> dict:
    """
    Produce the final structured report. Tries the LLM; on any failure falls
    back to the deterministic template. Numbers/citations are always exact.
    """
    llm = llm or get_llm()
    llm_used = False
    assessment, opposition = _deterministic_report(tk_entry, context)

    if llm.is_available():
        try:
            out = llm.generate_json(_build_prompt(tk_entry, context), system=_SYSTEM)
            llm_assessment = _as_text(out.get("assessment"))
            if llm_assessment:
                assessment = llm_assessment
                opposition = _as_text(out.get("opposition_draft")) or opposition
                llm_used = True
        except LLMUnavailable as e:
            logger.warning(f"Falling back to deterministic report: {e}")

    return {
        "tk_entry": {
            k: tk_entry.get(k) for k in
            ("tk_id", "practice_name", "community", "country", "documentation_date")
        },
        "risk": context["risk"],
        "top_patents": [
            {
                "patent_id": p.get("metadata", {}).get("patent_id", p.get("id")),
                "title": p.get("metadata", {}).get("title", ""),
                "assignee": p.get("metadata", {}).get("assignee", ""),
                "filing_date": p.get("metadata", {}).get("filing_date", ""),
                "country": p.get("metadata", {}).get("country", ""),
                "similarity": p.get("similarity_score", 0),
            }
            for p in context["patents"][:5]
        ],
        "citations": all_citations(context["evidence"]),
        "assessment": assessment,
        "opposition_draft": opposition,
        "llm_used": llm_used,
        "sources_skipped": context["evidence"].get("sources_skipped", []),
    }
