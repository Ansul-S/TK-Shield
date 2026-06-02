# src/clients/gbif_client.py
#
# GBIF API (keyless, verified live 2026).
# Resolves a species and its native geographic distribution. The native
# country list feeds the risk scorer's geographic factor — a strong
# bio-piracy signal when a patent's country differs from the plant's origin.

from loguru import logger

from src.clients._http import get_json
from src.utils.config import config


def species_origin(name: str) -> dict | None:
    """
    Look up `name` in GBIF and return a citation-tagged dict:
    {source, ref_id (usageKey), title (scientificName), detail (family),
     native_countries: [ISO codes], url} or None on failure / no match.
    """
    if not config.ENABLE_GBIF or not name.strip():
        return None

    # /species/match does fuzzy matching against the GBIF backbone taxonomy
    # and is far more precise than /species/search for scientific names
    # (the free-text search happily returns unrelated species for common names).
    rec = get_json(
        f"{config.GBIF_API_BASE}/species/match",
        params={"name": name, "strict": "false"},
    )
    if not isinstance(rec, dict):
        return None
    # Only trust confident species/genus matches — skip "NONE"/"HIGHERRANK" noise.
    if rec.get("matchType") in (None, "NONE") or not rec.get("usageKey"):
        return None

    key = rec.get("usageKey")

    native = []
    distributions = get_json(f"{config.GBIF_API_BASE}/species/{key}/distributions")
    if isinstance(distributions, dict):
        for d in distributions.get("results", []):
            if str(d.get("establishmentMeans", "")).upper() == "NATIVE" and d.get("country"):
                native.append(d["country"])

    logger.info(f"GBIF: '{name}' → {key}, native in {native or 'unknown'}")
    return {
        "source": "gbif",
        "ref_id": str(key),
        "title": rec.get("scientificName", name),
        "detail": rec.get("family", ""),
        "native_countries": sorted(set(native)),
        "url": f"https://www.gbif.org/species/{key}",
    }


if __name__ == "__main__":
    print(species_origin("Curcuma longa"))
    print(species_origin("Azadirachta indica"))
