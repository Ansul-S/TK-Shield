# src/clients/patentsview_client.py
#
# PatentsView PatentSearch API (live US patents).
# This is the ONE source that needs a key — a FREE X-Api-Key. The legacy
# keyless API was retired Feb 2025. Absent a key, this returns [] with a
# clear warning and the rest of TK-Shield keeps working on the offline
# HuggingFace corpus. This is the "live monitoring" of newly-filed patents.

from loguru import logger

from src.clients._http import post_json
from src.utils.config import config

# Fields requested from the API, mapped into TK-Shield's patent shape below.
_FIELDS = [
    "patent_id",
    "patent_title",
    "patent_abstract",
    "patent_date",
    "assignees.assignee_organization",
]


def is_available() -> bool:
    """Live monitoring is only possible when enabled AND a key is configured."""
    return config.ENABLE_PATENTSVIEW and bool(config.PATENTSVIEW_API_KEY)


def search_patents(query: str, n_results: int = 10) -> list[dict]:
    """
    Search live US patents whose title/abstract match `query`.
    Returns patents normalized to TK-Shield's shape
    ({id, text, metadata{...}}). Returns [] if no key, disabled, or failure.
    """
    if not is_available():
        logger.warning(
            "PatentsView skipped: no PATENTSVIEW_API_KEY set "
            "(live monitoring disabled — core pipeline unaffected)."
        )
        return []
    if not query.strip():
        return []

    body = {
        "q": {"_text_any": {"patent_title": query, "patent_abstract": query}},
        "f": _FIELDS,
        "o": {"size": n_results},
    }
    data = _post(body)
    if data is None:
        logger.warning(f"PatentsView returned no usable data for '{query}'")
        return []
    patents = [_normalize_patent(p) for p in (data.get("patents") or [])]
    logger.info(f"PatentsView: {len(patents)} live patents for '{query}'")
    return patents


def _post(body: dict) -> dict | None:
    """POST to the patent endpoint; returns the JSON dict or None on failure."""
    data = post_json(
        f"{config.PATENTSVIEW_API_BASE}/patent/",
        json_body=body,
        headers={"X-Api-Key": config.PATENTSVIEW_API_KEY},
    )
    if not isinstance(data, dict) or data.get("error"):
        return None
    return data


def _normalize_patent(p: dict) -> dict:
    """Map one PatentSearch record into TK-Shield's canonical patent shape."""
    assignees = p.get("assignees") or []
    assignee = ""
    if assignees and isinstance(assignees, list):
        assignee = (assignees[0].get("assignee_organization") or "")
    cpc = p.get("cpc_current") or []
    cpc_code = ""
    if cpc and isinstance(cpc, list):
        cpc_code = (cpc[0].get("cpc_group_id") or cpc[0].get("cpc_subclass_id") or "")
    pid = p.get("patent_id", "")
    title = p.get("patent_title", "") or ""
    abstract = p.get("patent_abstract", "") or ""
    return {
        "id": pid,
        "text": f"{title}. {abstract}".strip(),
        "metadata": {
            "patent_id": pid,
            "title": title[:config.TITLE_MAX_CHARS],
            "abstract": abstract[:config.ABSTRACT_MAX_CHARS],
            "assignee": assignee or "Unknown",
            "filing_date": p.get("patent_date", ""),
            "country": "US",
            "ipc_code": cpc_code,
            "source": "patentsview",
            "status": "GRANTED",
        },
    }


def search_by_cpc(cpc_prefixes: list[str], after: str | None = None,
                  size: int = 100) -> tuple[list[dict], str | None]:
    """
    One page of patents whose current CPC subclass is in `cpc_prefixes`,
    sorted by patent_id for stable cursor pagination.

    Returns (normalized_patents, next_cursor). next_cursor is the last
    patent_id of the page (pass it back as `after`), or None when exhausted.
    Returns ([], None) if no key / disabled / failure — never raises.

    NOTE: CPC field names / pagination are per the PatentSearch API docs; if a
    live run rejects them, adjust the `q`/`s`/`o` keys here. Normalization
    (the part covered by tests) is independent of those names.
    """
    if not is_available() or not cpc_prefixes:
        return [], None
    # Coarse subclass match (first 4 chars, e.g. "A61K36" -> "A61K"); the API
    # treats a list value as an IN/OR set.
    subclasses = sorted({c[:4] for c in cpc_prefixes})
    body = {
        "q": {"cpc_current.cpc_subclass_id": subclasses},
        "f": _FIELDS + ["cpc_current.cpc_group_id", "cpc_current.cpc_subclass_id"],
        "s": [{"patent_id": "asc"}],
        "o": {"size": size, **({"after": after} if after else {})},
    }
    data = _post(body)
    if data is None:
        return [], None
    raw = data.get("patents") or []
    patents = [_normalize_patent(p) for p in raw]
    next_cursor = patents[-1]["id"] if len(raw) == size and patents else None
    return patents, next_cursor


if __name__ == "__main__":
    print("Available:", is_available())
    for p in search_patents("turmeric wound healing", n_results=3):
        print(f"  {p['id']}: {p['metadata']['title'][:70]}")
