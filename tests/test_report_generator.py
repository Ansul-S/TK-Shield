# Tests for report assembly — verifies both the LLM branch and the offline
# deterministic fallback, without needing a running Ollama / model.

from src.rag import report_generator


def _context(risk_level="HIGH"):
    return {
        "query": "turmeric wound healing",
        "plants": ["turmeric"],
        "uses": ["wound healing"],
        "patents": [{
            "metadata": {"patent_id": "US5401504A", "title": "Use of turmeric in wound healing",
                         "assignee": "Univ of Mississippi", "filing_date": "1993-01-04",
                         "country": "US"},
            "similarity_score": 0.88,
        }],
        "risk": {
            "total_score": 71, "max_possible": 100, "risk_level": risk_level,
            "factors": {"similarity_score": 24, "temporal_risk": 15, "geographic_risk": 15,
                        "assignee_risk": 7, "ipc_risk": 10},
            "recommendations": ["File an opposition"],
        },
        "evidence": {
            "literature": [{"source": "pubmed", "ref_id": "111", "title": "Turmeric study",
                            "url": "https://pubmed.ncbi.nlm.nih.gov/111/"}],
            "taxonomy": [], "origin_countries": ["IN"], "aliases": [],
            "sources_used": ["pubmed"], "sources_skipped": ["gbif"],
        },
    }


class _FakeLLM:
    def __init__(self, available, payload=None): self._avail = available; self._payload = payload
    def is_available(self): return self._avail
    def generate_json(self, prompt, system=None):
        return self._payload or {"assessment": "LLM ASSESSMENT", "opposition_draft": "LLM OPPOSITION"}


def _entry():
    return {"tk_id": "TK-1", "practice_name": "Turmeric for wound healing",
            "community": "Ayurveda", "country": "IN", "documentation_date": "1950-01-01"}


def test_uses_llm_when_available():
    report = report_generator.generate_report(_entry(), _context(), llm=_FakeLLM(True))
    assert report["llm_used"] is True
    assert report["assessment"] == "LLM ASSESSMENT"
    assert report["opposition_draft"] == "LLM OPPOSITION"


def test_falls_back_when_llm_unavailable():
    report = report_generator.generate_report(_entry(), _context(), llm=_FakeLLM(False))
    assert report["llm_used"] is False
    assert "US5401504A" in report["assessment"]          # deterministic narrative
    assert "US5401504A" in report["opposition_draft"]


def test_coerces_non_string_llm_fields():
    # JSON-mode models sometimes return a list/dict; the report must still be
    # all strings so the renderer's "\n".join never blows up. (Regression.)
    payload = {"assessment": ["Para one.", "Para two."],
               "opposition_draft": {"basis": "prior art", "request": "revoke"}}
    report = report_generator.generate_report(_entry(), _context(), llm=_FakeLLM(True, payload))
    assert report["llm_used"] is True
    assert isinstance(report["assessment"], str) and "Para one." in report["assessment"]
    assert isinstance(report["opposition_draft"], str) and "prior art" in report["opposition_draft"]


def test_report_always_has_exact_facts_and_citations():
    report = report_generator.generate_report(_entry(), _context(), llm=_FakeLLM(False))
    assert report["risk"]["risk_level"] == "HIGH"
    assert report["top_patents"][0]["patent_id"] == "US5401504A"
    assert {"source": "pubmed", "ref_id": "111", "title": "Turmeric study",
            "url": "https://pubmed.ncbi.nlm.nih.gov/111/"} in report["citations"]
    assert report["sources_skipped"] == ["gbif"]
