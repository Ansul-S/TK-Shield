# src/classifier/ip_risk_scorer.py
#
# Interpretable 5-factor bio-piracy risk score (0–100). Design principles:
#   * Weights, band thresholds, the relevance gate and the high-risk
#     IPC/assignee lists all come from `config` (tunable, not hardcoded).
#   * The four "aggravating" factors (temporal, geographic, assignee, IPC) only
#     apply when there is a CREDIBLE candidate patent — i.e. top similarity ≥
#     `config.RISK_RELEVANCE_GATE`. Below the gate, risk reflects similarity
#     alone, so a benign practice that only weakly matches the corpus is not
#     inflated by structural traits (foreign filing, post-dating, corporate
#     assignee) that are meaningless without a real match.
#   * Missing data is NOT treated as risk: an unknown date/country/assignee/IPC
#     contributes 0, not a "assume risk" default. We score evidence, not gaps.

import re

from src.utils.config import config
from src.utils.dates import parse_date

# Word-boundary patterns so "inc" doesn't match "Cincinnati" etc.
_CORP_RE = re.compile(
    r"\b(inc|inc\.|incorporated|corp|corporation|co\.|company|ltd|ltd\.|llc|l\.l\.c\.|gmbh|s\.a\.|plc)\b"
)
_ACADEMIC_RE = re.compile(r"\b(universit|institut|college|polytechnic|académie|academy)")


def _round(intensity: float, weight: int) -> int:
    """Scale a 0..1 intensity to an integer point value capped at `weight`."""
    return int(round(max(0.0, min(1.0, intensity)) * weight))


def calc_similarity_risk(search_results: list) -> int:
    """Factor 1 — how close is the nearest patent? (cap: RISK_WEIGHT_SIMILARITY)

    Continuous, monotonic curve (no discontinuity at 0.85):
      sim ≥ 0.85 → full;  0.70–0.85 → high;  0.50–0.70 → medium;
      0.30–0.50 → low;    < 0.30 → minimal.
    """
    if not search_results:
        return 0
    s = search_results[0].get("similarity_score", 0) or 0
    if s >= 0.85:
        inten = 1.0
    elif s >= 0.70:
        inten = 0.625 + (s - 0.70) / 0.15 * 0.375
    elif s >= 0.50:
        inten = 0.375 + (s - 0.50) / 0.20 * 0.25
    elif s >= 0.30:
        inten = 0.125 + (s - 0.30) / 0.20 * 0.25
    else:
        inten = (s / 0.30) * 0.125 if s > 0 else 0.0
    return _round(inten, config.RISK_WEIGHT_SIMILARITY)


def calc_temporal_risk(tk_entry: dict, search_results: list) -> int:
    """Factor 2 — was a candidate patent filed AFTER the TK was documented?
    (cap: RISK_WEIGHT_TEMPORAL). Dates are parsed tolerantly (YYYY, YYYY-MM,
    YYYY-MM-DD, ISO timestamps); an unknown/unparseable TK date → 0 (no
    assumption)."""
    if not search_results:
        return 0
    tk_date = parse_date(tk_entry.get("documentation_date"))
    if tk_date is None:
        return 0

    inten = 0.0
    for result in search_results[:config.RISK_TOP_N_CONSIDERED]:
        patent_date = parse_date(result.get("metadata", {}).get("filing_date"))
        if patent_date is None:
            continue
        if patent_date > tk_date:
            years_gap = (patent_date - tk_date).days / 365
            if years_gap > 50:
                inten = max(inten, 1.0)
            elif years_gap > 10:
                inten = max(inten, 0.75)
            else:
                inten = max(inten, 0.4)
    return _round(inten, config.RISK_WEIGHT_TEMPORAL)


def calc_geographic_risk(tk_entry: dict, search_results: list) -> int:
    """Factor 3 — are candidate patents filed in a country other than the TK
    origin? (cap: RISK_WEIGHT_GEOGRAPHIC). Unknown origin → 0."""
    if not search_results:
        return 0
    tk_country = (tk_entry.get("country") or "").upper()
    if not tk_country:
        return 0

    foreign = total = 0
    for result in search_results[:config.RISK_TOP_N_CONSIDERED]:
        patent_country = (result.get("metadata", {}).get("country") or "").upper()
        if patent_country:
            total += 1
            if patent_country != tk_country:
                foreign += 1
    if total == 0:
        return 0

    ratio = foreign / total
    if ratio >= 1.0:
        inten = 1.0
    elif ratio >= 0.5:
        inten = 0.667
    elif ratio > 0:
        inten = 0.333
    else:
        inten = 0.0  # all patents share the TK origin country → no signal
    return _round(inten, config.RISK_WEIGHT_GEOGRAPHIC)


def calc_assignee_risk(search_results: list) -> int:
    """Factor 4 — who owns the candidate patents? (cap: RISK_WEIGHT_ASSIGNEE).
    Known bio-piracy actor > generic corporation > academic > individual/unknown.
    Unknown/individual contributes 0 (no profit-motive evidence)."""
    if not search_results:
        return 0
    inten = 0.0
    for result in search_results[:config.RISK_TOP_N_CONSIDERED]:
        assignee = (result.get("metadata", {}).get("assignee") or "").lower().strip()
        if not assignee or assignee == "unknown":
            continue
        if any(bad in assignee for bad in config.HIGH_RISK_ASSIGNEES):
            inten = max(inten, 1.0)
        elif _CORP_RE.search(assignee):
            inten = max(inten, 0.667)
        elif _ACADEMIC_RE.search(assignee):
            inten = max(inten, 0.267)
        # else: a named individual / unclassified entity → no added risk
    return _round(inten, config.RISK_WEIGHT_ASSIGNEE)


