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
def list_entries() -> list[dict]:
    return tk_store.list_entries()


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
