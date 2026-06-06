# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

TK-Shield is a **defensive bio-piracy monitoring & analysis platform**. It protects documented **Traditional Knowledge (TK)** — e.g. turmeric for wound healing, neem as antifungal — from patents that misappropriate it, the same mission as India's TKDL and WIPO IGC. Given a documented TK practice, it finds patents that may claim it, scores bio-piracy risk, gathers prior-art evidence from free public sources, and uses a local LLM to produce a citation-backed assessment plus a draft patent opposition.

The three landmark cases the project is built around — turmeric (US5401504A), neem (EP0436257B1), basmati (US5663484A) — are real disputes that were overturned using prior-art evidence. They are seeded into the corpus (`src/ingestion/seed_landmark_cases.py`) so the tool always demonstrates them.

**Core principles (non-negotiable):**
- **Free & keyless first.** The entire pipeline runs with **zero API keys**. Keyless+verified-live sources: PatentsView **bulk** files, PubMed E-utilities, Wikidata, GBIF, HuggingFace datasets, Dr. Duke (CC0), Ollama (local). Do **not** add paid or registration-gated APIs.
- **Graceful degradation is a hard rule.** No external API (or the LLM) may crash the pipeline. Clients return empty/None on any failure; reports note skipped sources. Everything works offline.
- **Offline-first.** Without Ollama the RAG report falls back to a deterministic template (figures/citations stay exact).

## End-to-end flow

```
TK entry (registry) → hybrid search over patents (RRF: semantic 0.7 + BM25 0.3)
→ 5-factor risk score → prior-art enrichment (PubMed/Wikidata/GBIF)
→ RAG report via Ollama (citation-backed assessment + opposition draft)
→ FastAPI endpoints → static web dashboard
   (+ optional live PatentsView monitoring of newly-filed patents)
```

## Three personas (one platform, no auth/workflow layer)

- **Defender** (communities/NGOs): register TK → analyze/report/monitor → opposition draft. `api/routes/{tk,analyze,report,monitor}`.
- **Examiner** (IP offices): paste a patent → reverse lookup over the `tk_entries` collection → novelty verdict + matching prior art. `src/rag/novelty.py`, `api/routes/novelty.py`.
- **Researcher**: aggregate analytics over registry + patent corpus (domains, geography, assignees). `api/routes/stats.py`.

The frontend (`frontend/`) is a **Vite + React + TypeScript** SPA with a role switcher for the three personas (see "Frontend" below). The previous single-file UI is archived at `frontend/legacy/index.html` as a porting reference.

---

## SETUP FROM SCRATCH (every step)

Target: macOS/Linux, **Python 3.11** (repo built/verified on 3.11.9). Run everything from the repo root via the project `venv` so the pinned deps are used.

### 1. Python environment

```bash
cd tk-shield
python3.11 -m venv venv            # create the venv (the project standard)
venv/bin/pip install --upgrade pip
venv/bin/pip install -r requirements.txt
```

`requirements.txt` is fully pinned (chromadb, sentence-transformers, rank-bm25, scikit-learn, numpy, torch, transformers, huggingface-hub, datasets, spacy, nltk, pandas, tqdm, fastapi, uvicorn, httpx, pydantic, reportlab, python-dotenv, loguru, pytest).

### 2. One-time model/data assets

```bash
venv/bin/python -m spacy download en_core_web_sm        # spaCy NER model (used by ner_extractor)
venv/bin/python -m nltk.downloader stopwords            # NLTK stopwords (preprocessor loads these at import)
```

### 3. Local LLM (optional but recommended)

The RAG report + examiner note use a local Ollama model. Without it they fall back to a deterministic template, so this is optional.

```bash
# install Ollama from https://ollama.com, then:
ollama pull llama3.2        # ~2GB; default model (config.OLLAMA_MODEL)
ollama list                 # confirm it shows up
```
Note: pull the model in your own terminal — model pulls do not complete inside the Claude Code Bash sandbox (see `~/.claude` memory). The local Ollama server (`localhost:11434`) is reachable from the sandbox once a model exists.

### 4. Configuration

All settings come from `.env` (copy from `.env.example`); **every value is optional** — sensible defaults mean the app runs with no `.env` at all. Nothing is hardcoded; `src/utils/config.py` is the single `config` singleton. Add new tunables there.

```bash
cp .env.example .env        # optional; edit only if you want non-defaults
```

### 5. Build the data (run in order)

The canonical data model: a **CSV** (`data/raw/patents_medicinal.csv`) is the source of truth for patents; `ingest_to_chromadb` (re)builds the ChromaDB `patents` collection from it; the API's in-memory BM25 is also built from that CSV at startup. **Keep them consistent** — re-run `ingest_to_chromadb` after changing the corpus.

**(a) Patent corpus — choose ONE source via `PATENT_SOURCE`:**

