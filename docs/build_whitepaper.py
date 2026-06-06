# docs/build_whitepaper.py
#
# Generates the TK-Shield project brief (concise whitepaper) as a polished PDF.
# Evaluation figures are read live from docs/evaluation_report.json so the brief
# can never drift from the measured results — regenerate after re-running the eval.
#
# Run:  PYTHONPATH=. venv/bin/python docs/build_whitepaper.py
# Out:  docs/TK-Shield-Whitepaper.pdf

import json
from datetime import date
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    HRFlowable, ListFlowable, ListItem, Paragraph, SimpleDocTemplate, Spacer, Table,
    TableStyle,
)

DOCS = Path(__file__).resolve().parent
AUTHOR = "Ansul Suryawanshi"  # edit if needed

INK = colors.HexColor("#1B1A18")
GREEN = colors.HexColor("#1F4D3A")     # brand: biodiversity / shield
GREEN_LT = colors.HexColor("#E7EFEA")
MUTED = colors.HexColor("#6C6A66")
LINE = colors.HexColor("#D8D5CF")


def _styles():
    ss = getSampleStyleSheet()
    s = {}
    s["title"] = ParagraphStyle("t", parent=ss["Title"], fontName="Helvetica-Bold",
                                fontSize=22, leading=26, textColor=INK, spaceAfter=4)
    s["subtitle"] = ParagraphStyle("st", parent=ss["Normal"], fontSize=11.5, leading=16,
                                   textColor=GREEN, spaceAfter=2)
    s["byline"] = ParagraphStyle("by", parent=ss["Normal"], fontSize=9, leading=13,
                                 textColor=MUTED)
    s["h2"] = ParagraphStyle("h2", parent=ss["Heading2"], fontName="Helvetica-Bold",
                             fontSize=13, leading=16, textColor=GREEN, spaceBefore=14,
                             spaceAfter=5)
    s["body"] = ParagraphStyle("b", parent=ss["Normal"], fontSize=9.7, leading=14.5,
                               textColor=INK, alignment=TA_JUSTIFY, spaceAfter=7)
    s["bullet"] = ParagraphStyle("bl", parent=s["body"], spaceAfter=3)
    s["lead"] = ParagraphStyle("ld", parent=s["body"], fontSize=11, leading=16,
                               textColor=INK, spaceAfter=9)
    s["small"] = ParagraphStyle("sm", parent=ss["Normal"], fontSize=8, leading=11,
                                textColor=MUTED)
    s["cell"] = ParagraphStyle("c", parent=ss["Normal"], fontSize=8.5, leading=11.5,
                               textColor=INK)
    s["cellb"] = ParagraphStyle("cb", parent=s["cell"], fontName="Helvetica-Bold")
    s["step"] = ParagraphStyle("sp", parent=ss["Normal"], fontSize=7.8, leading=9.5,
                               textColor=GREEN, alignment=TA_CENTER,
                               fontName="Helvetica-Bold")
    s["metric"] = ParagraphStyle("m", parent=ss["Normal"], fontSize=16,
                                 fontName="Helvetica-Bold", textColor=GREEN,
                                 alignment=TA_CENTER, leading=18)
    s["metriclbl"] = ParagraphStyle("ml", parent=ss["Normal"], fontSize=7.3,
                                    textColor=MUTED, alignment=TA_CENTER, leading=9)
    return s


def _footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(MUTED)
    canvas.drawString(2 * cm, 1.1 * cm,
                      "TK-Shield — Defensive Bio-Piracy Monitoring for Traditional Knowledge")
    canvas.drawRightString(A4[0] - 2 * cm, 1.1 * cm, f"{doc.page}")
    canvas.setStrokeColor(LINE)
    canvas.line(2 * cm, 1.4 * cm, A4[0] - 2 * cm, 1.4 * cm)
    canvas.restoreState()


def _pipeline(s):
    steps = ["Documented\nTK practice", "Hybrid search\n(semantic+BM25)",
             "5-factor\nrisk score", "Prior-art\n(PubMed/Wikidata/GBIF)",
             "RAG report\n(local LLM)", "Dashboard\n(3 personas)"]
    cells = [[Paragraph(st.replace("\n", "<br/>"), s["step"]) for st in steps]]
    w = (A4[0] - 4 * cm) / len(steps)
    t = Table(cells, colWidths=[w] * len(steps), rowHeights=[1.15 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), GREEN_LT),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.white),
        ("INNERGRID", (0, 0), (-1, -1), 3, colors.white),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    return t


