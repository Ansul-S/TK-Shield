# src/rag/novelty.py
#
# Examiner persona: reverse lookup. Given a patent (text), search the
# documented TK registry (the tk_entries ChromaDB collection) for prior art
# and judge whether the patent's subject matter is likely novel. This is the
# inverse of the defender flow and reuses the same indexed TK data.

from loguru import logger

from src.rag.llm_client import get_llm, LLMUnavailable
from src.search import vector_store
from src.utils.config import config

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
        "matches": [
            {
                "tk_id": m["metadata"].get("tk_id"),
                "practice_name": m["metadata"].get("practice_name"),
                "domain": m["metadata"].get("domain", ""),
                "country": m["metadata"].get("country", ""),
                "similarity": round(m["similarity_score"], 4),
            }
            for m in matches
        ],
        "assessment": assessment,
        "llm_used": llm_used,
    }
