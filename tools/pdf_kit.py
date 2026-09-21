#!/usr/bin/env python3
"""Shared reportlab styling used by the project's PDF documentation scripts.

Both :mod:`generate_project_guide_pdf` and :mod:`generate_commands_pdf` build
their documents from the helpers here, so every page of every generated PDF
looks the same and the layout lives in exactly one place.

Only the documentation tooling uses reportlab; the cipher tool itself depends on
the Python standard library alone.
"""

from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    PageTemplate,
    Paragraph,
    Preformatted,
    Spacer,
    Table,
    TableStyle,
)

__all__ = [
    "ACCENT",
    "BODY",
    "BULLET",
    "CELL",
    "CELL_BOLD",
    "CELL_MONO",
    "CELL_MONO_BOLD",
    "CODE",
    "CODE_BG",
    "DISCLAIMER_BG",
    "H1",
    "H2",
    "HEADER_BG",
    "INK",
    "META",
    "MUTED",
    "NOTE",
    "OK_BG",
    "RULE",
    "SUBTITLE",
    "TITLE",
    "WARN_BG",
    "build_document",
    "bullets",
    "callout",
    "code_block",
    "esc",
    "heading",
    "paragraph",
    "table",
]

#: Usable width of an A4 page with the standard 2 cm side margins.
PAGE_WIDTH = 17.1 * cm

# --------------------------------------------------------------------------- #
# Colours
# --------------------------------------------------------------------------- #
INK = colors.HexColor("#1b2733")
ACCENT = colors.HexColor("#0b5394")
MUTED = colors.HexColor("#5b6875")
RULE = colors.HexColor("#c9d3dd")
CODE_BG = colors.HexColor("#f4f6f8")
HEADER_BG = colors.HexColor("#e8eef5")
OK_BG = colors.HexColor("#eaf6ec")
WARN_BG = colors.HexColor("#fdf3e3")
DISCLAIMER_BG = colors.HexColor("#fff4f4")

# --------------------------------------------------------------------------- #
# Styles
# --------------------------------------------------------------------------- #
_SHEET = getSampleStyleSheet()

TITLE = ParagraphStyle(
    "GuideTitle", parent=_SHEET["Title"], fontName="Helvetica-Bold",
    fontSize=21, leading=25, textColor=ACCENT, alignment=TA_CENTER, spaceAfter=2,
)
SUBTITLE = ParagraphStyle(
    "GuideSubtitle", parent=_SHEET["Normal"], fontName="Helvetica",
    fontSize=11, leading=15, textColor=MUTED, alignment=TA_CENTER,
)
META = ParagraphStyle(
    "GuideMeta", parent=_SHEET["Normal"], fontName="Helvetica",
    fontSize=9, leading=13, textColor=MUTED, alignment=TA_CENTER,
)
H1 = ParagraphStyle(
    "GuideH1", parent=_SHEET["Heading1"], fontName="Helvetica-Bold",
    fontSize=14.5, leading=18, textColor=ACCENT, spaceBefore=14, spaceAfter=5,
)
H2 = ParagraphStyle(
    "GuideH2", parent=_SHEET["Heading2"], fontName="Helvetica-Bold",
    fontSize=11.5, leading=15, textColor=INK, spaceBefore=10, spaceAfter=3,
)
BODY = ParagraphStyle(
    "GuideBody", parent=_SHEET["BodyText"], fontName="Helvetica",
    fontSize=9.5, leading=13.2, textColor=INK, alignment=TA_JUSTIFY, spaceAfter=5,
)
BULLET = ParagraphStyle(
    "GuideBullet", parent=BODY, leftIndent=12, bulletIndent=3, spaceAfter=2,
)
NOTE = ParagraphStyle(
    "GuideNote", parent=BODY, fontSize=9, textColor=MUTED, alignment=0,
)
CODE = ParagraphStyle(
    "GuideCode", parent=_SHEET["Code"], fontName="Courier", fontSize=8,
    leading=10.4, textColor=colors.HexColor("#10222e"),
)
CELL = ParagraphStyle(
    "GuideCell", parent=BODY, fontSize=8.6, leading=11.4, alignment=0, spaceAfter=0,
)
CELL_BOLD = ParagraphStyle(
    "GuideCellBold", parent=CELL, fontName="Helvetica-Bold",
)
CELL_MONO = ParagraphStyle(
    "GuideCellMono", parent=CELL, fontName="Courier", fontSize=8.1, leading=11.2,
)
CELL_MONO_BOLD = ParagraphStyle(
    "GuideCellMonoBold", parent=CELL_MONO, fontName="Courier-Bold",
)


