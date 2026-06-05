# src/ingestion/tk_sources/duke_importer.py
#
# Build TK entries from Dr. Duke's Phytochemical & Ethnobotanical Databases
# (USDA, CC0 public domain). The ethnobotany table links a plant taxon to a
# documented traditional use (+ optional country/reference). We aggregate per
# taxon into one TK entry with all its uses.
#
# Data: set DUKE_CSV_PATH to a locally-downloaded ethnobotany CSV, or let this
# fetch DUKE_DATA_URL (a zip) and locate the ethnobotany table inside it.
# Column names vary across releases, so detection is fuzzy/case-insensitive.

import io
import zipfile
from collections import defaultdict
from pathlib import Path
from typing import Iterator

import httpx
import pandas as pd
from loguru import logger

from src.classifier.domain import infer_domain
from src.utils.config import config


def _find_col(columns, *needles) -> str | None:
    for c in columns:
        cl = str(c).lower()
        if any(n in cl for n in needles):
            return c
    return None


def _load_dataframe() -> pd.DataFrame | None:
    """Return the ethnobotany dataframe from local CSV or the remote zip."""
    local = Path(config.DUKE_CSV_PATH)
    if local.exists():
        logger.info(f"Duke: reading local CSV {local}")
        return pd.read_csv(local, encoding="latin-1", on_bad_lines="skip")

    logger.info(f"Duke: downloading {config.DUKE_DATA_URL}")
    try:
        resp = httpx.get(config.DUKE_DATA_URL, timeout=120, follow_redirects=True)
        resp.raise_for_status()
    except Exception as e:  # noqa: BLE001
        logger.error(f"Duke download failed ({e}). Set DUKE_CSV_PATH to a local file.")
        return None

    content = resp.content
    # Detect a zip by magic bytes (the download URL may not end in .zip).
    if content[:2] == b"PK":
        zf = zipfile.ZipFile(io.BytesIO(content))
        names = [n for n in zf.namelist() if "ethnobot" in n.lower() and n.lower().endswith(".csv")]
        if not names:
            names = [n for n in zf.namelist() if n.lower().endswith(".csv")]
        if not names:
            logger.error("Duke zip contained no CSV.")
            return None
        logger.info(f"Duke: using table {names[0]} from zip")
        return pd.read_csv(zf.open(names[0]), encoding="latin-1", on_bad_lines="skip")
    return pd.read_csv(io.BytesIO(content), encoding="latin-1", on_bad_lines="skip")


def entries_from_dataframe(df: pd.DataFrame, limit: int) -> list[dict]:
    """Aggregate the ethnobotany table into per-taxon TK entries."""
    taxon_col = _find_col(df.columns, "taxon", "latin", "scientific")
    use_col = _find_col(df.columns, "activity", "ethnob", "use")
    country_col = _find_col(df.columns, "country", "geo", "region")
    cname_col = _find_col(df.columns, "cname", "common")
    if not taxon_col or not use_col:
        logger.error(f"Duke: could not detect taxon/use columns in {list(df.columns)}")
        return []

    def _clean(v) -> str:
        # Empty cells read by pandas become NaN → str "nan"; never keep those.
        s = str(v).strip()
        return "" if s.lower() in ("nan", "none", "") else s

    uses_by_taxon: dict[str, set] = defaultdict(set)
    country_by_taxon: dict[str, str] = {}
    cname_by_taxon: dict[str, str] = {}
    for _, row in df.iterrows():
        taxon = _clean(row.get(taxon_col))
        use = _clean(row.get(use_col))
        if not taxon or not use:
            continue
        uses_by_taxon[taxon].add(use)
        if country_col and not country_by_taxon.get(taxon):
            country_by_taxon[taxon] = _clean(row.get(country_col))
        if cname_col and not cname_by_taxon.get(taxon):
            cname_by_taxon[taxon] = _clean(row.get(cname_col))

    entries = []
    for taxon, uses in uses_by_taxon.items():
        use_list = sorted(uses)[:25]
        cname = cname_by_taxon.get(taxon, "")
        name = cname or taxon                       # never "nan"
        desc = f"Documented traditional/ethnobotanical uses of {taxon}: " + ", ".join(use_list) + "."
        entries.append({
            "practice_name": f"{name} — traditional uses",
            "description": desc,
            "community": "Documented ethnobotany (Dr. Duke, USDA)",
            "country": country_by_taxon.get(taxon, ""),   # full name; not truncated to garbage
            "documentation_date": "",
            "category": "ethnobotanical",
            "domain": infer_domain(desc),
            "plants": [p for p in [taxon, cname] if p],   # no "nan"
            "uses": use_list,
            "aliases": [cname] if cname else [],
        })
        if len(entries) >= limit:
            break
    return entries


def iter_tk_entries(limit: int) -> Iterator[dict]:
    df = _load_dataframe()
    if df is None or df.empty:
        return
    entries = entries_from_dataframe(df, limit)
    logger.success(f"Duke: built {len(entries)} TK entries")
    yield from entries
