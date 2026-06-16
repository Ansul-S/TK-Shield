# docs/build_project_report.py
#
# Renders docs/PROJECT_REPORT.md (the source of truth) to a polished PDF.
# Keyless, dependency-light: uses only reportlab (already a project dep) and a
# small Markdown-subset renderer. The Markdown file keeps full fidelity (emoji,
# box-art, arrows) for GitHub; this builder sanitizes those to clean ASCII so the
# PDF renders correctly with the standard PDF fonts (no font embedding needed).
#
# Run:  PYTHONPATH=. venv/bin/python docs/build_project_report.py
# Out:  docs/TK-Shield-Project-Report.pdf

import re
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    HRFlowable, ListFlowable, ListItem, Paragraph, Preformatted,
    SimpleDocTemplate, Spacer, Table, TableStyle,
)

DOCS = Path(__file__).resolve().parent
SRC = DOCS / "PROJECT_REPORT.md"
OUT = DOCS / "TK-Shield-Project-Report.pdf"

INK = colors.HexColor("#1B1A18")
GREEN = colors.HexColor("#1F4D3A")
GREEN_LT = colors.HexColor("#E7EFEA")
MUTED = colors.HexColor("#6C6A66")
LINE = colors.HexColor("#D8D5CF")
CODE_BG = colors.HexColor("#F4F2ED")

# Unicode → ASCII so the standard PDF fonts (WinAnsi) render cleanly.
_MAP = {
    "→": "->", "←": "<-", "≥": ">=", "≤": "<=", "×": "x", "·": "-",
    "✓": "[ok]", "▶": ">", "▼": "v", "▲": "^",
    "─": "-", "│": "|", "┌": "+", "┐": "+", "└": "+", "┘": "+",
    "├": "+", "┤": "+", "┬": "+", "┴": "+", "┼": "+", "▏": "|",
    "🛡️": "", "⚖️": "", "📊": "", "🟢": "", "🟠": "", "🟡": "", "🔴": "",
}


def _san(text: str) -> str:
    for k, v in _MAP.items():
        text = text.replace(k, v)
    # Safety net: drop anything the standard fonts can't encode.
    return text.encode("cp1252", "replace").decode("cp1252").replace("�", "")


def _inline(text: str) -> str:
    """Markdown inline → reportlab mini-markup (escape XML, then bold/code)."""
    text = _san(text)
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"`(.+?)`", r'<font face="Courier" size="8.5">\1</font>', text)
    return text


def _styles():
    ss = getSampleStyleSheet()
    s = {}
    s["title"] = ParagraphStyle("ti", parent=ss["Title"], fontName="Helvetica-Bold",
                                fontSize=24, leading=28, textColor=INK, spaceAfter=4)
    s["sub"] = ParagraphStyle("su", parent=ss["Normal"], fontSize=11.5, leading=15,
                              textColor=GREEN, spaceAfter=2)
    s["meta"] = ParagraphStyle("me", parent=ss["Normal"], fontSize=8.5, leading=12,
                               textColor=MUTED, spaceAfter=2)
    s["h1"] = ParagraphStyle("h1", parent=ss["Heading1"], fontName="Helvetica-Bold",
                             fontSize=16, leading=20, textColor=GREEN, spaceBefore=16,
                             spaceAfter=6)
    s["h2"] = ParagraphStyle("h2", parent=ss["Heading2"], fontName="Helvetica-Bold",
                             fontSize=12.5, leading=16, textColor=INK, spaceBefore=11,
                             spaceAfter=4)
    s["h3"] = ParagraphStyle("h3", parent=ss["Heading3"], fontName="Helvetica-Bold",
                             fontSize=10.5, leading=14, textColor=INK, spaceBefore=8,
                             spaceAfter=3)
    s["body"] = ParagraphStyle("bo", parent=ss["Normal"], fontName="Helvetica",
                               fontSize=9.5, leading=14, textColor=INK, spaceAfter=6,
                               alignment=TA_LEFT)
    s["quote"] = ParagraphStyle("qu", parent=s["body"], leftIndent=12, textColor=GREEN,
                                fontName="Helvetica-Oblique", borderPadding=(2, 2, 2, 8),
                                spaceBefore=4, spaceAfter=8)
    s["li"] = ParagraphStyle("li", parent=s["body"], spaceAfter=2)
    s["code"] = ParagraphStyle("co", parent=ss["Code"], fontName="Courier", fontSize=7.6,
                               leading=9.4, textColor=INK)
    s["cell"] = ParagraphStyle("ce", parent=ss["Normal"], fontName="Helvetica",
                               fontSize=8.2, leading=11, textColor=INK)
    s["cellh"] = ParagraphStyle("ch", parent=s["cell"], fontName="Helvetica-Bold",
                                textColor=GREEN)
    return s


