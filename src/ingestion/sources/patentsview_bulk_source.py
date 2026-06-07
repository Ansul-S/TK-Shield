# src/ingestion/sources/patentsview_bulk_source.py
#
# Keyless, real-metadata patent source: PatentsView bulk TSV files. These are
# public S3 downloads — NO API key, NO registration (the key is only for the
# live API). Gives real patent IDs / titles / abstracts / grant dates and,
# optionally, real assignee organizations — the fidelity the risk scorer needs.
#
#   g_patent.tsv.zip               (~219 MB) — id, title, abstract, date
#   g_assignee_disambiguated.tsv.zip (~342 MB) — assignee organization (optional)
#
# Files are cached under config.PATENTSVIEW_BULK_DIR; drop pre-downloaded files
# there to skip the download. Rows are filtered to TK relevance by the strict
# keyword set (regex, vectorized) so we keep the bio-piracy-prone subset.

import re
from pathlib import Path
from typing import Iterator

import httpx
import pandas as pd
from loguru import logger

from src.ingestion.ingest_to_chromadb import STRICT_TK_KEYWORDS
from src.utils.config import config

_G_PATENT = "g_patent.tsv.zip"
_G_ASSIGNEE = "g_assignee_disambiguated.tsv.zip"
_CHUNK = 100_000
_TK_RE = re.compile("|".join(re.escape(k) for k in STRICT_TK_KEYWORDS), re.IGNORECASE)


def _ensure_file(fname: str) -> Path | None:
    """Return a local path to a bulk file, downloading (streamed) if absent."""
    path = Path(config.PATENTSVIEW_BULK_DIR) / fname
    if path.exists():
        logger.info(f"bulk: using cached {path}")
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    url = f"{config.PATENTSVIEW_BULK_BASE}/{fname}"
    logger.info(f"bulk: downloading {url} → {path} (one-time)")
    try:
        with httpx.stream("GET", url, timeout=None, follow_redirects=True) as r:
            r.raise_for_status()
            with open(path, "wb") as fh:
                for chunk in r.iter_bytes(chunk_size=1 << 20):
                    fh.write(chunk)
    except Exception as e:  # noqa: BLE001
        logger.error(f"bulk download failed for {fname}: {e}")
        if path.exists():
            path.unlink(missing_ok=True)
        return None
    return path


def _col(df: pd.DataFrame, *needles: str) -> str | None:
    for c in df.columns:
        if any(n in str(c).lower() for n in needles):
            return c
    return None


def patents_from_frame(df: pd.DataFrame) -> list[dict]:
    """Filter a g_patent chunk to TK relevance and normalize to canonical dicts."""
    id_c = _col(df, "patent_id") or "patent_id"
    title_c = _col(df, "patent_title", "title")
    abs_c = _col(df, "patent_abstract", "abstract")
    date_c = _col(df, "patent_date", "date")
    if not title_c:
        return []
    abs_series = df[abs_c].fillna("") if abs_c else ""
    blob = (df[title_c].fillna("") + " " + abs_series).str
    keep = df[blob.contains(_TK_RE, na=False)]

    out = []
    for _, row in keep.iterrows():
        pid = str(row.get(id_c, "")).strip()
        title = str(row.get(title_c, "") or "")
        abstract = str(row.get(abs_c, "") or "") if abs_c else ""
        if not pid or not title:
            continue
        out.append({
            "id": f"{config.DEFAULT_JURISDICTION}{pid}",
            "text": f"{title}. {abstract}".strip(),
            "metadata": {
                "patent_id": f"{config.DEFAULT_JURISDICTION}{pid}",
                "title": title[:config.TITLE_MAX_CHARS],
                "abstract": abstract[:config.ABSTRACT_MAX_CHARS],
                "assignee": "Unknown",
                "filing_date": str(row.get(date_c, "") or ""),
                "country": config.DEFAULT_PATENT_COUNTRY,
                "ipc_code": "",
                "source": "patentsview-bulk",
                "status": "GRANTED",
            },
        })
    return out


def assignee_map_from_frame(df: pd.DataFrame, ids: set[str]) -> dict[str, str]:
    """Map raw patent_id → assignee organization for the ids we kept."""
    id_c = _col(df, "patent_id") or "patent_id"
    org_c = _col(df, "organization")
    if not org_c:
        return {}
    sub = df[df[id_c].astype(str).isin(ids)]
    return {
        str(r[id_c]): str(r[org_c])
        for _, r in sub.iterrows() if str(r.get(org_c, "")).strip()
    }


def iter_patents(limit: int) -> Iterator[dict]:
    gpath = _ensure_file(_G_PATENT)
    if gpath is None:
        return

    kept: list[dict] = []
    for chunk in pd.read_csv(gpath, sep="\t", compression="zip", dtype=str,
                             chunksize=_CHUNK, on_bad_lines="skip"):
        kept.extend(patents_from_frame(chunk))
        if len(kept) >= limit:
            kept = kept[:limit]
            break
    logger.success(f"bulk: kept {len(kept)} TK-relevant patents")

    if config.BULK_ENRICH_ASSIGNEE and kept:
        apath = _ensure_file(_G_ASSIGNEE)
        if apath is not None:
            _plen = len(config.DEFAULT_JURISDICTION)
            raw_ids = {p["id"][_plen:] for p in kept}  # strip the jurisdiction prefix
            amap: dict[str, str] = {}
            for chunk in pd.read_csv(apath, sep="\t", compression="zip", dtype=str,
                                     chunksize=_CHUNK, on_bad_lines="skip"):
                amap.update(assignee_map_from_frame(chunk, raw_ids))
            for p in kept:
                org = amap.get(p["id"][2:])
                if org:
                    p["metadata"]["assignee"] = org
            logger.success(f"bulk: enriched {len(amap)} assignees")

    yield from kept
