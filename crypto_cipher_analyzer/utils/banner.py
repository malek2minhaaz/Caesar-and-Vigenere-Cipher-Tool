"""Terminal presentation helpers.

All CLI output goes through this module, which keeps the look of the tool
consistent and lets colour be disabled automatically on terminals that do not
understand ANSI escape sequences (redirected output, some Windows consoles).
The application never depends on colour: every message is readable as plain
text and coloured text is only ever an enhancement.
"""

from __future__ import annotations

import os
import shutil
import sys
from typing import Iterable, Sequence

#: Width of the decorative rules used across the CLI.
RULE_WIDTH: int = 57

STYLE_RESET = "\033[0m"
STYLE_BOLD = "\033[1m"
STYLE_DIM = "\033[2m"
STYLE_RED = "\033[31m"
STYLE_GREEN = "\033[32m"
STYLE_YELLOW = "\033[33m"
STYLE_BLUE = "\033[34m"
STYLE_CYAN = "\033[36m"

_COLOR_SUPPORT: bool | None = None
_EOF_REACHED: bool = False


def _enable_windows_ansi() -> bool:
    """Enable virtual terminal processing on Windows consoles.

    Returns:
        ``True`` when ANSI sequences can be used, ``False`` otherwise.
    """
    if os.name != "nt":  # pragma: no cover - platform specific
        return True
    try:  # pragma: no cover - platform specific
        import ctypes

        kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
        handle = kernel32.GetStdHandle(-11)
        mode = ctypes.c_uint32()
        if not kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            return False
        return bool(kernel32.SetConsoleMode(handle, mode.value | 0x0004))
    except Exception:  # pragma: no cover - defensive
        return False


def supports_color(stream: object | None = None) -> bool:
    """Decide whether ANSI colours should be emitted.

    Honours the ``NO_COLOR`` and ``FORCE_COLOR`` environment variables, requires
    an interactive terminal, and enables virtual terminal processing on Windows.
    """
    global _COLOR_SUPPORT
    if _COLOR_SUPPORT is not None:
        return _COLOR_SUPPORT

    target = stream if stream is not None else sys.stdout
    if os.environ.get("NO_COLOR"):
        _COLOR_SUPPORT = False
    elif os.environ.get("FORCE_COLOR"):
        _COLOR_SUPPORT = True
    elif os.environ.get("TERM", "") == "dumb":
        _COLOR_SUPPORT = False
    elif not getattr(target, "isatty", lambda: False)():
        _COLOR_SUPPORT = False
    else:
        _COLOR_SUPPORT = _enable_windows_ansi()
    return _COLOR_SUPPORT


def reset_color_cache() -> None:
    """Forget the cached colour decision (used by tests and by ``--no-color``)."""
    global _COLOR_SUPPORT
    _COLOR_SUPPORT = None


def disable_color() -> None:
    """Force plain text output for the rest of the session."""
    global _COLOR_SUPPORT
    _COLOR_SUPPORT = False


def colorize(text: str, *styles: str) -> str:
    """Wrap *text* in ANSI *styles* when the terminal supports colour."""
    if not styles or not supports_color():
        return text
    return "".join(styles) + text + STYLE_RESET


def _emit(message: str = "") -> None:
    """Print *message* defensively.

    A console that cannot encode a character (for example an accented letter on
    a legacy Windows code page) must never crash the application.
    """
    try:
        print(message)
    except UnicodeEncodeError:  # pragma: no cover - platform specific
        encoding = getattr(sys.stdout, "encoding", None) or "ascii"
        print(message.encode(encoding, "replace").decode(encoding, "replace"))


def terminal_width() -> int:
    """Return the usable terminal width, clamped to a sensible range."""
    width = shutil.get_terminal_size((80, 24)).columns
    return max(40, min(width, 120))


def eof_reached() -> bool:
    """Return ``True`` when standard input has been exhausted.

    The interactive menu uses this to exit cleanly instead of looping forever
    when the tool is fed from a pipe, a file or an automated test.
    """
    return _EOF_REACHED


def reset_eof_flag() -> None:
    """Clear the end-of-input flag (called once at start-up)."""
    global _EOF_REACHED
    _EOF_REACHED = False


def print_rule(character: str = "=", width: int = RULE_WIDTH) -> None:
    """Print a horizontal rule of *character*."""
    _emit(character * width)


def print_block(text: object, indent: str = "  ") -> None:
    """Print *text* as an indented block, one line at a time."""
    lines = str(text).splitlines() or [""]
    for line in lines:
        _emit(f"{indent}{line}" if line else "")


def print_banner(
    title: str = "CRYPTOGRAPHIC CIPHER ANALYZER",
    subtitle: str = "Caesar & Vigenère Cryptanalysis Tool",
) -> None:
    """Print the application banner."""
    _emit()
    print_rule()
    _emit(colorize(f"        {title}", STYLE_BOLD, STYLE_CYAN))
    _emit(colorize(f"        {subtitle}", STYLE_CYAN))
    print_rule()
    _emit()
    _emit("Purpose: Educational cybersecurity and cryptography analysis tool")