```bash
# RECOMMENDED — keyless, REAL metadata (PatentsView bulk TSV; ~219MB g_patent
# + ~342MB assignee, one-time download, cached under data/raw/bulk/).
# Verified: keeps ~16.3k TK-relevant real US patents with real titles/assignees/dates.
PATENT_SOURCE=patentsview_bulk MAX_PATENTS=20000 venv/bin/python -m src.ingestion.build_corpus

# OR — zero-download keyless fallback (HuggingFace ccdv corpus; low-fidelity
# synthetic metadata, ~1.6k rows → ~82 after the strict filter). No real dates/assignees.
PATENT_SOURCE=ccdv MAX_PATENTS=5000 venv/bin/python -m src.ingestion.build_corpus
```

**(b) Index + seed:**

```bash
venv/bin/python -m src.ingestion.ingest_to_chromadb     # embed + index the CSV into ChromaDB (batched; supports resume)
venv/bin/python -m src.ingestion.seed_landmark_cases    # add the 3 real bio-piracy patents (turmeric/neem/basmati)
```

**(c) TK registry — build at scale from open sources (`TK_SOURCE`):**

```bash
TK_SOURCE=duke     TK_IMPORT_LIMIT=2000 venv/bin/python -m src.ingestion.build_registry  # Dr. Duke CC0 ethnobotany (~2k entries)
TK_SOURCE=wikidata TK_IMPORT_LIMIT=40   venv/bin/python -m src.ingestion.build_registry  # curated cross-region multilingual seed (~30)
```

Verified full-scale result: **~16.4k patents** in the `patents` collection + **~2k TK entries** in the registry/`tk_entries` collection.

### 6. Run the app

```bash
# Dev (HMR): two processes — Vite on :5173 proxies /api → the backend on :8000.
venv/bin/uvicorn api.main:app --reload      # backend + /api at http://localhost:8000
npm --prefix frontend install               # one-time
npm --prefix frontend run dev               # SPA with hot-reload at http://localhost:5173

# Production-style (single origin): build the SPA, then uvicorn serves it.
npm --prefix frontend run build             # → frontend/dist (gitignored)
venv/bin/uvicorn api.main:app               # serves SPA + /api at http://localhost:8000
```
`api/main.py` serves `frontend/dist` when built (with a catch-all so client routes like `/defender/TK-123` survive a refresh); otherwise it falls back to `frontend/legacy/index.html`. First `analyze`/`report` call is slow: the hybrid engine is lazy (`@lru_cache`) and builds BM25 over the whole corpus on first use. Subsequent calls are fast.

**Frontend** (`frontend/`) — Vite + React 18 + TypeScript, React Router (per-persona routes incl. deep-linked `/defender/:tkId`), TanStack Query (server state + `/api/health` polling). Styling is the **"Duna Light"** design system (`Frontend_Insp/duna.com-design.md`): a light, editorial enterprise look on Tailwind v4 tokens (`src/styles/globals.css` `@theme`) + Radix primitives (accessible Tabs/Tooltip) + Lucide line icons + self-hosted **Inter** (`@fontsource-variable/inter`, GT America substitute — no CDN). The derived CRITICAL→MINIMAL risk scale lives in `src/lib/risk.ts`. Layout: `src/api` (typed client + hooks mirroring the API contract), `src/lib` (format/risk/url/safe-markdown), `src/components` (design-system primitives), `src/app` (shell + routes), `src/features/{onboarding,defender,examiner,researcher}`. **All three personas are built and wired live:** Defender (register w/ NER reveal → analyze/report/monitor/export), Examiner (paste patent → novelty verdict + matches), Researcher (corpus/registry analytics). **Invariant:** never `dangerouslySetInnerHTML` server/LLM/user text — markdown goes through `react-markdown` (no raw HTML) and citation hrefs are http(s)-validated (`src/lib/url.ts`). Build is pinned via `package-lock.json`; no runtime CDN.

### 7. Tests

```bash
venv/bin/pytest tests/ -q                       # 48 tests, network-free (fixtures/mocks)
venv/bin/pytest tests/test_registry.py -q       # a single file
venv/bin/pytest tests/test_novelty.py::test_uses_llm_when_available -q   # a single test
npm --prefix frontend run test                  # 21 frontend tests (Vitest; incl. XSS-safety)
```

`tests/test_landmark_eval.py` needs the built corpus and is auto-skipped if absent.

> **Module imports, not file paths.** Everything uses absolute `src.*` / `api.*` imports rooted at the repo root — run modules with `python -m src.x.y`, never as file paths. Each `src/` module keeps a `__main__` smoke block.

### 7a. Evaluation & project docs

```bash
PYTHONPATH=. venv/bin/python -m src.evaluation.landmark_eval   # → docs/evaluation_report.{md,json}
PYTHONPATH=. venv/bin/python docs/build_whitepaper.py          # → docs/TK-Shield-Whitepaper.pdf
```

