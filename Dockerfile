# TK-Shield — multi-stage image.
#
# Stage 1 builds the Vite/React SPA. Stage 2 is a slim Python runtime that
# installs the (CPU-only) ML stack, bakes the spaCy/NLTK/embedding assets into
# the image so the container needs NO network at runtime, copies the built SPA,
# and on start seeds the 3 landmark cases for an instant working demo.

# ─────────────────────────── Stage 1: frontend ───────────────────────────
FROM node:22-slim AS frontend
WORKDIR /app/frontend

# Install deps from the lockfile first (better layer caching).
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build            # → /app/frontend/dist

# ─────────────────────────── Stage 2: runtime ────────────────────────────
FROM python:3.11-slim AS runtime
WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HUB_DISABLE_TELEMETRY=1

# CPU-only torch first (avoids the multi-GB CUDA wheel), then the rest.
COPY requirements.txt ./
RUN pip install --upgrade pip \
 && pip install torch==2.11.0 --index-url https://download.pytorch.org/whl/cpu \
 && pip install -r requirements.txt

# Bake model/data assets so the runtime is fully offline.
RUN python -m spacy download en_core_web_sm \
 && python -m nltk.downloader stopwords \
 && python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

# Application code + lexicons + the built SPA.
COPY src/ ./src/
COPY api/ ./api/
COPY data/lexicons/ ./data/lexicons/
COPY docker-entrypoint.sh ./
COPY --from=frontend /app/frontend/dist ./frontend/dist

RUN chmod +x docker-entrypoint.sh

EXPOSE 8000
# Seed the landmark demo (idempotent) then serve SPA + API on one origin.
ENTRYPOINT ["./docker-entrypoint.sh"]
