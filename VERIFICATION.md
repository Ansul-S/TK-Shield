# TK-Shield — Verification

> Evidence for the claims made in the README and whitepaper. Every entry is a **command anyone can re-run** plus
> the **actual output observed** on this machine (macOS, Python 3.11, local Ollama `llama3.2`). Re-running these
> reproduces the results; nothing here is mocked.
>
> Last verified: 2026-06-06.

---

## 1. Automated tests

### Backend — 48 tests, network-free (fixtures/mocks)
```bash
PYTHONPATH=. venv/bin/pytest tests/ -q
```
```
................................................                         [100%]
48 passed in 36.64s
```
Covers: RRF fusion, risk buckets, client parsing, report LLM + deterministic fallback, domain inference,
Dr. Duke parsing (incl. NaN handling and the country→community split), patent sources (incl. bulk TSV +
assignee join), novelty thresholds, registry pagination/search, input-bound clamping, and the landmark
evaluation regression.

### Frontend — 21 tests (Vitest), including XSS-safety
```bash
npm --prefix frontend run test
```
```
 Test Files  6 passed (6)
      Tests  21 passed (21)
```
Covers: the markdown renderer and `safeHref()` against hostile inputs (`<script>`, `<img onerror>`,
`javascript:` URLs), `format.dash()` nan/empty handling, risk/verdict colour mapping, `Pager` math, and the
error boundary.

### Frontend — type-check and production build pass
```bash
npm --prefix frontend run typecheck && npm --prefix frontend run build
```
Build succeeds (`tsc -b` is the gate); output bundle ≈ 463 KB JS (146 KB gzip). Test files are confirmed
**not** present in the production bundle.

---

## 2. Evaluation — landmark bio-piracy cases

```bash
PYTHONPATH=. venv/bin/python -m src.evaluation.landmark_eval
# writes docs/evaluation_report.md + .json
```

| Metric | Result |
|---|---|
| Precision@5 | **100%** |
| Precision@1 | **67%** |
| Mean Reciprocal Rank | **0.833** |
| Flagged HIGH/CRITICAL | **100%** |

| TK practice (independently worded) | Patent | Rank | Sim. | Risk |
|---|---|---|---|---|
| Turmeric for wound healing | US5401504A | #1 | 0.823 | CRITICAL (85) |
| Neem as a crop antifungal | EP0436257B1 | #1 | 0.787 | CRITICAL (83) |
| Basmati aromatic rice | US5663484A | #2 | 0.606 | CRITICAL (83) |

The TK descriptions share **no wording** with the patent abstracts, so retrieval reflects genuine
semantic+lexical matching, not string overlap. Full report: [docs/evaluation_report.md](docs/evaluation_report.md).
A pytest regression (`tests/test_landmark_eval.py`) asserts these thresholds and skips cleanly if the corpus
isn't built.

---

## 3. Live API (backend running)

```bash
PYTHONPATH=. venv/bin/uvicorn api.main:app --port 8000
```

### Health — LLM detected, live-patents off (expected, keyless)
```bash
curl -s localhost:8000/api/health
```
```json
{"status":"ok","llm_available":true,"live_patents_available":false}
```

### Quick risk check — Defender path (no LLM, no network)
```bash
curl -s -X POST localhost:8000/api/analyze -H 'Content-Type: application/json' \
  -d '{"practice_name":"Turmeric for wound healing","description":"haldi paste applied to wounds in Ayurveda","country":"IN","n_results":3}'
```
```
latency: 0.113s
risk: HIGH 73
top patent: US5401504  sim 0.804
```
The closest patent is the real turmeric bio-piracy patent. **First-request latency is ~0.1s** because the
search engine is warmed at startup (no lazy cold-start).

### Stats — Researcher path (incl. community attribution)
```bash
curl -s localhost:8000/api/stats
```
```
registry total: 2030
patents total: 16371
top_communities: [['Santal', 90], ['Amerindian', 21], ['Seri', 15], ['Kwakiutl', 8]]
```

