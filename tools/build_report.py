#!/usr/bin/env python3
"""Build the filled Labmentix project report from the supplied template.

The template's styles, theme and page setup are reused (the document is opened,
cleared and rebuilt), so the finished report keeps the original house style while
containing only real project content.  Every section starts on a new page, body
text is justified, and the screenshots rendered by ``build_figures.py`` are
placed inside Section 4 with a numbered caption.

Run from the repository root::

    python tools/build_report.py
"""

from __future__ import annotations

import json
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

PROJECT = Path(__file__).resolve().parent.parent
TEMPLATE = PROJECT / "Labmentix_Project_Report_Template.docx"
FIGURE_DIR = PROJECT / "report_assets" / "figures"
OUTPUT = PROJECT / "Cryptographic_Cipher_Analyzer_Project_Report.docx"

ARIAL = "Arial"
COURIER = "Courier New"
BLUE = "185FA5"
BLUE_DARK = "0D3A6B"
HEADING_BLUE = "2E74B5"
GREY = "555555"
LIGHT = "EAF3FD"
BORDER = "BFBFBF"

#: Screenshots are placed 6.5 inches wide, but tall ones are scaled down so a
#: whole figure plus its caption can share a page with the text above it.  That
#: is what removes the half-empty pages a large figure would otherwise leave
#: behind.  ``MIN_FIGURE_WIDTH`` keeps the console text readable.
FIGURE_WIDTH = 6.5
MAX_FIGURE_HEIGHT = 5.2
MIN_FIGURE_WIDTH = 5.0

FIGURE_MANIFEST = PROJECT / "report_assets" / "captures" / "figures.json"
SIGNATURE = PROJECT / "report_assets" / "signature.png"

#: Cover page and footer details.  These are the student details used on the
#: earlier Labmentix submission that was written on this same template, so the
#: report is ready to submit without any placeholder left to fill in.
STUDENT_NAME = "Malek Minhaz"
BATCH = "Batch 01 - June 2026"
SUBMISSION_DATE = "21/09/2026"

_figure_number = 0
_SLICES: dict[str, list[str]] | None = None


# --------------------------------------------------------------------------- #
# Low level helpers
# --------------------------------------------------------------------------- #
def get_style(document, name: str):
    """Return a paragraph style by its display name.

    python-docx looks styles up through a name translation table, which fails for
    the built-in styles in this template, so the style list is searched directly.
    """
    for style in document.styles:
        if style.name == name:
            return style
    raise KeyError(f"style not found: {name}")


def style_run(run, *, size=None, bold=None, italic=None, color=None, font=None):
    """Apply character formatting that Word will honour on every platform."""
    if font:
        run.font.name = font
        rpr = run._element.get_or_add_rPr()
        fonts = rpr.get_or_add_rFonts()
        for attribute in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
            fonts.set(qn(attribute), font)
    if size is not None:
        run.font.size = Pt(size)
    if bold is not None:
        run.font.bold = bold
    if italic is not None:
        run.font.italic = italic
    if color:
        run.font.color.rgb = RGBColor.from_string(color)
    return run


def shade(element, fill: str) -> None:
    """Apply solid shading to a cell or paragraph properties element."""
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill)
    element.append(shd)


def cell_shade(cell, fill: str) -> None:
    shade(cell._tc.get_or_add_tcPr(), fill)


def table_borders(table, color: str = BORDER, size: str = "4") -> None:
    """Draw a thin single border around every cell of *table*."""
    borders = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        element = OxmlElement(f"w:{edge}")
        element.set(qn("w:val"), "single")
        element.set(qn("w:sz"), size)
        element.set(qn("w:space"), "0")
        element.set(qn("w:color"), color)
        borders.append(element)
    table._tbl.tblPr.append(borders)


def cell_borders(cell, left=None, others="none") -> None:
    """Set per-cell borders, used for the left-accented code and note boxes."""
    borders = OxmlElement("w:tcBorders")
    for edge in ("top", "left", "bottom", "right"):
        element = OxmlElement(f"w:{edge}")
        element.set(qn("w:val"), "single" if edge == "left" and left else others)
        element.set(qn("w:sz"), "16" if edge == "left" and left else "4")
        element.set(qn("w:space"), "0")
        element.set(qn("w:color"), left if edge == "left" and left else "FFFFFF")
        borders.append(element)
    tcpr = cell._tc.get_or_add_tcPr()
    tcpr.append(borders)


def cell_margins(cell, top=100, left=200, bottom=100, right=200) -> None:
    """Set the internal padding of a table cell."""
    margins = OxmlElement("w:tcMar")
    for edge, value in (("top", top), ("left", left), ("bottom", bottom), ("right", right)):
        element = OxmlElement(f"w:{edge}")
        element.set(qn("w:w"), str(value))
        element.set(qn("w:type"), "dxa")
        margins.append(element)
    cell._tc.get_or_add_tcPr().append(margins)


def repeat_header(row) -> None:
    """Mark a table row as a repeating header."""
    properties = row._tr.get_or_add_trPr()
    header = OxmlElement("w:tblHeader")
    header.set(qn("w:val"), "true")
    properties.append(header)


def spacer(document, size_pt: float = 6) -> None:
    """Add a short empty paragraph that separates a box or table from what follows.

    The paragraph's *mark* is given a small font so the gap is about seven
    points instead of the fourteen a default empty paragraph would consume.
    """
    paragraph = document.add_paragraph()
    paragraph.paragraph_format.space_before = Pt(0)
    paragraph.paragraph_format.space_after = Pt(0)
    properties = paragraph._p.get_or_add_pPr()
    run_properties = properties.find(qn("w:rPr"))
    if run_properties is None:
        run_properties = OxmlElement("w:rPr")
        properties.append(run_properties)
    for tag in ("w:sz", "w:szCs"):
        element = OxmlElement(tag)
        element.set(qn("w:val"), str(int(size_pt * 2)))
        run_properties.append(element)


def paragraph_border(paragraph, color: str = BLUE, size: str = "8") -> None:
    """Add a coloured rule underneath a paragraph (section banners)."""
    borders = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), size)
    bottom.set(qn("w:space"), "1")
    bottom.set(qn("w:color"), color)
    borders.append(bottom)
    paragraph._p.get_or_add_pPr().append(borders)


# --------------------------------------------------------------------------- #
# Building blocks
# --------------------------------------------------------------------------- #
def banner(document, text: str, *, new_page: bool = False) -> None:
    """Print the blue ``SECTION n - ...`` marker used by the template.

    ``new_page`` starts the section on a fresh page.  The break is attached to
    the banner itself rather than to a separate empty paragraph, which would
    otherwise be able to land on a page of its own.
    """
    paragraph = document.add_paragraph()
    paragraph.paragraph_format.space_before = Pt(0 if new_page else 16)
    paragraph.paragraph_format.space_after = Pt(0)
    paragraph.paragraph_format.page_break_before = new_page
    paragraph_border(paragraph)
    style_run(paragraph.add_run(text), size=10, bold=True, color=BLUE, font=ARIAL)


def h1(document, text: str) -> None:
    """Add a level-1 heading in the template's house style."""
    paragraph = document.add_paragraph(style=get_style(document, "Heading 1"))
    paragraph.paragraph_format.space_before = Pt(16)
    paragraph.paragraph_format.space_after = Pt(8)
    style_run(paragraph.add_run(text), size=16, bold=True, color=HEADING_BLUE, font=ARIAL)


def h2(document, text: str) -> None:
    """Add a level-2 heading in the template's house style."""
    paragraph = document.add_paragraph(style=get_style(document, "Heading 2"))
    paragraph.paragraph_format.space_before = Pt(12)
    paragraph.paragraph_format.space_after = Pt(6)
    style_run(paragraph.add_run(text), size=13, bold=True, color=HEADING_BLUE, font=ARIAL)


def body(document, text: str, *, space_after: float = 8, italic: bool = False):
    """Add a justified body paragraph."""
    paragraph = document.add_paragraph()
    paragraph.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    paragraph.paragraph_format.space_after = Pt(space_after)
    paragraph.paragraph_format.line_spacing = 1.15
    style_run(paragraph.add_run(text), size=11, italic=italic, font=ARIAL)
    return paragraph


