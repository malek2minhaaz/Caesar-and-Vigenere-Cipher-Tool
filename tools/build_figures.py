#!/usr/bin/env python3
"""Turn the captured sessions into numbered figure images for the report.

Each figure is a contiguous slice of one captured session rendered as a
terminal window (see :mod:`terminal_shot`).  Every slice is deliberately kept
short enough to fit on a page together with its caption.

Run from the repository root::

    python tools/build_figures.py
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

from PIL import Image

from terminal_shot import measure_terminal, render_terminal

PROJECT = Path(__file__).resolve().parent.parent
CAPTURE_DIR = PROJECT / "report_assets" / "captures"
FIGURE_DIR = PROJECT / "report_assets" / "figures"

#: Width at which every screenshot is placed in the report, and the height a
#: slice of console output may occupy at that width.  A slice taller than this
#: is split in two so that two of them share a page; without the split a tall
#: screenshot is pushed to the next page and leaves half a page blank.
FIGURE_WIDTH = 6.5
MAX_SLICE_HEIGHT = float(os.environ.get("SLICE_HEIGHT", "3.6"))

#: A trailing slice shorter than this many lines is merged back into the slice
#: before it.
MIN_TAIL_LINES = 4

ANSI = re.compile(r"\x1b\[[0-9;]*m")

#: The values typed during the interactive walkthrough, in the order they were
#: entered.  A piped session cannot echo them, so they are re-inserted here to
#: reproduce what the screen really showed.
TYPED_INPUT: list[tuple[str, str]] = [
    ("Enter your choice:", "1"),
    ("Selection [1]:", "1"),
    ("Selection [1]:", "1"),
    ("Enter the plaintext:", "HELLO WORLD"),
    ("Caesar shift (for example 3) [3]:", "3"),
    ("Save this analysis as a report? [y/n] [n]:", "n"),
    ("Press Enter to return to the main menu...", ""),
    ("Enter your choice:", "9"),
]

#: name, capture file, first line, last line (1-based, inclusive), window title
FIGURES: list[dict] = [
    {"file": "fig01_environment", "capture": "01_environment", "range": (1, 4),
     "title": "Command Prompt - python --version"},
    {"file": "fig02_structure", "capture": "02_structure", "range": (1, 12),
     "title": "Command Prompt - project structure"},
    {"file": "fig02b_modules", "capture": "02_structure", "range": (13, 41),
     "title": "Command Prompt - Python packages"},
    {"file": "fig03_launch", "capture": "03_launch", "range": (1, 32),
     "title": "Command Prompt - python main.py"},
    {"file": "fig04_caesar", "capture": "04_caesar_cli", "range": (1, 29),
     "title": "Command Prompt - Caesar cipher"},
    {"file": "fig05_vigenere", "capture": "05_vigenere_cli", "range": (1, 31),
     "title": "Command Prompt - Vigenere cipher"},
    {"file": "fig06_interactive_menu", "capture": "06_interactive_caesar",
     "range": ("MAIN MENU", "Caesar shift (for example 3)"),
     "title": "Command Prompt - interactive mode"},
    {"file": "fig07_interactive_exit", "capture": "06_interactive_caesar",
     "range": ("CAESAR ENCRYPTION", "End of input detected"),
     "title": "Command Prompt - interactive mode"},
    {"file": "fig08_frequency", "capture": "07_frequency", "range": (1, 39),
     "title": "Command Prompt - frequency analysis"},
    {"file": "fig09_crack_a", "capture": "08_crack_caesar", "range": (1, 31),
     "title": "Command Prompt - breaking the Caesar cipher"},
    {"file": "fig10_crack_b", "capture": "08_crack_caesar", "range": (32, 60),
     "title": "Command Prompt - recovered plaintext"},
    {"file": "fig11_ic", "capture": "09_ic", "range": (1, 29),
     "title": "Command Prompt - index of coincidence"},
    {"file": "fig12_kasiski_a", "capture": "10_kasiski", "range": (1, 32),
     "title": "Command Prompt - Kasiski examination"},
    {"file": "fig13_kasiski_b", "capture": "10_kasiski", "range": (33, 62),
     "title": "Command Prompt - Kasiski examination"},
    {"file": "fig14_vigenere_a", "capture": "11_vigenere_analysis", "range": (1, 30),
     "title": "Command Prompt - Vigenere cryptanalysis"},
    {"file": "fig15_vigenere_b", "capture": "11_vigenere_analysis", "range": (31, 60),
     "title": "Command Prompt - key recovery"},
    {"file": "fig16_vigenere_c", "capture": "11_vigenere_analysis", "range": (61, 89),
     "title": "Command Prompt - recovered key"},
    {"file": "fig17_file_decrypt", "capture": "12_file_decrypt", "range": (1, 22),
     "title": "Command Prompt - decrypting a file"},
    {"file": "fig18_file_encrypt", "capture": "13_file_encrypt", "range": (1, 21),
     "title": "Command Prompt - encrypting a file"},
    {"file": "fig19_security_caesar", "capture": "14_security_caesar", "range": (1, 39),
     "title": "Command Prompt - security assessment"},
    {"file": "fig20_security_vigenere", "capture": "15_security_vigenere", "range": (1, 41),
     "title": "Command Prompt - security assessment"},
    {"file": "fig21_report_saved", "capture": "16_report_file", "range": (1, 22),
     "title": "Command Prompt - saving an analysis report"},
    {"file": "fig22_report_content", "capture": "17_report_content", "range": (1, 40),
     "title": "Text file - generated analysis report"},
    {"file": "fig23_tests", "capture": "18_test_suite", "range": (-20, -1),
     "title": "Command Prompt - automated test suite"},
]


def read_capture(name: str) -> list[str]:
    """Return the captured session as a list of lines (ANSI kept)."""
    text = (CAPTURE_DIR / f"{name}.txt").read_text(encoding="utf-8")
    return text.replace("\r\n", "\n").split("\n")


def insert_typed_input(lines: list[str]) -> list[str]:
    """Re-insert the characters typed during an interactive session.

    A session fed from a pipe never echoes the user's keystrokes, so the prompts
    run into each other.  This rebuilds the screen a real user would have seen:
    the typed value follows its prompt and the next prompt starts on a new line.
    """
    pending = list(TYPED_INPUT)
    output: list[str] = []
    for line in lines:
        current = ""
        rest = line
        while pending:
            prompt, value = pending[0]
            index = rest.find(prompt)
            if index == -1:
                break
            end = index + len(prompt)
            current += rest[:end] + (" " + value if value else "")
            rest = rest[end:].lstrip()
            pending.pop(0)
            if rest:
                output.append(current)
                current = ""
        current += rest
        output.append(current)
    return output


def slice_lines(lines: list[str], bounds: tuple) -> list[str]:
    """Return the requested slice of *lines*.

    Bounds may be integers (1-based, negative counts from the end) or the
    literal text of the first / last line to include.
    """
    start, end = bounds
    if isinstance(start, str):
        first = next(
            (i for i, line in enumerate(lines) if start in ANSI.sub("", line)),
            None,
        )
        assert first is not None, f"start marker not found: {start!r}"
        start = first + 1
    if isinstance(end, str):
        last = next(
            (i for i, line in enumerate(lines) if end in ANSI.sub("", line)),
            None,
        )
        assert last is not None, f"end marker not found: {end!r}"
        end = last + 1
    if isinstance(start, int) and start < 0:
        start = len(lines) + start + 1
    if isinstance(end, int) and end < 0:
        end = len(lines) + end + 1
    return lines[start - 1 : end]


def show(name: str) -> None:
    """Print a capture with line numbers (for choosing figure ranges)."""
    lines = read_capture(name)
    if name == "06_interactive_caesar":
        lines = insert_typed_input(lines)
    for index, line in enumerate(lines, start=1):
        print(f"{index:>3} | {ANSI.sub('', line)}")


def columns_for(lines: list[str]) -> int:
    """Return the terminal width used for *lines* (72-96 columns)."""
    plain_width = max(len(ANSI.sub("", line)) for line in lines)
    return max(72, min(96, plain_width + 2))


def displayed_height(lines: list[str], width: float = FIGURE_WIDTH) -> float:
    """Height in inches that *lines* occupy when drawn *width* inches wide."""
    pixel_width, pixel_height = measure_terminal(lines, columns=columns_for(lines))
    return width * pixel_height / pixel_width


def slice_by_height(lines: list[str]) -> list[list[str]]:
    """Split *lines* into consecutive runs that each fit in one figure block.

    Slicing is driven by the height the render will actually have rather than by
    a fixed number of lines, so wide tables and narrow listings both end up with
    blocks of about the same height.  A run that would end with one or two lines
    is rebalanced with the run before it, because a figure holding a single line
    of output is not worth its caption.
    """
    chunks: list[list[str]] = []
    current: list[str] = []
    for line in lines:
        candidate = current + [line]
        if len(candidate) > 1 and displayed_height(candidate) > MAX_SLICE_HEIGHT:
            chunks.append(current)
            current = [line]
        else:
            current = candidate
    if current:
        chunks.append(current)

    while len(chunks) > 1 and len(chunks[-1]) < MIN_TAIL_LINES and len(chunks[-2]) > MIN_TAIL_LINES:
        chunks[-1].insert(0, chunks[-2].pop())
    return chunks


def main() -> int:
    if len(sys.argv) > 2 and sys.argv[1] == "--show":
        show(sys.argv[2])
        return 0

    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    # Remove figures from a previous run so that a renamed or re-sliced figure
    # can never be placed from a stale file.
    for stale in FIGURE_DIR.glob("*.png"):
        stale.unlink()

    manifest: list[dict] = []
    for figure in FIGURES:
        lines = read_capture(figure["capture"])
        if figure["capture"] == "06_interactive_caesar":
            lines = insert_typed_input(lines)

        selected = slice_lines(lines, figure["range"])
        # Drop leading / trailing blank lines so the window hugs the content.
        while selected and not ANSI.sub("", selected[0]).strip():
            selected.pop(0)
        while selected and not ANSI.sub("", selected[-1]).strip():
            selected.pop()
        assert selected, f"{figure['file']} is empty"

        chunks = slice_by_height(selected)
        entries: list[dict] = []
        for index, chunk in enumerate(chunks, start=1):
            columns = columns_for(chunk)
            image = render_terminal(chunk, title=figure["title"], columns=columns)
            name = figure["file"] if len(chunks) == 1 else f"{figure['file']}_{index}"
            path = FIGURE_DIR / f"{name}.png"
            image.save(path)
            page_height = round(FIGURE_WIDTH * image.height / image.width, 2)
            entries.append(
                {
                    "file": name,
                    "path": str(path.relative_to(PROJECT)).replace("\\", "/"),
                    "lines": len(chunk),
                    "width": image.width,
                    "height": image.height,
                    "page_height": page_height,
                }
            )
            flag = "  <-- taller than the slice budget" if page_height > MAX_SLICE_HEIGHT + 0.05 else ""
            print(
                f"{name:<30} lines={len(chunk):>3}  "
                f"{image.width}x{image.height}  page={page_height}in{flag}"
            )

        manifest.append(
            {
                "figure": figure["file"],
                "capture": figure["capture"],
                "title": figure["title"],
                "slices": entries,
            }
        )

    payload = {"figure_width": FIGURE_WIDTH, "figures": manifest}
    (CAPTURE_DIR / "figures.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    total = sum(len(entry["slices"]) for entry in manifest)
    print(f"\nRendered {total} figures from {len(manifest)} captured sessions into {FIGURE_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
