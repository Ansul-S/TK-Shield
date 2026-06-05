# api/main.py — TK-Shield FastAPI application.
#
# Run:  venv/bin/uvicorn api.main:app --reload
# Then open http://localhost:8000

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from api.routes import analyze, monitor, novelty, report, stats, tk
from src.registry import tk_store


@asynccontextmanager
async def lifespan(app: FastAPI):
    tk_store.init_db()
    yield


app = FastAPI(
    title="TK-Shield",
    description="Defensive bio-piracy monitoring for Traditional Knowledge.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # local dev / single-host deployment
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
_DIST = _FRONTEND / "dist"
_INDEX = _DIST / "index.html"

if _INDEX.exists():
    # Static assets (hashed JS/CSS/etc.) are served from /assets and friends.
    app.mount("/assets", StaticFiles(directory=str(_DIST / "assets")), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa_fallback(full_path: str):
        # /api/* is handled by the routers above; anything else returns the SPA
        # shell so the client router can resolve the route.
        candidate = _DIST / full_path
        if full_path and candidate.is_file():
            return FileResponse(str(candidate))
        return FileResponse(str(_INDEX))

elif (_FRONTEND / "legacy").exists():
    app.mount(
        "/",
        StaticFiles(directory=str(_FRONTEND / "legacy"), html=True),
        name="legacy-frontend",
    )
