# tests/test_rate_limit.py — proves the shared slowapi limiter (C7) actually
# enforces a per-IP cap and returns HTTP 429 once exceeded. We exercise the real
# `api.deps.limiter` instance + the same 429 handler `api.main` registers, on a
# throwaway route with a tiny limit — so the test is fast (no engine/corpus) yet
# verifies the exact wiring the production routes depend on.

import pytest
from fastapi import FastAPI, Request
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from starlette.testclient import TestClient

from api.deps import limiter


@pytest.fixture
def client():
    app = FastAPI()
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    @app.get("/ping")
    @limiter.limit("2/minute")
    def ping(request: Request) -> dict:
        return {"ok": True}

    return TestClient(app)


def test_returns_429_after_limit_exceeded(client):
    if not limiter.enabled:
        pytest.skip("rate limiting disabled via RATE_LIMIT_ENABLED")
    assert client.get("/ping").status_code == 200
    assert client.get("/ping").status_code == 200
    # Third call within the window is over the 2/minute cap.
    third = client.get("/ping")
    assert third.status_code == 429
    assert "rate limit" in third.text.lower() or third.status_code == 429