---

## 4. Data loading

| Dataset | Source | Records | License | Notes |
|---|---|---|---|---|
| Patent corpus | PatentsView bulk TSV (USPTO) | **16,371** | Public domain | Real titles, assignees, grant dates; keyless bulk download |
| Landmark cases | Seeded | 3 | — | turmeric/neem/basmati, real revoked patents |
| TK registry | Dr. Duke Phytochem & Ethnobotanical DB (USDA) | ~2,000 | CC0 | Multilingual common + scientific names |
| TK registry | Curated Wikidata | ~30 | CC0 | Cross-region multilingual seed |
| **Registry total** | | **2,030** | | |

Build commands are in the [README](README.md#quick-start). The migration
`src.ingestion.migrate_community_attribution` updated **208** entries, splitting holder communities out of the
country field (e.g. `INDIA(SANTAL)` → country `INDIA`, community `Santal`) and consolidating country counts.

**Known data limitations:** US patent *metadata* (not full claim text); English-language analysis; the
ethnobotany source skews to what has been documented in English-language databases, under-representing some
communities; risk weights are hand-set from domain reasoning, not learned from a labelled dataset.

---

## 5. Search & pagination

- **Hybrid search** — semantic (ChromaDB cosine) 0.7 + BM25 0.3, fused with Reciprocal Rank Fusion. Verified
  live above (turmeric query → correct landmark patent at rank 1, sim 0.804).
- **Search** — registry free-text search across name/description/plants/aliases/country/community;
  `LIKE` metacharacters are escaped (test: `tests/test_registry.py::test_search_escapes_like_wildcards`).
- **Pagination** — offset paging with a stable `created_at DESC, tk_id` ordering so pages never repeat/skip
  even when bulk imports share timestamps (test:
  `tests/test_registry.py::test_pagination_stable_with_equal_timestamps`).

---

## 6. Demo path (≈2 minutes, no API keys)

1. Start the app: `npm --prefix frontend run build && PYTHONPATH=. venv/bin/uvicorn api.main:app` → open
   `http://localhost:8000`.
2. **Defender** → search **turmeric** → open the entry → **Quick risk check** → **HIGH (73)**, closest patent
   `US5401504` (the real case). Optionally **Full report** for the AI-written assessment + opposition draft
   (needs Ollama; otherwise a deterministic fallback).
3. **Examiner** → paste a neem-oil antifungal abstract → **Check novelty** → **LIKELY NOT NOVEL** with matching
   TK prior art.
4. **Researcher** → registry/corpus analytics, including **Documented communities & peoples** (Santal, Seri, …).

**Graceful degradation to show:** stop Ollama → reports still generate (deterministic fallback, exact
citations); no `PATENTSVIEW_API_KEY` → the live-monitor tab shows a calm "unavailable" state, not an error.

---

## 7. Security & safety checks

- No `dangerouslySetInnerHTML` anywhere; markdown renders with no raw-HTML plugin → injected scripts are inert
  text (tests in `frontend/src/lib/markdown.test.tsx`).
- External/citation links validated to http(s) only (`frontend/src/lib/url.test.ts`).
- Request inputs bounded: text `max_length` caps and `n_results` clamped to 1–50 (`tests/test_schemas.py`).
- No hardcoded secrets, tokens, or credentials; the only optional key is read from the environment and degrades
  to "unavailable" when absent. Local data, DB, and `.env` are gitignored.

---

## Scope statement ("production-ready" — defined)

TK-Shield is **production-ready for its intended target: single-user / local deployment.** It is tested, input-
validated, XSS-hardened, and reliable under local concurrent access (SQLite WAL + busy-timeout). It is **not**
hardened for an internet-exposed multi-user deployment — that would require authentication, rate limiting, and
restricted CORS, which are intentionally deferred and documented as the gating items for any public hosting.
