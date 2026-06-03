# Tests for the TK domain classifier.

from src.classifier.domain import infer_domain


def test_keyword_domains():
    assert infer_domain("turmeric paste for wound healing") == "medicinal"
    assert infer_domain("herbal hair oil for shine and fragrance") == "cosmetic"
    assert infer_domain("traditional spice and beverage tea") == "food"


def test_ipc_prefix_takes_precedence():
    # Agricultural IPC overrides medicinal-looking text.
    assert infer_domain("treatment of crops", "A01H5/00") == "agricultural"
    assert infer_domain("anything", "A23L33/00") == "food"


def test_default_is_medicinal():
    assert infer_domain("") == "medicinal"
    assert infer_domain("nondescript text with no signal") == "medicinal"