def bullet(document, text: str) -> None:
    """Add a justified bullet list item using the template's bullet list."""
    paragraph = document.add_paragraph(style=get_style(document, "List Paragraph"))
    properties = paragraph._p.get_or_add_pPr()
    numbering = OxmlElement("w:numPr")
    level = OxmlElement("w:ilvl")
    level.set(qn("w:val"), "0")
    number = OxmlElement("w:numId")
    number.set(qn("w:val"), "2")
    numbering.append(level)
    numbering.append(number)
    properties.append(numbering)
    paragraph.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    paragraph.paragraph_format.space_after = Pt(3)
    paragraph.paragraph_format.line_spacing = 1.15
    style_run(paragraph.add_run(text), size=11, font=ARIAL)


def code_box(document, lines: list[str], *, font_size: float = 9.5, fill: str = "F5F5F5") -> None:
    """Add a shaded, left-accented box holding command-line text."""
    table = document.add_table(rows=1, cols=1)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    cell = table.cell(0, 0)
    cell.width = Inches(6.5)
    cell_borders(cell, left="AAAAAA")
    cell_margins(cell, top=120, left=200, bottom=120, right=200)
    cell_shade(cell, fill)
    paragraph = cell.paragraphs[0]
    paragraph.paragraph_format.space_after = Pt(0)
    paragraph.paragraph_format.line_spacing = 1.1
    for index, line in enumerate(lines):
        if index:
            paragraph.add_run().add_break()
        style_run(paragraph.add_run(line), size=font_size, color="333333", font=COURIER)
    spacer(document)


def note_box(document, text: str, *, fill: str = LIGHT, accent: str = BLUE) -> None:
    """Add a shaded callout box, matching the template's instruction styling."""
    table = document.add_table(rows=1, cols=1)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    cell = table.cell(0, 0)
    cell.width = Inches(6.5)
    cell_borders(cell, left=accent)
    cell_margins(cell, top=120, left=200, bottom=120, right=200)
    cell_shade(cell, fill)
    paragraph = cell.paragraphs[0]
    paragraph.paragraph_format.space_after = Pt(0)
    paragraph.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    style_run(paragraph.add_run(text), size=10, italic=True, color="444444", font=ARIAL)
    spacer(document)


def data_table(document, headers: list[str], rows: list[list[str]], widths: list[float]) -> None:
    """Add a bordered table with a shaded header row."""
    table = document.add_table(rows=1, cols=len(headers))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    table_borders(table)
    repeat_header(table.rows[0])

    for index, header in enumerate(headers):
        cell = table.rows[0].cells[index]
        cell_shade(cell, BLUE)
        cell_margins(cell, top=80, left=120, bottom=80, right=120)
        paragraph = cell.paragraphs[0]
        paragraph.paragraph_format.space_after = Pt(0)
        style_run(paragraph.add_run(header), size=10, bold=True, color="FFFFFF", font=ARIAL)

    for row_index, row in enumerate(rows):
        cells = table.add_row().cells
        for index, value in enumerate(row):
            cell = cells[index]
            cell_margins(cell, top=70, left=120, bottom=70, right=120)
            if row_index % 2:
                cell_shade(cell, "F7FAFD")
            paragraph = cell.paragraphs[0]
            paragraph.paragraph_format.space_after = Pt(0)
            style_run(paragraph.add_run(value), size=10, font=ARIAL)

    for row in table.rows:
        for index, width in enumerate(widths):
            row.cells[index].width = Inches(width)
    spacer(document)


def figure_slices() -> dict[str, list[str]]:
    """Map each captured session to the figure files ``build_figures`` wrote.

    A session too tall for one block is stored as several images; the report
    places all of them next to each other so that no screenshot is ever larger
    than the space a page can give it.
    """
    global _SLICES
    if _SLICES is None:
        _SLICES = {}
        if FIGURE_MANIFEST.exists():
            payload = json.loads(FIGURE_MANIFEST.read_text(encoding="utf-8"))
            for entry in payload.get("figures", []):
                _SLICES[entry["figure"]] = [item["file"] for item in entry["slices"]]
    return _SLICES


def total_figures() -> int:
    """Number of figures the report will contain, for the text that cites it."""
    slices = figure_slices()
    return sum(len(names) for names in slices.values()) if slices else 0


def short_caption(caption: str) -> str:
    """Return the leading phrase of *caption*, for a continuation figure.

    The slices of one screenshot share a description, so repeating it in full on
    every slice would be noisy.  Continuations therefore reuse only the first
    sentence of the description and are marked as continued.
    """
    head, separator, _ = caption.partition(". ")
    head = head.rstrip(". ")
    if len(head) > 90:  # keep a long single-sentence caption readable
        head = head[:87].rstrip(" ,;") + "..."
    return head + " (continued)."


def figure(document, filename: str, caption: str, *, width: float = FIGURE_WIDTH) -> None:
    """Insert a screenshot, or every slice of one, with a numbered caption."""
    names = figure_slices().get(filename, [filename])
    for index, name in enumerate(names, start=1):
        text = caption if index == 1 else short_caption(caption)
        _place_figure(document, name, text, width=width)


def _place_figure(document, filename: str, caption: str, *, width: float = FIGURE_WIDTH) -> None:
    """Insert one image with its numbered caption."""
    global _figure_number
    _figure_number += 1

    path = FIGURE_DIR / f"{filename}.png"
    if not path.exists():  # pragma: no cover - guards a forgotten render step
        raise FileNotFoundError(f"missing figure: {path}")

    # Keep every screenshot inside the printable height of a page together with
    # its heading and caption by shrinking the tall ones, without letting the
    # console text become too small to read.
    from PIL import Image

    with Image.open(path) as image:
        aspect = image.height / image.width
    if width * aspect > MAX_FIGURE_HEIGHT:
        target = max(MAX_FIGURE_HEIGHT, MIN_FIGURE_WIDTH * aspect)
        width = round(target / aspect, 2)

    paragraph = document.add_paragraph()
    paragraph.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    paragraph.paragraph_format.space_before = Pt(2)
    paragraph.paragraph_format.space_after = Pt(1)
    paragraph.paragraph_format.line_spacing = 1.0
    paragraph.paragraph_format.keep_with_next = True
    paragraph.add_run().add_picture(str(path), width=Inches(width))

    caption_paragraph = document.add_paragraph()
    caption_paragraph.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    caption_paragraph.paragraph_format.space_before = Pt(0)
    caption_paragraph.paragraph_format.space_after = Pt(5)
    caption_paragraph.paragraph_format.line_spacing = 1.0
    caption_paragraph.paragraph_format.keep_together = True
    style_run(
        caption_paragraph.add_run(f"Figure {_figure_number}: {caption}"),
        size=8.5,
        italic=True,
        color=GREY,
        font=ARIAL,
    )


def step(document, number: int, title: str) -> None:
    """Add a numbered methodology step heading."""
    h2(document, f"Step {number} - {title}")


def fill_footer(document) -> None:
    """Replace the blank name / batch lines in the template's running footer.

    The footer comes from the template and is reused unchanged, so its two
    fill-in lines are completed here rather than left as underscores.
    """
    replacement = (
        f"Student Name: {STUDENT_NAME}   |   Batch: {BATCH.removeprefix('Batch ')}"
    )
    for section in document.sections:
        footer = section.footer
        if footer.is_linked_to_previous:
            continue
        for paragraph in footer.paragraphs:
            for run in paragraph.runs:
                if "Student Name:" in run.text and "____" in run.text:
                    style_run(run, font=ARIAL)
                    run.text = replacement


