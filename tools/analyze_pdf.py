"""Report how much blank space is left at the bottom of each PDF page.

Usage:  python tools/analyze_pdf.py [pdf] [--min-in 1.0]

Content area of the template is roughly y = 50 pt .. y = 738 pt (the footer
starts at about y = 744).  Anything below the last content block on a page is
white space that a reader perceives as an empty gap.
"""
from __future__ import annotations

import sys
from pathlib import Path

import fitz

PT_PER_IN = 72.0
CONTENT_TOP = 52.0
CONTENT_BOTTOM = 738.0
FOOTER_TOP = 738.0


def page_last_content(page: "fitz.Page") -> float:
    """Return the y of the bottom-most content block that is not the footer."""
    last = CONTENT_TOP
    d = page.get_text("dict")
    for block in d["blocks"]:
        y1 = block["bbox"][3]
        if y1 >= FOOTER_TOP:
            continue
        # ignore the header band
        if block["bbox"][1] < CONTENT_TOP and y1 < CONTENT_TOP + 6:
            continue
        last = max(last, y1)
    return last


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    pdf = Path(args[0]) if args else Path("Cryptographic_Cipher_Analyzer_Project_Report.pdf")
    min_gap = 1.0
    for a in sys.argv[1:]:
        if a.startswith("--min-in"):
            min_gap = float(a.split("=", 1)[1]) if "=" in a else 1.0

    doc = fitz.open(pdf)
    gaps = []
    print(f"{pdf}  ({doc.page_count} pages)\n")
    print(f"{'page':>4} {'ends at':>8} {'gap (in)':>9}   note")
    total = 0.0
    for i, page in enumerate(doc, start=1):
        last = page_last_content(page)
        gap = max(0.0, CONTENT_BOTTOM - last) / PT_PER_IN
        total += gap
        gaps.append(gap)
        note = "empty band" if gap >= min_gap else ""
        print(f"{i:>4} {last:>8.1f} {gap:>9.2f}   {note}")

    worst = sorted(range(len(gaps)), key=lambda k: -gaps[k])[:6]
    print(f"\ntotal blank space at page bottoms: {total:.1f} in "
          f"({total / doc.page_count:.2f} in per page avg)")
    print(f"pages with the biggest gaps: "
          + ", ".join(f"p{i + 1} ({gaps[i]:.1f}in)" for i in worst))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
