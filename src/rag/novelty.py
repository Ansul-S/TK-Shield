# src/rag/novelty.py
#
# Examiner persona: reverse lookup. Given a patent (text), search the
# documented TK registry (the tk_entries ChromaDB collection) for prior art
# and judge whether the patent's subject matter is likely novel. This is the
# inverse of the defender flow and reuses the same indexed TK data.

from loguru import logger

from src.rag.claim_parser import split_claims
from src.rag.llm_client import get_llm, LLMUnavailable
from src.search import vector_store
from src.utils.config import config

# Verdict severity order (strongest prior-art signal first) for aggregating a
# patent's per-claim verdicts into one overall verdict.
_VERDICT_RANK = {"LIKELY NOT NOVEL": 2, "POSSIBLE PRIOR ART": 1, "LIKELY NOVEL": 0}

# Cosine-similarity thresholds → verdict (tunable via config/.env).
_NOT_NOVEL = config.NOVELTY_NOT_NOVEL
_POSSIBLE = config.NOVELTY_POSSIBLE

_SYSTEM = (
    "You are a patent examiner assessing novelty against documented traditional "
    "knowledge (TK). You ONLY use the provided TK prior-art matches. You are "
    "concise and never invent references."
)


def _verdict(top_sim: float) -> tuple[str, str]:
    if top_sim >= _NOT_NOVEL:
        return "LIKELY NOT NOVEL", "high"
    if top_sim >= _POSSIBLE:
        return "POSSIBLE PRIOR ART", "medium"
    return "LIKELY NOVEL", "low"


def _deterministic(patent_text: str, verdict: str, matches: list[dict]) -> str:
    if not matches:
        return ("No documented TK prior art was found in the registry for this "
                "patent text. On the available evidence the claim appears novel.")
    lines = [f"Assessment: **{verdict}**.", "",
             "Closest documented traditional-knowledge prior art:"]
    for m in matches[:5]:
        meta = m["metadata"]
        lines.append(
            f"- {meta.get('practice_name','?')} ({meta.get('tk_id','?')}, "
            f"{meta.get('domain','?')}) — similarity {round(m['similarity_score'],3)}"
        )
    lines += ["", "_(Generated offline; similarity figures are exact.)_"]
    return "\n".join(lines)


def assess_novelty(patent_text: str, n_results: int = 5, llm=None) -> dict:
    """
    Search the TK registry for prior art matching `patent_text` and return a
    novelty assessment. Raises ValueError only for empty input; otherwise never
    raises — the verdict is computed from cosine similarity (so it is immune to
    prompt injection in the patent text), and the narrative degrades to a
    deterministic template whenever the LLM is unavailable or errors.
    """
    if not patent_text.strip():
        raise ValueError("patent_text is required")

    matches = vector_store.search(config.TK_COLLECTION, patent_text, n_results=n_results)
    top_sim = matches[0]["similarity_score"] if matches else 0.0
    verdict, confidence = _verdict(top_sim)

    assessment = _deterministic(patent_text, verdict, matches)
    llm_used = False
    llm = llm or get_llm()
    if matches and llm.is_available():
        prior = "\n".join(
            f"- {m['metadata'].get('practice_name','?')} "
            f"({m['metadata'].get('tk_id','?')}): {m['document'][:200]}"
            for m in matches[:5]
        )
        prompt = (
            f"PATENT TEXT:\n{patent_text[:config.PATENT_TEXT_MAX_CHARS]}\n\n"
            f"DOCUMENTED TK PRIOR ART (most similar first):\n{prior}\n\n"
            f"Computed verdict from similarity: {verdict}.\n"
            "Write a 2-3 sentence examiner note explaining whether the patent "
            "lacks novelty over this traditional knowledge, citing the TK ids."
        )
        try:
            out = llm.generate(prompt, system=_SYSTEM)
            if out and out.strip():
                assessment = out.strip()
                llm_used = True
        except LLMUnavailable as e:
            logger.warning(f"Novelty LLM fallback: {e}")
        except Exception as e:  # noqa: BLE001 — any LLM error degrades gracefully
            logger.warning(f"Novelty LLM error, using deterministic note: {e}")

    return {
        "verdict": verdict,
        "confidence": confidence,
        "top_similarity": round(top_sim, 4),
        "matches": [_match_dict(m) for m in matches],
        "assessment": assessment,
        "llm_used": llm_used,
    }


def _match_dict(m: dict) -> dict:
    """Normalize a raw vector-store hit into the public match shape."""
    meta = m["metadata"]
    return {
        "tk_id": meta.get("tk_id"),
        "practice_name": meta.get("practice_name"),
        "domain": meta.get("domain", ""),
        "country": meta.get("country", ""),
        "similarity": round(m["similarity_score"], 4),
    }