# --------------------------------------------------------------------------- #
# Sections
# --------------------------------------------------------------------------- #
def build_cover(document) -> None:
    """Cover page: programme banner, report title and the details table."""
    table = document.add_table(rows=1, cols=1)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    cell = table.cell(0, 0)
    cell.width = Inches(6.5)
    cell_borders(cell, others="none")
    cell_margins(cell, top=240, left=300, bottom=240, right=300)
    cell_shade(cell, BLUE)

    first = cell.paragraphs[0]
    first.alignment = WD_ALIGN_PARAGRAPH.CENTER
    first.paragraph_format.space_after = Pt(4)
    style_run(first.add_run("LABMENTIX"), size=20, bold=True, color="FFFFFF", font=ARIAL)
    second = cell.add_paragraph()
    second.alignment = WD_ALIGN_PARAGRAPH.CENTER
    second.paragraph_format.space_after = Pt(0)
    style_run(second.add_run("Cybersecurity Training Program"), size=11, color="D0E8FF", font=ARIAL)

    spacer = document.add_paragraph()
    spacer.paragraph_format.space_after = Pt(18)

    title = document.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title.paragraph_format.space_after = Pt(6)
    style_run(
        title.add_run("CYBERSECURITY PROJECT REPORT"),
        size=18, bold=True, color=BLUE_DARK, font=ARIAL,
    )

    subtitle = document.add_paragraph()
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    subtitle.paragraph_format.space_after = Pt(26)
    style_run(subtitle.add_run("15-Day Hands-On Project Submission"), size=12, color=GREY, font=ARIAL)

    details = [
        ("Project Title", "Cryptographic Cipher Analyzer - a Caesar and Vigenere cryptanalysis tool"),
        ("Student Name", STUDENT_NAME),
        ("Batch / Cohort", BATCH),
        ("Domain", "Cybersecurity - Cryptography and Cryptanalysis"),
        ("Trainer Name", "Ganesh Kuche"),
        ("Submission Date", SUBMISSION_DATE),
        ("Difficulty Level", "Intermediate"),
    ]
    data_table(document, ["Field", "Details"], [list(row) for row in details], [1.9, 4.6])

    closing = document.add_paragraph()
    closing.alignment = WD_ALIGN_PARAGRAPH.CENTER
    closing.paragraph_format.space_before = Pt(20)
    style_run(
        closing.add_run(
            "A command-line tool that implements the Caesar and Vigenere ciphers and "
            "demonstrates, step by step, how both of them are broken."
        ),
        size=10, italic=True, color=GREY, font=ARIAL,
    )


def build_contents(document) -> None:
    """Add a simple contents page listing every section."""
    banner(document, "CONTENTS", new_page=True)
    h1(document, "Contents")
    entries = [
        ("1.", "Project Abstract"),
        ("2.", "Introduction - background, problem statement and objectives"),
        ("3.", "Tools and Environment Setup - tools used and the lab description"),
        ("4.", f"Methodology - fourteen numbered steps with screenshots "
               f"(Figures 1-{total_figures()})"),
        ("5.", "Results and Observations - findings table and analysis"),
        ("6.", "Challenges Faced"),
        ("7.", "Learning Outcomes"),
        ("8.", "Conclusion and Future Scope"),
        ("9.", "References"),
        ("", "Student Declaration"),
    ]
    for number, text in entries:
        paragraph = document.add_paragraph()
        paragraph.paragraph_format.space_after = Pt(6)
        paragraph.paragraph_format.line_spacing = 1.15
        if number:
            style_run(paragraph.add_run(f"{number}  "), size=11, bold=True, color=BLUE, font=ARIAL)
        style_run(paragraph.add_run(text), size=11, font=ARIAL)


def build_abstract(document) -> None:
    banner(document, "SECTION 1 - PROJECT ABSTRACT", new_page=True)
    h1(document, "1. Project Abstract")
    body(
        document,
        "This project delivers the Cryptographic Cipher Analyzer, a Python command-line "
        "application that implements the two most widely taught classical ciphers - the Caesar "
        "cipher and the Vigenere cipher - and then attacks them with the same techniques a real "
        "cryptanalyst would use. Textbooks state that these ciphers are weak, but the weakness "
        "only becomes convincing when the learner watches a ciphertext that looked unreadable "
        "collapse into plain English in front of them. The tool was therefore built around that "
        "moment: every operation prints not only the result but also the evidence that justifies "
        "it, and never presents a statistical guess as a proven fact.",
    )
    body(
        document,
        "The application provides direct encryption and decryption for both ciphers, single-letter "
        "frequency analysis, an automated Caesar breaker that scores all twenty-six shifts with the "
        "chi-square statistic, an Index of Coincidence analyser, a Kasiski examination of repeated "
        "sequences, a combined Vigenere cryptanalysis workflow that recovers the keyword one column "
        "at a time, file based encryption and decryption, a security assessment of each algorithm, "
        "and timestamped text reports. It offers both an interactive menu and a scriptable command "
        "line, and it is covered by 163 automated tests that all pass.",
    )
    body(
        document,
        "Running the tool on the supplied sample ciphertexts produced concrete results: the Caesar "
        "sample was broken automatically and returned the correct shift of 3 with the plaintext "
        "\"HELLO WORLD / CRYPTOGRAPHY IS THE PRACTICE AND STUDY OF TECHNIQUES FOR SECURE "
        "COMMUNICATION...\", and the Vigenere sample was analysed to an estimated key length of 5 "
        "and cracked to the keyword LEMON, again as the first ranked candidate. The exercise "
        "confirms the central lesson of the course: a cipher is only as strong as the secrecy of "
        "its key, and a large keyspace is worthless if the ciphertext still leaks statistical "
        "structure.",
    )


def build_introduction(document) -> None:
    banner(document, "SECTION 2 - INTRODUCTION", new_page=True)
    h1(document, "2. Introduction")

    h2(document, "2.1 Background")
    body(
        document,
        "Cryptography is the practice and study of techniques for secure communication in the "
        "presence of adversaries. Its classical branch covers the ciphers that were used before "
        "computers existed, and although they are far too weak to protect modern data, they remain "
        "the clearest way to learn how cryptographic thinking works. The Caesar cipher, used by "
        "Julius Caesar around 58 BC, replaces every letter with another letter a fixed number of "
        "positions further along the alphabet, which gives an attacker only twenty-six keys to try. "
        "The Vigenere cipher, described in the sixteenth century, removes that weakness by "
        "applying a different Caesar shift for every letter using a repeating keyword, and was "
        "considered unbreakable for around three hundred years. Studying why the first cipher "
        "falls to trivial brute force while the second falls to statistics rather than to brute "
        "force teaches the difference between key size and real security - the same distinction "
        "that separates a modern algorithm such as AES from a large but badly designed key.",
    )

    h2(document, "2.2 Problem Statement")
    body(
        document,
        "Classical cryptography is usually taught as theory. Students are told that the Caesar "
        "cipher can be brute forced and that the Vigenere cipher leaks its key length through "
        "repeated sequences, but they rarely run the attack on real text, choose a key length "
        "themselves, watch a wrong guess produce nonsense, and correct it. There is also no single "
        "tool that shows the whole attack chain in one place: ordinary calculators or spreadsheet "
        "scripts compute letter frequencies, but they do not connect the frequency profile to the "
        "Index of Coincidence, to the Kasiski factors, to the per-column key recovery and finally "
        "to the recovered keyword. Without that connection the learner cannot see which evidence "
        "is decisive and which is merely suggestive, and it is easy to leave the exercise believing "
        "that a statistical estimate is a proof. This project addresses that gap with one "
        "self-contained tool that performs the complete cryptanalysis of both ciphers and labels "
        "clearly which values are confirmed and which are estimates.",
    )

    h2(document, "2.3 Objectives")
    body(document, "The project set out to achieve the following specific goals:", space_after=6)
    for item in (
        "To implement the Caesar and Vigenere ciphers in Python with correct handling of "
        "punctuation, spaces, digits and case.",
        "To build a single-letter frequency analysis module and compare its output against "
        "standard English letter frequencies.",
        "To automate the breaking of the Caesar cipher by testing all twenty-six shifts and "
        "ranking the results with the chi-square statistic.",
        "To implement the Index of Coincidence and Kasiski examination in order to estimate the "
        "length of a repeating keyword.",
        "To recover a Vigenere keyword column by column, verify the candidate by reading the "
        "decrypted text, and report the result as an unconfirmed estimate.",
        "To add file based encryption and decryption together with a security (strength) "
        "assessment of both algorithms, and to cover the whole tool with automated tests and "
        "generated text reports.",
    ):
        bullet(document, item)


