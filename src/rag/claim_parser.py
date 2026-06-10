# src/rag/claim_parser.py
#
# Deterministic, keyless parser that splits a pasted patent into its individual
# claims so the examiner novelty check can assess them the way a real examiner
# does — claim by claim (anticipation under 35 U.S.C. §102 / EPC Art. 54) —
# rather than scoring the whole text as one blob.
#
# No LLM and no network: patent claims have a regular surface structure
# (a "what is claimed" preamble followed by numbered claims; dependent claims
# back-reference an earlier claim number). When no numbered structure is found
# (e.g. only an abstract was pasted), split_claims returns [] and the caller
# falls back to whole-text assessment — offline-first, graceful degradation.

import re

# Marker that introduces the claims section in US/EP patents. We drop everything
# before it so an abstract/description preamble isn't mistaken for claim 1.
_CLAIMS_MARKER_RE = re.compile(
    r"(?:^|\n)\s*(?:what\s+is\s+claimed(?:\s+is)?|we\s+claim|i\s+claim|claims?)\s*[:\.]",
    re.IGNORECASE,
)

# A numbered claim starts a line with "<n>." or "<n>)" (optionally indented).
# Multiline so ^ matches each line start.
_CLAIM_NUM_RE = re.compile(r"(?m)^[ \t]*(\d{1,3})[.)]\s+")

# Dependent-claim back-reference, e.g. "The method of claim 1", "as in claims 2
# or 3". We capture the FIRST referenced number as depends_on.
_DEPENDS_RE = re.compile(r"\bclaims?\s+(\d{1,3})", re.IGNORECASE)


def _strip_preamble(text: str) -> str:
    """Return the text from the claims marker onward, if a marker exists."""
    m = _CLAIMS_MARKER_RE.search(text)
    return text[m.end():] if m else text


def split_claims(patent_text: str) -> list[dict]:
    """
    Split `patent_text` into individual claims.

    Returns a list of dicts: {number, text, is_dependent, depends_on}. Returns
    an empty list when no numbered-claim structure is present (the caller then
    treats the input as a single block — preserving the prior whole-text
    behavior). `number` is the claim's own number; `depends_on` is the
    referenced claim number for a dependent claim, else None.
    """
    if not patent_text or not patent_text.strip():
        return []

    body = _strip_preamble(patent_text)

    # Find every numbered-claim marker; the claim text runs until the next one.
    markers = list(_CLAIM_NUM_RE.finditer(body))
    if not markers:
        return []

    claims: list[dict] = []
    for i, m in enumerate(markers):
        number = int(m.group(1))
        start = m.end()
        end = markers[i + 1].start() if i + 1 < len(markers) else len(body)
        claim_text = body[start:end].strip()
        if not claim_text:
            continue
        dep = _DEPENDS_RE.search(claim_text)
        # A claim is dependent if it back-references another (earlier) claim
        # number that isn't itself.
        depends_on = None
        if dep:
            ref = int(dep.group(1))
            if ref != number:
                depends_on = ref
        claims.append({
            "number": number,
            "text": claim_text,
            "is_dependent": depends_on is not None,
            "depends_on": depends_on,
        })

    return claims


if __name__ == "__main__":
    sample = (
        "A composition comprising neem oil.\n\n"
        "What is claimed is:\n"
        "1. A method of controlling fungi on a plant comprising applying a "
        "hydrophobic extracted neem oil to the plant.\n"
        "2. The method of claim 1, wherein the neem oil is storage stable.\n"
        "3. A composition as in claim 1 further comprising an emulsifier.\n"
    )
    for c in split_claims(sample):
        kind = f"dependent→{c['depends_on']}" if c["is_dependent"] else "independent"
        print(f"Claim {c['number']} ({kind}): {c['text'][:60]}…")
