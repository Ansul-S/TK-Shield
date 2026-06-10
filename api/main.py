# api/main.py — TK-Shield FastAPI application.
#
# Run:  venv/bin/uvicorn api.main:app --reload
# Then open http://localhost:8000

import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from loguru import logger
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from api.deps import limiter
from api.routes import analyze, monitor, novelty, report, stats, tk
from src.registry import tk_store
from src.utils.config import config


@asynccontextmanager
async def lifespan(app: FastAPI):
    tk_store.init_db()
    _warm_engine()
    yield


def _warm_engine() -> None:
    """Build the hybrid engine (and warm the embedding model + ChromaDB) at
    startup instead of lazily on the first /analyze. This fixes the cold-start
    latency a user would otherwise hit (C4 readiness) and the race where
    concurrent first requests build the ~16k-doc BM25 index more than once
    (C2 thread-safety). Failures degrade gracefully — the server still serves
    the SPA and /api/health; the affected route reports the real error."""
    from api.deps import get_engine
    t0 = time.perf_counter()
    try:
        engine = get_engine()
        engine.search("traditional medicinal plant extract", n_results=1)  # warm embeddings + Chroma
        logger.success(f"Search engine warmed in {time.perf_counter() - t0:.1f}s")
    except Exception as e:  # noqa: BLE001 — never let warmup crash startup
        logger.warning(f"Engine warmup skipped ({type(e).__name__}: {e}); "
                       "first /analyze will build it lazily.")


app = FastAPI(
    title="TK-Shield",
    description="Defensive bio-piracy monitoring for Traditional Knowledge.",
    version="0.1.0",
    lifespan=lifespan,
)

# Wire the shared rate limiter (C7): per-route `@limiter.limit(...)` decorators
# enforce per-IP caps; this registers the limiter and the 429 handler. No global
# middleware → static assets / SPA / health are unaffected.
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    # Defaults to "*" for local/single-host use; set CORS_ORIGINS in .env to a
    # comma-separated allow-list before exposing the app to a network.
    allow_origins=config.CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health", tags=["meta"])
def health() -> dict:
    from src.rag.llm_client import get_llm
    from src.clients import patentsview_client
    return {
        "status": "ok",
        "llm_available": get_llm().is_available(),
        "live_patents_available": patentsview_client.is_available(),
    }


# API routers (registered before the static mount so /api/* wins).
app.include_router(tk.router)
app.include_router(analyze.router)
app.include_router(report.router)
app.include_router(monitor.router)
app.include_router(novelty.router)   # examiner
app.include_router(stats.router)     # researcher

# Serve the frontend at "/". The UI is a Vite + React SPA built to
# `frontend/dist`. When that build exists we serve it with a catch-all fallback
# so client-side deep routes (e.g. /defender/TK-123) survive a hard refresh —
# StaticFiles(html=True) only serves directory index files, not SPA routes.
# Until the build is present we fall back to the archived legacy single-file UI.
_FRONTEND = Path(__file__).resolve().parent.parent / "frontend"
_DIST = (_FRONTEND / "dist").resolve()
_INDEX = _DIST / "index.html"


def _safe_static_file(full_path: str) -> Path | None:
    """Resolve a request path to a real file *inside* `_DIST`, or None.

    Security (C1): Starlette decodes `%2e%2e` → `..` and the `{full_path:path}`
    converter does NOT normalize it, so a naive `_DIST / full_path` escapes the
    build root (e.g. `/%2e%2e/%2e%2e/api/main.py` would read source / `.env` /
    the SQLite registry). We resolve the candidate and require it to stay under
    `_DIST` (`is_relative_to`) before serving — anything escaping returns None
    and the caller falls back to the SPA shell.
    """
    if not full_path:
        return None
    candidate = (_DIST / full_path).resolve()
    if candidate.is_file() and candidate.is_relative_to(_DIST):
        return candidate
    return None


if _INDEX.exists():
    # Static assets (hashed JS/CSS/etc.) are served from /assets and friends.
    app.mount("/assets", StaticFiles(directory=str(_DIST / "assets")), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa_fallback(full_path: str):
        # /api/* is handled by the routers above; anything else returns the SPA
        # shell so the client router can resolve the route. A real, in-root file
        # (validated by _safe_static_file) is served directly; everything else —
        # including path-traversal attempts — returns the SPA index.
        safe = _safe_static_file(full_path)
        return FileResponse(str(safe)) if safe else FileResponse(str(_INDEX))

elif (_FRONTEND / "legacy").exists():
    app.mount(
        "/",
        StaticFiles(directory=str(_FRONTEND / "legacy"), html=True),
        name="legacy-frontend",
    )
