# tests/test_claim_parser.py — deterministic claim splitting for the examiner
# claim-level novelty check (Tier 2). Pure-function tests, no network/LLM.

from src.rag.claim_parser import split_claims

_PATENT = """A composition comprising neem oil for agricultural use.

What is claimed is:
1. A method of controlling fungi on a plant comprising applying a hydrophobic
   extracted neem oil to the plant in a fungicidally effective amount.
2. The method of claim 1, wherein the neem oil is storage stable.
3. A composition as in claim 1 further comprising an agriculturally acceptable
   emulsifier.
"""


def test_splits_numbered_claims():
    claims = split_claims(_PATENT)
    assert [c["number"] for c in claims] == [1, 2, 3]


def test_strips_preamble_before_claims_marker():
    # The abstract sentence before "What is claimed is:" must not become a claim.
    claims = split_claims(_PATENT)
    assert "composition comprising neem oil for agricultural use" not in claims[0]["text"]
    assert claims[0]["text"].startswith("A method of controlling fungi")


def test_detects_dependent_claims_and_target():
    claims = split_claims(_PATENT)
    by_num = {c["number"]: c for c in claims}
    assert by_num[1]["is_dependent"] is False
    assert by_num[1]["depends_on"] is None
    assert by_num[2]["is_dependent"] is True
    assert by_num[2]["depends_on"] == 1
    assert by_num[3]["is_dependent"] is True
    assert by_num[3]["depends_on"] == 1


def test_no_claim_structure_returns_empty():
    # An abstract with no numbered claims → [] so the caller falls back to the
    # whole-text path.
    abstract = ("A method of promoting healing of a wound by administering "
                "turmeric to a patient afflicted with the wound.")
    assert split_claims(abstract) == []


def test_empty_input_returns_empty():
    assert split_claims("") == []
    assert split_claims("   \n  ") == []


def test_paren_numbering_and_no_marker():
    # Claims can use "1)" and appear without an explicit "what is claimed" marker.
    text = ("1) A formulation of curcumin for topical wound treatment.\n"
            "2) The formulation of claim 1 in a gel base.\n")
    claims = split_claims(text)
    assert [c["number"] for c in claims] == [1, 2]
    assert claims[1]["depends_on"] == 1
