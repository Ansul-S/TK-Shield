# TK-Shield — Full Project Report

**Defensive bio-piracy monitoring & novelty assessment for Traditional Knowledge**

Author: Ansul Suryawanshi · Status: Working, verified end-to-end · Licence: MIT

> A companion to the concise [project brief PDF](TK-Shield-Whitepaper.pdf). This
> report tells the complete story: what TK-Shield is, why it matters, how it is
> built, the decisions behind it, how it was evaluated and hardened, and where it
> can go next. It is written to be read by both policy reviewers (WIPO IGC, IP
> offices) and technical reviewers (engineers, interviewers).

---

## Executive summary

**Traditional Knowledge (TK)** — documented practices such as *turmeric for wound
healing* or *neem as a crop antifungal* — is routinely misappropriated by patents
that claim it as novel. Correcting such a patent after grant is slow and expensive,
and the communities who hold the knowledge rarely have the tooling to act.

**TK-Shield** is a defensive platform that answers one question for those
communities, the NGOs that support them, and the patent offices that examine
applications:

> **"Has someone patented our traditional knowledge — and can we prove prior art to stop them?"**

Given a documented practice, TK-Shield finds the patents that may claim it, scores
bio-piracy risk on an interpretable 0–100 scale, gathers citable prior-art
evidence from free public databases, and uses a local language model to draft a
citation-backed assessment plus a patent-opposition document. An examiner-facing
mode runs the inverse: paste a patent and get a **claim-by-claim** novelty verdict
against documented TK.

It runs **keyless and offline-first** — the entire pipeline works with zero API
keys, on public-domain data and a local model, so it can run on a community
laptop with no recurring cost or vendor lock-in.

**Headline facts**

| | |
|---|---|
| Patent corpus | **16,292** real US patents (PatentsView bulk — real titles, assignees, dates) |
| TK registry | **2,030** documented practices (Dr. Duke CC0 + curated multilingual Wikidata) |
| Landmark evaluation | **Precision@1 = 100%**, **Precision@5 = 100%**, **MRR = 1.000**, **0%** control false positives |
| Tests | **121** backend (network-free) + **22** frontend, green in CI |
| Cost to run | **Zero** — no API keys, no paid services, local LLM optional |

---

## Table of contents

1. The problem — bio-piracy and traditional knowledge
2. Policy context — alignment with WIPO's mandate
3. What TK-Shield does — three personas, one platform
4. System architecture
5. How it works — the technical core
6. Key design decisions and trade-offs
7. Data sources and corpus integrity
8. Evaluation and results
9. Security and hardening
10. Quality engineering
11. Technology stack
12. Limitations
13. Roadmap
14. How it was built — engineering process
15. Author and attribution
- Appendix A — repository map
- Appendix B — API reference
- Appendix C — reproduce everything

---

## 1. The problem — bio-piracy and traditional knowledge

**Bio-piracy** is the appropriation of traditional or indigenous knowledge of
nature — typically medicinal or agricultural uses of plants — by an entity that
patents it without recognition, consent, or benefit-sharing. The knowledge is
often centuries old and orally transmitted, so it rarely appears in the patent
literature an examiner searches. The result is a patent granted over something
that was never novel, but whose prior art is invisible to the system.

The field is defined by three landmark disputes, each eventually overturned using
documented prior art — and each seeded into TK-Shield so the tool always
demonstrates them:

| Case | Patent | Claimant | Outcome |
|---|---|---|---|
| **Turmeric** for wound healing | US5401504A | University of Mississippi Medical Center | Revoked by the USPTO in 1997 on documented Indian prior art |
| **Neem** as a crop antifungal | EP0436257B1 | W.R. Grace & Co. / USDA | Revoked by the EPO in 2000/2005 on documented Indian prior art |
| **Basmati** aromatic rice | US5663484A | RiceTec Inc. | Most claims withdrawn/struck at the USPTO in 2001–2002 |

These cases took years and significant legal resource to reverse. The premise of
TK-Shield is that **the prior art existed and was findable** — the gap was tooling
that could connect a documented practice to the patents claiming it and assemble
the evidence quickly. India's **Traditional Knowledge Digital Library (TKDL)**
proved the defensive-documentation model works at the state level; TK-Shield
mirrors that purpose using open data and open models so it is reproducible by
anyone.

