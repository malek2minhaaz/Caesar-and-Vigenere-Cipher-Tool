#!/usr/bin/env python3
"""Convert a PDF back into an editable Word document using Microsoft Word.

Word opens a PDF in "reflow" mode and rewrites it as editable content, which is
lossy: the original heading styles, section properties, header/footer fields and
table structure are reconstructed from the printed page rather than restored.

Usage::

    python tools/pdf_to_docx.py <input.pdf> <output.docx> [--justify]

``--justify`` restores the justified alignment of the body text.  Word's PDF
reflow always produces ragged-right paragraphs, so without this flag the
converted document is less like the PDF it came from, not more.
"""

from __future__ import annotations

import sys
from pathlib import Path

WD_FORMAT_DOCX = 16          # wdFormatXMLDocument
WD_DO_NOT_SAVE_CHANGES = 0


def justify_body_text(document) -> int:
    """Justify every left-aligned paragraph, in the body and in tables.

    Centred content (figure captions, the cover title) and right-aligned content
    are left alone.
    """
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml.ns import qn

    changed = 0

    def fix(paragraph) -> None:
        nonlocal changed
        if not paragraph.text.strip():
            return
        properties = paragraph._p.get_or_add_pPr()
        alignment = properties.find(qn("w:jc"))
        value = alignment.get(qn("w:val")) if alignment is not None else None
        if value in (None, "left", "start"):
            paragraph.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            changed += 1

    for paragraph in document.paragraphs:
        fix(paragraph)
    for table in document.tables:
        for row in table.rows:
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    fix(paragraph)
    return changed


def convert(source: Path, target: Path) -> None:
    """Ask Word to open *source* (a PDF) and save it as *target* (.docx)."""
    import win32com.client

    word = None
    document = None
    try:
        word = win32com.client.DispatchEx("Word.Application")
        word.Visible = False
        word.DisplayAlerts = 0
        document = word.Documents.Open(
            str(source), ReadOnly=False, AddToRecentFiles=False, Visible=False
        )
        document.SaveAs2(str(target), FileFormat=WD_FORMAT_DOCX)
    finally:
        if document is not None:
            document.Close(WD_DO_NOT_SAVE_CHANGES)
        if word is not None:
            word.Quit()


def main() -> int:
    arguments = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(arguments) != 2:
        print(__doc__)
        return 2
    source = Path(arguments[0]).resolve()
    target = Path(arguments[1]).resolve()
    if not source.exists():
        print(f"! {source} not found", file=sys.stderr)
        return 1

    target.parent.mkdir(parents=True, exist_ok=True)
    convert(source, target)

    if "--justify" in sys.argv:
        from docx import Document

        document = Document(target)
        restored = justify_body_text(document)
        document.save(target)
        print(f"Re-applied justified alignment to {restored} paragraphs")

    print(f"Wrote {target}  ({target.stat().st_size / 1024 / 1024:.2f} MB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
