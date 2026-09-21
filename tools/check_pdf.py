#!/usr/bin/env python3
"""Inspect the exported PDF: pagination, figures per page and blank space.

Every page is also rendered to ``report_assets/pdf_preview/page-NN.png`` so the
layout can be reviewed without opening the document.

Run from the repository root::

    python tools/check_pdf.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import fitz  # PyMuPDF

PROJECT = Path(__file__).resolve().parent.parent
PDF = PROJECT / "Cryptographic_Cipher_Analyzer_Project_Report.pdf"
PREVIEW_DIR = PROJECT / "report_assets" / "pdf_preview"

#: A page whose lowest ink ends far above the bottom marignal edge looks empty.
TAIL_THRESHOLD = 0.72


#: The header and footer bands are ignored when measuring how full a page is.
BODY_TOP = 0.09
BODY_BOTTOM = 0.91


def ink_bounds(page: "fitz.Page") -> tuple[float, float]:
    """Return the vertical extent of the page's body ink as fractions of height.

    The running header and footer are excluded, otherwise every page would look
    completely full.
    """
    height = page.rect.height
    top = height * BODY_BOTTOM
    bottom = 0.0
    for block in page.get_text("blocks"):
        if not BODY_TOP * height < block[1] < BODY_BOTTOM * height:
            continue
        top = min(top, block[1])
        bottom = max(bottom, block[3])
    for image in page.get_image_info():
        top = min(top, image["bbox"][1])
        bottom = max(bottom, image["bbox"][3])
    return (top / height, bottom / height) if bottom else (0.0, 0.0)


def overlapping(page: "fitz.Page") -> list[str]:
    """Report captions that are actually drawn on top of a figure.

    Word word boxes are used rather than paragraph boxes, because a paragraph's
    line box legitimately reaches back over an inline image while the glyphs are
    painted below it.
    """
    images = [fitz.Rect(image["bbox"]) for image in page.get_image_info()]
    clashes = []
    for word in page.get_text("words"):
        rectangle = fitz.Rect(word[:4])
        for image in images:
            if (rectangle & image).get_area() > 0.5 * rectangle.get_area():
                clashes.append(word[4])
    return clashes[:4]


def main() -> int:
    if not PDF.exists():
        print(f"! {PDF.name} not found - run tools/export_pdf.py first", file=sys.stderr)
        return 1

    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    document = fitz.open(PDF)
    print(f"File        : {PDF.name}")
    print(f"Pages       : {document.page_count}")
    print(f"Page size   : {document[0].rect.width:.0f} x {document[0].rect.height:.0f} pt")
    print()
    print(f"{'page':>4}  {'figs':>4}  {'chars':>6}  {'ink top':>7}  {'ink end':>7}  content")
    print("-" * 96)

    total_images = 0
    for index, page in enumerate(document, start=1):
        images = len(page.get_image_info())
        total_images += images
        text = page.get_text()
        caption = re.search(r"Figure (\d+):", text)
        first = next((line.strip() for line in text.splitlines() if line.strip()), "")
        marker = f"Figure {caption.group(1)}" if caption else ""
        top, bottom = ink_bounds(page)
        flag = "   <-- short page" if bottom and bottom < TAIL_THRESHOLD else ""
        clash = overlapping(page)
        if clash:
            flag += f"   !! overlap: {clash}"
        print(
            f"{index:>4}  {images:>4}  {len(text):>6}  {top:>7.2f}  {bottom:>7.2f}  "
            f"{marker or first[:48]}{flag}"
        )
        page.get_pixmap(dpi=96).save(PREVIEW_DIR / f"page-{index:02d}.png")

    print("-" * 96)
    print(f"Total figures placed: {total_images}")
    print(f"Previews written to : {PREVIEW_DIR}")

    outline = document.get_toc()
    print(f"PDF bookmarks       : {len(outline)}")
    document.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