---

## 2. Policy context — alignment with WIPO's mandate

TK-Shield operationalizes the **defensive protection** of traditional knowledge
that international IP policy is converging on:

- **WIPO IGC** — the Intergovernmental Committee on Intellectual Property and
  Genetic Resources, Traditional Knowledge and Folklore. Its core agenda is
  preventing the *erroneous granting* of patents over TK. TK-Shield's examiner
  mode is a direct instrument of that goal.
- **WIPO Treaty on IP, Genetic Resources and Associated Traditional Knowledge
  (2024)** — introduces a *disclosure-of-origin* requirement for patents based on
  genetic resources and associated TK. TK-Shield supports compliance: it links a
  practice to the patents claiming it and assembles the origin evidence.
- **Nagoya Protocol / Convention on Biological Diversity** — access and
  benefit-sharing depends on knowing *which community* holds a practice.
  TK-Shield surfaces documented **communities and peoples** (e.g. Santal, Seri,
  Kwakiutl) as a first-class attribution dimension, not an afterthought.
- **TKDL** — the proven national model TK-Shield generalizes with open data.

The design rule that ties this together: **every risk claim ties to a stable,
verifiable reference** — a PubMed PMID, a Wikidata QID, a GBIF key, or a patent
number. The output is evidence, not assertion.

---

## 3. What TK-Shield does — three personas, one platform

TK-Shield serves three real audiences through one platform (no auth/workflow
layer — a deliberate scope choice for a demonstration tool):

### Defender (communities / NGOs)
Register a documented practice → run a fast risk check → generate a full
RAG report (assessment + opposition draft) → monitor newly-filed patents → export.
The risk recommendations point to *real channels*: WIPO PATENTSCOPE, the TKDL, and
the WIPO IGC.

### Examiner (patent offices)
Paste a patent's text and get a novelty verdict — **LIKELY NOT NOVEL /
POSSIBLE PRIOR ART / LIKELY NOVEL** — against the documented TK registry, with the
matching prior art. When claims are present, TK-Shield assesses novelty **claim by
claim**: it splits the patent into its individual independent/dependent claims and
verdicts each against documented TK, the way an examiner checks anticipation. The
verdict is computed from cosine similarity, **not** the LLM, so it is immune to
prompt injection in the pasted text.

### Researcher
Aggregate analytics across the registry and the corpus: distribution by domain,
geography, documented **communities and peoples**, and top assignees.

The end-to-end flow:

```
TK entry (registry) → hybrid search over patents (RRF: semantic 0.7 + BM25 0.3)
→ 5-factor risk score → prior-art enrichment (PubMed / Wikidata / GBIF)
→ RAG report via local LLM (assessment + opposition draft)
→ FastAPI endpoints → React dashboard
   (+ optional live PatentsView monitoring of newly-filed patents)
```

---

## 4. System architecture

TK-Shield is a Python backend (FastAPI) over two vector collections and a SQLite
registry, with a React single-page frontend served from the same origin.

```
                        ┌─────────────────────────────────────────┐
   React SPA  ──/api──▶ │  FastAPI  (analyze · report · novelty ·  │
  (Vite + TS)           │           monitor · tk · stats · health) │
                        └───────────────┬─────────────────────────┘
                                        │
        ┌───────────────────────────────┼───────────────────────────────┐
        ▼                                ▼                               ▼
  Hybrid search                    Risk + RAG                     Enrichment
  ┌────────────┐    ┌──────────────────────────────┐    ┌────────────────────┐
  │ ChromaDB   │    │ 5-factor risk score          │    │ PubMed (PMID)      │
  │ (semantic) │    │ retriever → context          │    │ Wikidata (QID)     │
  │ BM25       │    │ report_generator (Ollama LLM │    │ GBIF (taxon key)   │
  │ (keyword)  │    │   + deterministic fallback)  │    │ resilient httpx    │
  └────────────┘    │ novelty (claim-level)        │    └────────────────────┘
        ▲           └──────────────────────────────┘
  ┌────────────┐
  │ SQLite     │  TK registry (source of truth) + tk_entries vector collection
  └────────────┘
```

**Module layout** (absolute `src.*` / `api.*` imports, run as `python -m ...`):

