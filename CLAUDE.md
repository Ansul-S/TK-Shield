# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

TK-Shield is a **defensive bio-piracy monitoring & analysis platform**. It protects documented **Traditional Knowledge (TK)** — e.g. turmeric for wound healing, neem as antifungal — from patents that misappropriate it, the same mission as India's TKDL and WIPO IGC. Given a documented TK practice, it finds patents that may claim it, scores bio-piracy risk, gathers prior-art evidence from free public sources, and uses a local LLM to produce a citation-backed assessment plus a draft patent opposition.

The three landmark cases the project is built around — turmeric (US5401504A), neem (EP0436257B1), basmati (US5663484A) — are real disputes that were overturned using prior-art evidence. They are seeded into the corpus (see `src/ingestion/seed_landmark_cases.py`) so the tool demonstrates them.

## End-to-end flow

```
TK entry (registry) → hybrid search over patents (RRF: semantic 0.7 + BM25 0.3)
→ 5-factor risk score → prior-art enrichment (PubMed/Wikidata/GBIF)
→ RAG report via Ollama (citation-backed assessment + opposition draft)
→ FastAPI endpoints → static web dashboard
   (+ optional live PatentsView monitoring of newly-filed patents)
```

## Three personas (one platform, no auth/workflow layer)

- **Defender** (communities/NGOs): register TK → analyze/report/monitor → opposition draft. `routes/{tk,analyze,report,monitor}`.
- **Examiner** (IP offices): paste a patent → reverse lookup over the `tk_entries` collection → novelty verdict + matching prior art. `src/rag/novelty.py`, `routes/novelty.py`.
- **Researcher**: aggregate analytics over registry + patent corpus (domains, geography, assignees). `routes/stats.py`.

The frontend (`frontend/index.html`) has a role switcher for the three.

## Environment & commands

Dependencies are pinned in `requirements.txt`; run everything via the project `venv`.

```bash
venv/bin/pip install -r requirements.txt
venv/bin/python -m spacy download en_core_web_sm    # one-time
# Ollama (one-time): install from ollama.com, then:
ollama pull llama3.2

# Data pipeline (run in order; produces data/raw/patents_medicinal.csv + chroma_db/):
# Patent corpus — keyless real-metadata bulk (recommended; ~219MB one-time download):
PATENT_SOURCE=patentsview_bulk MAX_PATENTS=20000 venv/bin/python -m src.ingestion.build_corpus
# (or PATENT_SOURCE=ccdv for the zero-download, low-fidelity offline default)
venv/bin/python -m src.ingestion.ingest_to_chromadb     # (re)build index from CSV
venv/bin/python -m src.ingestion.seed_landmark_cases    # add the real bio-piracy patents
# (legacy: `python -m src.ingestion.patent_scraper` still works as the ccdv path)

# TK registry — build at scale from open sources:
TK_SOURCE=duke     TK_IMPORT_LIMIT=2000 venv/bin/python -m src.ingestion.build_registry
TK_SOURCE=wikidata TK_IMPORT_LIMIT=50   venv/bin/python -m src.ingestion.build_registry

# Run the app (serves API + frontend at http://localhost:8000):
venv/bin/uvicorn api.main:app --reload

# Tests (network-free, fixture-based):
venv/bin/pytest tests/ -q
venv/bin/pytest tests/test_clients.py -q                # single file
```

Modules use absolute `src.*` / `api.*` imports rooted at the repo root — **run them as modules** (`python -m src.x.y`), never as file paths. Each `src/` module keeps a `__main__` smoke block.

## Architecture

**Config** — `src/utils/config.py` is the single `config` singleton; everything (model names, weights, paths, API bases, toggles) comes from `.env` with defaults. Nothing is hardcoded; see `.env.example`. Add new tunables here.

**Search** (`src/search/`)
- `vector_store.py` — ChromaDB persistent client (cosine). Functions take `collection_name`, so `patents` and `tk_entries` coexist. `search()` returns `{document, metadata, similarity_score}` (`similarity = 1 - distance`).
- `keyword_search.py` — in-memory BM25 (`KeywordSearchEngine`).
- `hybrid_ranker.py` — **main search**. `HybridSearchEngine` fuses semantic + BM25 via Reciprocal Rank Fusion (weights/k from config). The point is rescue cases: folk/Hindi/scientific synonyms BM25 misses but semantics recover.

**Risk** (`src/classifier/ip_risk_scorer.py`) — `score_risk(tk_entry, search_results)` → 0–100 from 5 weighted factors (similarity 40, temporal 20, geographic 15, assignee 15, IPC 10) → MINIMAL/LOW/MEDIUM/HIGH/CRITICAL + fixed recommendation lists.

**NLP** (`src/nlp/`) — `preprocessor.py` (clean→tokenize→stopwords→lemmatize) and `ner_extractor.py` (dictionary NER for plants/uses/practices + spaCy for locations). The registry uses `extract_all` to auto-tag entries.

**Clients** (`src/clients/`) — resilient `httpx` wrappers over free APIs. `_http.py` retries, times out, sends a descriptive `User-Agent` (Wikidata 403s without one), and **returns None on any failure — never raises**. `pubmed_client`, `wikidata_client`, `gbif_client` are keyless; `patentsview_client` needs a free key and no-ops (`is_available()` → False) without one.

**Enrichment** (`src/enrichment/prior_art.py`) — fans out to the keyless clients, returns one deduped, **citation-tagged** evidence bundle (each item carries `source` + stable ID: PMID / QID / GBIF key) plus `sources_used`/`sources_skipped` for transparent reports.

