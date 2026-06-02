# api/routes/monitor.py — live patent monitoring via PatentsView.
# Gracefully degrades: with no free API key, returns available=false and a
# note instead of failing. The rest of TK-Shield is unaffected.

from fastapi import APIRouter, HTTPException

from api.deps import resolve_entry
from api.schemas import MonitorIn
from src.clients import patentsview_client

router = APIRouter(prefix="/api/monitor", tags=["monitor"])


@router.post("")
def monitor(req: MonitorIn) -> dict:
    query = req.query
    if not query and req.tk_id:
        try:
            entry = resolve_entry(tk_id=req.tk_id)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        query = ". ".join(p for p in [entry.get("practice_name", ""), entry.get("description", "")] if p)
    if not query:
        raise HTTPException(status_code=400, detail="Provide a query or a tk_id")

    available = patentsview_client.is_available()
    patents = patentsview_client.search_patents(query, n_results=req.n_results)
    return {
        "available": available,
        "query": query,
        "patents": patents,
        "note": (
            "Live results from PatentsView."
            if available else
            "Live monitoring disabled: set a free PATENTSVIEW_API_KEY to enable. "
            "Core analysis still works on the offline corpus."
        ),
    }