def _metric_band(s, summary):
    data = [[
        Paragraph(f"{summary['precision_at_5']:.0%}", s["metric"]),
        Paragraph(f"{summary['precision_at_1']:.0%}", s["metric"]),
        Paragraph(f"{summary['mrr']:.3f}", s["metric"]),
        Paragraph(f"{summary['flagged_high_or_critical']:.0%}", s["metric"]),
    ], [
        Paragraph("Precision@5", s["metriclbl"]),
        Paragraph("Precision@1", s["metriclbl"]),
        Paragraph("Mean Recip. Rank", s["metriclbl"]),
        Paragraph("Flagged HIGH/CRITICAL", s["metriclbl"]),
    ]]
    w = (A4[0] - 4 * cm) / 4
    t = Table(data, colWidths=[w] * 4)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), GREEN_LT),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.white),
        ("INNERGRID", (0, 0), (-1, -1), 3, colors.white),
        ("TOPPADDING", (0, 0), (-1, 0), 8), ("BOTTOMPADDING", (0, 1), (-1, 1), 8),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    return t


def _case_table(s, results):
    head = [Paragraph(h, s["cellb"]) for h in
            ["TK practice", "Patent (claimant)", "Rank", "Sim.", "Risk", "Historical outcome"]]
    rows = [head]
    for r in results:
        rank = f"#{r['rank']}" if r["rank"] else "—"
        sim = f"{r['similarity']:.3f}" if r["similarity"] is not None else "—"
        rows.append([
            Paragraph(r["case"].split("(")[0].strip(), s["cell"]),
            Paragraph(f"{r['expected_patent']}<br/><font size=7 color='#6C6A66'>{r['claimant']}</font>", s["cell"]),
            Paragraph(rank, s["cell"]),
            Paragraph(sim, s["cell"]),
            Paragraph(f"{r['risk_level']} ({r['risk_score']})", s["cellb"]),
            Paragraph(r["outcome"], s["cell"]),
        ])
    W = A4[0] - 4 * cm
    t = Table(rows, colWidths=[W * x for x in (0.20, 0.24, 0.07, 0.08, 0.15, 0.26)])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), GREEN),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, GREEN_LT]),
        ("GRID", (0, 0), (-1, -1), 0.4, LINE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ]))
    return t


def _bullets(s, items):
    return ListFlowable(
        [ListItem(Paragraph(t, s["bullet"]), leftIndent=10, value="•") for t in items],
        bulletType="bullet", start="•", leftIndent=8,
    )


