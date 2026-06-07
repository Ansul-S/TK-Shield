# Tests for config hardening (A1) + config-promotion defaults — no network.

import pytest

from src.ingestion.build_corpus import build_corpus
from src.ingestion.sources import get_patent_source
from src.utils.config import config


# ── A1: PATENT_SOURCE footgun ────────────────────────────────

def test_default_patent_source_is_indexable():
    # A fresh install must build a corpus that actually survives indexing:
    # the default source must NOT be in the exclusion list, and must resolve.
    assert config.PATENT_SOURCE not in config.EXCLUDE_PATENT_SOURCES
    assert callable(get_patent_source(config.PATENT_SOURCE))


def test_default_config_validates():
    # The shipped defaults are a valid combination (no exception).
    config.validate_corpus_config()


def test_validate_rejects_excluded_source():
    with pytest.raises(ValueError, match="excluded by"):
        config.validate_corpus_config("ccdv")


def test_validate_allows_real_source():
    config.validate_corpus_config("patentsview_bulk")  # must not raise


def test_build_corpus_fails_fast_on_excluded_source():
    # Building from an excluded source would yield an empty index → fail fast,
    # before any download/iteration (so this needs no network).
    with pytest.raises(ValueError, match="excluded by"):
        build_corpus(source_name="ccdv")


# ── Config promotion: defaults must preserve prior behaviour ──

def test_promoted_defaults_match_prior_literals():
    assert config.RISK_TOP_N_CONSIDERED == 3
    assert config.STATS_PATENT_SAMPLE == 5000
    assert config.SPACY_MODEL == "en_core_web_sm"
    assert config.CHROMA_DISTANCE == "cosine"
    assert config.ENRICH_WORKERS == 8
    assert config.ENRICH_MAX_PLANTS == 8
    assert config.TITLE_MAX_CHARS == 200
    assert config.ABSTRACT_MAX_CHARS == 500
    assert config.PATENT_TEXT_MAX_CHARS == 1500


def test_jurisdiction_defaults_preserve_us():
    # Tier 3: bundled sources are US; defaults must keep prior behaviour.
    assert config.DEFAULT_PATENT_COUNTRY == "US"
    assert config.DEFAULT_JURISDICTION == "US"
