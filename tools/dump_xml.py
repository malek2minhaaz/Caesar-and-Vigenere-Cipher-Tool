#!/usr/bin/env python3
"""Print the raw WordprocessingML of chosen blocks of a .docx file."""

from __future__ import annotations

import sys

from docx import Document
from docx.oxml.ns import qn

WANTED = [int(value) for value in sys.argv[2:]] if len(sys.argv) > 2 else []


def main() -> None:
    document = Document(sys.argv[1])
    body = document.element.body
    for index, child in enumerate(body.iterchildren()):
        if child.tag == qn("w:sectPr"):
            print(f"[{index}] SECTION PROPERTIES")
            print(child.xml)
            continue
        if WANTED and index not in WANTED:
            continue
        print(f"[{index}] {child.tag.split('}')[-1]}")
        print(child.xml)
        print()


if __name__ == "__main__":
    main()
