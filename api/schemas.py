# api/schemas.py — request models. Responses are returned as plain dicts
# (the report/risk structures are rich and already JSON-serializable).

from typing import Annotated

from pydantic import AfterValidator, BaseModel, Field

# Bounds (S3/S4). Single-user/localhost today, but these are cheap insurance:
# a stray n_results=100000 or a multi-MB paste must not reach embeddings, the
# local LLM, or SQLite. Caps are generous so legitimate input always passes.
N_RESULTS_MAX = 50
MAX_NAME = 300        # practice name / short identifiers
MAX_SHORT = 200       # community, country, date, category
MAX_TEXT = 20_000     # free-text description
MAX_PATENT_TEXT = 50_000  # pasted patent abstract/claims (can be long)
MAX_LIST = 200        # plants / uses item count


def _clamp_n_results(v: int) -> int:
    # Silent clamp (matches the tk list-endpoint convention) rather than 422 —
    # out-of-range here is a knob to bound, not a malformed request.
    return max(1, min(v, N_RESULTS_MAX))


# Reusable clamped page-size type shared by every model that takes n_results.
NResults = Annotated[int, AfterValidator(_clamp_n_results)]


class TKEntryIn(BaseModel):
    practice_name: str = Field(..., max_length=MAX_NAME,
                               description="Short name of the traditional practice")
    description: str = Field("", max_length=MAX_TEXT)
    community: str = Field("", max_length=MAX_SHORT)
    country: str = Field("", max_length=MAX_SHORT)
    documentation_date: str = Field("", max_length=MAX_SHORT)  # YYYY-MM-DD
    category: str = Field("", max_length=MAX_SHORT)
    # optional; auto-extracted via NER if omitted
    plants: list[str] | None = Field(None, max_length=MAX_LIST)
    uses: list[str] | None = Field(None, max_length=MAX_LIST)


class AnalyzeIn(BaseModel):
    """Analyze either a registered entry (tk_id) or an ad-hoc TK description."""
    tk_id: str | None = Field(None, max_length=MAX_SHORT)
    practice_name: str = Field("", max_length=MAX_NAME)
    description: str = Field("", max_length=MAX_TEXT)
    country: str = Field("", max_length=MAX_SHORT)
    documentation_date: str = Field("", max_length=MAX_SHORT)
    n_results: NResults = 5


class MonitorIn(BaseModel):
    """Live patent check. Provide a tk_id or a free-text query."""
    tk_id: str | None = Field(None, max_length=MAX_SHORT)
    query: str = Field("", max_length=MAX_TEXT)
    n_results: NResults = 10