**RAG** (`src/rag/`)
- `llm_client.py` — pluggable LLM interface; `OllamaClient` is the default (`get_llm()` factory). `is_available()` checks the server + that the model is pulled.
- `retriever.py` — `build_context()` assembles patents (hybrid) + risk + evidence; reuses `score_risk`, `gather_evidence`, and NER fallback for ad-hoc text.
- `report_generator.py` — `generate_report()` prompts the LLM for JSON `{assessment, opposition_draft}`; **falls back to a deterministic template if the LLM is unavailable** (figures/citations stay exact). Offline-first.

**Reporting** (`src/report/renderer.py`) — `to_markdown()` (always) and `to_pdf()` (best-effort reportlab).

**Registry** (`src/registry/tk_store.py`) — CRUD for TK entries; SQLite (source of truth, `config.TK_DB_PATH`) + `tk_entries` ChromaDB collection. Auto-NER on create.

**Corpus scale-up** (`src/ingestion/`)
- `sources/` — pluggable patent sources exposing `iter_patents(limit)`, selected by `config.PATENT_SOURCE`:
  - **`patentsview_bulk`** (recommended) — keyless PatentsView **bulk TSV** S3 files (`g_patent` ~219MB + optional `g_assignee_disambiguated`). Real IDs/titles/abstracts/dates/assignees, **no key, no registration**. Streams + chunk-reads, regex-filters to TK relevance, caches under `config.PATENTSVIEW_BULK_DIR`. Frame-level logic (`patents_from_frame`, `assignee_map_from_frame`) is unit-tested.
  - `ccdv_source` — keyless HF corpus (no download; low-fidelity synthetic metadata) — the zero-setup default.
  - `patentsview_harvest` — PatentsView **live API** paged by CPC; real metadata but needs a free key. Kept optional; **not needed** now that bulk is keyless.
  - `build_corpus.py` drives the chosen source → appends to the canonical CSV (dedup by id); `ingest_to_chromadb` rebuilds the index (batched + `rebuild=False` resume for large runs). **Rejected sources:** HUPD (`datasets`≥4 removed loading-script support → dead) and the PatentsView bulk *landing page* (redirects to the USPTO ODP sign-in migration) — but the underlying bulk **S3 files** remain public and keyless, which is what `patentsview_bulk` uses.
- `tk_sources/` — pluggable TK-registry sources exposing `iter_tk_entries(limit)`: `duke_importer` (Dr. Duke CC0 ethnobotany, fuzzy column detection) and `wikidata_harvester` (curated cross-region seed + real Wikidata multilingual aliases). `build_registry.py` drives the chosen source → `tk_store.register_bulk` (batched). `config.TK_SOURCE`, `TK_IMPORT_LIMIT`.

**Domain classifier** (`src/classifier/domain.py`) — `infer_domain(text, ipc)` tags medicinal/agricultural/food/cosmetic (CPC prefix via `config.DOMAIN_IPC_GROUPS`, else keywords). Used on TK entries (stored `domain` field) and in researcher stats.

**API** (`api/`) — `main.py` (app, CORS, serves `frontend/` static at `/`, lifespan inits the DB), `deps.py` (`lru_cache` singletons: hybrid engine from the CSV, LLM; `resolve_entry` loads by `tk_id` or builds ad-hoc), `schemas.py`, and `routes/`: `tk` (CRUD; `GET` is paginated + free-text searchable — `?q=&limit=&offset=` → `{items,total,limit,offset,q}`), `analyze` (fast search+score, no LLM/network), `report` (full RAG; `?format=json|markdown|pdf`), `monitor` (live PatentsView, degrades gracefully), `novelty` (examiner reverse lookup), `stats` (researcher analytics). `/api/health` reports LLM + live-patent availability. Query building (`retriever.build_query`) folds TK aliases (folk/multilingual names) into the search.

**Frontend** (`frontend/index.html`) — single, **dependency-free** static SPA (hand-written CSS, vanilla JS, tiny inline markdown renderer). No CDN/npm by design, so nothing rots. Served by FastAPI.

## Key conventions & gotchas

- **Graceful degradation is a hard rule.** No external API (or the LLM) may crash the pipeline. Clients return empty; the report notes skipped sources. The whole tool works offline with zero keys on the HuggingFace corpus + Ollama.
- **Free APIs only.** Keyless & verified live: PubMed E-utilities, Wikidata, GBIF, HuggingFace datasets, Ollama. Live patents (PatentsView) need a *free* key — optional. Do not add paid/registration-gated APIs.
- **Two TK keyword lists differ on purpose** — `patent_scraper.py` (broad) vs `ingest_to_chromadb.py` (strict `STRICT_TK_KEYWORDS`). The hybrid engine's BM25 is built from the strict-filtered CSV, and ChromaDB is rebuilt from the same set, so re-run `ingest_to_chromadb` after changing the corpus to keep them consistent.
- **Patent record shape** is consistent everywhere: top-level `id`/`text` + a `metadata` dict (`patent_id`, `title`, `assignee`, `filing_date`, `country`, `ipc_code`, `status`, …). Preserve it when adding sources; `patentsview_client` and `seed_landmark_cases` both normalize to it.
- **TK entry shape**: `tk_id, practice_name, description, community, country, documentation_date, category, domain, plants[], uses[], locations[], aliases[]`. (`domain`/`aliases` added in scale-up; `tk_store.init_db` auto-migrates older DBs via `ALTER TABLE`.) Bulk imports use `tk_store.register_bulk`; single creates use `add_entry`.
- `data/`, `chroma_db/`, and the SQLite registry are gitignored and built locally.
