#!/usr/bin/env python3
"""Render captured console output as a realistic terminal-window PNG.

The picture is produced with Pillow: a dark window with a macOS/Windows style
title bar, and monospaced text in which the ANSI escape sequences emitted by the
tool (bold, dim, colour) are translated back into real colours.  Long lines are
soft-wrapped at the terminal width, exactly as a real console would wrap them.

Example::

    from terminal_shot import render_terminal
    render_terminal(["$ python main.py", "OK"], title="Command Prompt").save("shot.png")
"""

from __future__ import annotations

import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ANSI_RE = re.compile(r"\x1b\[([0-9;]*)m")

#: Terminal geometry (in "base" pixels; everything is multiplied by *scale*).
COLUMNS = 96
FONT_SIZE = 15
LINE_SPACING = 1.32
PADDING = 14
TITLE_BAR = 24
RADIUS = 8

BACKGROUND = (12, 12, 12)
TITLE_BACKGROUND = (50, 50, 51)
BORDER = (62, 62, 62)
TITLE_TEXT = (204, 204, 204)
DEFAULT_FG = (204, 204, 204)
DIMMED_FG = (118, 118, 118)
COMMAND_FG = (232, 232, 232)
PROMPT_FG = (35, 209, 139)

PALETTE = {
    31: (241, 76, 76),
    32: (35, 209, 139),
    33: (245, 222, 90),
    34: (59, 142, 234),
    35: (188, 140, 255),
    36: (41, 184, 219),
    37: (229, 229, 229),
}

FONT_REGULAR = "C:/Windows/Fonts/consola.ttf"
FONT_BOLD = "C:/Windows/Fonts/consolab.ttf"
FONT_FALLBACK = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
FONT_FALLBACK_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"


_FONT_CACHE: dict[tuple[bool, int], ImageFont.FreeTypeFont] = {}


def _font(bold: bool, size: int) -> ImageFont.FreeTypeFont:
    """Load a monospaced font, falling back to a DejaVu build when missing."""
    key = (bold, size)
    cached = _FONT_CACHE.get(key)
    if cached is not None:
        return cached
    candidates = (
        [FONT_BOLD, FONT_FALLBACK_BOLD] if bold else [FONT_REGULAR, FONT_FALLBACK, FONT_FALLBACK_BOLD]
    )
    font = None
    for path in candidates:
        if Path(path).exists():
            font = ImageFont.truetype(path, size)
            break
    if font is None:  # pragma: no cover - only on systems without any of the fonts
        font = ImageFont.load_default(size)
    _FONT_CACHE[key] = font
    return font


def parse_ansi(line: str) -> list[tuple[str, tuple[int, int, int], bool]]:
    """Split *line* into ``(text, colour, bold)`` runs."""
    runs: list[tuple[str, tuple[int, int, int], bool]] = []
    colour, bold = DEFAULT_FG, False
    position = 0
    for match in ANSI_RE.finditer(line):
        if match.start() > position:
            runs.append((line[position : match.start()], colour, bold))
        for code in [c for c in match.group(1).split(";") if c] or ["0"]:
            value = int(code)
            if value == 0:
                colour, bold = DEFAULT_FG, False
            elif value == 1:
                bold = True
            elif value == 2:
                colour = DIMMED_FG
            elif value == 22:
                bold = False
            elif value == 39:
                colour = DEFAULT_FG
            elif value in PALETTE:
                colour = PALETTE[value]
        position = match.end()
    if position < len(line):
        runs.append((line[position:], colour, bold))
    return runs


def style_command(line: str) -> list[tuple[str, tuple[int, int, int], bool]]:
    """Highlight a shell transcript line such as ``$ python main.py``."""
    if line.startswith("$ "):
        prompt, _, command = line.partition(" ")
        return [(prompt + " ", PROMPT_FG, True), (command, COMMAND_FG, True)]
    return parse_ansi(line)


