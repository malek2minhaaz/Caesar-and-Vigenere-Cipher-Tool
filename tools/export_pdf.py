#!/usr/bin/env python3
"""Export the finished report to PDF using Microsoft Word.

Word is driven through COM automation so that the PDF is byte-for-byte what a
user would get from File > Save As > PDF: identical pagination, fonts and image
placement.  Running Word is only used for the conversion; the document is opened
read-only and closed again without being modified.

Run from the repository root::

    python tools/export_pdf.py
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
SOURCE = PROJECT / "Cryptographic_Cipher_Analyzer_Project_Report.docx"
TARGET = PROJECT / "Cryptographic_Cipher_Analyzer_Project_Report.pdf"

WD_EXPORT_FORMAT_PDF = 17
WD_EXPORT_HEADING_BOOKMARKS = 1
WD_DO_NOT_SAVE_CHANGES = 0


def export_with_word(source: Path, target: Path) -> None:
    """Convert *source* to *target* with Word COM automation."""
    import win32com.client  # imported lazily: Windows only

    word = None
    document = None
    try:
        word = win32com.client.DispatchEx("Word.Application")
        word.Visible = False
        word.DisplayAlerts = 0
        document = word.Documents.Open(
            str(source), ReadOnly=True, AddToRecentFiles=False, Visible=False
        )
        document.ExportAsFixedFormat(
            OutputFileName=str(target),
            ExportFormat=WD_EXPORT_FORMAT_PDF,
            OpenAfterExport=False,
            OptimizeFor=0,           # 0 = print quality
            Range=0,                 # 0 = whole document
            Item=0,                  # 0 = document content
            IncludeDocProps=True,
            KeepIRM=True,
            CreateBookmarks=WD_EXPORT_HEADING_BOOKMARKS,
            DocStructureTags=True,
            BitmapMissingFonts=True,
            UseISO19005_1=False,
        )
    finally:
        if document is not None:
            document.Close(WD_DO_NOT_SAVE_CHANGES)
        if word is not None:
            word.Quit()


def export_with_docx2pdf(source: Path, target: Path) -> None:
    """Fallback conversion through the docx2pdf package."""
    from docx2pdf import convert

    convert(str(source), str(target))


def main() -> int:
    if not SOURCE.exists():
        print(f"! {SOURCE.name} not found - run tools/build_report.py first", file=sys.stderr)
        return 1

    try:
        export_with_word(SOURCE, TARGET)
        engine = "Microsoft Word"
    except Exception as error:  # noqa: BLE001 - fall back to the packaged converter
        print(f"Word automation failed ({error}); trying docx2pdf", file=sys.stderr)
        export_with_docx2pdf(SOURCE, TARGET)
        engine = "docx2pdf"

    if not TARGET.exists():
        print("! no PDF was produced", file=sys.stderr)
        return 1

    print(f"Wrote {TARGET.name} with {engine}")
    print(f"Size: {TARGET.stat().st_size / 1024 / 1024:.2f} MB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