def print_menu(options: Sequence[tuple[str, str]], title: str = "MAIN MENU") -> None:
    """Print a numbered menu.

    Args:
        options: ``(number, label)`` pairs.
        title: Heading printed above the entries.
    """
    _emit()
    print_section(title)
    width = max((len(number) for number, _ in options), default=1)
    for number, label in options:
        _emit(f"  [{number}]".ljust(width + 5) + label)
    _emit()


def print_section(title: str) -> str:
    """Print a section heading and return it (convenient for tests)."""
    line = f"{title}"
    _emit()
    _emit(colorize(line, STYLE_BOLD))
    _emit(colorize("-" * max(len(line), 12), STYLE_DIM))
    return line


def print_success(message: str) -> None:
    """Print a success message."""
    _emit(f"{colorize('[OK]', STYLE_GREEN, STYLE_BOLD)} {message}")


def print_error(message: str) -> None:
    """Print an error message."""
    _emit(f"{colorize('[ERROR]', STYLE_RED, STYLE_BOLD)} {message}")


def print_warning(message: str) -> None:
    """Print a warning message."""
    _emit(f"{colorize('[WARNING]', STYLE_YELLOW, STYLE_BOLD)} {message}")


def print_info(message: str) -> None:
    """Print an informational message."""
    _emit(f"{colorize('[INFO]', STYLE_BLUE, STYLE_BOLD)} {message}")


def print_note(message: str) -> None:
    """Print an explanatory note, wrapped to the terminal width."""
    width = terminal_width() - 2
    paragraphs = [paragraph.strip() for paragraph in message.strip().splitlines()]
    _emit()
    for paragraph in paragraphs:
        if not paragraph:
            _emit()
            continue
        for line in _wrap(paragraph, width):
            _emit(colorize(f"  {line}", STYLE_DIM))


def _wrap(text: str, width: int) -> list[str]:
    """Wrap *text* without importing :mod:`textwrap` at module level."""
    import textwrap

    return textwrap.wrap(text, width=width) or [""]


def print_key_values(pairs: Iterable[tuple[str, object]], indent: str = "  ") -> None:
    """Print aligned ``label: value`` lines."""
    items = [(str(label), str(value)) for label, value in pairs]
    if not items:
        return
    width = max(len(label) for label, _ in items)
    for label, value in items:
        _emit(f"{indent}{label.ljust(width)} : {value}")


def print_table(
    headers: Sequence[str],
    rows: Iterable[Sequence[object]],
    aligns: Sequence[str] | None = None,
    title: str | None = None,
    indent: str = "  ",
) -> None:
    """Print a simple, dependency-free ASCII table.

    Args:
        headers: Column headings.
        rows: Rows of cell values.
        aligns: Per-column alignment characters (``"<"``, ``">"`` or ``"^"``).
        title: Optional table caption.
        indent: String printed before every line.
    """
    if not headers:
        return
    columns = len(headers)
    string_rows = [[str(cell) for cell in row[:columns]] for row in rows]
    widths = [len(str(header)) for header in headers]
    for row in string_rows:
        for index, cell in enumerate(row):
            widths[index] = max(widths[index], len(cell))

    alignment = list(aligns or ["<"] * columns)
    while len(alignment) < columns:
        alignment.append("<")

    if title:
        _emit(f"{indent}{title}")

    def format_row(cells: Sequence[str]) -> str:
        padded = [
            f"{cell:{alignment[index]}{widths[index]}}"
            for index, cell in enumerate(cells)
        ]
        return indent + "  ".join(padded).rstrip()

    _emit(colorize(format_row([str(header) for header in headers]), STYLE_BOLD))
    _emit(indent + "-" * (sum(widths) + 2 * (columns - 1)))
    for row in string_rows:
        _emit(format_row(row))


def prompt(label: str, default: str | None = None) -> str:
    """Read a line from the user.

    Returns the raw (stripped) input. ``EOFError`` returns the default so that
    piping input into the tool cannot crash it.
    """
    global _EOF_REACHED
    suffix = f" [{default}]" if default is not None else ""
    try:
        answer = input(f"{label}{suffix}: ")
    except EOFError:
        _EOF_REACHED = True
        _emit()
        return default if default is not None else ""
    if not answer.strip() and default is not None:
        return default
    return answer.strip()


def confirm(question: str, default: bool = False) -> bool:
    """Ask a yes/no question and return the answer as a boolean."""
    default_text = "y" if default else "n"
    while True:
        answer = prompt(f"{question}", default=default_text).strip().lower()
        if answer in {"y", "yes"}:
            return True
        if answer in {"n", "no", ""}:
            return False
        print_error("Please answer 'y' or 'n'.")


def pause(message: str = "Press Enter to return to the main menu") -> None:
    """Wait for the user to press Enter."""
    global _EOF_REACHED
    try:
        input(f"{message}...")
    except EOFError:
        _EOF_REACHED = True
        _emit()


def print_disclaimer(text: str | None = None) -> None:
    """Print the educational-use disclaimer in a framed block."""
    if text is None:
        from analysis.security import EDUCATIONAL_DISCLAIMER

        text = EDUCATIONAL_DISCLAIMER
    width = max(len(line) for line in text.splitlines()) + 2
    print_rule("=", width)
    for line in text.splitlines():
        _emit(colorize(line, STYLE_YELLOW))
    print_rule("=", width)