- `src/search/` — `vector_store` (ChromaDB), `keyword_search` (BM25),
  `hybrid_ranker` (RRF fusion + kind-code dedup). The main search path.
- `src/classifier/` — `ip_risk_scorer` (5-factor model), `domain` (medicinal /
  agricultural / food / cosmetic tagging).
- `src/nlp/` — `preprocessor` (clean/tokenize/lemmatize), `ner_extractor`
  (dictionary NER for plants/uses/practices + transliterations, spaCy for places).
- `src/clients/` — resilient keyless API wrappers (PubMed, Wikidata, GBIF,
  PatentsView). Shared `_http` retries, times out, and **returns None on failure —
  never raises**.
- `src/enrichment/prior_art` — concurrent fan-out to the clients → one deduped,
  citation-tagged evidence bundle with `sources_used` / `sources_skipped`.
- `src/rag/` — `retriever` (assembles context), `report_generator`
  (assessment + opposition; LLM with deterministic fallback), `novelty`
  (examiner reverse lookup, claim-level), `claim_parser`, `llm_client` (Ollama).
- `src/registry/tk_store` — CRUD over SQLite + the `tk_entries` vector collection.
- `src/ingestion/` — pluggable patent sources and TK sources, corpus/registry
  builders, ChromaDB indexer, landmark seeder, demo seeder.
- `api/` — app, cached singletons (`deps`), request schemas, and routers.

A core convention keeps the data layer consistent: a **CSV is the source of truth**
for patents; the ChromaDB `patents` collection and the in-memory BM25 index are
both built from that same CSV via one loader, so the three stay **1:1** (verified
16,292 each). Storage access is isolated behind `vector_store` / `tk_store` so a
future database swap stays localized.

---

## 5. How it works — the technical core

### 5.1 Hybrid retrieval (semantic + keyword, fused by RRF)

A single retrieval method has blind spots: pure keyword search (BM25) misses folk
and multilingual synonyms ("haldi" for turmeric, "curcumin" for the active
compound); pure semantic search can drift on exact technical terms. TK-Shield runs
**both** and fuses them with **Reciprocal Rank Fusion (RRF)**:

```
score(doc) = Σ  weight / (k + rank)        k = 60
```

- Semantic side: `all-MiniLM-L6-v2` sentence embeddings (384-dim) in ChromaDB,
  cosine distance, `similarity = 1 − distance`.
- Keyword side: in-memory BM25 (`rank-bm25`).
- Weights: **semantic 0.7, keyword 0.3** (config-tunable).

RRF is rank-based, not score-based, so it combines the two systems without having
to calibrate their incomparable score scales. The ranker also **de-duplicates
kind-code variants** (`US5401504` vs `US5401504A`) by normalizing the patent id,
merging metadata so a richer record backfills empty fields on its twin — which
matters because a seeded landmark row may carry an IPC code the bulk row lacks.

### 5.2 The 5-factor risk model

Risk is an **interpretable, hand-weighted** 0–100 score — deliberately not a
black-box classifier, because the output must be explainable to a community or a
patent office. Five factors, each capped:

| Factor | Max | What it measures |
|---|---|---|
| Similarity | 40 | How close is the nearest patent? (continuous, monotonic curve) |
| Temporal | 20 | Was a candidate patent filed *after* the TK was documented? |
| Geographic | 15 | Are candidate patents filed in a country other than the TK origin? |
| Assignee | 15 | Corporate / known-actor assignee vs. academic vs. individual |
| IPC class | 10 | Is a candidate in a historically bio-piracy-prone patent class? |

Bands: **CRITICAL ≥ 80, HIGH ≥ 60, MEDIUM ≥ 40, LOW ≥ 20, else MINIMAL.**

Two specificity rules prevent false positives — the failure mode that would
destroy trust in a defensive tool:

1. **Relevance gate.** The four "aggravating" factors (temporal, geographic,
   assignee, IPC) only apply when there is a *credible* candidate — top similarity
   ≥ 0.50. Below the gate, risk reflects similarity alone. This stops a benign
   practice that only weakly matches the corpus from being inflated by structural
   traits (foreign filing, corporate assignee) that are meaningless without a real
   match.