def build_tools(document) -> None:
    banner(document, "SECTION 3 - TOOLS & ENVIRONMENT", new_page=True)
    h1(document, "3. Tools and Environment Setup")
    body(
        document,
        "The whole project was built and demonstrated on a single Windows machine using only the "
        "Python standard library, so it can be reproduced anywhere Python 3.10 or later is "
        "installed. The table below lists every tool that was used and the part it played.",
    )
    data_table(
        document,
        ["Tool / Software", "Version / Platform", "Purpose"],
        [
            ["Python", "3.13.14 (Windows 64-bit)", "Core language runtime; the tool itself imports only the standard library"],
            ["Windows 11", "64-bit", "Development and demonstration operating system"],
            ["Windows Terminal (PowerShell)", "Windows 11 bundled", "Running the tool and capturing the screenshots in Section 4"],
            ["GNU Bash (Git Bash)", "5.x", "Helper file commands used in the walkthrough (ls, head, cat)"],
            ["unittest", "Python standard library", "Automated test suite - 163 tests covering ciphers, analysis and files"],
            ["python-docx", "1.2", "Building this report and inserting the figures programmatically"],
            ["Pillow (PIL)", "12.3", "Rendering the console screenshots that appear in Section 4"],
        ],
        [1.5, 1.6, 3.4],
    )

    h2(document, "3.1 Lab / Environment Description")
    body(
        document,
        "No virtual machines or cloud instances were required, because the project is a "
        "self-contained Python application rather than a network or host based attack. The lab "
        "consisted of one Windows 11 workstation with Python 3.13.14 installed as the system "
        "interpreter. The project lives in a single folder, crypto_cipher_analyzer, which contains "
        "the entry point main.py, the packages analysis (cryptanalysis algorithms), ciphers (Caesar "
        "and Vigenere implementations), file_operations (safe file input and output) and utils "
        "(terminal presentation, validation, text helpers and report generation), plus the tests "
        "and sample_data folders and the reports folder that receives the generated text reports.",
    )
    body(
        document,
        "The tool can be driven in two ways. Interactive mode (python main.py) presents a numbered "
        "menu and never crashes on unexpected input; command line mode runs one operation per "
        "invocation, for example python main.py caesar-encrypt --text \"HELLO\" --shift 3, which "
        "makes the tool easy to script and easy to demonstrate during a viva. Every analysis "
        "command accepts --report to write a timestamped text file under reports/, and every file "
        "operation refuses to overwrite an existing file unless --overwrite is given, so the "
        "original data is never lost. All output shown in the next section was captured from this "
        "environment exactly as the user sees it; the only post-processing was re-wrapping long "
        "lines at the width of the window shown in each figure.",
    )


