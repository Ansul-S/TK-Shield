# Tests for registry pagination + search. ChromaDB writes are stubbed and the
# SQLite DB is redirected to a temp file, so no model load / no data pollution.

from src.registry import tk_store


def _isolate(monkeypatch, tmp_path):
    monkeypatch.setattr(tk_store.config, "TK_DB_PATH", str(tmp_path / "reg.sqlite3"))
    monkeypatch.setattr(tk_store.vector_store, "add_documents", lambda **k: None)


def test_pagination(monkeypatch, tmp_path):
    _isolate(monkeypatch, tmp_path)
    for i in range(30):
        tk_store.add_entry({"practice_name": f"Plant {i:02d} remedy", "plants": [f"p{i}"]})
    assert tk_store.count_entries() == 30
    p1 = tk_store.list_entries(limit=10, offset=0)
    p2 = tk_store.list_entries(limit=10, offset=10)
    assert len(p1) == 10 and len(p2) == 10
    assert {e["tk_id"] for e in p1}.isdisjoint({e["tk_id"] for e in p2})  # no overlap
    assert len(tk_store.list_entries()) == 30  # no limit → all (used by stats)


def test_search(monkeypatch, tmp_path):
    _isolate(monkeypatch, tmp_path)
    tk_store.add_entry({"practice_name": "Turmeric for wounds", "plants": ["turmeric", "Curcuma longa"]})
    tk_store.add_entry({"practice_name": "Neem antifungal", "plants": ["neem"], "country": "Brazil"})
    tk_store.add_entry({"practice_name": "Ginger tonic", "plants": ["ginger"]})
    assert tk_store.count_entries(query="turmeric") == 1
    assert tk_store.count_entries(query="curcuma") == 1    # matches the plants JSON
    assert tk_store.count_entries(query="brazil") == 1     # matches country (case-insensitive)
    assert tk_store.count_entries(query="zzzznomatch") == 0
    hit = tk_store.list_entries(query="neem")
    assert len(hit) == 1 and hit[0]["practice_name"] == "Neem antifungal"