2. **Missing data is not risk.** An unknown date / country / assignee / IPC
   contributes **0**, never an "assume risk" default. The model scores evidence,
   not gaps.

The response surfaces `relevance_gated` for transparency, plus the full factor
breakdown and a fixed list of channel-specific recommendations per band.

### 5.3 Prior-art enrichment

For the plants and uses in a TK entry, TK-Shield fans out **concurrently** to
three keyless databases and returns one normalized bundle:

- **PubMed** (NCBI E-utilities) → peer-reviewed literature, cited by **PMID**.
- **Wikidata** → taxonomy + multilingual aliases, cited by **QID**.
- **GBIF** → species occurrence / native range, cited by **taxon key**.

Each item carries its source and a stable id, deduped across common/scientific
names. Every source degrades independently: if one is disabled, empty, or down it
is recorded in `sources_skipped` and the rest proceed. Nothing here can crash the
pipeline.

### 5.4 RAG report generation

The retriever assembles candidate patents + risk + evidence into a context, and
`report_generator` prompts a **local LLM (Ollama, `llama3.2`)** for two fields: a
markdown **assessment** and a formal **opposition draft**. Three guarantees make
the output trustworthy:

- **Deterministic fallback.** With no LLM running, a templated report is produced
  instead — figures and citations stay exact; only the prose is templated. The
  tool is fully usable offline.
- **No hallucinated citations.** Any reference id the LLM narrative mentions that
  is *not* in the verified citation/patent set is surfaced as
  `unverified_citation_refs` — a trust guard against fabricated evidence.
- **Exact numbers.** The risk score, factor breakdown, and citation list are
  always computed deterministically; the LLM only writes narrative around them.

### 5.5 Claim-level novelty (the examiner core)

