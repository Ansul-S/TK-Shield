# src/registry/tk_store.py
#
# CRUD store for documented Traditional Knowledge entries — the "watched"
# TK that the defensive-monitoring use case checks against patents.
#
# Two layers, kept in sync:
#   1. SQLite (structured metadata, source of truth)
#   2. ChromaDB `tk_entries` collection (semantic index for similarity search)
#
# On create, the existing dictionary NER auto-populates plants/uses/locations
# so the entry is immediately enriched without manual tagging.

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

from loguru import logger

from src.classifier.domain import infer_domain
from src.nlp.ner_extractor import extract_all
from src.search import vector_store
from src.utils.config import config

_JSON_FIELDS = ("plants", "uses", "locations", "aliases")
_COLUMNS = (
    "tk_id", "practice_name", "description", "community", "country",
    "documentation_date", "category", "domain", "plants", "uses", "locations",
    "aliases", "created_at",
)


def _connect() -> sqlite3.Connection:
    Path(config.TK_DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(config.TK_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Create the table if missing and migrate older DBs (idempotent)."""
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS tk_entries (
                tk_id              TEXT PRIMARY KEY,
                practice_name      TEXT NOT NULL,
                description        TEXT,
                community          TEXT,
                country            TEXT,
                documentation_date TEXT,
                category           TEXT,
                domain             TEXT,
                plants             TEXT,
                uses               TEXT,
                locations          TEXT,
                aliases            TEXT,
                created_at         TEXT
            )
            """
        )
        # Migrate DBs created before domain/aliases existed.
        existing = {r[1] for r in conn.execute("PRAGMA table_info(tk_entries)")}
        for col in ("domain", "aliases"):
            if col not in existing:
                conn.execute(f"ALTER TABLE tk_entries ADD COLUMN {col} TEXT")


def _row_to_entry(row: sqlite3.Row) -> dict:
    entry = {k: row[k] for k in row.keys()}
    for f in _JSON_FIELDS:
        entry[f] = json.loads(entry.get(f) or "[]")
    return entry


def _index_text(entry: dict) -> str:
    """Text indexed for semantic search — includes aliases so folk/multilingual
    names are findable."""
    parts = [entry["practice_name"], entry["description"]] + entry.get("aliases", [])
    return ". ".join(p for p in parts if p)


def _build_entry(data: dict) -> dict:
    """Normalize input into a full TK entry dict (auto-NER, domain, aliases)."""
    practice_name = (data.get("practice_name") or "").strip()
    if not practice_name:
        raise ValueError("practice_name is required")
    description = data.get("description", "")
    text = f"{practice_name}. {description}"
    ents = extract_all(text)["tk_entities"]
    plants = data.get("plants") or ents["plants"]
    uses = data.get("uses") or ents["medical_uses"]
    locations = data.get("locations") or ents["locations"]
    domain = data.get("domain") or infer_domain(text, data.get("ipc_code", ""))
    return {
        "tk_id": data.get("tk_id") or f"TK-{uuid.uuid4().hex[:8].upper()}",
        "practice_name": practice_name,
        "description": description,
        "community": data.get("community", ""),
        "country": (data.get("country", "") or "").upper(),
        "documentation_date": data.get("documentation_date", ""),
        "category": data.get("category", ""),
        "domain": domain,
        "plants": plants,
        "uses": uses,
        "locations": locations,
        "aliases": data.get("aliases") or [],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def _persist_sql(conn, entries: list[dict]) -> None:
    conn.executemany(
        f"INSERT OR REPLACE INTO tk_entries ({','.join(_COLUMNS)}) "
        f"VALUES ({','.join('?' for _ in _COLUMNS)})",
        [tuple(json.dumps(e[c]) if c in _JSON_FIELDS else e[c] for c in _COLUMNS)
         for e in entries],
    )


def add_entry(data: dict) -> dict:
    """
    Create a single TK entry (auto NER + domain). Persists to SQLite and indexes
    into the tk_entries ChromaDB collection. Used by the API.
    """
    init_db()
    entry = _build_entry(data)
    with _connect() as conn:
        _persist_sql(conn, [entry])
    vector_store.add_documents(
        collection_name=config.TK_COLLECTION,
        documents=[_index_text(entry)],
        metadatas=[_chroma_meta(entry)],
        ids=[entry["tk_id"]],
    )
    logger.success(f"Registered TK entry {entry['tk_id']}: {entry['practice_name']}")
    return entry


def _chroma_meta(entry: dict) -> dict:
    return {
        "tk_id": entry["tk_id"],
        "practice_name": entry["practice_name"],
        "country": entry["country"],
        "domain": entry.get("domain", ""),
        "documentation_date": entry["documentation_date"],
    }


def register_bulk(entries: list[dict], chunk: int = 256) -> int:
    """
    Batch-register many TK entries (importers). Embeds + indexes in chunks so
    thousands of entries are feasible. Returns the count registered.
    """
    init_db()
    built = []
    for d in entries:
        try:
            built.append(_build_entry(d))
        except ValueError:
            continue  # skip entries with no practice_name
    if not built:
        return 0

    with _connect() as conn:
        _persist_sql(conn, built)

    for i in range(0, len(built), chunk):
        part = built[i : i + chunk]
        vector_store.add_documents(
            collection_name=config.TK_COLLECTION,
            documents=[_index_text(e) for e in part],
            metadatas=[_chroma_meta(e) for e in part],
            ids=[e["tk_id"] for e in part],
        )
    logger.success(f"Bulk-registered {len(built)} TK entries")
    return len(built)


def get_entry(tk_id: str) -> dict | None:
    init_db()
    with _connect() as conn:
        row = conn.execute("SELECT * FROM tk_entries WHERE tk_id = ?", (tk_id,)).fetchone()
    return _row_to_entry(row) if row else None


def _search_clause(query: str | None) -> tuple[str, list]:
    """Build a WHERE clause + params for a free-text search across key fields."""
    if not query:
        return "", []
    like = f"%{query.strip()}%"
    cols = ("practice_name", "description", "plants", "aliases", "country", "community")
    clause = " WHERE " + " OR ".join(f"{c} LIKE ?" for c in cols)
    return clause, [like] * len(cols)


def list_entries(limit: int | None = None, offset: int = 0,
                 query: str | None = None) -> list[dict]:
    """
    List TK entries newest-first. Optional free-text `query` (substring match
    across name/description/plants/aliases/country/community) and `limit`/`offset`
    pagination. With no limit, returns all (used by stats).
    """
    init_db()
    clause, params = _search_clause(query)
    sql = f"SELECT * FROM tk_entries{clause} ORDER BY created_at DESC"
    if limit is not None:
        sql += " LIMIT ? OFFSET ?"
        params = params + [limit, offset]
    with _connect() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [_row_to_entry(r) for r in rows]


def count_entries(query: str | None = None) -> int:
    """Total entries matching `query` (for pagination)."""
    init_db()
    clause, params = _search_clause(query)
    with _connect() as conn:
        return conn.execute(f"SELECT COUNT(*) FROM tk_entries{clause}", params).fetchone()[0]


def delete_entry(tk_id: str) -> bool:
    init_db()
    with _connect() as conn:
        cur = conn.execute("DELETE FROM tk_entries WHERE tk_id = ?", (tk_id,))
        deleted = cur.rowcount > 0
    if deleted:
        try:
            vector_store.get_or_create_collection(config.TK_COLLECTION).delete(ids=[tk_id])
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Could not remove {tk_id} from ChromaDB: {e}")
    return deleted


if __name__ == "__main__":
    e = add_entry({
        "practice_name": "Turmeric paste for wound healing",
        "description": "Haldi applied to cuts and abrasions in Ayurveda",
        "community": "Traditional Ayurvedic communities",
        "country": "IN",
        "documentation_date": "1950-01-01",
        "category": "Medicinal",
    })
    print("Created:", e["tk_id"], "| plants:", e["plants"], "| uses:", e["uses"])
    print("List count:", len(list_entries()))