def calc_ipc_risk(search_results: list) -> int:
    """Factor 5 — is a candidate patent in a historically bio-piracy-prone IPC
    class? (cap: RISK_WEIGHT_IPC). No match / no data → 0."""
    if not search_results:
        return 0
    for result in search_results[:config.RISK_TOP_N_CONSIDERED]:
        ipc = (result.get("metadata", {}).get("ipc_code") or "").strip()
        if not ipc:
            continue
        if any(ipc.startswith(code) for code in config.HIGH_RISK_IPC_CODES):
            return config.RISK_WEIGHT_IPC
    return 0


def get_recommendation(risk_level: str) -> list:
    """Actionable, channel-specific recommendations per risk band."""
    recommendations = {
        "CRITICAL": [
            "File an opposition immediately with the relevant patent office",
            "Submit evidence of prior art to USPTO/EPO/WIPO",
            "Contact WIPO IGC for emergency TK protection measures",
            "Engage a patent attorney specializing in bio-piracy cases",
            "Notify the originating indigenous community immediately",
        ],
        "HIGH": [
            "File a defensive publication in WIPO PATENTSCOPE",
            "Submit TK entry to Traditional Knowledge Digital Library (TKDL)",
            "Monitor patent status closely for grant decisions",
            "Contact WIPO IGC for formal TK protection registration",
            "Document community use with timestamps and witnesses",
        ],
        "MEDIUM": [
            "Register TK formally in TKDL as a precautionary measure",
            "Set up patent monitoring alerts for related IPC codes",
            "Document TK with dates, community names, and geographic origin",
            "Consult with an IP lawyer about defensive documentation",
        ],
        "LOW": [
            "Document TK entry with formal timestamps",
            "Monitor USPTO Class 514 for similar future applications",
            "Consider registering in CBD Access and Benefit Sharing database",
        ],
        "MINIMAL": [
            "TK appears safe currently — continue routine monitoring",
            "Maintain documentation for future reference",
        ],
    }
    return recommendations.get(risk_level, [])


def _band(total_score: int) -> str:
    if total_score >= config.RISK_BAND_CRITICAL:
        return "CRITICAL"
    if total_score >= config.RISK_BAND_HIGH:
        return "HIGH"
    if total_score >= config.RISK_BAND_MEDIUM:
        return "MEDIUM"
    if total_score >= config.RISK_BAND_LOW:
        return "LOW"
    return "MINIMAL"


def score_risk(tk_entry: dict, search_results: list) -> dict:
    """
    Run all 5 factors and return the complete risk assessment.

    The four aggravating factors are gated on a credible match: if the top
    similarity is below `config.RISK_RELEVANCE_GATE`, they are zeroed and risk
    reflects similarity alone (see module docstring).
    """
    factors = {
        "similarity_score": calc_similarity_risk(search_results),
        "temporal_risk":    calc_temporal_risk(tk_entry, search_results),
        "geographic_risk":  calc_geographic_risk(tk_entry, search_results),
        "assignee_risk":    calc_assignee_risk(search_results),
        "ipc_risk":         calc_ipc_risk(search_results),
    }

    top_sim = (search_results[0].get("similarity_score", 0) or 0) if search_results else 0
    gated = top_sim < config.RISK_RELEVANCE_GATE
    if gated:
        for k in ("temporal_risk", "geographic_risk", "assignee_risk", "ipc_risk"):
            factors[k] = 0

    total_score = sum(factors.values())
    risk_level = _band(total_score)

    return {
        "total_score": total_score,
        "max_possible": 100,
        "risk_level": risk_level,
        "factors": factors,
        # Transparency: surface that aggravating factors were withheld because no
        # credible candidate patent was found (helps explain a low score).
        "relevance_gated": gated,
        "recommendations": get_recommendation(risk_level),
    }


# ── Quick smoke test ─────────────────────────────────────────
if __name__ == "__main__":
    turmeric_tk = {"practice_name": "Turmeric for wound healing", "country": "IN",
                   "documentation_date": "1950-01-01"}
    turmeric_hit = [{"metadata": {"patent_id": "US5401504A", "assignee": "University of Mississippi",
                                  "filing_date": "1993-01-04", "country": "US",
                                  "ipc_code": "A61K36/906"}, "similarity_score": 0.88}]
    benign = [{"metadata": {"patent_id": "US9999999", "assignee": "Acme Inc.",
                            "filing_date": "2015-01-01", "country": "US",
                            "ipc_code": "G06F"}, "similarity_score": 0.49}]
    for name, tk, hits in [("TURMERIC", turmeric_tk, turmeric_hit),
                           ("BENIGN(IN, weak match)", {"country": "IN"}, benign)]:
        r = score_risk(tk, hits)
        print(f"{name}: {r['risk_level']} {r['total_score']}/100 "
              f"gated={r['relevance_gated']} factors={r['factors']}")
