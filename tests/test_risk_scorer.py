# Tests for the 5-factor bio-piracy risk scorer — no network, no models.

from src.classifier.ip_risk_scorer import score_risk


def _patent(sim, **meta):
    base = {
        "patent_id": "US0000000A", "assignee": "Unknown", "filing_date": "1990-01-01",
        "country": "US", "ipc_code": "A61K36/906",
    }
    base.update(meta)
    return {"metadata": base, "similarity_score": sim}


def test_empty_results_is_minimal():
    r = score_risk({"country": "IN"}, [])
    assert r["total_score"] == 0
    assert r["risk_level"] == "MINIMAL"


def test_classic_turmeric_pattern_is_high_or_critical():
    # High similarity, foreign corporate patent filed long after TK documented.
    tk = {"country": "IN", "documentation_date": "1900-01-01"}
    patents = [_patent(0.9, assignee="W.R. Grace & Co.", filing_date="1994-01-01", country="US")]
    r = score_risk(tk, patents)
    assert r["risk_level"] in ("HIGH", "CRITICAL")
    assert r["factors"]["similarity_score"] == 40
    assert r["factors"]["geographic_risk"] == 15   # US patent vs IN origin
    assert r["factors"]["assignee_risk"] == 15     # known bad actor
    assert r["recommendations"]                    # non-empty


def test_low_similarity_same_country_is_lower_risk():
    tk = {"country": "US", "documentation_date": "2020-01-01"}
    patents = [_patent(0.2, assignee="Some University", filing_date="2019-01-01", country="US")]
    r = score_risk(tk, patents)
    assert r["risk_level"] in ("MINIMAL", "LOW")


def test_score_never_exceeds_max():
    tk = {"country": "IN", "documentation_date": "1800-01-01"}
    patents = [_patent(0.99, assignee="Monsanto", filing_date="1999-01-01", country="US")]
    r = score_risk(tk, patents)
    assert 0 <= r["total_score"] <= r["max_possible"] == 100


def test_relevance_gate_blocks_weak_match_specificity():
    # A benign India-origin practice that only weakly matches the corpus must NOT
    # be inflated to MEDIUM/HIGH by the structural factors (geographic, assignee,
    # IPC). Below the relevance gate, only the similarity factor applies. (H1)
    tk = {"country": "IN", "documentation_date": "2020-01-01"}
    weak = [_patent(0.49, assignee="Acme Inc.", filing_date="2015-01-01",
                    country="US", ipc_code="A61K36/906")]
    r = score_risk(tk, weak)
    assert r["relevance_gated"] is True
    assert r["factors"]["geographic_risk"] == 0
    assert r["factors"]["assignee_risk"] == 0
    assert r["factors"]["ipc_risk"] == 0
    assert r["risk_level"] in ("MINIMAL", "LOW")


def test_missing_data_is_not_treated_as_risk():
    # Unknown date/country/assignee/IPC must contribute 0, not an "assume risk"
    # default — even on a strong match. (H1)
    tk = {"country": "", "documentation_date": ""}
    hit = [_patent(0.9, assignee="", filing_date="", country="", ipc_code="")]
    r = score_risk(tk, hit)
    assert r["factors"]["temporal_risk"] == 0
    assert r["factors"]["geographic_risk"] == 0
    assert r["factors"]["assignee_risk"] == 0
    assert r["factors"]["ipc_risk"] == 0
    # Only the (strong) similarity factor remains.
    assert r["factors"]["similarity_score"] == 40


def test_assignee_word_boundary_avoids_false_corp_match():
    # "Cincinnati" contains "inc" but is not a corporation marker. (L3)
    tk = {"country": "IN", "documentation_date": "1990-01-01"}
    hit = [_patent(0.9, assignee="City of Cincinnati", filing_date="1999-01-01", country="US")]
    assert score_risk(tk, hit)["factors"]["assignee_risk"] == 0
