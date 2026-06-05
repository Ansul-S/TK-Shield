# TK-Shield — Frontend Development Handoff

> **For the next session.** Your mission: design and build a professional, production-ready **frontend** for TK-Shield, acting as a Senior Backend/Product/Frontend engineer who understands the business logic — not a visual-only UI designer. Adapt any Figma/template/inspiration to the business requirements; do not blindly replicate. Read this top to bottom before touching anything; read `CLAUDE.md` for full system detail.

---

## 1. What TK-Shield is (purpose & business goals)

TK-Shield is a **defensive bio-piracy monitoring platform**. It protects documented **Traditional Knowledge (TK)** — traditional medicinal/agricultural practices (e.g. turmeric for wound healing, neem as antifungal) — from patents that improperly claim it. Same mission as India's TKDL and WIPO IGC.

**The user's job-to-be-done:** *"Has someone patented our traditional knowledge, and can I prove prior art to stop them?"* The product answers this by: finding patents that overlap a documented practice, scoring bio-piracy risk, gathering citable prior-art evidence (peer-reviewed papers, taxonomy, geographic origin), and generating a citation-backed assessment + a draft patent opposition.

Real, currently-loaded scale: **~16,400 real US patents** (real titles/assignees/dates) + **~2,030 TK registry entries** (Dr. Duke ethnobotany + curated Wikidata). It is fully **keyless** and runs **offline-first** (local LLM via Ollama, with a deterministic fallback).

**Design implication:** this is a serious, evidence-driven legal/research tool for communities, NGOs, patent examiners, and researchers — not a consumer app. The UX should feel **credible, transparent, and citation-forward**, not flashy. Every risk claim ties to a real reference (PMID / Wikidata QID / GBIF key / patent number) — surface those, they are the product's trust anchor.

## 2. Three personas (the core of the IA)

The app is one platform with a **role switcher** (currently three tabs). Each persona is a distinct workflow:

| Persona | Who | Job | Backend |
|---|---|---|---|
| **🛡️ Defender** | Communities / NGOs | Register their TK → check it against patents → get a risk report + draft opposition → (optionally) monitor new patents | `tk`, `analyze`, `report`, `monitor` |
| **⚖️ Examiner** | Patent offices | Paste an incoming patent → reverse-lookup against documented TK → novelty verdict + matching prior art | `novelty` |
| **📊 Researcher** | Analysts/academics | Explore the corpus + registry: domains, geography, top assignees, counts | `stats` |

The current frontend treats these as top-nav tabs. Consider whether a **landing/role-selection screen** or persistent left-rail role nav serves first-time users better — there is currently no onboarding explaining what each role is for.

## 3. Current frontend (what exists today)

- **One file:** `frontend/index.html` — a dependency-free SPA (hand-written CSS, vanilla JS, a tiny inline markdown renderer). Served as static files by FastAPI at `/`. (`frontend/components/` and `frontend/pages/` dirs exist but are **empty/unused**.)
- **Why vanilla:** chosen deliberately for zero-dependency reliability (no CDN/npm rot). It works and all flows are verified, but it is **not structured for scale** — all logic/state is global functions + module-level `let` variables in one `<script>`.
- **What works today (verified live in-browser):** role switching; Defender (entry list with **search + Prev/Next pagination**, register form with NER auto-extract, quick risk check, full RAG report with citations + opposition, live-monitor graceful message, export-markdown); Examiner (paste → verdict + matches); Researcher (stat bars + tables). Display helpers already handle `nan`→`—`, title capitalization/ellipsis, and HTML-escaping.

**You may keep vanilla and harden it, or migrate to a framework — that is an architecture decision for you to make and justify (see §6).** If you migrate, the dependency-free reliability rationale must be replaced with a real build/deploy story; don't drop it casually.

## 4. API contract (authoritative — the data the UI binds to)

Base URL: same origin (`http://localhost:8000`). All POST bodies are JSON. Errors return `{"detail": "..."}` with 400/404/422. CORS is currently `*`.

### `GET /api/health`
→ `{ "status": "ok", "llm_available": bool, "live_patents_available": bool }`
Use to drive the header status dots and to disable LLM-dependent affordances when `llm_available` is false.

