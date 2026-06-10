# api/routes/novelty.py — Examiner persona: check a patent's novelty against
# the documented TK registry (reverse lookup).

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from api.deps import LLMBusy, get_llm_client, limiter, llm_slot
from api.schemas import MAX_PATENT_TEXT, MAX_SHORT, NResults
from src.clients import patentsview_client
from src.rag import novelty
from src.utils.config import config

router = APIRouter(prefix="/api/novelty", tags=["examiner"])


class NoveltyIn(BaseModel):
    patent_text: str = Field("", max_length=MAX_PATENT_TEXT)
    # optional: fetch text live (needs free key)
    patent_id: str | None = Field(None, max_length=MAX_SHORT)
    n_results: NResults = 5


@router.post("")
@limiter.limit(config.RATE_LIMIT_LLM)
def check_novelty(request: Request, req: NoveltyIn) -> dict:
    text = req.patent_text.strip()

    # Optionally resolve a live patent by id (graceful if no key).
    if not text and req.patent_id and patentsview_client.is_available():
        hits = patentsview_client.search_patents(req.patent_id, n_results=1)
        if hits:
            text = hits[0]["text"]

    if not text:
        raise HTTPException(
            status_code=400,
            detail="Provide patent_text (or a patent_id with a PatentsView key configured).",
        )

    try:
        with llm_slot():  # bound concurrent expensive requests
            # Claim-level assessment when the pasted text has claim structure;
            # falls back to whole-text automatically (claim_level=False).
            return novelty.assess_novelty_by_claim(
                text, n_results=req.n_results, llm=get_llm_client()
            )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except LLMBusy as e:
        raise HTTPException(status_code=503, detail=str(e))