- **`src/evaluation/landmark_eval.py`** — quantitative eval: submits independently-worded TK descriptions for the 3 landmark cases through the full pipeline and reports Precision@1/@5, MRR, and HIGH/CRITICAL rate. The headline credibility result (P@5 100%, all CRITICAL).
- **`docs/build_whitepaper.py`** — renders the project brief PDF from the eval JSON (reportlab), so the brief never drifts from measured numbers.
- **`src/ingestion/migrate_community_attribution.py`** — idempotent migration that splits Duke's `COUNTRY(PEOPLE)` labels into a clean country + a `community` field (Nagoya/WIPO-IGC attribution); surfaced in `/api/stats` `top_communities` and the Researcher view.

---

## Architecture

**Config** — `src/utils/config.py`: the single `config` singleton; all model names, weights, paths, API bases, toggles, and scale knobs come from env with defaults. See `.env.example` for the full annotated list.

**Search** (`src/search/`)
- `vector_store.py` — ChromaDB persistent client (cosine). Functions take `collection_name`, so `patents` and `tk_entries` coexist. `search()` returns `{document, metadata, similarity_score}` (`similarity = 1 - distance`).
- `keyword_search.py` — in-memory BM25 (`KeywordSearchEngine`).
- `hybrid_ranker.py` — **main search.** `HybridSearchEngine` fuses semantic + BM25 via Reciprocal Rank Fusion (weights/k from config). Rescues folk/Hindi/scientific synonyms BM25 misses but semantics recover.

**Risk** (`src/classifier/ip_risk_scorer.py`) — `score_risk(tk_entry, search_results)` → 0–100 from 5 weighted factors (similarity 40, temporal 20, geographic 15, assignee 15, IPC 10) → MINIMAL/LOW/MEDIUM/HIGH/CRITICAL + fixed recommendation lists. Real patent dates/assignees (from the bulk source) make the temporal/assignee factors actually fire.

**Domain classifier** (`src/classifier/domain.py`) — `infer_domain(text, ipc)` tags medicinal/agricultural/food/cosmetic (CPC prefix via `config.DOMAIN_IPC_GROUPS`, else keywords). Stored on TK entries and used in researcher stats.

**NLP** (`src/nlp/`) — `preprocessor.py` (clean→tokenize→stopwords→lemmatize; loads NLTK stopwords at import) and `ner_extractor.py` (multi-domain dictionary NER for plants/uses/practices + transliterations, plus spaCy for locations). The registry uses `extract_all` to auto-tag entries.

**Clients** (`src/clients/`) — resilient `httpx` wrappers over free APIs. `_http.py` retries, times out, sends a descriptive `User-Agent` (Wikidata 403s without one), and **returns None on any failure — never raises**. `pubmed_client`, `wikidata_client`, `gbif_client` are keyless; `patentsview_client` is the live API (needs a free key, `is_available()` → False without one) and also exposes `search_by_cpc` used by the API harvester.

**Enrichment** (`src/enrichment/prior_art.py`) — fans out to the keyless clients, returns one deduped, **citation-tagged** evidence bundle (each item carries `source` + stable ID: PMID / QID / GBIF key) plus `sources_used`/`sources_skipped` for transparent reports.

**RAG** (`src/rag/`)
- `llm_client.py` — pluggable LLM interface; `OllamaClient` is default (`get_llm()` factory). `is_available()` checks the server + that the model is pulled. JSON-mode output is coerced to strings (models sometimes return lists/dicts).
- `retriever.py` — `build_context()` assembles patents (hybrid) + risk + evidence; `build_query()` folds TK aliases (folk/multilingual names) into the search. Reused by `analyze`.
- `report_generator.py` — `generate_report()` prompts the LLM for `{assessment, opposition_draft}`; **falls back to a deterministic template if the LLM is unavailable**.
- `novelty.py` — examiner reverse lookup: searches the `tk_entries` collection for a pasted patent → verdict (LIKELY NOT NOVEL / POSSIBLE PRIOR ART / LIKELY NOVEL by similarity threshold) + LLM/template note.

**Reporting** (`src/report/renderer.py`) — `to_markdown()` (always) and `to_pdf()` (best-effort reportlab).

**Registry** (`src/registry/tk_store.py`) — CRUD for TK entries; SQLite (source of truth, `config.TK_DB_PATH`) + `tk_entries` ChromaDB collection. Auto-NER + domain inference on create. `add_entry` (single), `register_bulk` (batched importers), `list_entries(limit, offset, query)` + `count_entries(query)` for pagination/search. `init_db` auto-migrates older DBs (`ALTER TABLE` for `domain`/`aliases`).

