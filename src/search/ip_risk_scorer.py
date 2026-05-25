# src/classifier/ip_risk_scorer.py

from datetime import datetime


# ── Known high-risk patent classification codes ──────────────
# These IPC codes are categories where bio-piracy most commonly occurs
HIGH_RISK_IPC_CODES = {
    "A61K36",  # Medicinal plants
    "A61K31",  # Organic chemistry medicines (often derived from plants)
    "A01H5",   # Plant varieties
    "C12N15",  # Genetic engineering / gene sequences
    "A23L33",  # Nutritional additives (food TK)
    "A61P31",  # Antiinfectives — common bio-piracy target
}

# ── Known corporate assignees with bio-piracy history ────────
HIGH_RISK_ASSIGNEES = {
    "w.r. grace", "ricetec", "unilever", "monsanto", "bayer",
    "syngenta", "dupont", "dow agrosciences", "pfizer",
    "glaxosmithkline", "novartis", "roche"
}


def calc_similarity_risk(search_results: list) -> int:
    """
    Factor 1: How similar are the top patents to our TK entry?
    Max 40 points

    Logic:
    - If top result similarity > 0.85 → very high risk (35-40 pts)
    - If top result similarity > 0.70 → high risk (25-34 pts)
    - If top result similarity > 0.50 → medium risk (15-24 pts)
    - If top result similarity > 0.30 → low risk (5-14 pts)
    - Below 0.30 → minimal risk (0-4 pts)
    """
    if not search_results:
        return 0

    top_score = search_results[0].get("similarity_score", 0)

    if top_score >= 0.85:
        return 40
    elif top_score >= 0.70:
        return int(25 + (top_score - 0.70) / 0.15 * 10)
    elif top_score >= 0.50:
        return int(15 + (top_score - 0.50) / 0.20 * 10)
    elif top_score >= 0.30:
        return int(5 + (top_score - 0.30) / 0.20 * 10)
    else:
        return int(top_score / 0.30 * 5)


def calc_temporal_risk(tk_entry: dict, search_results: list) -> int:
    """
    Factor 2: Was the patent filed AFTER the TK was documented?
    Max 20 points

    Why this matters:
    If TK was documented in 1800s and patent was filed in 1994,
    the patent has no novelty — it's stealing existing knowledge.

    If TK was documented AFTER the patent, the TK community
    documented it defensively (less risk from this factor).
    """
    if not search_results:
        return 0

    tk_date_str = tk_entry.get("documentation_date", "")
    if not tk_date_str:
        # Unknown TK date — assume risk
        return 10

    try:
        tk_date = datetime.strptime(tk_date_str, "%Y-%m-%d")
    except ValueError:
        return 10

    risk_points = 0

    for result in search_results[:3]:  # Check top 3 patents
        patent_date_str = result.get("metadata", {}).get("filing_date", "")
        if not patent_date_str:
            continue

        try:
            patent_date = datetime.strptime(patent_date_str, "%Y-%m-%d")
        except ValueError:
            continue

        # Patent filed AFTER TK was documented = prior art exists = risk
        if patent_date > tk_date:
            years_gap = (patent_date - tk_date).days / 365
            if years_gap > 50:
                risk_points = max(risk_points, 20)  # TK very old, patent new
            elif years_gap > 10:
                risk_points = max(risk_points, 15)
            else:
                risk_points = max(risk_points, 8)

    return risk_points


def calc_geographic_risk(tk_entry: dict, search_results: list) -> int:
    """
    Factor 3: Does the patent country differ from TK origin country?
    Max 15 points

    Bio-piracy pattern: TK from India, patent filed in US/EP
    If TK and patent are from the same country → lower risk
    If patent is from a different country → higher risk
    """
    if not search_results:
        return 0

    tk_country = tk_entry.get("country", "").upper()
    if not tk_country:
        return 8  # Unknown — assume moderate risk

    foreign_patents = 0
    total_checked = 0

    for result in search_results[:3]:
        patent_country = result.get("metadata", {}).get("country", "").upper()
        if patent_country:
            total_checked += 1
            if patent_country != tk_country:
                foreign_patents += 1

    if total_checked == 0:
        return 8

    foreign_ratio = foreign_patents / total_checked

    if foreign_ratio >= 1.0:
        return 15   # All patents from different country
    elif foreign_ratio >= 0.5:
        return 10
    else:
        return 5


def calc_assignee_risk(search_results: list) -> int:
    """
    Factor 4: Who owns the patent?
    Max 15 points

    Corporate assignees = higher risk (profit motive)
    Known bad actors = highest risk
    Academic/university = lower risk
    Individual = lowest risk
    """
    if not search_results:
        return 0

    max_risk = 0

    for result in search_results[:3]:
        assignee = result.get("metadata", {}).get("assignee", "").lower()

        if any(bad in assignee for bad in HIGH_RISK_ASSIGNEES):
            max_risk = max(max_risk, 15)  # Known bio-piracy company
        elif any(corp in assignee for corp in ["inc", "corp", "ltd", "co.", "llc", "gmbh"]):
            max_risk = max(max_risk, 10)  # Generic corporation
        elif any(acad in assignee for acad in ["university", "institute", "college"]):
            max_risk = max(max_risk, 5)   # Academic — lower risk
        else:
            max_risk = max(max_risk, 7)   # Unknown — moderate risk

    return max_risk


