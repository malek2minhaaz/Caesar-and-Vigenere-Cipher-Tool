"""Report generation.

Analysis results can be written to ``reports/analysis_YYYYMMDD_HHMMSS.txt``.
The builder below keeps the layout in one place so every report has the same
professional header regardless of which operation produced it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Iterable, Sequence

from analysis.security import EDUCATIONAL_DISCLAIMER

#: Width of the banner rules used inside generated reports.
REPORT_RULE_WIDTH: int = 49

#: Name of the folder (relative to the project root) holding generated reports.
REPORTS_DIRECTORY_NAME: str = "reports"


def project_root() -> Path:
    """Return the absolute path of the project root directory."""
    return Path(__file__).resolve().parent.parent


def reports_directory(create: bool = True) -> Path:
    """Return the reports directory, creating it when *create* is ``True``."""
    directory = project_root() / REPORTS_DIRECTORY_NAME
    if create:
        directory.mkdir(parents=True, exist_ok=True)
    return directory


def timestamped_filename(prefix: str = "analysis", extension: str = "txt") -> str:
    """Build a unique report file name such as ``analysis_20260915_184500.txt``."""
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{prefix}_{stamp}.{extension}"


def _rule(character: str = "=") -> str:
    return character * REPORT_RULE_WIDTH


@dataclass
class ReportBuilder:
    """Assemble a plain-text analysis report.

    Example:
        >>> report = ReportBuilder(cipher="Caesar", operation="Encryption")
        >>> report.add_key_value("Shift", 3)
        >>> report.add_section("Result", ["KHOOR ZLRUOG"])
        >>> text = report.render()
    """

    cipher: str
    operation: str
    summary: list[tuple[str, str]] = field(default_factory=list)
    sections: list[tuple[str, list[str]]] = field(default_factory=list)
    note: str = EDUCATIONAL_DISCLAIMER
    created_at: datetime = field(default_factory=datetime.now)

    def add_key_value(self, label: str, value: object) -> "ReportBuilder":
        """Add a line to the ``Input statistics`` header block."""
        self.summary.append((str(label), str(value)))
        return self

    def add_section(self, title: str, lines: Iterable[object]) -> "ReportBuilder":
        """Add a titled section containing one string per line."""
        self.sections.append((title, [str(line) for line in lines]))
        return self

    def add_paragraph(self, title: str, text: str) -> "ReportBuilder":
        """Add a titled section holding a paragraph of prose."""
        return self.add_section(title, [line for line in text.splitlines() if line.strip()])

    def render(self) -> str:
        """Return the complete report as a single string."""
        lines: list[str] = [
            _rule(),
            "CRYPTOGRAPHIC CIPHER ANALYSIS REPORT",
            _rule(),
            "",
            f"Date: {self.created_at.strftime('%Y-%m-%d %H:%M:%S')}",
            f"Cipher: {self.cipher}",
            f"Operation: {self.operation}",
            "",
        ]

        if self.summary:
            lines.append("Input statistics:")
            lines.append("-" * len("Input statistics:"))
            width = max((len(label) for label, _ in self.summary), default=0)
            lines.extend(f"{label.ljust(width)} : {value}" for label, value in self.summary)
            lines.append("")

        for title, section_lines in self.sections:
            lines.append(f"{title}:")
            lines.append("-" * len(f"{title}:"))
            lines.extend(section_lines)
            lines.append("")

        lines.append("Educational note:")
        lines.append("-" * len("Educational note:"))
        lines.extend(self.note.splitlines())
        lines.append("")
        return "\n".join(lines)


def save_report(
    content: str,
    directory: Path | str | None = None,
    prefix: str = "analysis",
    filename: str | None = None,
) -> Path:
    """Write *content* to a report file and return the path that was written.

    Args:
        content: Report text.
        directory: Destination folder; defaults to ``<project>/reports``.
        prefix: Prefix used when generating the timestamped file name.
        filename: Explicit file name, overriding the generated one.

    Raises:
        OSError: If the report cannot be written.
    """
    target_directory = Path(directory) if directory is not None else reports_directory()
    target_directory.mkdir(parents=True, exist_ok=True)
    path = target_directory / (filename or timestamped_filename(prefix))
    path.write_text(content, encoding="utf-8")
    return path


def format_frequency_report_lines(
    total_characters: int,
    total_letters: int,
    rows: Sequence[Sequence[object]],
    headers: Sequence[str] = ("Letter", "Count", "Frequency"),
) -> list[str]:
    """Render a frequency table as fixed-width text lines for a report."""
    columns = len(headers)
    widths = [len(header) for header in headers]
    string_rows = [[str(cell) for cell in row[:columns]] for row in rows]
    for row in string_rows:
        for index, cell in enumerate(row):
            widths[index] = max(widths[index], len(cell))

    def render_row(cells: Sequence[str]) -> str:
        return "  ".join(
            f"{cell:<{widths[index]}}" for index, cell in enumerate(cells)
        ).rstrip()

    lines = [
        f"Total characters    : {total_characters}",
        f"Alphabetic characters: {total_letters}",
        "",
        render_row(list(headers)),
        "-" * (sum(widths) + 2 * (columns - 1)),
    ]
    lines.extend(render_row(row) for row in string_rows)
    return lines
