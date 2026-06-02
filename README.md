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

# 3. Build the patent corpus
python -m src.ingestion.patent_scraper          # fetch + filter patents → CSV
python -m src.ingestion.ingest_to_chromadb      # embed + index into ChromaDB
python -m src.ingestion.seed_landmark_cases     # add the real bio-piracy cases

# 4. Run
uvicorn api.main:app --reload
# open http://localhost:8000
```

## Using it

- **Web dashboard** (`http://localhost:8000`): register a TK entry (plants/uses are auto-extracted), then run a quick risk check, a full RAG report, or live patent monitoring; export the report as markdown.
- **API** (docs at `/docs`): `POST /api/tk`, `GET /api/tk`, `POST /api/analyze`, `POST /api/report?format=json|markdown|pdf`, `POST /api/monitor`, `GET /api/health`.

## Optional: live patent monitoring

PatentsView retired its keyless API in Feb 2025. To enable live monitoring of newly-filed US patents, request a **free** key at <https://patentsview.org/apis/keyrequest> and set `PATENTSVIEW_API_KEY` in `.env` (see `.env.example`). Without it, everything else still works.

## Configuration

All settings live in `.env` (copy from `.env.example`); sensible defaults mean it's optional. See [CLAUDE.md](CLAUDE.md) for architecture details.

## Tests

```bash
pytest tests/ -q      # network-free, fixture-based
```
