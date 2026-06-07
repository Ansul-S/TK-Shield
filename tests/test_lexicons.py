# Tests for the lexicon loader + a regression guard that the committed JSON
# lexicons exactly reproduce the frozen in-code fallbacks (no hidden drift).

import json

from src.utils import lexicons
from src.utils.config import config


# ── loader unit tests (isolated temp dir) ────────────────────

def _use_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "LEXICON_DIR", str(tmp_path))


def test_load_set_from_file(tmp_path, monkeypatch):
    _use_dir(tmp_path, monkeypatch)
    (tmp_path / "x.json").write_text(json.dumps(["a", "b", "c"]))
    assert lexicons.load_set("x", {"fallback"}) == {"a", "b", "c"}


def test_load_set_missing_file_uses_fallback(tmp_path, monkeypatch):
    _use_dir(tmp_path, monkeypatch)
    assert lexicons.load_set("nope", {"f1", "f2"}) == {"f1", "f2"}


def test_load_set_invalid_json_uses_fallback(tmp_path, monkeypatch):
    _use_dir(tmp_path, monkeypatch)
    (tmp_path / "bad.json").write_text("{ not valid json")
    assert lexicons.load_set("bad", {"f"}) == {"f"}


def test_load_set_wrong_shape_uses_fallback(tmp_path, monkeypatch):
    _use_dir(tmp_path, monkeypatch)
    (tmp_path / "empty.json").write_text(json.dumps([]))        # empty list
    assert lexicons.load_set("empty", {"f"}) == {"f"}
    (tmp_path / "nums.json").write_text(json.dumps([1, 2, 3]))  # non-strings
    assert lexicons.load_set("nums", {"f"}) == {"f"}
    (tmp_path / "obj.json").write_text(json.dumps({"a": 1}))    # not a list
    assert lexicons.load_set("obj", {"f"}) == {"f"}


def test_load_list_preserves_order_and_duplicates(tmp_path, monkeypatch):
    _use_dir(tmp_path, monkeypatch)
    (tmp_path / "l.json").write_text(json.dumps(["a", "b", "a"]))
    assert lexicons.load_list("l", []) == ["a", "b", "a"]


def test_load_keyword_map(tmp_path, monkeypatch):
    _use_dir(tmp_path, monkeypatch)
    (tmp_path / "m.json").write_text(json.dumps({"d": ["k1", "k2"]}))
    assert lexicons.load_keyword_map("m", {"x": ["y"]}) == {"d": ["k1", "k2"]}
    (tmp_path / "bad.json").write_text(json.dumps({"d": "not-a-list"}))
    assert lexicons.load_keyword_map("bad", {"x": ["y"]}) == {"x": ["y"]}


# ── regression: committed JSON == frozen in-code fallback ────

def test_committed_lexicons_match_frozen_fallbacks():
    from src.nlp import ner_extractor as ne
    assert ne.PLANT_NAMES == ne._PLANT_NAMES_FALLBACK
    assert ne.MEDICAL_USES == ne._MEDICAL_USES_FALLBACK
    assert ne.KNOWLEDGE_SYSTEMS == ne._KNOWLEDGE_SYSTEMS_FALLBACK
    assert ne.PRACTICES == ne._PRACTICES_FALLBACK

    from src.nlp import preprocessor as pp
    assert pp.LEGAL_STOPWORDS == pp._LEGAL_STOPWORDS_FALLBACK

    from src.classifier import domain as dm
    assert dm._DOMAIN_KEYWORDS == dm._DOMAIN_KEYWORDS_FALLBACK

    from src.ingestion import ingest_to_chromadb as ic
    assert ic.STRICT_TK_KEYWORDS == ic._STRICT_TK_KEYWORDS_FALLBACK


def test_core_terms_present_after_load():
    # Spot-check the landmark-critical terms survive the externalization.
    from src.nlp.ner_extractor import PLANT_NAMES, MEDICAL_USES
    assert {"turmeric", "neem", "basmati", "azadirachta indica"} <= PLANT_NAMES
    assert {"wound healing", "antifungal"} <= MEDICAL_USES
