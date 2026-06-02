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
    data = post_json(
        f"{config.PATENTSVIEW_API_BASE}/patent/",
        json_body=body,
        headers={"X-Api-Key": config.PATENTSVIEW_API_KEY},
    )
    if not isinstance(data, dict) or data.get("error"):
        logger.warning(f"PatentsView returned no usable data for '{query}'")
        return []

    patents = []
    for p in data.get("patents", []) or []:
        assignees = p.get("assignees") or []
        assignee = ""
        if assignees and isinstance(assignees, list):
            assignee = assignees[0].get("assignee_organization", "") or ""
        pid = p.get("patent_id", "")
        title = p.get("patent_title", "") or ""
        abstract = p.get("patent_abstract", "") or ""
        patents.append({
            "id": pid,
            "text": f"{title}. {abstract}".strip(),
            "metadata": {
                "patent_id": pid,
                "title": title[:200],
                "abstract": abstract[:500],
                "assignee": assignee or "Unknown",
                "filing_date": p.get("patent_date", ""),
                "country": "US",
                "ipc_code": "",
                "source": "patentsview-live",
                "status": "GRANTED",
            },
        })
    logger.info(f"PatentsView: {len(patents)} live patents for '{query}'")
    return patents


if __name__ == "__main__":
    print("Available:", is_available())
    for p in search_patents("turmeric wound healing", n_results=3):
        print(f"  {p['id']}: {p['metadata']['title'][:70]}")