def build_methodology(document) -> None:
    banner(document, "SECTION 4 - METHODOLOGY / STEP-BY-STEP PROCESS", new_page=True)
    h1(document, "4. Methodology")
    body(
        document,
        "This section documents exactly how the project was built and run. Each step states what "
        "was done and why, shows the command that was executed, and is followed by the resulting "
        f"console screenshot with a caption describing what the screenshot shows. "
        f"{total_figures()} screenshots are included as Figures 1 to {total_figures()} and they "
        "were all captured from real runs of the finished tool on the sample data supplied with "
        "the project. A screenshot that is taller than half a page is placed as two consecutive "
        "figures so that the pages of this section stay full and every line of the console stays "
        "legible. Nothing below is illustrative: the numbers, rankings and recovered keys are the "
        "values the tool actually printed.",
    )
    note_box(
        document,
        "Convention used in this section: values that the tool can prove (the Caesar shift of a "
        "decryption, the contents of a decrypted file) are reported as results, while values that "
        "depend on statistics (an estimated Vigenere key length, a ranked candidate key) are "
        "labelled as estimates and were verified separately by reading the decrypted text.",
    )

    # ------------------------------------------------------------------ step 1
    step(document, 1, "Setting up the environment and verifying the project structure")
    body(
        document,
        "The workstation already had Python installed, so the first task was to record the exact "
        "interpreter version and to confirm the project layout before touching any code. The tool "
        "was deliberately written against the standard library only (argparse, dataclasses, "
        "pathlib, re, statistics), which means there is no dependency to install and no risk of a "
        "package upgrade changing the behaviour of the demonstrations.",
    )
    code_box(document, [
        "python --version",
        "python -c \"import sys; print('Environment:', sys.executable)\"",
        "cd crypto_cipher_analyzer",
        "ls -1",
        "ls -1 analysis ciphers file_operations utils",
    ])
    figure(
        document, "fig01_environment",
        "Environment check. Python 3.13.14 runs the tool and the project reports that it depends on "
        "the standard library only, so no third party package has to be installed to reproduce the "
        "results.",
    )
    body(
        document,
        "The listing below shows the top level of the project and then the contents of the four "
        "Python packages. Keeping the cryptanalysis algorithms (analysis), the ciphers themselves "
        "(ciphers), the disk access (file_operations) and the presentation helpers (utils) in "
        "separate packages is what allows the same algorithms to be driven from the interactive "
        "menu, from the command line and from the test suite without any duplication.",
    )
    figure(
        document, "fig02_structure",
        "Top level of crypto_cipher_analyzer. Besides main.py, the entry point, there are separate "
        "packages for the ciphers, the cryptanalysis algorithms, file handling, utilities, tests and "
        "sample data.",
    )
    figure(
        document, "fig02b_modules",
        "Contents of the four Python packages: analysis holds the Caesar cracker, frequency, Index of "
        "Coincidence, Kasiski and Vigenere analysers; ciphers holds the two cipher implementations; "
        "file_operations holds the safe file reader and writer; utils holds the terminal banner, "
        "validators, text helpers and report generator.",
    )

    # ------------------------------------------------------------------ step 2
    step(document, 2, "Launching the tool and reading the main menu")
    body(
        document,
        "Running main.py with no arguments starts interactive mode. The banner fixes the purpose of "
        "the tool at the top of the screen, the educational-use disclaimer is printed before any "
        "result is produced and pauses with a full stop between them, and the nine-entry menu "
        "exposes every capability of the program. Option 9 exits the tool cleanly, which is what "
        "was done here to capture the complete start-up screen in a single figure.",
    )
    figure(
        document, "fig03_launch",
        "Start-up screen. The banner identifies the tool, the disclaimer states that the classical "
        "ciphers must not be used for real data, and the main menu lists the eight operations plus "
        "Exit; the session was ended with option 9.",
    )

    # ------------------------------------------------------------------ step 3
    step(document, 3, "Encrypting and decrypting text with the Caesar cipher")
    body(
        document,
        "The first functional test was a round trip through the Caesar cipher using the shift of 3 "
        "that makes the cipher famous. Encryption turns ATTACK AT DAWN into DWWDFN DW GDZQ and "
        "decryption must return the original text exactly, including the spaces, because the tool "
        "only shifts alphabetic characters. The command line form was used here so that the "
        "operation, the shift and the result are all visible on one screen.",
    )
    code_box(document, [
        "python main.py caesar-encrypt --text \"ATTACK AT DAWN\" --shift 3",
        "python main.py caesar-decrypt --text \"DWWDFN DW GDZQ\" --shift 3",
    ])
    figure(
        document, "fig04_caesar",
        "Caesar encryption and decryption. Each run prints the shift used and the input and output "
        "lengths, and the decryption reproduces ATTACK AT DAWN exactly, confirming that the "
        "implementation is symmetric and that non-alphabetic characters are left untouched.",
    )

    # ------------------------------------------------------------------ step 4
    step(document, 4, "Encrypting and decrypting text with the Vigenere cipher")
    body(
        document,
        "The Vigenere cipher was tested next with the classic textbook example, the keyword LEMON "
        "against the plaintext ATTACKATDAWN, which is the pairing used in nearly every description "
        "of the cipher and therefore an easy way to check the implementation against an "
        "independent source. The keystream repeats every five letters, so the same plaintext letter "
        "produces different ciphertext letters at different positions - the property that defeats "
        "simple frequency analysis.",
    )
    code_box(document, [
        "python main.py vigenere-encrypt --text \"ATTACKATDAWN\" --key LEMON",
        "python main.py vigenere-decrypt --text \"LXFOPVEFRNHR\" --key LEMON",
    ])
    figure(
        document, "fig05_vigenere",
        "Vigenere encryption and decryption of the standard textbook example. ATTACKATDAWN becomes "
        "LXFOPVEFRNHR with the key LEMON, and decrypting the ciphertext with the same key returns "
        "the original plaintext.",
    )

    # ------------------------------------------------------------------ step 5
    step(document, 5, "Running the tool in interactive mode")
    body(
        document,
        "The same two ciphers were then exercised through the menu, which is the route a student "
        "taking their first look at the tool would normally follow. Interactive mode asks for the "
        "input source (typed text or a file), validates every answer, and offers to save the result "
        "as a report at the end of the operation. Here the text HELLO WORLD was typed, the shift 3 "
        "was accepted from the default, and the report prompt was answered with n so that no file "
        "was written.",
    )
    code_box(document, [
        "python main.py",
        "",
        "1      -> Caesar Cipher (encrypt / decrypt)",
        "1      -> Encrypt text",
        "1      -> Type or paste the text",
        "HELLO WORLD",
        "3      -> Caesar shift",
        "n      -> do not save a report",
        "9      -> Exit",
    ])
    figure(
        document, "fig06_interactive_menu",
        "Interactive walkthrough, menu and encryption. The user selects the Caesar cipher, chooses to encrypt, "
        "selects typed input, enters HELLO WORLD and the shift 3; the tool prints the shift, the "
        "input and output lengths and the ciphertext KHOOR ZRUOG.",
    )
    figure(
        document, "fig07_interactive_exit",
        "Interactive walkthrough, result and exit. The educational note is repeated after the result, the "
        "tool offers to save the analysis as a report (answered n), waits for Enter and returns to "
        "the main menu, where option 9 ends the session cleanly.",
    )

    # ------------------------------------------------------------------ step 6
    step(document, 6, "Single-letter frequency analysis")
    body(
        document,
        "With both ciphers working, cryptanalysis began with the most basic tool. The Caesar sample "
        "file was analysed at letter level: the module counts every letter, converts the counts into "
        "percentages and prints them beside the standard English frequencies so that the distortion "
        "caused by the cipher is immediately visible. It then computes the Index of Coincidence of "
        "the whole text as supporting evidence, which is why that value also appears in this figure.",
    )
    code_box(document, ["python main.py frequency --input sample_data/caesar_sample.txt"])
    figure(
        document, "fig08_frequency",
        "Frequency analysis of the Caesar sample. H is by far the most common letter at 15.31% "
        "against 6.09% in ordinary English while E has almost vanished, and the Index of Coincidence "
        "of 0.06987 sits close to the value for English prose - the signature of a single-alphabet "
        "cipher in which one letter of the plaintext is always replaced by one fixed letter.",
    )

    # ------------------------------------------------------------------ step 7
    step(document, 7, "Breaking the Caesar cipher automatically")
    body(
        document,
        "The distorted distribution makes the attack on the Caesar cipher almost trivial, and the "
        "cracker performs it without any hint from the user. All twenty-six possible shifts are "
        "applied to the ciphertext, each candidate is scored with the chi-square statistic against "
        "the standard English letter frequencies, and the candidates are ranked from most to least "
        "English-like. The tool then prints the best candidate together with the full decrypted "
        "text so that the result can be judged by reading it rather than by trusting a number.",
    )
    code_box(document, ["python main.py crack-caesar --input sample_data/caesar_sample.txt --top 5"])
    figure(
        document, "fig09_crack_a",
        "Automatic Caesar cracking, ranked candidates. Twenty-six candidates were evaluated; the shift of 3 "
        "scores 70.52, more than three times the second-ranked candidate at 22.94, and is the only "
        "row whose preview begins with recognisable English (HELLO WORLD, CRYPTOGRAPHY...).",
    )
    figure(
        document, "fig10_crack_b",
        "Automatic Caesar cracking, recovered plaintext. The best candidate is shift 3 with a score of 70.52 and "
        "the recovered plaintext matches the known text of the sample file, so no shift had to be "
        "guessed by the user. The closing notes explain that the ranking is statistical and that "
        "short or unusual messages can rank the wrong shift first.",
    )

    # ------------------------------------------------------------------ step 8
    step(document, 8, "Measuring the Index of Coincidence")
    body(
        document,
        "The Caesar cipher was easy precisely because every letter of the plaintext maps to one "
        "fixed letter. To show the contrast with a polyalphabetic cipher, the Index of Coincidence "
        "was measured on its own. The metric is computed as the sum over letters of "
        "fi(fi-1) divided by N(N-1); English prose sits near 0.0667 and random text near 0.0385. "
        "The same value is then recalculated for text split into two, three and up to twelve "
        "columns, because a repeating-key cipher whose key length has been guessed correctly will "
        "produce columns that each look like ordinary language and therefore raise the average.",
    )
    code_box(document, ["python main.py ic --input sample_data/caesar_sample.txt --max-key-length 12"])
    figure(
        document, "fig11_ic",
        "Index of Coincidence of the Caesar sample. The overall value of 0.06987 is above the 0.0667 "
        "reference for English, and because splitting a single-alphabet cipher into columns cannot "
        "increase the value, every key length stays close to the same level - there is no key length "
        "that stands out, exactly as expected for a monoalphabetic cipher.",
    )

    # ------------------------------------------------------------------ step 9
    step(document, 9, "Kasiski examination of the Vigenere sample")
    body(
        document,
        "Attention then moved to the Vigenere sample, which had been produced with the keyword "
        "LEMON. Kasiski examination searches the ciphertext for fragments that occur more than once. "
        "In a repeating-key cipher an exact repeat can only happen when the key realigns with the "
        "plaintext, so the distance between two occurrences of the same fragment must be a multiple "
        "of the key length. The tool lists those repeated sequences, factorises the distances, ranks "
        "the factors by how much evidence supports them and finally prints a table of candidate key "
        "lengths.",
    )
    code_box(document, ["python main.py kasiski --input sample_data/vigenere_sample.txt"])
    figure(
        document, "fig12_kasiski_a",
        "Kasiski examination, repeated sequences. Fifty repeated sequences were found; the five-letter sequences "
        "OWCSI and WCSID each occur three times at distances of 500 and 395 apart, and every one of "
        "those distances is divisible by 5, which is the strongest possible hint that the key length "
        "is 5. The tool also warns in writing that these are candidate lengths and not facts.",
    )
    figure(
        document, "fig13_kasiski_b",
        "Kasiski examination, distances and factors. The repeated sequences are tabulated with their distances and "
        "shared factors, and the ranked list of likely key lengths places length 5 first with 164 "
        "points of evidence, ahead of length 2 (160) and length 4 (74).",
    )

    # ----------------------------------------------------------------- step 10
    step(document, 10, "Full Vigenere cryptanalysis and key recovery")
    body(
        document,
        "Kasiski examination alone can suggest a wrong length when the text is short, so the tool "
        "combines it with the Index of Coincidence in a single workflow. It computes the overall IC "
        "of the ciphertext, calculates the average IC of the columns for every candidate key length, "
        "adds the Kasiski evidence and produces one combined score. The winning length is then used "
        "to split the ciphertext into that many columns, and each column is solved as an independent "
        "Caesar cipher: the three most likely letters for every key position are suggested, complete "
        "candidate keys are built from those suggestions, and each candidate is scored by how much "
        "its decryption looks like English.",
    )
    code_box(document, ["python main.py analyze-vigenere --input sample_data/vigenere_sample.txt"])
    figure(
        document, "fig14_vigenere_a",
        "Vigenere cryptanalysis, key length estimate. The overall Index of Coincidence of 0.04351 is close to the "
        "0.0385 expected from randomised text, which is the signature of a polyalphabetic cipher. The "
        "combined ranking nevertheless puts key length 5 first because its column IC of 0.07079 is "
        "English-like and the Kasiski evidence is the strongest, even though length 2 collects almost "
        "as many Kasiski hits.",
    )
    figure(
        document, "fig15_vigenere_b",
        "Vigenere cryptanalysis, per column key recovery. Assuming key length 5, each of the five key positions is "
        "solved on its own and the suggested letters are L, E, M, O and N with fitness scores between "
        "50 and 58 against alternatives in the low twenties. The assembled candidate keys are then "
        "ranked, and LEMON is first with a score of 70.15.",
    )
    figure(
        document, "fig16_vigenere_c",
        "Vigenere cryptanalysis, recovered keyword. The best guess is the key LEMON with a fitness score of "
        "70.15, and its decryption is readable English from the first word. The tool still labels the "
        "result unconfirmed and reminds the user to verify a candidate key by reading the recovered "
        "plaintext, which is what makes the difference between an estimate and a result.",
    )
    body(
        document,
        "The recovered keyword LEMON is correct - it is the key that was used to build the sample "
        "file - and it was obtained without any knowledge of the plaintext, using nothing but the "
        "ciphertext and three statistical techniques applied in the right order. This is the central "
        "demonstration of the project.",
    )

    # ----------------------------------------------------------------- step 11
    step(document, 11, "Encrypting and decrypting whole files")
    body(
        document,
        "Real work happens on files rather than on typed strings, so the same ciphers were applied "
        "to the sample files on disk. The file handler reads the input, transforms the text and "
        "writes the result to a new file without ever modifying the source: the default output name "
        "adds the suffix _out, and replacing an existing file requires the explicit --overwrite flag. "
        "The first file, held as Caesar ciphertext, was decrypted back into plain English; the "
        "resulting plaintext was then re-encrypted with the Vigenere cipher and a different key to "
        "produce a second ciphertext for comparison.",
    )
    code_box(document, [
        "python main.py file-caesar --input sample_data/caesar_sample.txt --shift 3 --decrypt",
        "python main.py file-vigenere --input sample_data/caesar_sample_out.txt --key LEMON \\",
        "    --output sample_data/message_vigenere.txt",
    ])
    figure(
        document, "fig17_file_decrypt",
        "Decrypting a file with the Caesar cipher. 1287 characters were read and 1287 written to "
        "caesar_sample_out.txt, the tool confirms that no existing file was overwritten, and the "
        "first 320 characters printed from the output file are readable English beginning with "
        "HELLO WORLD.",
    )
    figure(
        document, "fig18_file_encrypt",
        "Encrypting a file with the Vigenere cipher. The decrypted file was re-encrypted with the key "
        "LEMON into message_vigenere.txt, and the preview shows that the identical plaintext now "
        "starts with SIXZB HSDZQ instead of KHOOR ZRUOG, confirming that the two ciphers transform "
        "the same bytes differently.",
    )

    # ----------------------------------------------------------------- step 12
    step(document, 12, "Assessing the strength of both ciphers")
    body(
        document,
        "Finally the tool was asked to state, in plain language, how much protection each cipher "
        "actually offers. The security module reports the keyspace, the strengths, the weaknesses "
        "and the known cryptanalytic attacks for the chosen cipher, and finishes with the practical "
        "verdict. Both ciphers were assessed so that the two reports can be compared.",
    )
    code_box(document, [
        "python main.py security --cipher caesar",
        "python main.py security --cipher vigenere",
    ])
    figure(
        document, "fig19_security_caesar",
        "Security assessment of the Caesar cipher. It is rated VERY WEAK with an effective keyspace "
        "of only 25 keys; the report lists the small keyspace, vulnerability to single-letter "
        "frequency analysis, the surviving letter patterns and the absence of authentication as "
        "weaknesses, and ends with the verdict never to use it for real information.",
    )
    figure(
        document, "fig20_security_vigenere",
        "Security assessment of the Vigenere cipher. It is rated WEAK / EDUCATIONAL ONLY. The report "
        "explains the key insight of this project: the keyspace of 26^L for a key of length L is "
        "large, but it is not the weakness - the repeating keyword leaks the key length, and once the "
        "length is known the cipher decomposes into L independent Caesar ciphers.",
    )

    # ----------------------------------------------------------------- step 13
    step(document, 13, "Saving an analysis report to disk")
    body(
        document,
        "Every operation can write its complete result to a timestamped text file under reports/ by "
        "adding the --report flag, which makes it possible to keep a record of an analysis or to "
        "attach one to written work. The flag was used on a Caesar encryption and the generated file "
        "was then listed and opened to confirm its contents.",
    )
    code_box(document, [
        "python main.py caesar-encrypt --text \"ATTACK AT DAWN\" --shift 3 --report",
        "ls -1 reports",
        "cat reports/analysis_<timestamp>.txt",
    ])
    figure(
        document, "fig21_report_saved",
        "Saving a report. After the encryption output the tool confirms that the report was written "
        "to reports/analysis_<timestamp>.txt, and the directory listing shows the newly created file "
        "with its timestamped name.",
    )
    figure(
        document, "fig22_report_content",
        "The generated report file. It carries a header with the date, cipher and operation, an "
        "input statistics block, the input and output text, the educational notes and the security "
        "assessment of the cipher - a self-contained record that can be submitted as evidence of the "
        "work.",
    )

    # ----------------------------------------------------------------- step 14
    step(document, 14, "Running the automated test suite")
    body(
        document,
        "The last step was to confirm that none of the demonstrations above depended on manual "
        "testing alone. The project ships with 163 unit and integration tests covering the cipher "
        "implementations (including the known textbook examples, punctuation, digits and case "
        "handling), the cryptanalysis algorithms, the validators, the file operations and the "
        "command line interface itself. The suite was run in verbose mode so that individual test "
        "names as well as the final summary are visible.",
    )
    code_box(document, ["python -m unittest discover -s tests -v"])
    figure(
        document, "fig23_tests",
        "End of the automated test run. The last tests exercise the Vigenere implementation - key "
        "offsets, keystream behaviour, repeating keys and the known example - and the summary reports "
        "that all 163 tests ran and returned OK.",
    )
    note_box(
        document,
        "Reproducing this section: run the commands inside crypto_cipher_analyzer with Python 3.10 or "
        "later. All twenty-four screenshots were produced from these exact commands, and the "
        "captured console output is stored as plain text under report_assets/captures so that every "
        "figure can be checked against it.",
    )


