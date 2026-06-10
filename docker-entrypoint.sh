#!/usr/bin/env sh
# Seed the instant landmark demo (idempotent, fast — 3 patents + 3 TK entries),
# then serve the SPA + /api from a single origin. The seed writes into the
# mounted data/ and chroma_db/ volumes so it persists across restarts.
set -e

echo "[entrypoint] Seeding landmark demo (turmeric / neem / basmati)…"
python -m src.ingestion.seed_demo

echo "[entrypoint] Starting TK-Shield on :8000"
exec uvicorn api.main:app --host 0.0.0.0 --port 8000
