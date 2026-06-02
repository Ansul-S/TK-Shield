# api/routes/analyze.py — fast risk check: hybrid search + 5-factor score.
# No LLM, no external enrichment — this is the quick "how risky is this?" call.

from fastapi import APIRouter, HTTPException

from api.deps import get_engine, resolve_entry
from api.schemas import AnalyzeIn
from src.classifier.ip_risk_scorer import score_risk

router = APIRouter(prefix="/api/analyze", tags=["analyze"])


@router.post("")
def analyze(req: AnalyzeIn) -> dict:
    try:
        entry = resolve_entry(
            tk_id=req.tk_id,
            practice_name=req.practice_name,
            description=req.description,
            country=req.country,
            documentation_date=req.documentation_date,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    engine = get_engine()
    query = ". ".join(p for p in [entry.get("practice_name", ""), entry.get("description", "")] if p)
    patents = engine.search(query, n_results=req.n_results) if query else []
    risk = score_risk(entry, patents)

    return {
        "tk_entry": {k: entry.get(k) for k in ("tk_id", "practice_name", "country", "documentation_date")},
        "risk": risk,
        "patents": [
            {
                "patent_id": p.get("metadata", {}).get("patent_id", p.get("id")),
                "title": p.get("metadata", {}).get("title", ""),
                "assignee": p.get("metadata", {}).get("assignee", ""),
                "filing_date": p.get("metadata", {}).get("filing_date", ""),
                "country": p.get("metadata", {}).get("country", ""),
                "similarity": p.get("similarity_score", 0),
                "rrf_score": p.get("rrf_score", 0),
            }
            for p in patents
        ],
    }