def build_results(document) -> None:
    banner(document, "SECTION 5 - RESULTS & OBSERVATIONS", new_page=True)
    h1(document, "5. Results and Observations")
    body(
        document,
        "The tool and the sample data produced a complete end-to-end demonstration: both ciphers "
        "encrypt and decrypt correctly, the Caesar cipher was broken automatically, the Vigenere "
        "sample was fingerprinted, sized and cracked back to its keyword, and file based round trips "
        "were lossless. The findings below summarise what was observed, how each was measured and how "
        "much it matters for the security of the two algorithms.",
    )

    h2(document, "5.1 Summary of Findings")
    data_table(
        document,
        ["#", "Finding / Observation", "Details", "Severity / Impact"],
        [
            [
                "1",
                "The Caesar cipher is broken instantly",
                "All 26 shifts were scored with chi-square; shift 3 ranked first with 70.52 against "
                "22.94 for the runner-up and produced readable English. No plaintext hint was needed.",
                "Critical",
            ],
            [
                "2",
                "A monoalphabetic cipher preserves the letter distribution",
                "In the Caesar sample H occurred 15.31% of the time against 6.09% in English while E "
                "fell to 1.12%, and the Index of Coincidence was 0.06987 against 0.0667 for English prose.",
                "High",
            ],
            [
                "3",
                "The Vigenere cipher flattens the distribution",
                "The overall Index of Coincidence of the Vigenere sample was 0.04351, close to the "
                "0.0385 expected from random text, so single-letter frequency analysis finds nothing.",
                "High",
            ],
            [
                "4",
                "Repeated sequences leak the key length",
                "50 repeated fragments were found; OWCSI and WCSID each occurred three times at "
                "distances of 500 and 395, both divisible by 5, so key length 5 ranked first.",
                "High",
            ],
            [
                "5",
                "The keyword was recovered automatically",
                "Column-by-column analysis suggested L, E, M, O and N, and the assembled key LEMON "
                "ranked first with a fitness score of 70.15, decrypting the file into plain English.",
                "Critical",
            ],
            [
                "6",
                "Statistical evidence must be verified, not trusted",
                "Key length 2 collected almost as many Kasiski hits (160) as length 5 (164) but gave a "
                "column IC of only 0.04341 and meaningless output, so the combination of evidence and "
                "reading the result is what settles the answer.",
                "Medium",
            ],
            [
                "7",
                "File operations are lossless and non-destructive",
                "1287 characters were read and 1287 written in both directions, the original sample "
                "files were left untouched and an existing output file was never replaced without "
                "explicit confirmation.",
                "Informational",
            ],
        ],
        [0.35, 1.5, 3.15, 1.0],
    )

    h2(document, "5.2 Analysis")
    body(
        document,
        "The results show a clear progression from trivial to subtle, and each stage depends on the "
        "one before it. The Caesar cipher fails on its first weakness, the size of the key: with "
        "twenty-six possible keys an exhaustive search costs nothing, and the chi-square score merely "
        "automates the human step of deciding which of the twenty-six candidates looks like English. "
        "The frequency analysis explains why that works. Because the shift maps every letter of the "
        "plaintext to exactly one letter of the ciphertext, the shape of the distribution is preserved "
        "and simply slides along the alphabet; the Index of Coincidence stays close to the English "
        "value and confirms that a single alphabet was used, which is the fingerprint of a "
        "monoalphabetic cipher.",
    )
    body(
        document,
        "The Vigenere cipher defeats that specific attack but not the underlying idea. Its overall "
        "Index of Coincidence of 0.04351 is barely above the value for random text, so counting "
        "letters in the whole ciphertext reveals nothing. What it cannot hide is repetition. Whenever "
        "the keyword realigns with the plaintext, the same plaintext fragment is encrypted with the "
        "same part of the key, so exact repeats appear at distances that are multiples of the key "
        "length. Both observations in the sample - OWCSI and WCSID repeating 500 and 395 letters "
        "apart, and both distances divisible by 5 - pointed straight at a key length of five. The "
        "tool did not act on that alone: it also measured the average Index of Coincidence of the "
        "columns for every candidate length, because when the guessed length is right each column "
        "contains one consistent Caesar shift and therefore looks like ordinary language again. Key "
        "length 5 scored 0.07079 on that measure while the equally well supported length 2 scored "
        "only 0.04341, and combining both kinds of evidence is what pushed 5 to the top.",
    )
    body(
        document,
        "Once the length was fixed at five, the cipher collapsed into five independent Caesar ciphers "
        "and the rest followed mechanically. Each column was scored against English letter "
        "frequencies, the best three letters were suggested for each position and complete keys were "
        "assembled from those suggestions. L, E, M, O and N emerged with scores between 50 and 58 "
        "against alternatives in the low twenties, and the full key LEMON scored 70.15 and decrypted "
        "the whole file into readable prose. Two lessons from the results are worth stating "
        "explicitly. First, a large keyspace does not make a cipher strong: 26^5 is more than eleven "
        "million keys, which is far beyond brute force by hand, yet the key fell to statistics in a "
        "fraction of a second because the cipher leaks structure rather than because the key was "
        "guessed. Second, statistical output must be read critically. Key length 2 had almost as much "
        "Kasiski support as key length 5, and only the column Index of Coincidence and the "
        "readability of the decrypted text separated them, which is why the tool labels every "
        "estimate as an estimate and always prints the decrypted preview beside the candidate key.",
    )
    body(
        document,
        "The security assessments close the loop with the theory. The report for the Vigenere cipher "
        "says directly that its keyspace is not the weakness, and the experiments above are the "
        "evidence for that statement. Both ciphers share weaknesses that no amount of care can fix: "
        "they are deterministic, so identical plaintext always produces identical ciphertext; they "
        "provide no integrity protection, so ciphertext can be altered without detection; and they "
        "share a single secret key, so the problem of delivering the key is never solved. Those "
        "limitations are exactly what modern cryptography replaced with large random keys, "
        "authenticated encryption and reviewed algorithms, which is why the tool's verdict for both "
        "ciphers is educational use only.",
    )


