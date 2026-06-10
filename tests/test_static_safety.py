# tests/test_static_safety.py — regression guard for the SPA static-file
# path-traversal fix (C1). _safe_static_file must only ever return a real file
# that lives *inside* the built frontend dist; any escape attempt → None (the
# caller then serves the SPA index instead of leaking source/.env/the DB).

from pathlib import Path

from api.main import _DIST, _safe_static_file


def test_traversal_with_dotdot_is_blocked():
    # Starlette hands us the already-decoded path, so `..` is the real attack
    # surface (the wire form is %2e%2e). Both must resolve to None.
    for attack in (
        "../../api/main.py",
        "../../.env",
        "../../data/tk_registry.sqlite3",
        "..%2f..%2fapi%2fmain.py",   # not decoded by us → not a real file → None
        "../../../../../../etc/passwd",
    ):
        assert _safe_static_file(attack) is None, attack


def test_absolute_path_is_blocked():
    # `_DIST / "/etc/hosts"` collapses to "/etc/hosts" (absolute RHS) — must not
    # be served even though it exists.
    assert _safe_static_file("/etc/hosts") is None


def test_empty_path_is_none():
    assert _safe_static_file("") is None


def test_real_in_dist_file_is_served_when_present():
    # Positive case: a genuine file inside dist resolves to itself. Skip cleanly
    # if the SPA hasn't been built in this environment.
    index = _DIST / "index.html"
    if not index.exists():
        import pytest
        pytest.skip("frontend not built (frontend/dist absent)")
    resolved = _safe_static_file("index.html")
    assert resolved is not None
    assert resolved == index.resolve()
    assert Path(resolved).is_relative_to(_DIST)
