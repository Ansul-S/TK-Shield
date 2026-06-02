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
