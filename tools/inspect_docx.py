#!/usr/bin/env python3
"""Dump the structure of a .docx file so it can be inspected in a terminal."""

from __future__ import annotations

import sys

from docx import Document
from docx.table import Table
from docx.text.paragraph import Paragraph


def iter_block_items(parent):
    """Yield paragraphs and tables of *parent* in document order."""
    from docx.document import Document as _Document
    from docx.oxml.ns import qn

    if isinstance(parent, _Document):
        parent_elm = parent.element.body
    else:  # pragma: no cover - cells
        parent_elm = parent._tc
    for child in parent_elm.iterchildren():
        if child.tag == qn("w:p"):
            yield Paragraph(child, parent)
        elif child.tag == qn("w:tbl"):
            yield Table(child, parent)


def main(path: str) -> None:
    document = Document(path)
    for index, block in enumerate(iter_block_items(document)):
        if isinstance(block, Paragraph):
            style = block.style.name if block.style is not None else "?"
            text = block.text
            runs = "|".join(run.text for run in block.runs)
            print(f"[{index:03d}] P style={style!r} runs={len(block.runs)} text={text!r}")
        else:
            print(f"[{index:03d}] TABLE rows={len(block.rows)} cols={len(block.columns)}")
            for row_index, row in enumerate(block.rows):
                cells = [cell.text.replace("\n", " / ") for cell in row.cells]
                print(f"        r{row_index}: {cells}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "Labmentix_Project_Report_Template.docx")