# --------------------------------------------------------------------------- #
# Flowable helpers
# --------------------------------------------------------------------------- #
def esc(text: str) -> str:
    """Escape the characters that are special inside reportlab paragraphs."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def heading(text: str, story: list, level: int = 1) -> None:
    """Append a section heading."""
    story.append(Paragraph(esc(text), H1 if level == 1 else H2))


def paragraph(text: str, story: list, style: ParagraphStyle = BODY) -> None:
    """Append a wrapped paragraph."""
    story.append(Paragraph(esc(text), style))


def bullets(items: list[str], story: list) -> None:
    """Append a bullet list."""
    for item in items:
        story.append(Paragraph(esc(item), BULLET, bulletText="\u2022"))


def code_block(text: str, story: list) -> None:
    """Append a shaded, bordered code block."""
    block = Table(
        [[Preformatted(text, CODE)]],
        colWidths=[PAGE_WIDTH],
        style=TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), CODE_BG),
                ("BOX", (0, 0), (-1, -1), 0.5, RULE),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        ),
    )
    story.append(Spacer(1, 3))
    story.append(block)
    story.append(Spacer(1, 6))


def callout(title: str, lines: list[str], story: list, background=WARN_BG) -> None:
    """Append a shaded callout box with a bold title."""
    inner = [Paragraph(esc(title), CELL_BOLD)]
    inner.extend(Paragraph(esc(line), CELL) for line in lines)
    box = Table(
        [[inner]],
        colWidths=[PAGE_WIDTH],
        style=TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), background),
                ("BOX", (0, 0), (-1, -1), 0.6, RULE),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        ),
    )
    story.append(Spacer(1, 3))
    story.append(box)
    story.append(Spacer(1, 7))


def table(
    headers: list[str],
    rows: list[list[str]],
    story: list,
    widths: list[float] | None = None,
    mono_columns: tuple[int, ...] = (),
) -> None:
    """Append a bordered table; *mono_columns* are rendered in Courier."""
    data = [[Paragraph(esc(cell), CELL_BOLD) for cell in headers]]
    for row in rows:
        data.append(
            [
                Paragraph(esc(cell), CELL_MONO if index in mono_columns else CELL)
                for index, cell in enumerate(row)
            ]
        )

    if widths is None:
        widths = [PAGE_WIDTH / len(headers)] * len(headers)

    style = [
        ("BACKGROUND", (0, 0), (-1, 0), HEADER_BG),
        ("GRID", (0, 0), (-1, -1), 0.4, RULE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    for index in range(1, len(rows) + 1):
        if index % 2 == 0:
            style.append(("BACKGROUND", (0, index), (-1, index), colors.HexColor("#fbfcfd")))

    story.append(Spacer(1, 3))
    story.append(Table(data, colWidths=widths, repeatRows=1, style=TableStyle(style)))
    story.append(Spacer(1, 7))


# --------------------------------------------------------------------------- #
# Document
# --------------------------------------------------------------------------- #
def _draw_footer(canvas, document, footer_text: str) -> None:
    """Draw the running footer and the page number."""
    canvas.saveState()
    canvas.setStrokeColor(RULE)
    canvas.setLineWidth(0.4)
    canvas.line(2 * cm, 1.45 * cm, A4[0] - 2 * cm, 1.45 * cm)
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(MUTED)
    canvas.drawString(2 * cm, 1.05 * cm, footer_text)
    canvas.drawRightString(A4[0] - 2 * cm, 1.05 * cm, f"Page {document.page}")
    canvas.restoreState()


def build_document(
    path: Path,
    *,
    story: list,
    title: str,
    subject: str,
    footer_text: str,
    author: str = "Cryptographic Cipher Analyzer project",
) -> Path:
    """Render *story* to a PDF at *path* and return the path written.

    Args:
        path: Destination PDF file; parent folders are created automatically.
        story: List of reportlab flowables.
        title: PDF document title.
        subject: PDF document subject.
        footer_text: Left-hand text printed at the bottom of every page.
        author: PDF document author.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    document = BaseDocTemplate(
        str(path),
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=1.8 * cm,
        bottomMargin=1.9 * cm,
        title=title,
        author=author,
        subject=subject,
    )
    frame = Frame(
        document.leftMargin,
        document.bottomMargin,
        document.width,
        document.height,
        id="page",
    )
    document.addPageTemplates(
        [
            PageTemplate(
                id="all",
                frames=[frame],
                onPage=lambda canvas, doc: _draw_footer(canvas, doc, footer_text),
            )
        ]
    )
    document.build(story)
    return path


def report(path: Path) -> None:
    """Print where a generated PDF was written and how big it is."""
    path = Path(path)
    print(f"Written: {path}")
    print(f"Size: {path.stat().st_size / 1024:.0f} KB")