### `GET /api/tk?q=&limit=25&offset=0`  (paginated + searchable)
→ `{ "items": TKEntry[], "total": int, "limit": int, "offset": int, "q": str }`
`limit` is clamped to 1–200 server-side. `q` is a free-text substring match over name/description/plants/aliases/country/community.

**`TKEntry`** = `{ tk_id, practice_name, description, community, country, documentation_date, category, domain, plants[], uses[], locations[], aliases[], created_at }`
(`country`/`documentation_date` are often `""`; `domain` ∈ medicinal|agricultural|food|cosmetic|"".)

### `POST /api/tk`  (create)
Body `{ practice_name* , description?, community?, country?, documentation_date?, category?, plants?[], uses?[] }` → the created `TKEntry` (plants/uses auto-extracted via NER if omitted; `domain` inferred). 400 if `practice_name` missing.

### `GET /api/tk/{tk_id}` → `TKEntry` (404 if missing)
### `DELETE /api/tk/{tk_id}` → `{ "deleted": tk_id }` (404 if missing)

### `POST /api/analyze`  (fast; no LLM, no network)
Body `{ tk_id? }` **or** `{ practice_name, description?, country?, documentation_date? }`, plus `n_results=5`.
→ `{ tk_entry:{tk_id,practice_name,country,documentation_date}, risk:RiskResult, patents:Patent[] }`
**`RiskResult`** = `{ total_score:int(0-100), max_possible:100, risk_level:"MINIMAL|LOW|MEDIUM|HIGH|CRITICAL", factors:{similarity_score,temporal_risk,geographic_risk,assignee_risk,ipc_risk}, recommendations:string[] }`
**`Patent`** = `{ patent_id, title, assignee, filing_date, country, similarity, rrf_score }` (empty strings possible → render `—`).

### `POST /api/report?format=json|markdown|pdf`  (SLOW: live enrichment + LLM, ~15–45s)
Same body as `analyze`.
- `json` → `{ tk_entry, risk:RiskResult, top_patents:Patent[], citations:Citation[], assessment:string(markdown), opposition_draft:string, llm_used:bool, sources_skipped:string[], markdown:string }`
- `markdown` → `text/markdown` body
- `pdf` → `application/pdf` bytes
**`Citation`** = `{ source:"pubmed|wikidata|gbif", ref_id, title, url }`.
`llm_used:false` means the deterministic fallback was used (still valid; figures/citations exact). `sources_skipped` lists enrichment sources that returned nothing this run — surface this for transparency.

### `POST /api/novelty`  (examiner; SLOW if LLM available)
Body `{ patent_text }` (or `{ patent_id }` which only resolves with a PatentsView key), `n_results=5`.
→ `{ verdict:"LIKELY NOT NOVEL|POSSIBLE PRIOR ART|LIKELY NOVEL", confidence:"high|medium|low", top_similarity:float, matches:[{tk_id,practice_name,domain,country,similarity}], assessment:string, llm_used:bool }`. 400 if no text.

### `POST /api/monitor`  (live patents; optional)
Body `{ tk_id? | query?, n_results=10 }` → `{ available:bool, query, patents:[{id,text,metadata{patent_id,title,assignee,filing_date,...}}], note:string }`.
`available:false` when no `PATENTSVIEW_API_KEY` — the UI must treat this as a normal state, not an error.

### `GET /api/stats`  (researcher)
→ `{ registry:{ total, by_domain:{}, top_countries:[[code,count]] }, patents:{ total, sampled, by_domain:{}, by_source:{}, top_assignees:[[name,count]] } }`.

> Interactive API docs are live at `/docs` (FastAPI Swagger) — use it to probe shapes.

## 5. Critical UX constraints rooted in the backend

These shape the UX more than aesthetics — design around them:

