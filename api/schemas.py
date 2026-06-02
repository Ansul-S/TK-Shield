# api/schemas.py — request models. Responses are returned as plain dicts
# (the report/risk structures are rich and already JSON-serializable).

from pydantic import BaseModel, Field


class TKEntryIn(BaseModel):
    practice_name: str = Field(..., description="Short name of the traditional practice")
    description: str = ""
    community: str = ""
    country: str = ""
    documentation_date: str = ""  # YYYY-MM-DD
    category: str = ""
    plants: list[str] | None = None  # optional; auto-extracted via NER if omitted
    uses: list[str] | None = None


class AnalyzeIn(BaseModel):
    """Analyze either a registered entry (tk_id) or an ad-hoc TK description."""
    tk_id: str | None = None
    practice_name: str = ""
    description: str = ""
    country: str = ""
    documentation_date: str = ""
    n_results: int = 5


class MonitorIn(BaseModel):
    """Live patent check. Provide a tk_id or a free-text query."""
    tk_id: str | None = None
    query: str = ""
    n_results: int = 10