def build_challenges(document) -> None:
    banner(document, "SECTION 6 - CHALLENGES FACED", new_page=True)
    h1(document, "6. Challenges Faced")
    body(
        document,
        "Several problems came up during the build and during the demonstrations. They are recorded "
        "here together with the solution that was adopted, because most of them changed the design "
        "of the tool.",
    )
    data_table(
        document,
        ["Challenge Faced", "How I Solved It"],
        [
            [
                "The cryptanalysis output is statistical, and it is easy to present a guess as a "
                "confirmed result.",
                "Every estimated value is labelled in the output itself - 'Candidate key lengths "
                "(estimated)', 'BEST GUESS (unconfirmed)' - the decrypted preview is always printed "
                "next to a candidate key so that it can be judged by reading it, and the notes state "
                "plainly that estimates must be verified.",
            ],
            [
                "The interactive menu blocked the automated tests, because input() waits forever when "
                "the tool is fed from a pipe or a file.",
                "The prompt helper catches EOFError, sets an end-of-input flag and returns the "
                "default, and the menu checks that flag after every operation, so a piped session "
                "exits cleanly instead of looping.",
            ],
            [
                "The accented letter in 'Vigenere' crashed the tool on a console using a legacy "
                "Windows code page.",
                "Output streams are reconfigured with errors='replace' at start-up, so an "
                "unencodable character degrades gracefully instead of raising "
                "UnicodeEncodeError, and colours are disabled automatically when the output is not "
                "an interactive terminal.",
            ],
            [
                "Kasiski examination produced false positives: a short repeated fragment can appear "
                "by chance and its distance may be divisible by an innocent number.",
                "Repeated sequences are reported only from a minimum length of three characters, "
                "the factors are ranked by the amount of evidence rather than by a single match, and "
                "the result is combined with the column Index of Coincidence before any key length "
                "is used.",
            ],
            [
                "Some commands produce more output than fits on one page, which made the first "
                "screenshots unreadable in the report.",
                "Long outputs were split into consecutive figures at natural boundaries (header, "
                "evidence tables, recovery, best guess) and long lines are soft-wrapped at the width "
                "of the window shown, so the text in every figure stays legible.",
            ],
            [
                "A file operation could overwrite the very file it was reading from.",
                "The file handler refuses to write unless the destination is different or "
                "--overwrite is given, the default output name adds the suffix _out, and the "
                "interactive mode asks for confirmation before replacing anything.",
            ],
        ],
        [2.6, 3.9],
    )


def build_learning(document) -> None:
    banner(document, "SECTION 7 - LEARNING OUTCOMES", new_page=True)
    h1(document, "7. Learning Outcomes")
    body(document, "Working through this project produced the following concrete skills and insights:", space_after=6)
    for item in (
        "I can explain why the Caesar cipher collapses under an exhaustive search and implement the "
        "search myself, scoring candidates with the chi-square statistic instead of relying on a "
        "single frequency comparison.",
        "I understand the difference between a monoalphabetic and a polyalphabetic cipher in "
        "measurable terms: the Caesar sample held an Index of Coincidence of 0.06987 close to "
        "English, while the Vigenere sample fell to 0.04351 close to random text.",
        "I can carry out a Kasiski examination by hand on a short ciphertext - finding repeated "
        "fragments, measuring the distances, factorising them and reading the shared factors as "
        "candidate key lengths - and I know that the result is a hypothesis rather than a fact.",
        "I understand why guessing the key length correctly makes the columns look like ordinary "
        "language again, which is exactly what the average Index of Coincidence per key length "
        "measures, and how that test separated key length 5 (0.07079) from key length 2 (0.04341).",
        "I can recover a Vigenere keyword column by column by treating every column as its own "
        "Caesar cipher, and I verified the recovered key by reading the decrypted text rather than "
        "by trusting the score.",
        "I learned why a large keyspace is not the same thing as security: 26^5 is over eleven "
        "million keys, yet the Vigenere sample was cracked from statistics alone, which is the "
        "lesson that carries over to modern cryptography.",
        "On the engineering side I practised structuring a program into focused packages, writing "
        "defensive input validation, keeping interactive, command line and test driven use of the "
        "same algorithms in sync, and backing the whole tool with 163 automated tests.",
    ):
        bullet(document, item)


def build_conclusion(document) -> None:
    banner(document, "SECTION 8 - CONCLUSION & FUTURE SCOPE", new_page=True)
    h1(document, "8. Conclusion")
    body(
        document,
        "The project met its objectives. A single self-contained Python tool now implements the "
        "Caesar and Vigenere ciphers, breaks the first by exhaustive search with chi-square scoring, "
        "and breaks the second by combining frequency analysis, the Index of Coincidence and Kasiski "
        "examination. Run against the supplied sample data it recovered the Caesar shift of 3 "
        "automatically and, with no knowledge of the plaintext, reduced the Vigenere sample to an "
        "estimated key length of 5 and the exact keyword LEMON as the highest ranked candidate. Both "
        "ciphers were also assessed for strength and reported as unsuitable for protecting real "
        "information.",
    )
    body(
        document,
        "The most valuable result is not the recovered key itself but the demonstration of how "
        "security is lost. The Caesar cipher failed because its keyspace is tiny; the Vigenere cipher "
        "had a keyspace of more than eleven million keys for a five-letter keyword and failed "
        "anyway, because a repeating key leaves statistical traces - repeated sequences at regular "
        "distances and columns that behave like plain language once the length is known. The project "
        "also showed how easy it is to mistake a statistical estimate for a proof: key length 2 had "
        "almost the same Kasiski evidence as the correct length 5 and was rejected only after its "
        "column Index of Coincidence and its decrypted output were examined. That habit of verifying "
        "evidence, which the tool enforces by labelling every guess as a guess and printing the "
        "decrypted text beside the candidate key, is the most transferable outcome of the exercise.",
    )
    body(
        document,
        "If the project were repeated, the cryptanalysis engine would be separated cleanly from the "
        "presentation layer from the start, and a non-interactive batch mode would be added early so "
        "that a whole folder of sample files could be analysed and compared in one run instead of "
        "one command at a time.",
    )

    h2(document, "8.1 Future Scope")
    body(document, "The following extensions would build naturally on what already exists:", space_after=6)
    for item in (
        "Add further classical ciphers (affine, Playfair, columnar transposition, one-time pad) "
        "and reuse the existing frequency and Index of Coincidence modules to attack them.",
        "Implement the Friedman test and mutual Index of Coincidence so that key length estimation "
        "no longer depends on repeated sequences alone.",
        "Add a graphical interface (Tkinter or a small web front end) that displays the letter "
        "frequency chart and the candidate ranking side by side for teaching purposes.",
        "Add multi-file batch analysis with a summary table so that several ciphertexts can be "
        "compared in one run.",
        "Compare the classical ciphers against a modern reference implementation of AES to show the "
        "transition from key secrecy to algorithm transparency.",
        "Support non-English alphabets and language profiles, so that the frequency and fitness "
        "scoring can be applied to text in other languages.",
    ):
        bullet(document, item)