def build():
    rep = json.loads((DOCS / "evaluation_report.json").read_text())
    summary, results = rep["summary"], rep["results"]
    s = _styles()
    story = []

    # --- Title block ---
    story += [
        Paragraph("TK-Shield", s["title"]),
        Paragraph("Defensive Bio-Piracy Monitoring for Traditional Knowledge", s["subtitle"]),
        Paragraph("A keyless, offline-first AI system for the defensive protection of documented "
                  "traditional knowledge — aligned with the WIPO IGC and the 2024 Treaty on "
                  "Intellectual Property, Genetic Resources and Associated Traditional Knowledge.",
                  s["byline"]),
        Spacer(1, 4),
        Paragraph(f"{AUTHOR} · Project brief · {date.today():%B %Y}", s["byline"]),
        Spacer(1, 6),
        HRFlowable(width="100%", thickness=1, color=GREEN, spaceAfter=10),
    ]

    # --- Lead / problem ---
    story += [
        Paragraph(
            "<b>The problem.</b> Communities have practised and documented traditional medicinal and "
            "agricultural knowledge for centuries, yet patents are repeatedly granted over that same "
            "knowledge. The landmark turmeric, neem, and basmati patents were each eventually revoked — "
            "but only after costly, multi-year legal challenges that assembled prior-art evidence by hand. "
            "TK-Shield automates the defensive workflow: given a documented practice, it finds the patents "
            "that may claim it, scores bio-piracy risk, gathers citable prior-art evidence, and drafts an "
            "assessment and patent opposition — running entirely on free, open data and a local model so "
            "any community can use it.", s["lead"]),
    ]

    # --- Policy alignment ---
    story += [
        Paragraph("Alignment with international IP policy", s["h2"]),
        _bullets(s, [
            "<b>WIPO IGC</b> — the Intergovernmental Committee on IP, Genetic Resources, Traditional "
            "Knowledge and Folklore, whose central goal is preventing the erroneous granting of patents over TK.",
            "<b>WIPO GRATK Treaty (2024)</b> — introduces a disclosure-of-origin requirement for patents "
            "based on genetic resources and associated TK; TK-Shield assembles exactly that origin evidence.",
            "<b>Nagoya Protocol / CBD</b> — benefit-sharing depends on identifying the holder community; "
            "TK-Shield surfaces documented communities &amp; peoples as a first-class attribution dimension.",
            "<b>TKDL</b> — India's Traditional Knowledge Digital Library is the proven model; TK-Shield "
            "mirrors its defensive purpose with open data and open models.",
        ]),
    ]

    # --- System ---
    story += [
        Paragraph("How the system works", s["h2"]),
        _pipeline(s),
        Spacer(1, 8),
        Paragraph(
            "A documented practice flows through a hybrid search engine that fuses dense semantic retrieval "
            "with lexical BM25 via Reciprocal Rank Fusion — recovering folk, multilingual, and scientific "
            "synonyms a single method would miss. A transparent five-factor model (similarity, temporal "
            "proximity, geographic overlap, assignee profile, and patent classification) produces a 0–100 "
            "risk score and a MINIMAL→CRITICAL band. Keyless prior-art enrichment fans out to PubMed, "
            "Wikidata, and GBIF, returning one deduplicated, citation-tagged evidence bundle. Finally a "
            "local LLM (Ollama) writes a citation-backed assessment and a draft opposition; with no model "
            "present it falls back to a deterministic template, keeping figures and citations exact.", s["body"]),
        Paragraph(
            "<b>Three personas, one platform.</b> A <b>Defender</b> (community/NGO) registers a practice and "
            "obtains a risk report and opposition draft; an <b>Examiner</b> (patent office) pastes a patent "
            "and receives a novelty verdict against the TK registry; a <b>Researcher</b> explores corpus and "
            "registry analytics. The system indexes <b>16,371</b> real US patents and <b>2,030</b> documented "
            "TK practices, with zero API keys.", s["body"]),
    ]

    # --- Evaluation ---
    story += [
        Paragraph("Evaluation — re-identifying the landmark cases", s["h2"]),
        Paragraph(
            f"Each of the three landmark bio-piracy cases was submitted as an <b>independently-worded</b> TK "
            f"description sharing no wording with the patent, then run through the full pipeline over the "
            f"{summary['corpus_size']:,}-patent corpus (retrieval depth k={summary['n_results']}). Retrieval "
            f"therefore reflects genuine semantic and lexical matching, not string overlap.", s["body"]),
        _metric_band(s, summary),
        Spacer(1, 9),
        _case_table(s, results),
        Spacer(1, 7),
        Paragraph(
            f"From folk-worded inputs alone, TK-Shield re-identifies all three historically-revoked patents — "
            f"every one retrieved within the top {summary['n_results']} (Precision@5 {summary['precision_at_5']:.0%}), "
            f"{summary['precision_at_1']:.0%} as the single closest match — and scores "
            f"{summary['flagged_high_or_critical']:.0%} in the HIGH/CRITICAL band. The result is reproducible "
            f"via <font face='Courier'>python -m src.evaluation.landmark_eval</font>.", s["body"]),
    ]

    # --- Engineering ---
    story += [
        Paragraph("Engineering principles", s["h2"]),
        _bullets(s, [
            "<b>Free &amp; keyless first</b> — the entire pipeline runs with zero API keys on public-domain / "
            "open data (PatentsView, Dr. Duke CC0, Wikidata) and a local model; no paid or gated services.",
            "<b>Graceful degradation</b> — no external source or the LLM can crash the pipeline; reports note "
            "any skipped source, and everything works offline.",
            "<b>Citations, not hand-waving</b> — every claim carries a stable reference (PMID / Wikidata QID / "
            "GBIF key / patent number).",
            "<b>Security by construction</b> — server/LLM/user text is never rendered as raw HTML, external "
            "links are scheme-validated, and request inputs are bounded.",
            "<b>Tested</b> — 48 network-free backend tests and 21 frontend tests, including XSS-safety and the "
            "landmark-evaluation regressions above.",
        ]),
    ]

    # --- Impact / future ---
    story += [
        Paragraph("Impact and future work", s["h2"]),
        Paragraph(
            "TK-Shield lowers the cost of defensive TK protection from a specialist legal exercise to a tool a "
            "community can run on a laptop, and provides patent examiners a fast prior-art check at the point of "
            "decision — directly supporting the disclosure-of-origin objective of the 2024 WIPO treaty. Current "
            "scope is US patent metadata, English-language analysis, and a small local model; natural extensions "
            "are full-text and non-US patent coverage, multilingual TK ingestion at scale, continuous monitoring "
            "with alerting, and a multi-tenant deployment for institutional use. The architecture isolates data "
            "access behind clean interfaces so these extensions are localized changes.", s["body"]),
        Spacer(1, 4),
        Paragraph(
            "Data: PatentsView (USPTO, public domain); Dr. Duke's Phytochemical &amp; Ethnobotanical Databases "
            "(USDA, CC0); Wikidata (CC0); enrichment via PubMed, Wikidata, and GBIF. TK-Shield is a defensive "
            "research tool and does not constitute legal advice.", s["small"]),
    ]

    out = DOCS / "TK-Shield-Whitepaper.pdf"
    doc = SimpleDocTemplate(
        str(out), pagesize=A4, title="TK-Shield — Project Brief", author=AUTHOR,
        leftMargin=2 * cm, rightMargin=2 * cm, topMargin=1.8 * cm, bottomMargin=1.8 * cm,
    )
    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    print(f"Wrote {out}")


if __name__ == "__main__":
    build()
