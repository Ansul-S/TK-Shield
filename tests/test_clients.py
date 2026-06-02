# Tests that clients correctly parse recorded API payloads, and degrade
# gracefully on failure. No network — the HTTP layer is monkeypatched.

from src.clients import pubmed_client, wikidata_client, gbif_client, patentsview_client


# ── PubMed ───────────────────────────────────────────────────
def test_pubmed_parses_and_dedupes(monkeypatch):
    def fake_get(url, params=None, **kw):
        if "esearch" in url:
            return {"esearchresult": {"idlist": ["111", "222"]}}
        return {"result": {
            "111": {"title": "Turmeric for wound healing.", "pubdate": "1995 Jan",
                    "fulljournalname": "J Ethnopharmacology"},
            "222": {"title": "Neem antifungal study", "pubdate": "2001",
                    "fulljournalname": "Phytomedicine"},
        }}
    monkeypatch.setattr(pubmed_client, "get_json", fake_get)
    out = pubmed_client.search_literature("turmeric", retmax=2)
    assert [o["ref_id"] for o in out] == ["111", "222"]
    assert out[0]["year"] == "1995"
    assert out[0]["source"] == "pubmed"
    assert out[0]["url"].endswith("/111/")


def test_pubmed_empty_on_failure(monkeypatch):
    monkeypatch.setattr(pubmed_client, "get_json", lambda *a, **k: None)
    assert pubmed_client.search_literature("turmeric") == []


# ── Wikidata ─────────────────────────────────────────────────
def test_wikidata_parses_entity(monkeypatch):
    monkeypatch.setattr(wikidata_client, "get_json", lambda *a, **k: {
        "search": [{"id": "Q42562", "label": "Curcuma longa",
                    "description": "plant used as spice", "aliases": ["turmeric"],
                    "concepturi": "http://www.wikidata.org/entity/Q42562"}]
    })
    out = wikidata_client.search_plant("turmeric")
    assert out["ref_id"] == "Q42562"
    assert "turmeric" in out["aliases"]


def test_wikidata_none_on_empty(monkeypatch):
    monkeypatch.setattr(wikidata_client, "get_json", lambda *a, **k: {"search": []})
    assert wikidata_client.search_plant("zzz") is None


# ── GBIF ─────────────────────────────────────────────────────
def test_gbif_match_and_native_countries(monkeypatch):
    def fake_get(url, params=None, **kw):
        if "/match" in url:
            return {"usageKey": 2757624, "scientificName": "Curcuma longa L.",
                    "family": "Zingiberaceae", "matchType": "EXACT"}
        return {"results": [
            {"establishmentMeans": "NATIVE", "country": "IN"},
            {"establishmentMeans": "INTRODUCED", "country": "US"},
        ]}
    monkeypatch.setattr(gbif_client, "get_json", fake_get)
    out = gbif_client.species_origin("Curcuma longa")
    assert out["ref_id"] == "2757624"
    assert out["native_countries"] == ["IN"]


def test_gbif_skips_no_match(monkeypatch):
    monkeypatch.setattr(gbif_client, "get_json", lambda *a, **k: {"matchType": "NONE"})
    assert gbif_client.species_origin("turmeric") is None


# ── PatentsView ──────────────────────────────────────────────
def test_patentsview_no_key_returns_empty(monkeypatch):
    monkeypatch.setattr(patentsview_client.config, "PATENTSVIEW_API_KEY", "")
    assert patentsview_client.search_patents("turmeric") == []


def test_patentsview_normalizes_results(monkeypatch):
    monkeypatch.setattr(patentsview_client.config, "PATENTSVIEW_API_KEY", "demo-key")
    monkeypatch.setattr(patentsview_client.config, "ENABLE_PATENTSVIEW", True)
    monkeypatch.setattr(patentsview_client, "post_json", lambda *a, **k: {
        "error": False,
        "patents": [{
            "patent_id": "US5401504A", "patent_title": "Use of turmeric in wound healing",
            "patent_abstract": "Method of promoting healing.", "patent_date": "1995-03-28",
            "assignees": [{"assignee_organization": "Univ of Mississippi"}],
        }],
    })
    out = patentsview_client.search_patents("turmeric")
    assert out[0]["id"] == "US5401504A"
    assert out[0]["metadata"]["assignee"] == "Univ of Mississippi"
    assert out[0]["metadata"]["source"] == "patentsview-live"
