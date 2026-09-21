#!/usr/bin/env python3
"""Print a captured session with line numbers and ANSI codes stripped."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ANSI = re.compile(r"\x1b\[[0-9;]*m")


def main() -> None:
    for name in sys.argv[1:]:
        path = Path("report_assets/captures") / f"{name}.txt"
        text = ANSI.sub("", path.read_text(encoding="utf-8"))
        lines = text.splitlines()
        print(f"===== {name}  ({len(lines)} lines) =====")
        for index, line in enumerate(lines, start=1):
            print(f"{index:>3} | {line}")


if __name__ == "__main__":
    main()
