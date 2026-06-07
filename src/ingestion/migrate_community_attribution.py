# src/ingestion/migrate_community_attribution.py
#
# One-off, idempotent migration over the existing TK registry. Earlier Duke
# imports stored the documented holder group inside the country cell
# (e.g. 'INDIA(SANTAL)') and an occasional footnote asterisk ('JAPAN*'). This
# pass splits the people/community out into the `community` field and cleans the
# country, so:
#   * country values consolidate (INDIA(BENGAL)/INDIA(SANTAL)/... -> INDIA), and
#   * the indigenous/local community is attributed — the dimension the Nagoya
#     Protocol and WIPO IGC center on.
#
# Safe to re-run: rows already split are left unchanged. Updates SQLite (source
# of truth) and the tk_entries ChromaDB metadata (country) in lockstep.
#
# Run:  PYTHONPATH=. venv/bin/python -m src.ingestion.migrate_community_attribution

import sqlite3

from loguru import logger

from src.ingestion.tk_sources.duke_importer import (
    DUKE_PROVENANCE,
    is_not_a_people,
    split_geo,
)
from src.registry import tk_store
from src.search import vector_store
from src.utils.config import config


def migrate() -> dict:
    tk_store.init_db()
    conn = sqlite3.connect(config.TK_DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT tk_id, practice_name, country, community, domain, documentation_date "
        "FROM tk_entries"
    ).fetchall()

    changed = []
    for r in rows:
        country, people = split_geo(r["country"])
        new_country = country.upper()  # tk_store stores country uppercased
        new_community = r["community"] or ""
        # Clear a previously mis-attributed country/region/religion that was
        # stored as a community (e.g. 'India', 'Asia', 'Hindu') — these are not
        # holder peoples (M2). Genuine peoples (Santal, Aztec, …) are kept.
        if new_community and new_community != DUKE_PROVENANCE and is_not_a_people(new_community):
            new_community = ""
        # Only adopt the parsed people as community when we don't already have a
        # specific one (empty or the generic Duke provenance placeholder).
        if people and new_community in ("", DUKE_PROVENANCE):
            new_community = people
        if new_country != (r["country"] or "") or new_community != (r["community"] or ""):
            changed.append({
                "tk_id": r["tk_id"], "country": new_country, "community": new_community,
                "practice_name": r["practice_name"], "domain": r["domain"] or "",
                "documentation_date": r["documentation_date"] or "",
            })

    for c in changed:
        conn.execute(
            "UPDATE tk_entries SET country=?, community=? WHERE tk_id=?",
            (c["country"], c["community"], c["tk_id"]),
        )
    conn.commit()
    conn.close()

    # Keep the semantic index metadata in sync (country lives in chroma meta).
    if changed:
        try:
            col = vector_store.get_or_create_collection(config.TK_COLLECTION)
            col.update(
                ids=[c["tk_id"] for c in changed],
                metadatas=[{
                    "tk_id": c["tk_id"], "practice_name": c["practice_name"],
                    "country": c["country"], "domain": c["domain"],
                    "documentation_date": c["documentation_date"],
                } for c in changed],
            )
        except Exception as e:  # noqa: BLE001 — index resync is best-effort
            logger.warning(f"ChromaDB metadata resync skipped: {e}")

    logger.success(
        f"Community-attribution migration: updated {len(changed)} / {len(rows)} entries"
    )
    return {"updated": len(changed), "total": len(rows)}


if __name__ == "__main__":
    migrate()
