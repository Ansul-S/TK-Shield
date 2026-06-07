# src/report/renderer.py
#
# Render a structured report (from rag.report_generator) into a shareable
# markdown document, and optionally a PDF. PDF uses reportlab and is best-
# effort: if reportlab is missing it raises a clear error, but markdown
# always works.

import io

_RISK_BADGE = {
    "CRITICAL": "🔴 CRITICAL",
    "HIGH": "🟠 HIGH",
    "MEDIUM": "🟡 MEDIUM",
    "LOW": "🟢 LOW",
    "MINIMAL": "⚪ MINIMAL",
}


def to_markdown(report: dict) -> str:
    """Render the report dict to a self-contained markdown document."""
    risk = report["risk"]
    tk = report["tk_entry"]
    lines = [
        f"# TK-Shield Bio-Piracy Report — {tk.get('practice_name', '')}",
        "",
        f"**Risk level:** {_RISK_BADGE.get(risk['risk_level'], risk['risk_level'])} "
        f"({risk['total_score']}/100)",
        f"**Community:** {tk.get('community', 'unknown')}  ",
        f"**Origin:** {tk.get('country', 'unknown')}  ",
        f"**Documented:** {tk.get('documentation_date', 'unknown')}",
        "",
        "## Risk factors",
        "",
        "| Factor | Score |",
        "| --- | --- |",
    ]
    lines += [f"| {k} | {v} |" for k, v in risk["factors"].items()]

    lines += ["", "## Assessment", "", report["assessment"], ""]

    lines += ["## Closest patents", ""]
    if report["top_patents"]:
        lines += ["| Patent | Title | Assignee | Filed | Sim |", "| --- | --- | --- | --- | --- |"]
        for p in report["top_patents"]:
            lines.append(
                f"| {p['patent_id']} | {p['title'][:50]} | {p['assignee']} "
                f"| {p['filing_date']} | {p['similarity']} |"
            )
    else:
        lines.append("_No candidate patents found._")

    lines += ["", "## Prior-art citations", ""]
    if report["citations"]:
        for c in report["citations"]:
            lines.append(f"- **[{c['source']}:{c['ref_id']}]** {c['title']} — {c.get('url', '')}")
    else:
        lines.append("_No external citations on record._")

    lines += ["", "## Recommendations", ""]
    lines += [f"- {r}" for r in risk.get("recommendations", [])]

    lines += ["", "## Draft opposition / defensive publication", "", report["opposition_draft"]]

    if report.get("sources_skipped"):
        lines += ["", f"> ⚠️ Sources unavailable this run: {', '.join(report['sources_skipped'])}."]
    if not report.get("llm_used"):
        lines += ["", "> ℹ️ Narrative generated offline (LLM unavailable); figures and citations are exact."]
    if report.get("unverified_citation_refs"):
        refs = ", ".join(report["unverified_citation_refs"])
        lines += [
            "",
            f"> ⚠️ The AI narrative referenced identifier(s) not in the verified citation "
            f"list ({refs}). Treat the narrative as a draft and rely on the **Prior-art "
            f"citations** section above as the authoritative evidence.",
        ]

    return "\n".join(lines)


def to_pdf(report: dict) -> bytes:
    """Render to a simple PDF (best-effort). Raises if reportlab is absent."""
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter)
    styles = getSampleStyleSheet()
    flow = []
    for raw in to_markdown(report).split("\n"):
        text = raw.strip()
        if not text:
            flow.append(Spacer(1, 6))
            continue
        style = "Heading2" if text.startswith("#") else "BodyText"
        flow.append(Paragraph(text.lstrip("# ").replace("|", " "), styles[style]))
    doc.build(flow)
    return buf.getvalue()
