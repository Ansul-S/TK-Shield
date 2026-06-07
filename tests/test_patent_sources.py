# Tests for the pluggable patent source layer — no network.

import pandas as pd

from src.clients import patentsview_client as pv
from src.ingestion.sources import patentsview_harvest as harvest
from src.ingestion.sources import patentsview_bulk_source as bulk
import src.ingestion.build_corpus as bc


def _fake_record(n):
    return {
        "patent_id": f"US{n}A", "patent_title": f"Title {n}", "patent_abstract": "abstract",
        "patent_date": "2010-01-01",
        "assignees": [{"assignee_organization": "Acme Corp"}],
        "cpc_current": [{"cpc_group_id": "A61K36/00", "cpc_subclass_id": "A61K"}],
    }


def test_search_by_cpc_normalizes_and_paginates(monkeypatch):
    monkeypatch.setattr(pv, "is_available", lambda: True)
    monkeypatch.setattr(pv, "_post", lambda body: {"patents": [_fake_record(i) for i in range(100)]})
    patents, cursor = pv.search_by_cpc(["A61K36"], size=100)
    assert len(patents) == 100
    assert cursor == "US99A"                       # full page → cursor set
    assert patents[0]["metadata"]["assignee"] == "Acme Corp"
    assert patents[0]["metadata"]["ipc_code"] == "A61K36/00"
    assert patents[0]["metadata"]["source"] == "patentsview"


def test_search_by_cpc_no_key_returns_empty(monkeypatch):
    monkeypatch.setattr(pv, "is_available", lambda: False)
    assert pv.search_by_cpc(["A61K36"]) == ([], None)


def test_harvester_respects_limit_and_dedupes(monkeypatch):
    pages = [
        {"patents": [_fake_record(i) for i in range(100)]},   # full page → continue
        {"patents": [_fake_record(0), _fake_record(200)]},     # dup + 1 new
    ]
    calls = {"i": 0}

    def fake_post(body):
        i = calls["i"]; calls["i"] += 1
        return pages[i] if i < len(pages) else {"patents": []}

    monkeypatch.setattr(pv, "is_available", lambda: True)
    monkeypatch.setattr(pv, "_post", fake_post)
    monkeypatch.setattr(harvest.time, "sleep", lambda *_: None)

    got = list(harvest.iter_patents(limit=150))
    ids = [p["id"] for p in got]
    assert len(ids) == len(set(ids))               # deduped across pages
    assert len(got) == 101                          # 100 + 1 unique


def test_bulk_filters_to_tk_and_keeps_real_metadata():
    gp = pd.DataFrame({
        "patent_id": ["10000001", "10000002", "10000003"],
        "patent_title": ["Turmeric wound healing composition", "A semiconductor device",
                          "Neem oil antifungal formulation"],
        "patent_abstract": ["herbal extract for wounds", "transistor", "azadirachta indica based"],
        "patent_date": ["2015-01-06", "2015-01-06", "2016-03-01"],
    })
    pts = bulk.patents_from_frame(gp)
    assert [p["id"] for p in pts] == ["US10000001", "US10000003"]   # semiconductor dropped
    assert pts[0]["metadata"]["filing_date"] == "2015-01-06"         # real date preserved
    assert pts[0]["metadata"]["source"] == "patentsview-bulk"


def test_bulk_uses_configurable_jurisdiction(monkeypatch):
    # The id prefix + country come from config (no hardcoded "US"); changing the
    # jurisdiction relabels new rows. (Tier 3)
    monkeypatch.setattr(bulk.config, "DEFAULT_JURISDICTION", "EP")
    monkeypatch.setattr(bulk.config, "DEFAULT_PATENT_COUNTRY", "EP")
    gp = pd.DataFrame({
        "patent_id": ["12345"],
        "patent_title": ["Turmeric wound healing"],
        "patent_abstract": ["herbal extract"],
        "patent_date": ["2015-01-06"],
    })
    p = bulk.patents_from_frame(gp)[0]
    assert p["id"] == "EP12345"
    assert p["metadata"]["patent_id"] == "EP12345"
    assert p["metadata"]["country"] == "EP"


def test_bulk_assignee_join():
    ga = pd.DataFrame({
        "patent_id": ["10000001", "10000003", "9999999"],
        "disambig_assignee_organization": ["Acme Pharma", "Neem Corp", ""],
    })
    amap = bulk.assignee_map_from_frame(ga, {"10000001", "10000003"})
    assert amap == {"10000001": "Acme Pharma", "10000003": "Neem Corp"}


def test_build_corpus_appends_and_dedupes(monkeypatch, tmp_path):
    csv = tmp_path / "patents.csv"
    monkeypatch.setattr(bc.config, "PATENTS_CSV", csv)

    def fake_iter(limit):
        for n in range(limit):
            yield {"id": f"X{n}", "text": f"plant extract {n}",
                   "metadata": {"patent_id": f"X{n}", "title": "t", "abstract": "a",
                                "assignee": "Z", "filing_date": "2000", "country": "US",
                                "ipc_code": "A61K36", "source": "test", "status": "GRANTED"}}

    monkeypatch.setattr(bc, "get_patent_source", lambda name: fake_iter)
    bc.build_corpus("fake", 3)
    df = bc.build_corpus("fake", 3)        # second run must not duplicate
    assert len(df) == 3
    assert set(df["id"]) == {"X0", "X1", "X2"}
