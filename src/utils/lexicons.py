# src/utils/lexicons.py
#
# Loader for the versioned domain lexicons under config.LEXICON_DIR
# (plants, medical uses, knowledge systems, practices, domain keywords, strict
# TK keywords, legal stopwords). The JSON files are the AUTHORITATIVE source —
# edit them to extend coverage without touching code. Each call passes a frozen
# in-code `fallback`, used (with a loud warning) only if the file is missing or
# invalid, so the pipeline never breaks on a bad/absent lexicon file.

import json
from pathlib import Path
from typing import Iterable

from loguru import logger

from src.utils.config import config


def _read(name: str):
    """Return parsed JSON for a lexicon, or None if missing/unreadable."""
    path = Path(config.LEXICON_DIR) / f"{name}.json"
    if not path.exists():
        logger.warning(f"lexicon '{name}' not found at {path}; using in-code fallback")
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        logger.warning(f"lexicon '{name}' unreadable ({e}); using in-code fallback")
        return None


def _valid_str_list(data) -> bool:
    return isinstance(data, list) and bool(data) and all(isinstance(x, str) for x in data)


def load_set(name: str, fallback: Iterable[str]) -> set[str]:
    """Load a lexicon as a set of terms. Falls back to `fallback` on any problem."""
    data = _read(name)
    if not _valid_str_list(data):
        if data is not None:
            logger.warning(f"lexicon '{name}' must be a non-empty list[str]; using fallback")
        return set(fallback)
    return set(data)


def load_list(name: str, fallback: Iterable[str]) -> list[str]:
    """Load a lexicon as an ordered list (use when order/duplication matters)."""
    data = _read(name)
    if not _valid_str_list(data):
        if data is not None:
            logger.warning(f"lexicon '{name}' must be a non-empty list[str]; using fallback")
        return list(fallback)
    return list(data)


def load_keyword_map(name: str, fallback: dict[str, list[str]]) -> dict[str, list[str]]:
    """Load a {category: [keywords]} lexicon (e.g. domain keywords)."""
    data = _read(name)
    ok = (
        isinstance(data, dict)
        and bool(data)
        and all(isinstance(k, str) and _valid_str_list(v) for k, v in data.items())
    )
    if not ok:
        if data is not None:
            logger.warning(f"lexicon '{name}' must be {{str: list[str]}}; using fallback")
        return {k: list(v) for k, v in fallback.items()}
    return {k: list(v) for k, v in data.items()}