def build_references(document) -> None:
    banner(document, "SECTION 9 - REFERENCES", new_page=True)
    h1(document, "9. References")
    references = [
        "[1] Caesar cipher - Wikipedia. https://en.wikipedia.org/wiki/Caesar_cipher",
        "[2] Vigenere cipher - Wikipedia. https://en.wikipedia.org/wiki/Vigen%C3%A8re_cipher",
        "[3] Kasiski examination - Wikipedia. https://en.wikipedia.org/wiki/Kasiski_examination",
        "[4] Index of coincidence - Wikipedia. https://en.wikipedia.org/wiki/Index_of_coincidence",
        "[5] Chi-squared test - Wikipedia. https://en.wikipedia.org/wiki/Chi-squared_test",
        "[6] Python 3.13 documentation - Standard library reference (argparse, dataclasses, pathlib, "
        "statistics, unittest). https://docs.python.org/3/library/",
        "[7] python-docx documentation - reading and writing Microsoft Word files. "
        "https://python-docx.readthedocs.io/",
        "[8] Labmentix Cybersecurity Training Program - course notes and 15-day project brief "
        "(internal training material).",
    ]
    for entry in references:
        paragraph = document.add_paragraph()
        paragraph.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        paragraph.paragraph_format.space_after = Pt(6)
        paragraph.paragraph_format.line_spacing = 1.15
        style_run(paragraph.add_run(entry), size=10.5, font=ARIAL)


def build_declaration(document) -> None:
    banner(document, "DECLARATION", new_page=True)
    h1(document, "Student Declaration")
    body(
        document,
        "I hereby declare that this project report is my own original work, completed as part of "
        "the Labmentix Cybersecurity Training Program. The work presented in this report is "
        "genuine, and all external references have been duly acknowledged.",
    )
    body(
        document,
        "All commands, results and screenshots in Section 4 were produced by running the tool that "
        "accompanies this report on the sample data supplied with the project; the console output "
        "behind every figure is retained in the project folder for verification.",
    )

    spacer = document.add_paragraph()
    spacer.paragraph_format.space_after = Pt(36)

    table = document.add_table(rows=1, cols=2)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table_borders(table)
    for index in (0, 1):
        cell = table.cell(0, index)
        cell.width = Inches(3.25)
        cell_margins(cell, top=120, left=200, bottom=120, right=200)

    # The hand written signature is placed above its caption line, which is
    # where a printed report is signed.  Drop any image at
    # report_assets/signature.png and it is used here automatically.
    signature_cell = table.cell(0, 0)
    if SIGNATURE.exists():
        image_paragraph = signature_cell.paragraphs[0]
        image_paragraph.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
        image_paragraph.paragraph_format.space_before = Pt(4)
        image_paragraph.paragraph_format.space_after = Pt(0)
        image_paragraph.add_run().add_picture(str(SIGNATURE), width=Inches(1.0))
        label_paragraph = signature_cell.add_paragraph()
    else:
        label_paragraph = signature_cell.paragraphs[0]
        label_paragraph.add_run("\n\n\n")
    label_paragraph.paragraph_format.space_after = Pt(0)
    style_run(label_paragraph.add_run("Student Signature"), size=10.5, font=ARIAL)

    date_paragraph = table.cell(0, 1).paragraphs[0]
    date_paragraph.paragraph_format.space_after = Pt(0)
    style_run(date_paragraph.add_run("\n\n\nDate of Submission"), size=10.5, font=ARIAL)


#: Canonical child order of the property elements, as required by the OOXML
#: schema.  python-docx inserts its own elements in order but the hand-built
#: ones are appended, so the document is sorted before it is saved.
PPR_ORDER = (
    "w:pStyle", "w:keepNext", "w:keepLines", "w:pageBreakBefore", "w:framePr", "w:widowControl",
    "w:numPr", "w:suppressLineNumbers", "w:pBdr", "w:shd", "w:tabs", "w:suppressAutoHyphens",
    "w:kinsoku", "w:wordWrap", "w:overflowPunct", "w:topLinePunct", "w:autoSpaceDE",
    "w:autoSpaceDN", "w:bidi", "w:adjustRightInd", "w:snapToGrid", "w:spacing", "w:ind",
    "w:contextualSpacing", "w:mirrorIndents", "w:suppressOverlap", "w:jc", "w:textDirection",
    "w:textAlignment", "w:textboxTightWrap", "w:outlineLvl", "w:divId", "w:cnfStyle", "w:rPr",
    "w:sectPr", "w:pPrChange",
)
TCPR_ORDER = (
    "w:cnfStyle", "w:tcW", "w:gridSpan", "w:hMerge", "w:vMerge", "w:tcBorders", "w:shd",
    "w:noWrap", "w:tcMar", "w:textDirection", "w:tcFitText", "w:vAlign", "w:hideMark",
    "w:tcPrChange",
)
TBLPR_ORDER = (
    "w:tblStyle", "w:tblpPr", "w:tblOverlap", "w:bidiVisual", "w:tblStyleRowBandSize",
    "w:tblStyleColBandSize", "w:tblW", "w:jc", "w:tblCellSpacing", "w:tblInd", "w:tblBorders",
    "w:shd", "w:tblLayout", "w:tblCellMar", "w:tblLook", "w:tblCaption", "w:tblDescription",
)
TRPR_ORDER = (
    "w:cnfStyle", "w:divId", "w:gridBefore", "w:gridAfter", "w:wBefore", "w:wAfter",
    "w:cantSplit", "w:trHeight", "w:tblHeader", "w:tblCellSpacing", "w:jc", "w:hidden",
)


def sort_properties(document) -> None:
    """Reorder property elements so the file is schema-valid for Word."""
    body = document.element.body
    for tag, order in (
        ("w:pPr", PPR_ORDER),
        ("w:tcPr", TCPR_ORDER),
        ("w:tblPr", TBLPR_ORDER),
        ("w:trPr", TRPR_ORDER),
    ):
        rank = {qn(name): index for index, name in enumerate(order)}
        for parent in body.iter(qn(tag)):
            children = list(parent)
            if len(children) < 2:
                continue
            children.sort(key=lambda element: rank.get(element.tag, len(order)))
            for child in children:
                parent.append(child)


def polish_typography(document) -> None:
    """Use a proper en dash in prose while leaving code boxes untouched."""
    def fix(paragraph) -> None:
        for run in paragraph.runs:
            if run.font.name != COURIER and " - " in run.text:
                run.text = run.text.replace(" - ", " \u2013 ")

    for paragraph in document.paragraphs:
        fix(paragraph)
    for table in document.tables:
        for row in table.rows:
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    fix(paragraph)


def main() -> int:
    if not FIGURE_DIR.exists():
        raise SystemExit("run tools/build_figures.py first: no figures were found")

    document = Document(TEMPLATE)

    # Clear the template body but keep its styles, numbering and page setup.
    element = document.element.body
    for child in list(element.iterchildren()):
        if child.tag != qn("w:sectPr"):
            element.remove(child)

    build_cover(document)
    build_contents(document)
    build_abstract(document)
    build_introduction(document)
    build_tools(document)
    build_methodology(document)
    build_results(document)
    build_challenges(document)
    build_learning(document)
    build_conclusion(document)
    build_references(document)
    build_declaration(document)

    fill_footer(document)
    sort_properties(document)
    polish_typography(document)
    document.save(OUTPUT)
    print(f"Wrote {OUTPUT.name}")
    print(f"Figures inserted: {_figure_number}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
