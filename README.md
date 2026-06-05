# 🛡️ TK-Shield

**Defensive bio-piracy monitoring for Traditional Knowledge.**

TK-Shield helps communities and researchers protect documented **Traditional Knowledge (TK)** — traditional medicinal and agricultural practices — from patents that improperly claim it. Given a documented practice (e.g. *turmeric for wound healing*), it:

1. **Finds** patents that may misappropriate the knowledge (hybrid semantic + keyword search).
2. **Scores** bio-piracy risk across five factors (similarity, timing, geography, assignee, patent class).
3. **Gathers** prior-art evidence from free public sources (PubMed, Wikidata, GBIF).
4. **Generates** a citation-backed risk assessment and a draft patent opposition using a **local LLM**.

It addresses a real problem: landmark cases like the turmeric (US5401504A), neem (EP0436257B1), and basmati (US5663484A) patents were all challenged and overturned using exactly this kind of prior-art evidence. TK-Shield helps assemble it.

## Design principles

- **Free & reliable only.** Keyless public APIs (PubMed, Wikidata, GBIF, HuggingFace) + a local LLM (Ollama). No paid services.
- **Offline-first / graceful degradation.** The full pipeline runs with **zero API keys**. Every external source can fail or be absent without breaking anything — the report just notes what was skipped. Live patent monitoring (PatentsView) is an optional add-on that needs a *free* key.
- **Citations, not hand-waving.** Every claim links to a stable reference ID (PMID / Wikidata QID / GBIF key / patent number).

## Quick start

```bash
# 1. Install
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python -m spacy download en_core_web_sm

# 2. (Optional) local LLM for narrative reports — works without it too
#    Install Ollama from https://ollama.com then:
ollama pull llama3.2

# 3. Build the patent corpus — keyless, REAL metadata (~219MB one-time download)
PATENT_SOURCE=patentsview_bulk MAX_PATENTS=20000 python -m src.ingestion.build_corpus
python -m src.ingestion.ingest_to_chromadb      # embed + index into ChromaDB
python -m src.ingestion.seed_landmark_cases     # add the real bio-piracy cases
# (or PATENT_SOURCE=ccdv for a zero-download, lower-fidelity offline corpus)

# 4. Build the TK registry from open sources
TK_SOURCE=duke     TK_IMPORT_LIMIT=2000 python -m src.ingestion.build_registry  # Dr. Duke CC0
TK_SOURCE=wikidata TK_IMPORT_LIMIT=50   python -m src.ingestion.build_registry  # multilingual seed

# 5. Run
uvicorn api.main:app --reload
# open http://localhost:8000
```

## Scaling up the data

- **Patents — no API key needed.** `PATENT_SOURCE=patentsview_bulk` downloads PatentsView's **public bulk TSV files** (no key, no registration) and gives real patent IDs, titles, abstracts, grant dates, and assignees — the fidelity the risk scorer needs. Files cache under `PATENTSVIEW_BULK_DIR`; drop pre-downloaded `*.tsv.zip` there to skip the download. `PATENT_SOURCE=ccdv` is a zero-download, lower-fidelity fallback. (A live-API harvester exists too but needs a free key and isn't required.)
- **TK registry.** `TK_SOURCE=duke` imports Dr. Duke's CC0 ethnobotany (point `DUKE_CSV_PATH` at a local download, or let it fetch the zip). `TK_SOURCE=wikidata` adds a curated cross-region seed enriched with real Wikidata multilingual aliases.

## Three personas (one platform)

- **🛡️ Defender** — register TK, run risk analysis + a full RAG report, monitor live patents, export an opposition draft.
- **⚖️ Examiner** — paste a patent's text; get a novelty verdict against the documented TK registry with the matching prior art.
- **📊 Researcher** — analytics across the registry and patent corpus (domains, geography, top assignees).

## API (docs at `/docs`)

`POST /api/tk` · `GET /api/tk` · `POST /api/analyze` · `POST /api/report?format=json|markdown|pdf` · `POST /api/monitor` · `POST /api/novelty` · `GET /api/stats` · `GET /api/health`

## Optional: live patent monitoring

The whole pipeline — including the **real-metadata patent corpus** (`patentsview_bulk`) — runs with **zero API keys**. The only key-gated feature is the live "newly-filed patents" monitor tab, which uses PatentsView's live API. It's entirely optional; leave `PATENTSVIEW_API_KEY` blank and refresh the corpus from the bulk files instead.

## Configuration

All settings live in `.env` (copy from `.env.example`); sensible defaults mean it's optional. See [CLAUDE.md](CLAUDE.md) for architecture details.

## Tests

```bash
pytest tests/ -q      # network-free, fixture-based
```
