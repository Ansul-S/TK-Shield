# src/clients/_http.py
#
# Shared HTTP helpers with retries, timeouts, and graceful failure.
# These never raise on network/HTTP errors — they return None so callers
# can degrade gracefully (the whole point of TK-Shield's offline-first design).

import time
import httpx
from loguru import logger

from src.utils.config import config

# Wikimedia (and good API etiquette generally) requires a descriptive
# User-Agent; the default httpx UA gets a 403 from Wikidata.
_DEFAULT_HEADERS = {
    "User-Agent": "TK-Shield/0.1 (traditional-knowledge bio-piracy research; contact: tk-shield)",
    "Accept": "application/json",
}


def _request_json(method: str, url: str, **kwargs) -> dict | list | None:
    """
    Make an HTTP request and parse JSON, retrying transient failures.
    Returns parsed JSON on success, or None on any failure.
    """
    timeout = kwargs.pop("timeout", config.HTTP_TIMEOUT)
    headers = {**_DEFAULT_HEADERS, **(kwargs.pop("headers", None) or {})}
    last_err = None

    for attempt in range(1, config.MAX_RETRIES + 1):
        try:
            resp = httpx.request(method, url, timeout=timeout, headers=headers, **kwargs)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:  # noqa: BLE001 — deliberately broad: never propagate
            last_err = e
            logger.warning(f"{method} {url} attempt {attempt}/{config.MAX_RETRIES} failed: {e}")
            # Linear backoff; respects the politeness delay shared with ingestion.
            time.sleep(config.REQUEST_DELAY * attempt)

    logger.error(f"{method} {url} failed after {config.MAX_RETRIES} attempts: {last_err}")
    return None


def get_json(url: str, params: dict | None = None, headers: dict | None = None,
             timeout: float | None = None) -> dict | list | None:
    return _request_json("GET", url, params=params, headers=headers, timeout=timeout)


def post_json(url: str, json_body: dict | None = None, headers: dict | None = None,
              timeout: float | None = None) -> dict | list | None:
    return _request_json("POST", url, json=json_body, headers=headers, timeout=timeout)