The examiner flow accepts up to 50,000 characters of pasted patent text. When that
text contains claim structure, `claim_parser` splits it into individual claims —
detecting numbering and independent vs. dependent relationships ("The method of
claim 1, wherein…"). Each claim is searched independently against the TK registry,
producing a **per-claim verdict** from cosine similarity (thresholds:
NOT-NOVEL ≥ 0.60, POSSIBLE ≥ 0.45). The overall verdict aggregates like an
examiner does: a patent fails novelty if **any independent claim** is anticipated.
If no claim structure is present (e.g. only an abstract was pasted), it falls back
to whole-text assessment — the contract is uniform.

Critically, **the verdict is computed from similarity, not the LLM** — so a patent
applicant cannot manipulate the verdict by embedding instructions in the patent
text. The LLM only narrates the already-decided verdicts.

---

## 6. Key design decisions and trade-offs

| Decision | Rationale | Trade-off accepted |
|---|---|---|
| **Keyless & offline-first** | Any community can run it; no cost, no vendor lock-in, no deprecation risk | Smaller local model; one-time bulk data download |
| **Hybrid retrieval over pure embeddings** | Recovers folk/multilingual/scientific synonyms a single method misses | More moving parts than a single index |
| **Interpretable risk model (not learned)** | Output must be explainable to communities and offices; no labelled training set exists | Hand-weighted, not data-optimized |
| **Deterministic fallbacks everywhere** | Graceful degradation is a hard requirement for a tool used in low-resource settings | More code paths to maintain and test |
| **Similarity-computed verdicts** | Immune to prompt injection in untrusted patent text | LLM cannot override an obviously-wrong threshold call |
| **Real-metadata corpus only** | Credibility — synthetic rows are excluded from the index | Bounded corpus size vs. an inflated synthetic one |
| **Three personas, no auth** | Demonstrates the full value to all stakeholders without a workflow layer | Not multi-tenant; single-user/local |

The throughline: **every choice favours trustworthiness and reproducibility over
raw capability**, because a defensive IP tool that is occasionally wrong, opaque,
or unaffordable is worse than no tool.

---

## 7. Data sources and corpus integrity

All sources are keyless and verified live:

| Source | Role | Licence |
|---|---|---|
| **PatentsView bulk** (USPTO) | Patent corpus — real titles, assignees, grant dates | Public domain |
| **Dr. Duke's Phytochemical & Ethnobotanical DB** (USDA) | TK registry ethnobotany | CC0 |
| **Wikidata** | Curated multilingual TK seed + taxonomy aliases | CC0 |
| **PubMed** (NCBI E-utilities) | Literature prior art | Public |
| **GBIF** | Species / native-range evidence | Open |
| **Ollama** (`llama3.2`) | Local report narrative | Local, optional |

**Corpus integrity** is enforced, not assumed:

- A strict TK-relevance keyword filter and an **exclusion of synthetic sources**
  (a low-fidelity HuggingFace fallback used only for offline bootstrap) mean the
  searchable corpus is **100% real metadata**.
- The same loader feeds the ChromaDB rebuild and the API's BM25, so
  **CSV ↔ ChromaDB ↔ BM25 stay 1:1** (verified 16,292 each).
- **NaN hygiene**: empty CSV/TSV cells (read by pandas as `NaN`) are cleaned to
  empty strings throughout ingest, so the literal string "nan" is never stored or
  displayed; the frontend shows "—" for empty values.
- A migration splits Duke's `COUNTRY(PEOPLE)` labels into a clean country + a
  `community` field for Nagoya/WIPO-IGC attribution, with a country/region
  stoplist so a country is never mis-stored as a holder people.

---

## 8. Evaluation and results

The evaluation harness (`src/evaluation/landmark_eval.py`) submits
**independently-authored, folk-worded** TK descriptions — different sentences from
the patents, though sharing the plant/use terms a real registrant would use — for
the three landmark cases through the *full* pipeline, and measures retrieval and
risk.

### Retrieval and risk (corpus of 16,292 real US patents)

| Case | Expected patent | Rank | Similarity | Risk |
|---|---|---|---|---|
| Turmeric for wound healing | US5401504A | **1** | 0.823 | **CRITICAL (86)** |
| Neem as crop antifungal | EP0436257B1 | **1** | 0.787 | **CRITICAL (94)** |
| Basmati aromatic rice | US5663484A | **1** | 0.662 | **CRITICAL (83)** |

| Metric | Result |
|---|---|
| Precision@1 | **100%** |
| Precision@5 | **100%** |
| Mean Reciprocal Rank | **1.000** |
| Cases flagged HIGH/CRITICAL | **100%** |
| Control false-positive rate | **0%** |

Three benign control practices — "drinking warm water in the morning",
"afternoon walk for relaxation", and "distributed cloud job scheduler" — were all
correctly left at **MINIMAL** (scores 12, 9, 4), relevance-gated, matching no
landmark. This is the false-positive guard working.

### Honesty about the ablation

A retrieval ablation (BM25-only vs. semantic-only vs. hybrid) shows all three
methods rank the target at #1 on these canonical cases — because the shared plant
terms let keyword search alone already find them. **The report says so plainly.**
Hybrid's added value is for the synonym/multilingual queries these specific
descriptions do not stress. This is a **small demonstration on canonical cases,
not a population-scale benchmark** — and stating that clearly is itself a
credibility feature. The honest framing is repeated in the README and the brief.

Reproduce: `PYTHONPATH=. python -m src.evaluation.landmark_eval`.

---

## 9. Security and hardening

TK-Shield underwent a structured engineering-board audit; the findings were fixed
in a dedicated hardening pass (merged as PR #9). Security is treated as a property
of construction, not a later add-on.

**Confirmed-and-fixed vulnerability — path traversal (the headline finding).**
The SPA catch-all route served any file reachable from `dist / <path>`. Starlette
decodes `%2e%2e` → `..` and does not normalize the path parameter, so a request
for `/%2e%2e/%2e%2e/api/main.py` **leaked source code, `.env`, and the SQLite
registry** — verified through the ASGI stack. The fix requires the resolved path
to stay under the build directory (`is_relative_to`), with a regression test. Live
re-verification: the same request now returns the SPA shell; source is not served.

**Other hardening:**

- **Per-IP rate limiting** (slowapi, in-memory, keyless) via per-route decorators
  — never throttling static assets, the SPA, or `/api/health` — with a tighter cap
  on the expensive LLM routes (`/report`, `/novelty`), which are *also* bounded by
  a concurrency semaphore (excess returns a clean 503).
- **Configurable CORS** (default `*` for local; tighten via env for deployment).
- **Bounded inputs** — every request field is length-capped so a multi-megabyte
  paste or a huge `n_results` never reaches embeddings, the LLM, or SQLite.
- **XSS-safe by construction** — server/LLM/user text is rendered through
  `react-markdown` with **no raw-HTML pass-through**; citation hrefs are
  scheme-validated (http/https only), blocking `javascript:`/`data:` URIs. There
  are dedicated frontend XSS-safety regression tests.
- **Prompt-injection-immune verdicts** — novelty verdicts are similarity-computed,
  so untrusted patent text cannot steer them.
- **SQLite robustness** — WAL mode + busy-timeout so concurrent threadpool
  handlers and bulk writes don't hit "database is locked"; `LIKE` metacharacters
  in search are escaped (still bound parameters — no injection).

---

## 10. Quality engineering

- **Tests** — **121 backend** tests (fully network-free; external APIs and the LLM
  are mocked/fixtured) and **22 frontend** tests (Vitest, including the XSS-safety
  regressions). A `pyproject.toml` puts the repo root on the path so the documented
  `pytest tests/` works directly.
- **Continuous integration** — GitHub Actions runs the backend suite and the
  frontend typecheck + tests on every push and PR; both PRs in the hardening and
  feature work merged green.
- **One-command demo** — a multi-stage Dockerfile + compose file boot an instant
  landmark-case demo (`docker compose up --build` → `http://localhost:8000`) with
  the three cases seeded and **no 219 MB corpus download**.
- **Reproducibility** — fully pinned `requirements.txt` and a `package-lock.json`;
  no runtime CDN; every `src/` module keeps a `__main__` smoke block.
- **Evaluation as code** — the brief PDF is rendered from the eval JSON, so the
  published numbers can never drift from the measured ones.

---

## 11. Technology stack

**Backend** — Python 3.11 · FastAPI · ChromaDB (vector search) · `rank-bm25`
(keyword) · SQLite (registry) · sentence-transformers (`all-MiniLM-L6-v2`) ·
spaCy NER · resilient `httpx` clients · slowapi (rate limiting) · Ollama
(`llama3.2`, local LLM) · reportlab (PDF) · loguru.

**Frontend** — Vite · React 18 · TypeScript · React Router · TanStack Query ·
Tailwind v4 · Radix primitives · Lucide icons · self-hosted Inter font · Vitest.

**Ops** — Docker + docker-compose · GitHub Actions CI · `.env`-driven config (a
single `config` singleton; every value has a sensible default).

---

## 12. Limitations

Stated honestly — TK-Shield is **decision-support that flags candidates for expert
human review; it does not establish or prove misappropriation.**

- **Scope** — US patent *metadata* (titles, abstracts, assignees, dates) for the
  corpus; non-US full text is not yet covered. (The examiner mode does parse claims
  from pasted text.)
- **Language** — English-centric; multilingual TK names are matched but the
  pipeline is English-first.
- **Model** — the local LLM is small (`llama3.2`); narrative quality is below
  frontier API models — a deliberate keyless/offline trade-off, with an exact
  deterministic fallback.
- **Risk model** — interpretable hand-weighted factors, not learned from a
  labelled dataset.
- **Evaluation** — a canonical-case demonstration (3 cases + 3 controls + an
  ablation), **not** a population-scale labelled benchmark.
- **Data** — the ethnobotany source skews to English-documented knowledge,
  under-representing some communities.
- **Deployment** — hardened for local/single-user (rate limiting, configurable
  CORS, bounded inputs, path-safe static serving) but **no authentication /
  multi-tenancy** — the gate for shared public hosting.

---

## 13. Roadmap

**Tier 1 — done.** Security hardening (path traversal, rate limiting, CORS, input
bounds), CI, one-command Docker demo, test-path fix, documentation sync.

**Tier 2 — done.** Claim-level novelty assessment in the examiner flow
(independent/dependent claim splitting, per-claim verdicts, injection-immune).

**Tier 3 — strong differentiators (next).**
- A larger, expert-labelled evaluation benchmark (precision/recall at scale).
- Full-text and non-US patent coverage; multilingual TK ingestion at scale.
- A live hosted demo URL so reviewers can click rather than build.
- Continuous monitoring + alerting for newly-filed patents.

**Moonshot.**
- Multi-tenant institutional deployment (auth, per-org isolation).
- Community consent and governance as a first-class feature.
- Claim-element (sub-claim) decomposition for finer anticipation analysis.

---

## 14. How it was built — engineering process

TK-Shield was built **AI-assisted, under direction and review.** The architecture,
data-source, evaluation, security, and product decisions are the author's —
keyless/offline-first design, hybrid retrieval over pure embeddings, the
interpretable risk model, the three-persona structure, the community-attribution
feature, and the WIPO policy framing. Implementation was accelerated with an AI
coding assistant.

The work proceeded in disciplined, reviewable increments:

1. **Core platform** — search, risk, enrichment, RAG, API, frontend.
2. **Scale-up** — real keyless data (PatentsView bulk), registry to ~2k entries,
   corpus-integrity guarantees.
3. **Evaluation & framing** — the landmark harness, honest metrics, the WIPO brief.
4. **Audit-driven hardening (Tier 1)** — an engineering-board review found a real
   path-traversal vulnerability and several productization gaps; all were fixed,
   tested, and merged via PR with green CI.
5. **Feature deepening (Tier 2)** — claim-level novelty, the feature that closes
   the biggest credibility gap for the examiner audience.
6. **Final audit** — full end-to-end verification: 121+22 tests green, every
   endpoint smoke-tested live, security re-verified, repository confirmed clean and
   in sync with GitHub.

Every change landed through a pull request with passing CI; the repository tracks
no build artifacts or scratch files.

---

## 15. Author and attribution

Designed and directed by **Ansul Suryawanshi**, applying an AI/ML and
environmental-science background to the defensive protection of traditional
knowledge.

**Source code** — MIT Licence. **Patent metadata** — PatentsView (USPTO, public
domain). **TK entries** — Dr. Duke's databases (USDA, CC0) and Wikidata (CC0).
**Enrichment** — PubMed, Wikidata, GBIF. TK-Shield is a defensive research tool;
it surfaces and organizes public evidence and does not constitute legal advice.

> Built as a demonstration of how open data and open models can serve the
> defensive-protection goals of the WIPO IGC and the 2024 Treaty on Genetic
> Resources and Associated Traditional Knowledge.

---

## Appendix A — repository map

```
api/            FastAPI app, cached deps, request schemas, routers
src/
  search/       vector_store · keyword_search · hybrid_ranker (RRF)
  classifier/   ip_risk_scorer (5-factor) · domain
  nlp/          preprocessor · ner_extractor
  clients/      pubmed · wikidata · gbif · patentsview · _http (resilient)
  enrichment/   prior_art (concurrent fan-out, citation-tagged)
  rag/          retriever · report_generator · novelty · claim_parser · llm_client
  registry/     tk_store (SQLite + vector collection)
  ingestion/    sources/ · tk_sources/ · build_corpus · ingest_to_chromadb · seed_*
  evaluation/   landmark_eval
  utils/        config (single singleton) · dates · lexicons
frontend/       Vite + React + TS SPA (api · lib · components · features)
docs/           this report · whitepaper PDF + builder · evaluation report
tests/          121 backend tests (network-free)
```

## Appendix B — API reference

| Method & path | Purpose |
|---|---|
| `GET /api/health` | Status + LLM / live-patent availability |
| `POST /api/tk` · `GET /api/tk` · `GET/DELETE /api/tk/{id}` | TK registry CRUD + paginated search |
| `POST /api/analyze` | Fast hybrid search + 5-factor risk (no LLM/network) |
| `POST /api/report?format=json\|markdown\|pdf` | Full RAG report + opposition draft |
| `POST /api/novelty` | Examiner claim-level novelty verdict |
| `POST /api/monitor` | Live PatentsView check (degrades gracefully without a key) |
| `GET /api/stats` | Researcher analytics over registry + corpus |

## Appendix C — reproduce everything

```bash
# Fastest — instant landmark demo (no keys, no big download)
docker compose up --build                      # → http://localhost:8000

# Tests
pytest tests/                                  # 121 backend, network-free
npm --prefix frontend run test                 # 22 frontend

# Evaluation (writes docs/evaluation_report.{md,json})
PYTHONPATH=. python -m src.evaluation.landmark_eval

# Rebuild this report's PDF from the markdown
PYTHONPATH=. python docs/build_project_report.py   # → docs/TK-Shield-Project-Report.pdf
```
