# api/routes/tk.py — CRUD for documented TK entries (the registry).

from fastapi import APIRouter, HTTPException

from api.schemas import TKEntryIn
from src.registry import tk_store

router = APIRouter(prefix="/api/tk", tags=["tk"])


@router.post("")
def create_entry(entry: TKEntryIn) -> dict:
    try:
        return tk_store.add_entry(entry.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("")
def list_entries(q: str = "", limit: int = 25, offset: int = 0) -> dict:
    """Paginated, searchable list. Returns {items, total, limit, offset, q}."""
    limit = max(1, min(limit, 200))   # clamp page size
    offset = max(0, offset)
    query = q.strip() or None
    return {
        "items": tk_store.list_entries(limit=limit, offset=offset, query=query),
        "total": tk_store.count_entries(query=query),
        "limit": limit,
        "offset": offset,
        "q": q,
    }


@router.get("/{tk_id}")
def get_entry(tk_id: str) -> dict:
    entry = tk_store.get_entry(tk_id)
    if not entry:
        raise HTTPException(status_code=404, detail=f"TK entry '{tk_id}' not found")
    return entry


@router.delete("/{tk_id}")
def delete_entry(tk_id: str) -> dict:
    if not tk_store.delete_entry(tk_id):
        raise HTTPException(status_code=404, detail=f"TK entry '{tk_id}' not found")
    return {"deleted": tk_id}
