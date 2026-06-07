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
import re
import zipfile
from collections import defaultdict
from pathlib import Path
from typing import Iterator

import httpx
import pandas as pd
from loguru import logger

from src.classifier.domain import infer_domain
from src.utils.config import config

DUKE_PROVENANCE = "Documented ethnobotany (Dr. Duke, USDA)"

# Values that are NOT a holder people/community — countries, continents/regions,
# and religions. Duke sometimes puts these in the parenthetical (e.g.
# 'X(ASIA)', 'X(INDIA)', 'X(HINDU)'); they must not be attributed as a
# community (Nagoya/WIPO-IGC). Genuine peoples (Santal, Seri, Aztec, …) are NOT
# listed here, so they pass through. Compared case-insensitively.
_GEO_REGIONS_RELIGIONS = {
    # continents / macro-regions
    "ASIA", "AFRICA", "EUROPE", "AMERICA", "NORTH AMERICA", "SOUTH AMERICA",
    "CENTRAL AMERICA", "LATIN AMERICA", "OCEANIA", "EURASIA", "MIDDLE EAST",
    "SCANDINAVIA", "CARIBBEAN", "AMAZONIA", "INDOCHINA", "MEDITERRANEAN",
    "WEST INDIES", "EAST INDIES", "BALKANS", "HIMALAYA", "HIMALAYAS",
    # religions / faiths (descriptors, not peoples)
    "HINDU", "MUSLIM", "ISLAM", "ISLAMIC", "CHRISTIAN", "CATHOLIC", "BUDDHIST",
    "BUDDHISM", "JEWISH", "JUDAISM", "SIKH", "JAIN", "TAOIST", "SHINTO",
}

# Country names are sourced from `pycountry` (so we don't hand-maintain the
# world). The set below is the FALLBACK used only when pycountry is unavailable
# — it preserves the prior behaviour exactly. Common/colloquial forms that
# pycountry's canonical names omit (US/UK/England/Burma/…) are always added on
# top via _COUNTRY_ALIASES, so no Duke label regresses.
_FALLBACK_COUNTRIES = {
    "INDIA", "CHINA", "JAPAN", "USA", "US", "UNITED STATES", "UK",
    "UNITED KINGDOM", "ENGLAND", "SCOTLAND", "IRELAND", "FRANCE", "GERMANY",
    "ITALY", "SPAIN", "PORTUGAL", "GREECE", "TURKEY", "RUSSIA", "POLAND",
    "NETHERLANDS", "BELGIUM", "SWEDEN", "NORWAY", "FINLAND", "DENMARK",
    "SWITZERLAND", "AUSTRIA", "HUNGARY", "ROMANIA", "BULGARIA", "UKRAINE",
    "EGYPT", "MOROCCO", "ALGERIA", "TUNISIA", "NIGERIA", "GHANA", "KENYA",
    "ETHIOPIA", "TANZANIA", "UGANDA", "SOUTH AFRICA", "ZIMBABWE", "ZAMBIA",
    "SUDAN", "SENEGAL", "CAMEROON", "CONGO", "MADAGASCAR", "MEXICO", "BRAZIL",
    "ARGENTINA", "CHILE", "PERU", "COLOMBIA", "VENEZUELA", "BOLIVIA",
    "ECUADOR", "PARAGUAY", "URUGUAY", "CANADA", "GUATEMALA", "CUBA",
    "PAKISTAN", "BANGLADESH", "SRI LANKA", "NEPAL", "BHUTAN", "AFGHANISTAN",
    "IRAN", "IRAQ", "ISRAEL", "SAUDI ARABIA", "YEMEN", "JORDAN", "LEBANON",
    "SYRIA", "THAILAND", "VIETNAM", "CAMBODIA", "LAOS", "MYANMAR", "BURMA",
    "MALAYSIA", "INDONESIA", "PHILIPPINES", "SINGAPORE", "KOREA",
    "SOUTH KOREA", "NORTH KOREA", "MONGOLIA", "AUSTRALIA", "NEW ZEALAND",
    "FIJI", "PAPUA NEW GUINEA", "HAWAII", "TIBET",
}

# Colloquial / sub-national forms pycountry's canonical names don't include
# (verified against _FALLBACK_COUNTRIES) — always applied so behaviour is
# preserved whether or not pycountry is present.
_COUNTRY_ALIASES = {
    "US", "USA", "UK", "ENGLAND", "SCOTLAND", "BURMA", "TIBET", "HAWAII",
    "KOREA", "SOUTH KOREA", "NORTH KOREA", "RUSSIA", "TURKEY",
}


def _country_names() -> set[str]:
    """Uppercased country names from pycountry; falls back to the built-in set
    when pycountry is unavailable (preserves prior behaviour)."""
    try:
        import pycountry
    except Exception as e:  # noqa: BLE001
        logger.warning(f"pycountry unavailable ({e}); using built-in country list")
        return set(_FALLBACK_COUNTRIES)
    names: set[str] = set()
    for c in pycountry.countries:
        for attr in ("name", "official_name", "common_name"):
            v = getattr(c, attr, None)
            if v:
                names.add(v.upper())
    return names


_GEO_NOT_PEOPLE = _GEO_REGIONS_RELIGIONS | _country_names() | _COUNTRY_ALIASES


def is_not_a_people(value: str) -> bool:
    """True if `value` is a country/region/religion (not a holder community)."""
    return (value or "").strip().upper() in _GEO_NOT_PEOPLE


def split_geo(raw) -> tuple[str, str]:
    """Split a Duke geographic label into (country, community/people).

    Duke encodes the documented holder group inside the country cell and tags
    some labels with a footnote asterisk, e.g. 'INDIA(SANTAL)' -> ('INDIA',
    'Santal'), 'JAPAN*' -> ('JAPAN', ''), 'US(AMERINDIAN)' -> ('US',
    'Amerindian'). A parenthetical that is itself a country/region/religion
    (e.g. 'X(ASIA)', 'X(HINDU)') is NOT a people, so it is dropped rather than
    mis-attributed as a community. Plain labels pass through unchanged.
    """
    s = str(raw or "").strip()
    if s.lower() in ("nan", "none", ""):
        return "", ""
    s = s.rstrip("*").strip()
    m = re.search(r"\(([^)]+)\)\s*$", s)
    if m:
        country = s[: m.start()].strip()
        people = m.group(1).strip().title()
        if is_not_a_people(people):
            return country, ""
        return country, people
    return s, ""


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
        # Duke buries the holder community in the country cell (e.g. INDIA(SANTAL));
        # split it out so country consolidates and the community is attributed.
        country, people = split_geo(country_by_taxon.get(taxon, ""))
        entries.append({
            "practice_name": f"{name} — traditional uses",
            "description": desc,
            "community": people or DUKE_PROVENANCE,
            "country": country,                           # holder community split out
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