**Corpus scale-up** (`src/ingestion/`)
- `sources/` — pluggable patent sources exposing `iter_patents(limit)`, selected by `config.PATENT_SOURCE`:
  - **`patentsview_bulk`** (recommended) — keyless PatentsView bulk TSV S3 files; real metadata; streams + chunk-reads, regex-filters to TK relevance, optional assignee join, caches under `config.PATENTSVIEW_BULK_DIR`. Frame-level logic (`patents_from_frame`, `assignee_map_from_frame`) is unit-tested.
  - `ccdv_source` — keyless HF corpus, zero-download, low-fidelity.
  - `patentsview_harvest` — PatentsView **live API** paged by CPC; needs a free key; optional, not required now that bulk is keyless.
  - `build_corpus.py` drives the chosen source → appends to the canonical CSV (dedup by id); `ingest_to_chromadb` rebuilds the index (batched + `rebuild=False` resume for large runs).
- `tk_sources/` — pluggable TK sources exposing `iter_tk_entries(limit)`: `duke_importer` (Dr. Duke CC0 ethnobotany; fuzzy column detection; cleans NaN cells) and `wikidata_harvester` (curated cross-region seed enriched with real Wikidata multilingual aliases). `build_registry.py` drives the chosen source → `tk_store.register_bulk`. `config.TK_SOURCE`, `TK_IMPORT_LIMIT`.

**API** (`api/`) — `main.py` (app, CORS, serves `frontend/` at `/`, lifespan inits the DB), `deps.py` (`@lru_cache` singletons: hybrid engine from the CSV, LLM; `resolve_entry` loads by `tk_id` or builds ad-hoc), `schemas.py`, and `routes/`:
- `tk` (CRUD; `GET /api/tk?q=&limit=&offset=` → paginated/searchable `{items,total,limit,offset,q}`)
- `analyze` (fast hybrid search + risk score; no LLM/network)
- `report` (full RAG; `?format=json|markdown|pdf`)
- `monitor` (live PatentsView; degrades gracefully with no key)
- `novelty` (examiner reverse lookup)
- `stats` (researcher analytics; samples patent metadata)
- `/api/health` reports LLM + live-patent availability.

---

## Key conventions & gotchas

- **Patent record shape** is consistent everywhere: top-level `id`/`text` + a `metadata` dict (`patent_id`, `title`, `abstract`, `assignee`, `filing_date`, `country`, `ipc_code`, `status`, `source`). Preserve it when adding sources.
- **TK entry shape**: `tk_id, practice_name, description, community, country, documentation_date, category, domain, plants[], uses[], locations[], aliases[]`. Bulk imports use `register_bulk`; single creates use `add_entry`.
- **NaN hygiene.** pandas reads empty CSV/TSV cells as NaN → `str(NaN)=="nan"`. Importers and `load_patents_from_csv` clean these to `""` (never store/display the literal "nan"); the frontend also shows `—` for empty/nan. Apply the same cleaning in any new ingest/parse code.
- **CSV ↔ ChromaDB ↔ BM25 consistency.** `ingest_to_chromadb` applies a strict TK filter (`STRICT_TK_KEYWORDS`) when (re)building from the CSV; the bulk source already filters by the same strict keywords, so its rows survive 1:1. Always re-run `ingest_to_chromadb` after changing the corpus.
- **Rejected data sources (don't retry):** HUPD HF dataset is dead (`datasets`≥4 removed loading-script support, `trust_remote_code` gone); the PatentsView bulk *landing page* 301-redirects into the USPTO ODP sign-in migration — but the underlying bulk **S3 files** remain public + keyless, which `patentsview_bulk` uses. Dr. Duke's old `data.nal.usda.gov` path 301s away; the working CC0 download is the figshare URL in `config.DUKE_DATA_URL`.
- `data/`, `chroma_db/`, the SQLite registry, `venv/`, `.env`, and `.claude/` are gitignored and built/local-only.

## Verification (end-to-end)

1. `venv/bin/pytest tests/ -q` → 48 green (no network); `npm --prefix frontend run test` → 21 green.
2. `curl -s localhost:8000/api/health` → `{"status":"ok","llm_available":...,"live_patents_available":false}`.
3. Defender: register/select **turmeric** → quick risk check → **HIGH**; with the bulk corpus the closest patents are real US turmeric patents (US5401504, Univ. of Mississippi, real dates).
4. Examiner: paste a neem-oil patent abstract → **LIKELY NOT NOVEL** with matching TK prior art.
5. Researcher: stats show domain/source/assignee distributions over the corpus.
6. No-key / source-down paths degrade gracefully (report notes skipped sources; monitor returns `available:false`).

## Explicitly out of scope (deferred)

Continuous monitoring + alerting; multi-user auth; case management / audit trail; non-US patent full-text; Postgres/pgvector migration. Store access is isolated behind `vector_store` / `tk_store` so a future DB swap stays localized.
