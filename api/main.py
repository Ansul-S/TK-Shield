# api/main.py — TK-Shield FastAPI application.
#
# Run:  venv/bin/uvicorn api.main:app --reload
# Then open http://localhost:8000

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
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

# Serve the build-free static frontend at "/".
_FRONTEND = Path(__file__).resolve().parent.parent / "frontend"
if _FRONTEND.exists():
    app.mount("/", StaticFiles(directory=str(_FRONTEND), html=True), name="frontend")
