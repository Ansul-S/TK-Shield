# TK-Shield — Final Code Review & Production-Readiness Handoff

> **For the next session.** Your mission: act as Principal Engineer / Architect / Security & Performance Reviewer / Production-Readiness Auditor. **Do not add features** unless required to fix a critical issue. Find what can break, fail, be exploited, lose data, cause downtime, or block scaling. For each issue: root cause → impact → severity → recommended fix → implement when appropriate. **Challenge assumptions; verify everything — don't assume code is correct because it works.** Read `CLAUDE.md` for full architecture before starting.
>
> This document is an honest self-audit by the engineer who built it: a map of where to look. It is a starting point, **not** an exhaustive list — treat it as leads to verify and expand, and hunt for what's not here.

---

## 0. System snapshot

- Python 3.11, FastAPI (sync route handlers → run in Starlette's threadpool), ChromaDB (local persistent), SQLite (TK registry), in-memory BM25, Ollama (local LLM, optional), resilient httpx clients over keyless free APIs.
- Data loaded: ~16.4k real patents (`patents` collection + CSV), ~2k TK entries (SQLite + `tk_entries` collection).
- **No authentication, no authorization, no rate limiting** anywhere. CORS = `*`. Single-process dev server (`uvicorn --reload`).
- 37 unit tests (network-free, fixtures/mocks). No API-integration or concurrency tests.
- Entry points: `api/main.py` (app), `api/routes/*`, `api/deps.py`. Ingestion CLIs under `src/ingestion/`.

The product **intentionally deferred** auth, multi-user, monitoring/alerts, case management, and a Postgres/pgvector migration. For a real production deployment these become gating decisions — flag them; don't silently implement auth unless the deployment target demands it and the user agrees.

---

## 1. Security

### S1 — No authentication/authorization on any endpoint — **Critical (deployment-gating)**
- **Root cause:** every route is public; there is no auth layer (no `Depends` guard, no API key check). CORS `allow_origins=["*"]` (`api/main.py`).
- **Impact:** anyone who can reach the host can read/write the registry (`POST/DELETE /api/tk`), and trigger expensive LLM/network calls. For an internet-exposed deploy this is unacceptable; for a single-user localhost tool it's acceptable.
- **Recommendation:** decide the deployment model. If exposed: add at least an API key / reverse-proxy auth, scope write/expensive endpoints, and tighten CORS to known origins. Confirm scope with the user before building an auth system (it was deferred).

### S2 — Stored/DOM XSS via unescaped LLM-derived output in the frontend — **High**
- **Root cause:** `frontend/index.html` injects several server values into `innerHTML` **without escaping**: the report **citations** (`${c.url}`, `${c.title}`, `${c.source}` — ~line 291), the **opposition draft** (`${j.opposition_draft}` — ~line 299), and monitor/other fields in places. `md()` escapes the assessment, but these sinks bypass it. The content originates from the **LLM** and from **user-pasted patent text** / external APIs — i.e. attacker-influencable.
- **Impact:** a crafted patent text (examiner) or a manipulated LLM response could inject `<script>`/`<img onerror>` executing in the dashboard.
- **Recommendation:** route every dynamic value through the existing `esc()` helper (or set via `textContent`); for the citation `href`, validate the URL scheme (http/https only). Add a test. (If the frontend is being rebuilt in the other session, coordinate — but the contract is "never inject unescaped server/LLM/user text".)

### S3 — Unbounded, unauthenticated expensive endpoints (DoS / resource exhaustion) — **High**
- **Root cause:** `/api/report` and `/api/novelty` run live network enrichment **and** local LLM generation synchronously, with **no rate limiting** and **no auth**. `n_results` on `analyze`/`report` is **not clamped** (`api/schemas.py`: `n_results: int = 5` with no bound), unlike `tk` which clamps to 1–200.
- **Impact:** a handful of concurrent `/report` calls (or a single `n_results=100000`) can saturate the threadpool, pin CPU on the LLM, and make the app unresponsive — trivially, without credentials.
- **Recommendation:** clamp `n_results` (e.g. 1–50); add rate limiting (per-IP/token); cap concurrency for LLM/report work; consider moving heavy work off the request path (deferred job queue) or at least an overall deadline.

### S4 — Unbounded input sizes — **Medium**
- **Root cause:** Pydantic models validate types but not lengths. `patent_text` (novelty), `description`, `practice_name` are unbounded. Novelty truncates `patent_text[:1500]` before the LLM, but the raw value is still stored/searched; `report` prompt embeds entry/context without a hard cap.
- **Impact:** memory pressure, oversized prompts/cost, slow embeddings.
- **Recommendation:** add `max_length` constraints on user-supplied fields; truncate consistently before storage and prompting.

### S5 — CORS wildcard in a deployable app — **Medium (context-dependent)**
- `allow_origins=["*"]` is fine for localhost but should be restricted to known origins if deployed. No credentials are used, which limits impact.

### S6 — Secrets handling — **OK (verify)**
- API keys come from env (`PATENTSVIEW_API_KEY`, NCBI); `.env` and `.claude/` are gitignored. Verify no secret is ever logged (clients log URLs incl. query params — check PubMed/Wikidata logs don't leak the optional `api_key`).

---

## 2. Concurrency & reliability

### C1 — SQLite without WAL/busy_timeout under threaded access — **High**
- **Root cause:** `tk_store._connect()` opens a bare `sqlite3.connect(path)` per call — no `WAL` journal, no `busy_timeout`, no connection reuse. Sync FastAPI handlers run concurrently in the threadpool, and `register_bulk` writes thousands of rows.
- **Impact:** concurrent write (e.g. an ingest/import) during reads → `sqlite3.OperationalError: database is locked`, failed requests, partial writes.
- **Recommendation:** enable `PRAGMA journal_mode=WAL` and `PRAGMA busy_timeout=5000` on connect; consider a single shared connection guarded by a lock, or serialize writes. Add a concurrency test.

### C2 — `@lru_cache` engine/LLM singletons are not first-call thread-safe — **Medium**
- **Root cause:** `api/deps.py` `get_engine()`/`get_llm_client()` use `functools.lru_cache`. On the very first concurrent requests, multiple threads can enter the builder before the cache populates → the ~16k-doc BM25 index gets built more than once (memory spike, latency), and (rarely) inconsistent state.
- **Impact:** startup-time latency/memory spikes under concurrent first hits.
- **Recommendation:** build the engine eagerly in the `lifespan` startup (also fixes C4 readiness), or guard the builder with a lock.

### C3 — ChromaDB multi-access — **Medium**
- **Root cause:** several modules instantiate `chromadb.PersistentClient(path=...)` independently (`vector_store`, `ingest_to_chromadb`, `seed_landmark_cases`, `stats`, `tk_store` via vector_store). ChromaDB local persistence is not designed for concurrent multi-process writers.
- **Impact:** running an ingest CLI while the server serves, or running multiple uvicorn workers, risks lock contention/corruption.
- **Recommendation:** document/enforce single-writer; for multi-worker or concurrent ingest, move to a client/server vector DB. Don't run ingest against a live server's DB.

### C4 — Lazy warmup defeats readiness probes — **Medium**
- **Root cause:** the hybrid engine builds on first `/analyze` (lazy), so the process accepts traffic before it's actually ready; the first user eats a multi-second build.
- **Impact:** first-request latency; a naive readiness check passes prematurely.
- **Recommendation:** warm the engine (and optionally the embedding model/LLM check) in `lifespan`; gate readiness on it.

### C5 — Long synchronous requests can exhaust the threadpool — **High (perf)**
- **Root cause:** `/report` and `/novelty` are sync handlers doing sequential network calls (PubMed esearch+esummary, Wikidata, GBIF per plant — each with up-to-3 retries + backoff) **plus** LLM generation, all inside one threadpool worker for 15–45s+. There is no overall deadline.
- **Impact:** a few slow requests block the limited threadpool → whole app stalls; worst-case enrichment retries make a single request very long.
- **Recommendation:** impose an overall time budget; parallelize independent enrichment calls; cap LLM timeout (`config.LLM_TIMEOUT` exists — verify it's enforced); long-term move heavy work to a background job. At minimum, bound concurrency.

---

## 3. Correctness & edge cases

### D1 — Unstable offset pagination ordering — **Medium**
- **Root cause:** `list_entries` orders by `created_at DESC` only. `register_bulk` sets `created_at = datetime.now(timezone.utc)` per entry in a tight loop → many near-identical timestamps. With offset pagination, equal keys make page boundaries non-deterministic.
- **Impact:** rows can repeat or be skipped between pages in the registry UI.
- **Recommendation:** add a stable tiebreaker: `ORDER BY created_at DESC, tk_id`. (Cheap, high value.)

### D2 — `LIKE` wildcards in search not escaped — **Low**
- **Root cause:** `_search_clause` parameterizes the value (safe from injection) but doesn't escape `%`/`_`; a user typing `%` matches everything.
- **Impact:** confusing search results; not a security issue.
- **Recommendation:** escape `%`/`_` with an `ESCAPE` clause, or document.

### D3 — Duplicate near-identical patents — **Low**
- Seed landmark `US5401504A` vs bulk `US5401504` appear as two rows in results. Cosmetic; consider id normalization/dedup if it matters.

### D4 — Full-table loads as registry grows — **Medium (scaling)**
- `stats` calls `tk_store.list_entries()` with no limit (loads all ~2k rows + JSON-parses each) and `collection.get(limit=5000)` for patents. Fine now; O(n) and unbounded as the registry grows. Recommend aggregate SQL (`GROUP BY domain/country`) instead of loading all rows.

### D5 — Memory footprint per process — **Medium (scaling)**
- BM25 holds ~16k patent docs in RAM; `load_patents_from_csv` reads the whole CSV; the embedding model is loaded at import (and `ingest_to_chromadb.embed_and_store` loads a **second** SentenceTransformer instance during ingest). With N uvicorn workers, multiply. Document/limit worker count or externalize search.

### D6 — Verify NaN hygiene is complete — **Low**
- NaN→"" cleaning was added to importers and `load_patents_from_csv`; verify no other ingest/serialization path can emit the literal "nan" into stored metadata or API responses.

---

## 4. Error handling & observability

### O1 — Blanket exception swallowing hides failures — **Medium**
- **Root cause:** clients (`src/clients/_http.py` and each client) catch all exceptions and return `None`/`[]` by design (resilience). `stats`, chroma delete, `llm.is_available` use broad `except Exception`.
- **Impact:** great for not crashing, but failures are near-invisible — only loguru warnings, no metrics, no alerting. A silently-degraded source looks like "no results."
- **Recommendation:** add structured logging + counters for degraded sources/skips; surface dependency health beyond the two booleans in `/api/health` (e.g., last-error timestamps). Add request IDs.

### O2 — No monitoring/metrics/log aggregation — **Medium (deployment)**
- No metrics endpoint, no structured (JSON) logs, no tracing. For production, add request/latency/error metrics and a real log format.

---

## 5. Deployment & data safety

### P1 — Dev server config — **High (deployment)**
- Running `uvicorn --reload` (dev). No production process manager, no worker/timeout config, no container. Multiple workers each rebuild BM25, load the model, and open ChromaDB → heavy + the C3 multi-writer risk. Recommend a documented production run (single worker or externalized search/DB), graceful-shutdown, request timeouts.

### P2 — No backups / local-only state — **High (data loss)**
- `chroma_db/`, the SQLite registry, and the CSV are local, gitignored, unbacked. Losing the disk loses the registry (the user-authored data). Recommend a backup/export story for the SQLite registry at minimum (it's the source of truth and the only non-reproducible data).

### P3 — Reproducibility of data — **OK**
- Patents and TK corpus are reproducible from the documented ingest commands (CLAUDE.md). The only irreplaceable data is user-registered TK entries (→ P2).

---

## 6. Data validation & sanitization

- Add `max_length`/bounds to Pydantic inputs (S4) and clamp `n_results` (S3).
- `documentation_date` is a free string (not validated as a date); temporal scoring parses defensively. Decide whether to validate format.
- SQL is parameterized (good); verify no f-string interpolation of user input reaches SQL anywhere (only `_search_clause` builds dynamic SQL — it parameterizes values; the column list is static).

---

## 7. Tests — gaps to close

- 37 unit tests pass, network-free (RRF, risk buckets, client parsing, report LLM/fallback + coercion, domain, Duke parsing incl. NaN, patent sources incl. bulk zip + assignee join, novelty thresholds, registry pagination/search). Solid unit coverage.
- **Missing:** FastAPI **route/integration tests** (TestClient) for each endpoint incl. error paths (400/404, missing tk_id); **concurrency** test (SQLite lock); **pagination-stability** test (D1); **frontend escaping** test (S2); a test asserting `n_results` clamping (S3).

---

## 8. Suggested triage order

1. **S2** (XSS escaping) and **S3** (clamp `n_results`) — small, high-value, low-risk fixes.
2. **C1** (SQLite WAL + busy_timeout) and **D1** (stable pagination order) — small fixes, real correctness/reliability wins.
3. **C2/C4** (warm engine in lifespan) — fixes thread-safety + readiness together.
4. **S1/S5, C5, P1/P2** — deployment-gating decisions; align with the user on the target environment before implementing (auth and infra were deferred).
5. **O1/O2** — observability hardening.

For each fix you implement: keep the existing **graceful-degradation** and **keyless/offline-first** guarantees intact, re-run `venv/bin/pytest tests/ -q`, and prefer adding a regression test. Verify behavior live (`uvicorn api.main:app`, `/docs`) — don't assume.