def _wrap(runs: list[tuple[str, tuple[int, int, int], bool]], columns: int):
    """Soft-wrap styled runs to *columns* characters per visual line."""
    lines: list[list[tuple[str, tuple[int, int, int], bool]]] = [[]]
    used = 0
    for text, colour, bold in runs:
        piece = ""
        for character in text:
            if used == columns:
                lines[-1].append((piece, colour, bold))
                lines.append([])
                piece, used = "", 0
            piece += character
            used += 1
        if piece:
            if lines[-1] and lines[-1][-1][1:] == (colour, bold):
                previous, _, previous_bold = lines[-1][-1]
                lines[-1][-1] = (previous + piece, colour, previous_bold)
            else:
                lines[-1].append((piece, colour, bold))
    return lines


def render_terminal(
    lines: list[str],
    title: str = "Command Prompt",
    columns: int = COLUMNS,
    scale: int = 2,
) -> Image.Image:
    """Render *lines* inside a terminal window and return the image."""
    font_size = FONT_SIZE * scale
    bold_font_size = font_size
    line_height = round(FONT_SIZE * LINE_SPACING) * scale
    padding = PADDING * scale
    title_bar = TITLE_BAR * scale
    radius = RADIUS * scale

    regular = _font(False, font_size)
    bold = _font(True, bold_font_size)
    title_font = _font(True, round(FONT_SIZE * 0.8) * scale)

    wrapped: list[list[tuple[str, tuple[int, int, int], bool]]] = []
    for line in lines:
        wrapped.extend(_wrap(style_command(line), columns))

    char_width = regular.getlength("M")
    width = int(padding * 2 + char_width * columns)
    height = int(title_bar + padding * 2 + line_height * len(wrapped))

    image = Image.new("RGB", (width, height), BORDER)
    draw = ImageDraw.Draw(image)

    # Window body.
    draw.rounded_rectangle(
        (0, 0, width - 1, height - 1), radius=radius, fill=BACKGROUND
    )
    # Title bar with square bottom corners.
    draw.rounded_rectangle(
        (0, 0, width - 1, int(title_bar * 1.6)),
        radius=radius,
        fill=TITLE_BACKGROUND,
        corners=(True, True, False, False),
    )
    draw.rectangle((0, title_bar - 1, width - 1, title_bar - 1), fill=(38, 38, 39))

    # Window buttons.
    dot_radius = 5 * scale
    for index, colour in enumerate(((255, 95, 86), (255, 189, 46), (39, 201, 63))):
        centre_x = padding + index * dot_radius * 3
        centre_y = title_bar // 2
        draw.ellipse(
            (
                centre_x - dot_radius,
                centre_y - dot_radius,
                centre_x + dot_radius,
                centre_y + dot_radius,
            ),
            fill=colour,
        )

    title_width = draw.textlength(title, font=title_font)
    draw.text(
        ((width - title_width) / 2, (title_bar - title_font.size) / 2 - 1),
        title,
        font=title_font,
        fill=TITLE_TEXT,
    )

    y = title_bar + padding
    for visual_line in wrapped:
        x = padding
        for text, colour, is_bold in visual_line:
            active = bold if is_bold else regular
            draw.text((x, y), text, font=active, fill=colour)
            x += active.getlength(text)
        y += line_height

    return image


def measure_terminal(
    lines: list[str],
    columns: int = COLUMNS,
    scale: int = 2,
) -> tuple[int, int]:
    """Return the pixel size :func:`render_terminal` would produce for *lines*.

    Used by the figure builder to decide how many console lines fit in a slice
    without having to render the picture twice.
    """
    font_size = FONT_SIZE * scale
    line_height = round(FONT_SIZE * LINE_SPACING) * scale
    padding = PADDING * scale
    title_bar = TITLE_BAR * scale
    char_width = _font(False, font_size).getlength("M")
    visual_lines = 0
    for line in lines:
        visual_lines += len(_wrap(style_command(line), columns))
    width = int(padding * 2 + char_width * columns)
    height = int(title_bar + padding * 2 + line_height * visual_lines)
    return width, height


def has_image(config: dict) -> bool:  # pragma: no cover - tiny helper
    """Return ``True`` when *config* looks like a renderable figure."""
    return bool(config.get("lines"))