def _table(rows, S):
    header, body = rows[0], rows[1:]
    data = [[Paragraph(_inline(c), S["cellh"]) for c in header]]
    data += [[Paragraph(_inline(c), S["cell"]) for c in r] for r in body]
    ncols = len(header)
    width = A4[0] - 3.6 * cm
    col_w = [width / ncols] * ncols
    t = Table(data, colWidths=col_w, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), GREEN_LT),
        ("LINEBELOW", (0, 0), (-1, 0), 0.6, GREEN),
        ("GRID", (0, 0), (-1, -1), 0.3, LINE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return t


def _split_row(line):
    cells = line.strip().strip("|").split("|")
    return [c.strip() for c in cells]


def build():
    md = SRC.read_text(encoding="utf-8")
    S = _styles()
    flow = []
    lines = md.split("\n")
    i, n = 0, len(lines)
    bullets = []

    def flush_bullets():
        nonlocal bullets
        if bullets:
            flow.append(ListFlowable(
                [ListItem(Paragraph(_inline(b), S["li"]), leftIndent=12, value="•")
                 for b in bullets],
                bulletType="bullet", start="•", leftIndent=14,
            ))
            flow.append(Spacer(1, 4))
            bullets = []

    while i < n:
        line = lines[i]
        stripped = line.strip()

        # Fenced code block
        if stripped.startswith("```"):
            flush_bullets()
            i += 1
            code = []
            while i < n and not lines[i].strip().startswith("```"):
                code.append(_san(lines[i]))
                i += 1
            i += 1
            block = "\n".join(code)
            tbl = Table([[Preformatted(block, S["code"])]],
                        colWidths=[A4[0] - 3.6 * cm])
            tbl.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), CODE_BG),
                ("BOX", (0, 0), (-1, -1), 0.3, LINE),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]))
            flow.append(tbl)
            flow.append(Spacer(1, 6))
            continue

        # Table (consecutive | lines)
        if stripped.startswith("|") and "|" in stripped[1:]:
            flush_bullets()
            rows = []
            while i < n and lines[i].strip().startswith("|"):
                row = lines[i].strip()
                if not re.match(r"^\|[\s:|-]+\|?$", row):  # skip |---|---| separator
                    rows.append(_split_row(row))
                i += 1
            if rows:
                flow.append(_table(rows, S))
                flow.append(Spacer(1, 8))
            continue

        if not stripped:
            flush_bullets()
            i += 1
            continue

        if stripped.startswith("# "):
            flush_bullets()
            flow.append(Paragraph(_inline(stripped[2:]), S["h1"]))
        elif stripped.startswith("## "):
            flush_bullets()
            flow.append(Paragraph(_inline(stripped[3:]), S["h2"]))
        elif stripped.startswith("### "):
            flush_bullets()
            flow.append(Paragraph(_inline(stripped[4:]), S["h3"]))
        elif stripped.startswith(("- ", "* ")):
            bullets.append(stripped[2:])
        elif re.match(r"^\d+\.\s", stripped):
            bullets.append(re.sub(r"^\d+\.\s", "", stripped))
        elif stripped.startswith("> "):
            flush_bullets()
            flow.append(Paragraph(_inline(stripped[2:]), S["quote"]))
        elif stripped == "---":
            flush_bullets()
            flow.append(Spacer(1, 2))
            flow.append(HRFlowable(width="100%", thickness=0.5, color=LINE))
            flow.append(Spacer(1, 4))
        else:
            flush_bullets()
            flow.append(Paragraph(_inline(stripped), S["body"]))
        i += 1

    flush_bullets()

    doc = SimpleDocTemplate(
        str(OUT), pagesize=A4,
        leftMargin=1.8 * cm, rightMargin=1.8 * cm,
        topMargin=1.6 * cm, bottomMargin=1.6 * cm,
        title="TK-Shield — Full Project Report", author="Ansul Suryawanshi",
    )
    doc.build(flow, onLaterPages=_footer, onFirstPage=_footer)
    print(f"✅ Wrote {OUT}  ({OUT.stat().st_size // 1024} KB)")


def _footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(MUTED)
    canvas.drawString(1.8 * cm, 1.0 * cm, "TK-Shield — Full Project Report")
    canvas.drawRightString(A4[0] - 1.8 * cm, 1.0 * cm, f"{doc.page}")
    canvas.restoreState()


if __name__ == "__main__":
    build()