def calc_ipc_risk(search_results: list) -> int:
    """
    Factor 5: Is the patent in a high-risk category?
    Max 10 points

    IPC codes are international patent classification codes
    Certain categories have historically been used for bio-piracy
    """
    if not search_results:
        return 0

    for result in search_results[:3]:
        ipc = result.get("metadata", {}).get("ipc_code", "")
        if not ipc:
            continue

        # Check if IPC code starts with any high-risk prefix
        for risk_code in HIGH_RISK_IPC_CODES:
            if ipc.startswith(risk_code):
                return 10

    return 3  # Default low risk if no IPC data


def get_recommendation(risk_level: str) -> list:
    """
    Generate actionable recommendations based on risk level
    """
    recommendations = {
        "CRITICAL": [
            "File an opposition immediately with the relevant patent office",
            "Submit evidence of prior art to USPTO/EPO/WIPO",
            "Contact WIPO IGC for emergency TK protection measures",
            "Engage a patent attorney specializing in bio-piracy cases",
            "Notify the originating indigenous community immediately"
        ],
        "HIGH": [
            "File a defensive publication in WIPO PATENTSCOPE",
            "Submit TK entry to Traditional Knowledge Digital Library (TKDL)",
            "Monitor patent status closely for grant decisions",
            "Contact WIPO IGC for formal TK protection registration",
            "Document community use with timestamps and witnesses"
        ],
        "MEDIUM": [
            "Register TK formally in TKDL as a precautionary measure",
            "Set up patent monitoring alerts for related IPC codes",
            "Document TK with dates, community names, and geographic origin",
            "Consult with an IP lawyer about defensive documentation"
        ],
        "LOW": [
            "Document TK entry with formal timestamps",
            "Monitor USPTO Class 514 for similar future applications",
            "Consider registering in CBD Access and Benefit Sharing database"
        ],
        "MINIMAL": [
            "TK appears safe currently — continue routine monitoring",
            "Maintain documentation for future reference"
        ]
    }
    return recommendations.get(risk_level, [])


def score_risk(tk_entry: dict, search_results: list) -> dict:
    """
    Master function — runs all 5 factors and returns complete risk assessment
    This is what TK-Shield calls after every search
    """
    factors = {
        "similarity_score": calc_similarity_risk(search_results),
        "temporal_risk":    calc_temporal_risk(tk_entry, search_results),
        "geographic_risk":  calc_geographic_risk(tk_entry, search_results),
        "assignee_risk":    calc_assignee_risk(search_results),
        "ipc_risk":         calc_ipc_risk(search_results)
    }

    total_score = sum(factors.values())

    # Determine risk level
    if total_score >= 80:
        risk_level = "CRITICAL"
    elif total_score >= 60:
        risk_level = "HIGH"
    elif total_score >= 40:
        risk_level = "MEDIUM"
    elif total_score >= 20:
        risk_level = "LOW"
    else:
        risk_level = "MINIMAL"

    return {
        "total_score": total_score,
        "max_possible": 100,
        "risk_level": risk_level,
        "factors": factors,
        "recommendations": get_recommendation(risk_level)
    }


# ── Quick test ──────────────────────────────────────────────
if __name__ == "__main__":

    # Simulate the real turmeric bio-piracy case
    turmeric_tk = {
        "tk_id": "TK-IND-0001",
        "practice_name": "Turmeric for wound healing",
        "community": "Traditional Ayurvedic communities",
        "country": "IN",
        "documentation_date": "1950-01-01",  # Ancient knowledge, documented 1950
        "category": "Medicinal"
    }

    # These are the search results our hybrid search returned
    turmeric_patents = [
        {
            "metadata": {
                "patent_id": "US5401504A",
                "title": "Use of turmeric in wound healing",
                "assignee": "University of Mississippi",
                "filing_date": "1993-01-04",
                "country": "US",
                "status": "REVOKED",
                "ipc_code": "A61K36/906"
            },
            "similarity_score": 0.88
        }
    ]

    # Simulate the neem bio-piracy case
    neem_tk = {
        "tk_id": "TK-IND-0002",
        "practice_name": "Neem as antifungal agent",
        "community": "Indian farming communities",
        "country": "IN",
        "documentation_date": "1960-06-01",
        "category": "Agricultural"
    }

    neem_patents = [
        {
            "metadata": {
                "patent_id": "EP0436257B1",
                "title": "Neem oil antifungal agent",
                "assignee": "W.R. Grace & Co.",
                "filing_date": "1990-06-12",
                "country": "EP",
                "status": "CANCELLED",
                "ipc_code": "A01H5/00"
            },
            "similarity_score": 0.70
        }
    ]

    test_cases = [
        ("TURMERIC CASE", turmeric_tk, turmeric_patents),
        ("NEEM CASE",     neem_tk,     neem_patents),
    ]

    print("=" * 60)
    print("TK-SHIELD — IP RISK CLASSIFIER TEST")
    print("=" * 60)

    for case_name, tk_entry, patents in test_cases:
        result = score_risk(tk_entry, patents)

        print(f"\n{'='*60}")
        print(f"CASE: {case_name}")
        print(f"{'='*60}")
        print(f"  Risk Level    : {result['risk_level']}")
        print(f"  Total Score   : {result['total_score']} / {result['max_possible']}")
        print(f"\n  Score Breakdown:")
        for factor, score in result["factors"].items():
            bar = "█" * score
            print(f"    {factor:<20} {score:>3} pts  {bar}")
        print(f"\n  Recommendations:")
        for rec in result["recommendations"]:
            print(f"    → {rec}")