1. **`/report` and `/novelty` are slow (15–45s)** when the LLM is on: they run live PubMed/Wikidata/GBIF enrichment **plus** local LLM generation synchronously. The UI **must** show a meaningful progress/loading state (ideally staged: "searching patents → gathering prior art → drafting report"), keep the action button disabled, and never look frozen. Consider optimistic display of the fast parts (risk + patents are computable instantly via `/analyze`) before the slow narrative arrives.
2. **First `/analyze` after server start is slow** (one-time): the hybrid search engine lazily builds an in-memory BM25 index over ~16k patents on first use. Subsequent calls are fast. A first-load spinner that doesn't alarm the user matters.
3. **LLM may be unavailable** (`health.llm_available=false`): reports still work (deterministic fallback) but read differently. Show an honest, non-error banner ("AI narrative offline — figures and citations are exact").
4. **Live monitoring is usually off** (`available:false`): this is the default keyless state. Present it as an optional/disabled feature with a one-line explanation, not a failure.
5. **Data realism:** patent titles can be long; assignee can be "Unknown"; dates/countries can be empty. Empty/`nan` must render as `—` (helpers already exist). Plan table truncation/tooltips for long titles.
6. **Registry is large (~2k, growing):** lists must paginate/search (already wired). Examiner power scales with registry size — make the registry feel substantial.
7. **No auth today.** There is no login/user concept (deferred). Don't build auth UI unless asked; but design the IA so a future auth/account layer can slot in (e.g., where a "my community / my watchlist" concept would live).

## 6. Architecture recommendations to evaluate (your call, justify it)

You are expected to **recommend** the frontend architecture, component structure, folder organization, and state patterns. Decisions to make and document:

- **Framework vs vanilla.** Options: (a) harden the current vanilla SPA into modular ES modules (keeps zero-build reliability); (b) migrate to **Vite + React/TypeScript** (better for the component/state scale this product is heading toward, real loading/error/empty-state ergonomics, testability). If you migrate, keep it served by FastAPI as static build output (or document a separate deploy) and preserve the "no fragile CDN at runtime" spirit via a pinned build.
- **State management.** Server state dominates (entries, reports, stats) → recommend a data-fetching/caching layer (e.g. TanStack Query if React) over hand-rolled fetches; local UI state stays minimal. Define how role, selected entry, search/pagination, and in-flight long requests are modeled.
- **Component structure.** Persona views (Defender/Examiner/Researcher) as route-level features; shared primitives (RiskBadge, FactorTable, PatentTable, CitationList, OppositionDraft, LoadingStages, EmptyState, ErrorState, Pager, SearchBox). Risk level → consistent color scale (CRITICAL→MINIMAL).
- **Folder organization.** Feature-first (e.g. `src/features/{defender,examiner,researcher}`, `src/components`, `src/api` for the typed client, `src/lib`). Generate a typed API client from the contracts in §4 (or OpenAPI at `/openapi.json`).
- **Routing/deep-linking.** Today everything is one URL. Consider routes per persona + per selected entry/report so states are shareable/bookmarkable.

## 7. Gaps / missing states to design (non-exhaustive — find more)

- **Onboarding / role explanation** for first-time users (what each persona does).
- **Loading states**: staged progress for report/novelty; skeleton for lists/stats; first-call warmup.
- **Empty states**: empty registry, no search matches, no patents found, no citations, no prior-art match (examiner "likely novel").
- **Error states**: API down, 4xx/5xx, validation errors on the register form (inline), network timeout on the long calls.
- **Edge cases**: very long titles/assignees; entries with no country/date/plants; report when `llm_used:false`; monitor when key absent; pasted patent text that's too short for novelty (400).
- **Register form UX**: show the auto-extracted plants/uses/domain after creation (so the NER is visible and trustworthy); validation; success feedback.
- **Report consumption**: the report is the product's deliverable — make the assessment + citations + opposition draft genuinely usable (copy buttons, export to PDF/markdown already exist server-side, print styles, citation links open in new tab).
- **Accessibility**: the current entry "cards" are clickable `<div>`s (not buttons) — fix for keyboard/screen-reader; ensure color-contrast on the risk palette; labels on inputs.
- **Researcher**: current bars are basic — consider clearer charts, but keep it lightweight.

## 8. What NOT to break

- The **API contracts in §4** are stable and tested — bind to them as-is; coordinate any backend change with the review session.
- **Graceful-degradation behaviors** (LLM off, no key, source skipped) are features — preserve them in the UX.
- **Keyless/offline-first** posture — don't introduce runtime dependencies on third-party hosted services for the app to function.

## 9. How to run while developing

```bash
venv/bin/uvicorn api.main:app --reload     # backend + current static frontend at http://localhost:8000
# /docs for live API exploration; /openapi.json for the schema
```
Data is already loaded (~16k patents, ~2k TK entries). If starting cold, follow the "SETUP FROM SCRATCH" section in `CLAUDE.md`.
