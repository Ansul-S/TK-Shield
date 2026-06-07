# Credibility regression for the landmark evaluation. Unlike the rest of the
# suite (network-free, data-free), this needs the real ~16k-patent corpus +
# ChromaDB present, so it skips cleanly when the data hasn't been built.

import pytest

from src.utils.config import config

pytestmark = pytest.mark.skipif(
    not config.PATENTS_CSV.exists(),
    reason="patent corpus not built (run the ingestion pipeline) — eval test skipped",
)


@pytest.fixture(scope="module")
def report():
    from src.evaluation.landmark_eval import evaluate
    return evaluate()


def test_all_landmark_cases_flagged_high_risk(report):
    # The defensive claim: every historically-revoked patent is scored HIGH+.
    assert report["summary"]["flagged_high_or_critical"] == 1.0
    for r in report["results"]:
        assert r["risk_level"] in ("HIGH", "CRITICAL"), r["case"]


def test_all_landmark_patents_retrieved_in_top_k(report):
    # Each known biopiracy patent is retrieved (rank is not None) within top-k.
    for r in report["results"]:
        assert r["rank"] is not None, f"{r['expected_patent']} not retrieved"
        assert r["top5"], f"{r['expected_patent']} ranked #{r['rank']} (> 5)"


def test_retrieval_quality_thresholds(report):
    s = report["summary"]
    assert s["precision_at_5"] == 1.0          # all three in top 5
    assert s["precision_at_1"] >= 0.6          # at least 2/3 as the closest match
    assert s["mrr"] >= 0.8


def test_benign_controls_are_not_false_positives(report):
    # Specificity: benign control practices must not be flagged HIGH/CRITICAL,
    # nor match a landmark patent. Guards against the risk-model inflation (H1).
    assert report["summary"]["control_false_positive_rate"] == 0.0
    for c in report["controls"]:
        assert not c["flagged"], c["practice_name"]
        assert not c["matched_landmark"], c["practice_name"]