def _deterministic_claims(claim_results: list[dict], overall_verdict: str) -> str:
    """Offline examiner note summarizing the per-claim findings."""
    anticipated = [c for c in claim_results if c["verdict"] == "LIKELY NOT NOVEL"]
    lines = [f"Overall assessment: **{overall_verdict}** (assessed claim by claim).", ""]
    if anticipated:
        nums = ", ".join(str(c["number"]) for c in anticipated)
        lines.append(f"Claim(s) fully anticipated by documented TK prior art: {nums}.")
        lines.append("")
    lines.append("Per-claim findings:")
    for c in claim_results:
        kind = f"dependent on claim {c['depends_on']}" if c["is_dependent"] else "independent"
        top = c["matches"][0] if c["matches"] else None
        ref = (f" — closest TK: {top['practice_name']} ({top['tk_id']}, "
               f"sim {top['similarity']})") if top else ""
        lines.append(f"- Claim {c['number']} ({kind}): **{c['verdict']}**{ref}")
    lines += ["", "_(Verdicts are computed from cosine similarity; figures are exact.)_"]
    return "\n".join(lines)


def assess_novelty_by_claim(patent_text: str, n_results: int = 5, llm=None) -> dict:
    """
    Claim-level examiner novelty assessment. Splits the pasted patent into its
    individual claims and scores each against the documented TK registry, the
    way an examiner assesses anticipation (§102 / EPC Art. 54).

    If the text has no parseable claim structure (e.g. only an abstract was
    pasted), this delegates to the whole-text `assess_novelty` and tags the
    result `claim_level=False` — so the endpoint contract is uniform and the
    prior behavior is preserved. Like `assess_novelty`, verdicts are computed
    from cosine similarity (prompt-injection-immune) and the narrative degrades
    to a deterministic template offline.
    """
    if not patent_text.strip():
        raise ValueError("patent_text is required")

    claims = split_claims(patent_text)
    if not claims:
        result = assess_novelty(patent_text, n_results=n_results, llm=llm)
        result["claim_level"] = False
        result["claims"] = []
        return result

    claim_results = []
    for c in claims:
        matches = vector_store.search(config.TK_COLLECTION, c["text"], n_results=n_results)
        top_sim = matches[0]["similarity_score"] if matches else 0.0
        verdict, confidence = _verdict(top_sim)
        claim_results.append({
            "number": c["number"],
            "text": c["text"],
            "is_dependent": c["is_dependent"],
            "depends_on": c["depends_on"],
            "verdict": verdict,
            "confidence": confidence,
            "top_similarity": round(top_sim, 4),
            "matches": [_match_dict(m) for m in matches],
        })

    # Aggregate like an examiner: a patent fails novelty if any INDEPENDENT claim
    # is anticipated. (If no independent claim parsed, consider all claims.)
    independent = [c for c in claim_results if not c["is_dependent"]] or claim_results
    overall_verdict = max((c["verdict"] for c in independent),
                          key=lambda v: _VERDICT_RANK[v])
    overall_confidence = next(c["confidence"] for c in independent
                              if c["verdict"] == overall_verdict)
    overall_top_sim = max((c["top_similarity"] for c in claim_results), default=0.0)

    # Overall matches: best (highest-similarity) hit per TK id across all claims,
    # so the existing top-level match table stays meaningful.
    best_by_tk: dict = {}
    for c in claim_results:
        for m in c["matches"]:
            tk = m["tk_id"]
            if tk and (tk not in best_by_tk or m["similarity"] > best_by_tk[tk]["similarity"]):
                best_by_tk[tk] = m
    overall_matches = sorted(best_by_tk.values(), key=lambda m: m["similarity"], reverse=True)

    # The claim-level assessment is a DETERMINISTIC, structured summary. We do
    # not let the LLM restate per-claim verdicts: a small local model conflates
    # multiple claims and produces a narrative that contradicts the authoritative
    # (similarity-computed, injection-immune) badges — unacceptable for a legal
    # tool. Verdicts/figures are exact and consistent with the per-claim cards.
    assessment = _deterministic_claims(claim_results, overall_verdict)

    return {
        "verdict": overall_verdict,
        "confidence": overall_confidence,
        "top_similarity": round(overall_top_sim, 4),
        "matches": overall_matches,
        "assessment": assessment,
        "llm_used": False,
        "deterministic_verdicts": True,
        "claim_level": True,
        "claims": claim_results,
    }
