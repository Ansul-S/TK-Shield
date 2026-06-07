# src/classifier/domain.py
#
# Lightweight TK domain classifier — tags an entry/patent as
# medicinal / agricultural / food / cosmetic from its text + IPC/CPC codes.
# Used to broaden coverage beyond medicinal plants (Phase C) and to power the
# researcher stats view.

from src.utils.config import config

_DOMAIN_KEYWORDS = {
    "medicinal": ["wound", "fever", "infection", "antifungal", "antibacterial",
                  "anti-inflammatory", "antiviral", "antimalarial", "remedy",
                  "treatment", "disease", "therapeutic", "medicine", "ailment",
                  "ulcer", "pain", "diabetes", "cancer", "skin", "digestive"],
    "agricultural": ["crop", "cultivar", "landrace", "seed", "variety", "pest",
                     "pesticide", "yield", "harvest", "soil", "germination", "rice",
                     "wheat", "grain", "farming", "plant variety"],
    "food": ["food", "edible", "spice", "flavor", "beverage", "nutrition",
             "dietary", "fermented", "cooking", "culinary", "preserve", "tea"],
    "cosmetic": ["cosmetic", "skincare", "hair", "fragrance", "perfume", "beauty",
                 "moisturizer", "complexion", "anti-aging", "lotion", "soap"],
}


def infer_domain(text: str, ipc_codes: str | list[str] = "") -> str:
    """
    Return the best-matching domain. IPC/CPC prefix match (config.DOMAIN_IPC_GROUPS)
    takes precedence; otherwise fall back to keyword scoring.

    DEFAULT BEHAVIOUR: when neither the IPC codes nor any keyword matches, this
    returns "medicinal" — the project's core domain and the most common case for
    TK. This is a deliberate bias, not "unknown": it means an unclassifiable
    entry is counted as medicinal in the researcher stats. If you need to
    distinguish "couldn't classify" from "is medicinal", add an explicit
    "unclassified" branch here and a corresponding domain bucket.
    """
    codes = ipc_codes if isinstance(ipc_codes, list) else [ipc_codes]
    codes = [c.upper() for c in codes if c]
    for domain, prefixes in config.DOMAIN_IPC_GROUPS.items():
        if any(any(c.startswith(p) for p in prefixes) for c in codes):
            return domain

    text_lower = (text or "").lower()
    scores = {
        domain: sum(kw in text_lower for kw in kws)
        for domain, kws in _DOMAIN_KEYWORDS.items()
    }
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "medicinal"


if __name__ == "__main__":
    print(infer_domain("turmeric paste for wound healing"))          # medicinal
    print(infer_domain("novel basmati rice cultivar", "A01H5/00"))   # agricultural
    print(infer_domain("herbal hair oil for shine"))                 # cosmetic
