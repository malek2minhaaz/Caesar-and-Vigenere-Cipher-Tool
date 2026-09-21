#!/usr/bin/env python3
"""Build the Cryptographic Cipher Analyzer project presentation.

Creates a 20-slide PPTX from the real terminal captures in
``report_assets/figures`` with full speaker notes sized for a 7-10+ minute
talk. Run from the repository root::

    python tools/build_presentation.py

Output: ``Cryptographic_Cipher_Analyzer_Presentation.pptx``
"""

from __future__ import annotations

from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt

ROOT = Path(__file__).resolve().parents[1]
FIG = ROOT / "report_assets" / "figures"
OUT = ROOT / "Cryptographic_Cipher_Analyzer_Presentation.pptx"

# --------------------------------------------------------------------------- #
# Design constants (16:9, dark navy + cyan/green terminal theme)
# --------------------------------------------------------------------------- #
SLIDE_W = Inches(13.333)
SLIDE_H = Inches(7.5)

NAVY = RGBColor(0x0B, 0x1D, 0x3A)
NAVY_2 = RGBColor(0x12, 0x2B, 0x52)
ACCENT = RGBColor(0x3E, 0xB8, 0xF0)
ACCENT_DK = RGBColor(0x1E, 0x88, 0xC7)
GREEN = RGBColor(0x39, 0xD3, 0x53)
GREEN_PANEL = RGBColor(0x10, 0x33, 0x1B)
WHITE = RGBColor(0xF5, 0xF7, 0xFA)
MUTED = RGBColor(0x9A, 0xB4, 0xCC)
CODE_BG = RGBColor(0x03, 0x0E, 0x1C)

TITLE_FONT = "Segoe UI"
BODY_FONT = "Segoe UI"
MONO_FONT = "Consolas"


# --------------------------------------------------------------------------- #
# Deck / Slide helpers
# --------------------------------------------------------------------------- #
class Deck:
    def __init__(self) -> None:
        self.prs = Presentation()
        self.prs.slide_width = SLIDE_W
        self.prs.slide_height = SLIDE_H
        self.blank = self.prs.slide_layouts[6]
        self.count = 0

    def add_slide(self) -> "Slide":
        self.count += 1
        return Slide(self.prs.slides.add_slide(self.blank), self)

    def save(self) -> None:
        props = self.prs.core_properties
        props.title = "Cryptographic Cipher Analyzer"
        props.author = "Crypto Cipher Analyzer Project"
        props.subject = "Caesar & Vigenere Cryptanalysis Tool"
        props.comments = "20 slides; speaker notes sized for a 7-10+ minute talk"
        self.prs.save(OUT)


class Slide:
    def __init__(self, slide, deck: Deck) -> None:
        self.s = slide
        self.deck = deck

    # -- primitives -------------------------------------------------------- #
    def background(self, color: RGBColor) -> None:
        fill = self.s.background.fill
        fill.solid()
        fill.fore_color.rgb = color

    def rect(self, x, y, w, h, fill_color=None, line_color=None, line_w: float = 1.0):
        from pptx.enum.shapes import MSO_SHAPE

        shape = self.s.shapes.add_shape(MSO_SHAPE.RECTANGLE, x, y, w, h)
        shape.shadow.inherit = False
        if fill_color is None:
            shape.fill.background()
        else:
            shape.fill.solid()
            shape.fill.fore_color.rgb = fill_color
        if line_color is None:
            shape.line.fill.background()
        else:
            shape.line.color.rgb = line_color
            shape.line.width = Pt(line_w)
        return shape

    def text(self, x, y, w, h, runs, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP):
        """runs: list of (text, size_pt, color, bold, font_name, space_before_pt)."""
        box = self.s.shapes.add_textbox(x, y, w, h)
        tf = box.text_frame
        tf.word_wrap = True
        tf.vertical_anchor = anchor
        tf.margin_left = 0
        tf.margin_right = 0
        tf.margin_top = 0
        tf.margin_bottom = 0
        first = True
        for txt, size, color, bold, font, space_before in runs:
            p = tf.paragraphs[0] if first else tf.add_paragraph()
            first = False
            p.alignment = align
            if space_before:
                p.space_before = Pt(space_before)
            r = p.add_run()
            r.text = txt
            r.font.size = Pt(size)
            r.font.color.rgb = color
            r.font.bold = bold
            r.font.name = font
        return box

    def bullet_list(self, x, y, w, h, items, size: float = 14, color: RGBColor = WHITE,
                    line_gap: float = 6):
        """items: list of (bold_lead, rest)."""
        box = self.s.shapes.add_textbox(x, y, w, h)
        tf = box.text_frame
        tf.word_wrap = True
        tf.margin_left = 0
        tf.margin_right = 0
        tf.margin_top = 0
        tf.margin_bottom = 0
        first = True
        for lead, rest in items:
            p = tf.paragraphs[0] if first else tf.add_paragraph()
            first = False
            p.alignment = PP_ALIGN.LEFT
            p.space_after = Pt(line_gap)
            dot = p.add_run()
            dot.text = "\u2022  "
            dot.font.size = Pt(size)
            dot.font.color.rgb = ACCENT
            dot.font.name = BODY_FONT
            if lead:
                r1 = p.add_run()
                r1.text = lead
                r1.font.size = Pt(size)
                r1.font.color.rgb = color
                r1.font.bold = True
                r1.font.name = BODY_FONT
            if rest:
                r2 = p.add_run()
                r2.text = rest
                r2.font.size = Pt(size)
                r2.font.color.rgb = color
                r2.font.name = BODY_FONT
        return box

    # -- composed regions --------------------------------------------------- #
    def title_bar(self, kicker: str, title: str) -> None:
        self.rect(0, 0, SLIDE_W, Inches(1.06), fill_color=NAVY_2)
        self.rect(0, Inches(1.06), SLIDE_W, Pt(2.5), fill_color=ACCENT)
        self.text(Inches(0.55), Inches(0.14), Inches(9.5), Inches(0.3),
                  [(kicker, 11, ACCENT, True, BODY_FONT, 0)])
        self.text(Inches(0.55), Inches(0.38), Inches(11.5), Inches(0.6),
                  [(title, 26, WHITE, True, TITLE_FONT, 0)])
        self.rect(Inches(12.4), Inches(0.3), Inches(0.55), Inches(0.45), fill_color=NAVY)
        self.text(Inches(12.4), Inches(0.33), Inches(0.55), Inches(0.4),
                  [(f"{self.deck.count:02d}", 12, ACCENT, True, MONO_FONT, 0)],
                  align=PP_ALIGN.CENTER)

    def screenshot(self, path: Path, x, y, w, h, border: bool = True) -> None:
        """Fit an image inside (x, y, w, h), centred, with a thin border."""
        try:
            from PIL import Image

            with Image.open(path) as im:
                iw, ih = im.size
        except Exception:
            return
        scale = min(w / iw, h / ih)
        dw, dh = int(iw * scale), int(ih * scale)
        dx = x + int((w - dw) / 2)
        dy = y + int((h - dh) / 2)
        if border:
            self.rect(dx - 9525, dy - 9525, dw + 19050, dh + 19050,
                      fill_color=None, line_color=ACCENT_DK, line_w=1.0)
        self.s.shapes.add_picture(str(path), dx, dy, width=dw, height=dh)

    def footer(self, note: str) -> None:
        self.text(Inches(0.55), Inches(7.1), Inches(11.5), Inches(0.3),
                  [(note, 9, MUTED, False, BODY_FONT, 0)])

    def notes(self, text: str) -> None:
        self.s.notes_slide.notes_text_frame.text = text


# --------------------------------------------------------------------------- #
# Slide builders
# --------------------------------------------------------------------------- #
def slide_title(d: Deck) -> Slide:
    sl = d.add_slide()
    sl.background(NAVY)
    for i in range(4):
        x = SLIDE_W / 4 * i
        sl.rect(x, SLIDE_H - Inches(0.06), Inches(3.33), Pt(3), fill_color=ACCENT_DK)

    sl.rect(Inches(0.9), Inches(1.55), Inches(0.14), Inches(3.95), fill_color=ACCENT)
    sl.text(Inches(1.25), Inches(1.62), Inches(11.2), Inches(0.4),
            [("CRYPTOGRAPHY  \u00b7  PYTHON 3  \u00b7  CLI APPLICATION  \u00b7  EDUCATIONAL",
              13, ACCENT, True, BODY_FONT, 0)])
    sl.text(Inches(1.25), Inches(2.1), Inches(11.4), Inches(1.9),
            [("Cryptographic Cipher Analyzer", 44, WHITE, True, TITLE_FONT, 0),
             ("Caesar & Vigen\u00e8re Cryptanalysis Tool", 24, MUTED, False, BODY_FONT, 8)])
    sl.text(Inches(1.25), Inches(4.2), Inches(11.4), Inches(1.2),
            [("Encrypt \u00b7 Decrypt \u00b7 Analyze \u00b7 Break", 16, GREEN, True, MONO_FONT, 0),
             ("Frequency analysis  \u00b7  Index of Coincidence  \u00b7  Kasiski examination",
              14, MUTED, False, BODY_FONT, 8)])

    chips = [("163", "unit tests"), ("9", "CLI commands"), ("100%", "passing")]
    cx = Inches(1.25)
    for num, label in chips:
        sl.rect(cx, Inches(5.55), Inches(1.85), Inches(0.95), fill_color=NAVY_2)
        sl.text(cx, Inches(5.67), Inches(1.85), Inches(0.42),
                [(num, 22, ACCENT, True, TITLE_FONT, 0)], align=PP_ALIGN.CENTER)
        sl.text(cx, Inches(6.11), Inches(1.85), Inches(0.32),
                [(label, 11, MUTED, False, BODY_FONT, 0)], align=PP_ALIGN.CENTER)
        cx = cx + Inches(2.1)

    sl.text(Inches(1.25), Inches(6.85), Inches(11), Inches(0.4),
            [("Project viva presentation  \u00b7  2026", 13, MUTED, False, BODY_FONT, 0)])
    return sl


def slide_agenda(d: Deck) -> Slide:
    sl = d.add_slide()
    sl.background(NAVY)
    sl.title_bar("ROADMAP", "Agenda")
    items = [
        ("01   Introduction & Objectives", "What the tool is, why it exists, technology stack"),
        ("02   System Design", "Layered architecture and the request data flow"),
        ("03   Ciphers in Action", "Caesar & Vigen\u00e8re: CLI demos + interactive menu"),
        ("04   Cryptanalysis Engine", "Frequency \u00b7 IC \u00b7 Kasiski \u00b7 full key recovery"),
        ("05   Files & Reports", "Whole-file encryption and timestamped reports"),
        ("06   Security & Testing", "Honest security verdicts and 163 unit tests"),
        ("07   Conclusion", "Results, limitations and future work"),
    ]
    y = Inches(1.45)
    for head, desc in items:
        sl.rect(Inches(0.55), y, Inches(12.2), Inches(0.68), fill_color=NAVY_2)
        sl.rect(Inches(0.55), y, Inches(0.08), Inches(0.68), fill_color=ACCENT)
        sl.text(Inches(0.85), y + Inches(0.18), Inches(5.4), Inches(0.4),
                [(head, 15, WHITE, True, BODY_FONT, 0)])
        sl.text(Inches(6.4), y + Inches(0.2), Inches(6.2), Inches(0.4),
                [(desc, 12, MUTED, False, BODY_FONT, 0)])
        y = y + Inches(0.79)
    sl.footer("Target talk time: 8\u201312 minutes across 20 slides")
    return sl


def slide_intro(d: Deck) -> Slide:
    sl = d.add_slide()
    sl.background(NAVY)
    sl.title_bar("01 \u00b7 INTRODUCTION", "Project Overview & Objectives")
    bullets = [
        ("Command-line cryptanalysis laboratory. ",
         "A Python 3 CLI that encrypts, decrypts and breaks classical ciphers \u2014 Caesar and Vigen\u00e8re."),
        ("Every attack stage is automated. ",
         "Brute-force Caesar cracking, statistical key-length estimation, per-column Vigen\u00e8re key recovery."),
        ("Two complete interfaces. ",
         "Menu-driven interactive mode plus nine scriptable CLI subcommands."),
        ("Evidence trail built in. ",
         "Every analysis can be saved as a timestamped text report under reports/."),
        ("Honest security messaging. ",
         "Every run prints an educational disclaimer \u2014 classical ciphers are not secure."),
    ]
    sl.bullet_list(Inches(0.55), Inches(1.45), Inches(6.55), Inches(5.0), bullets,
                   size=14, line_gap=13)
    sl.screenshot(FIG / "fig03_launch_1.png", Inches(7.35), Inches(1.45), Inches(5.5), Inches(3.35))
    sl.screenshot(FIG / "fig03_launch_3.png", Inches(7.35), Inches(5.0), Inches(5.5), Inches(1.8))
    sl.footer("Screenshots: tool launch \u2014 banner, main menu and command reference")
    return sl


def slide_environment(d: Deck) -> Slide:
    sl = d.add_slide()
    sl.background(NAVY)
    sl.title_bar("01 \u00b7 ENVIRONMENT", "Technology Stack & Project Structure")
    left = [
        ("Python 3.13 ", "\u2014 pure standard library, zero third-party runtime dependencies"),
        ("Modular packages ", "\u2014 ciphers, analysis, file_operations, utils, tests"),
        ("Two interfaces ", "\u2014 interactive menu + 9 CLI subcommands"),
        ("Sample data & reports ", "\u2014 ready-made ciphertexts, timestamped output folder"),
        ("Verified quality ", "\u2014 163 unit tests run in ~0.6 s, all passing"),
    ]
    sl.bullet_list(Inches(0.55), Inches(1.5), Inches(6.0), Inches(4.8), left,
                   size=14, line_gap=13)
    sl.screenshot(FIG / "fig02_structure.png", Inches(6.85), Inches(1.45), Inches(3.05), Inches(4.5))
    sl.screenshot(FIG / "fig01_environment.png", Inches(10.05), Inches(1.45), Inches(2.8), Inches(0.95))
    sl.screenshot(FIG / "fig02b_modules_1.png", Inches(10.05), Inches(2.6), Inches(2.8), Inches(3.35))
    sl.footer("Screenshots: python --version, folder structure and Python packages")
    return sl


def slide_architecture(d: Deck) -> Slide:
    sl = d.add_slide()
    sl.background(NAVY)
    sl.title_bar("02 \u00b7 SYSTEM DESIGN", "Layered Architecture")
    layers = [
        ("USER INTERACTION",
         "Interactive menu (banner.py)   \u00b7   argparse CLI (main.py)", ACCENT),
        ("OPERATIONS",
         "Caesar / Vigen\u00e8re encrypt \u00b7 decrypt   \u00b7   Frequency \u00b7 IC \u00b7 Kasiski \u00b7 Security   \u00b7   Files \u00b7 Reports",
         GREEN),
        ("CORE ENGINES",
         "ciphers/caesar.py \u00b7 vigenere.py   \u00b7   analysis/caesar_cracker.py \u00b7 vigenere_analyzer.py",
         ACCENT),
        ("SHARED SERVICES",
         "validators \u00b7 text_utils \u00b7 report_generator \u2014 standard library only", MUTED),
    ]
    y = Inches(1.4)
    for name, detail, color in layers:
        h = Inches(1.2)
        sl.rect(Inches(0.55), y, Inches(7.55), h, fill_color=NAVY_2)
        sl.rect(Inches(0.55), y, Inches(0.1), h, fill_color=color)
        sl.text(Inches(0.85), y + Inches(0.12), Inches(6.9), Inches(0.35),
                [(name, 13, color, True, BODY_FONT, 0)])
        sl.text(Inches(0.85), y + Inches(0.5), Inches(6.9), Inches(0.62),
                [(detail, 11.5, WHITE, False, BODY_FONT, 0)])
        if name != "SHARED SERVICES":
            sl.text(Inches(9.2) if False else Inches(4.1), y + h + Inches(0.02),
                    Inches(0.5), Inches(0.3),
                    [("\u25bc", 12, MUTED, False, BODY_FONT, 0)], align=PP_ALIGN.CENTER)
        y = y + h + Inches(0.16)

    sl.rect(Inches(8.5), Inches(1.4), Inches(4.35), Inches(5.35), fill_color=NAVY_2)
    sl.text(Inches(8.8), Inches(1.62), Inches(3.8), Inches(0.4),
            [("WHY LAYERS?", 13, ACCENT, True, BODY_FONT, 0)])
    sl.bullet_list(Inches(8.8), Inches(2.1), Inches(3.8), Inches(4.5), [
        ("", "main.py only presents results \u2014 no cryptography lives there"),
        ("", "Each analysis module is independently testable"),
        ("", "Validators stop bad input before the engines run"),
        ("", "One ReportBuilder is shared by every command"),
        ("", "The 163 tests map directly to module boundaries"),
    ], size=12, line_gap=10)
    sl.footer("Design principle: presentation strictly separated from cryptanalysis logic")
    return sl


def slide_data_flow(d: Deck) -> Slide:
    sl = d.add_slide()
    sl.background(NAVY)
    sl.title_bar("02 \u00b7 SYSTEM DESIGN", "Request Flow: From Input to Report")
    steps = [
        ("1", "INPUT", "Typed text, file input, or CLI flags"),
        ("2", "VALIDATE", "validators.py \u2014 shift, key and text rules"),
        ("3", "PROCESS", "Cipher engines / analysis engines"),
        ("4", "PRESENT", "banner tables and ranked candidates"),
        ("5", "REPORT", "Optional timestamped text report"),
    ]
    x = Inches(0.55)
    w = Inches(2.28)
    gap = Inches(0.22)
    for num, name, desc in steps:
        sl.rect(x, Inches(1.65), w, Inches(2.05), fill_color=NAVY_2)
        sl.rect(x, Inches(1.65), w, Inches(0.09), fill_color=ACCENT)
        sl.text(x + Inches(0.18), Inches(1.85), w - Inches(0.36), Inches(0.5),
                [(num, 26, ACCENT, True, TITLE_FONT, 0)])
        sl.text(x + Inches(0.18), Inches(2.45), w - Inches(0.36), Inches(0.35),
                [(name, 14, WHITE, True, BODY_FONT, 0)])
        sl.text(x + Inches(0.18), Inches(2.85), w - Inches(0.36), Inches(0.8),
                [(desc, 11, MUTED, False, BODY_FONT, 0)])
        if num != "5":
            sl.text(x + w, Inches(2.5), gap, Inches(0.4),
                    [("\u25b6", 12, ACCENT, False, MONO_FONT, 0)], align=PP_ALIGN.CENTER)
        x = x + w + gap

    sl.rect(Inches(0.55), Inches(4.3), Inches(12.23), Inches(2.4), fill_color=NAVY_2)
    sl.text(Inches(0.85), Inches(4.5), Inches(11), Inches(0.35),
            [("ENGINEERING HIGHLIGHTS", 13, ACCENT, True, BODY_FONT, 0)])
    sl.bullet_list(Inches(0.85), Inches(4.95), Inches(11.6), Inches(1.7), [
        ("Never crashes on bad input: ",
         "invalid shifts, empty text and missing files produce friendly messages, not tracebacks"),
        ("Idempotent files: ",
         "the source file is never modified without explicit --overwrite confirmation"),
        ("Graceful EOF handling: ",
         "piped input or Ctrl+Z exits the menu cleanly"),
    ], size=12.5, line_gap=8)
    sl.footer("One pipeline serves both the interactive menu and the CLI commands")
    return sl


def slide_caesar(d: Deck) -> Slide:
    sl = d.add_slide()
    sl.background(NAVY)
    sl.title_bar("03 \u00b7 CIPHERS IN ACTION", "Caesar Cipher \u2014 Encryption & Decryption")
    left = [
        ("Mechanics: ",
         "every letter shifts by a fixed amount (mod 26); case, digits and punctuation are preserved"),
        ("Example: ",
         "\u201cHELLO WORLD\u201d + shift 3 \u2192 \u201cKHOOR ZRUOG\u201d"),
        ("CLI: ",
         'python main.py caesar-encrypt --text "HELLO WORLD" --shift 3'),
        ("Extras: ",
         "menu option 1, negative shifts, input from file, --report output"),
        ("Keyspace: ",
         "only 25 effective keys \u2014 the fatal weakness exploited on slide 11"),
    ]
    sl.bullet_list(Inches(0.55), Inches(1.5), Inches(6.55), Inches(4.8), left,
                   size=13.5, line_gap=12)
    sl.screenshot(FIG / "fig04_caesar_1.png", Inches(7.35), Inches(1.45), Inches(5.5), Inches(2.65))
    sl.screenshot(FIG / "fig04_caesar_2.png", Inches(7.35), Inches(4.25), Inches(5.5), Inches(2.3))
    sl.footer("Screenshots: Caesar encryption and decryption from the command line")
    return sl


def slide_vigenere(d: Deck) -> Slide:
    sl = d.add_slide()
    sl.background(NAVY)
    sl.title_bar("03 \u00b7 CIPHERS IN ACTION", "Vigen\u00e8re Cipher \u2014 Polyalphabetic Layer")
    left = [
        ("Mechanics: ",
         "a repeating keyword picks a different Caesar shift for every letter"),
        ("Example: ",
         "ATTACKATDAWN + key LEMON \u2192 LXFOPVEFRNHR (classic reference example)"),
        ("CLI: ",
         'python main.py vigenere-encrypt --text ... --key LEMON'),
        ("Strength over Caesar: ",
         "flattens single-letter frequencies \u2014 naive frequency analysis fails"),
        ("Hidden flaw: ",
         "the key repeats, and that repetition leaks structure (slide 13)"),
    ]
    sl.bullet_list(Inches(0.55), Inches(1.5), Inches(6.55), Inches(4.8), left,
                   size=13.5, line_gap=12)
    sl.screenshot(FIG / "fig05_vigenere_1.png", Inches(7.35), Inches(1.45), Inches(5.5), Inches(2.65))
    sl.screenshot(FIG / "fig05_vigenere_2.png", Inches(7.35), Inches(4.25), Inches(5.5), Inches(2.3))
    sl.footer("Screenshots: Vigen\u00e8re encryption with key LEMON and the matching decryption")
    return sl


def slide_interactive(d: Deck) -> Slide:
    sl = d.add_slide()
    sl.background(NAVY)
    sl.title_bar("03 \u00b7 CIPHERS IN ACTION", "Interactive Menu Mode")
    left = [
        ("Nine options ",
         "covering ciphers, analyses, files, security and help"),
        ("Guided prompts ",
         "validate every input and re-ask on mistakes \u2014 cannot be crashed"),
        ("Submenus ",
         "choose the source: type text or read from a file"),
        ("Report prompts ",
         "offer to save every analysis as a text file"),
        ("Crash-proof loop ",
         "invalid choices and end-of-input are handled without tracebacks"),
    ]
    sl.bullet_list(Inches(0.55), Inches(1.5), Inches(6.55), Inches(4.8), left,
                   size=13.5, line_gap=12)
    sl.screenshot(FIG / "fig06_interactive_menu_1.png", Inches(7.35), Inches(1.45), Inches(5.5), Inches(2.65))
    sl.screenshot(FIG / "fig06_interactive_menu_2.png", Inches(7.35), Inches(4.25), Inches(5.5), Inches(2.3))
    sl.footer("Screenshots: banner, main menu and a guided Caesar session")
    return sl


def slide_frequency(d: Deck) -> Slide:
    sl = d.add_slide()
    sl.background(NAVY)
    sl.title_bar("04 \u00b7 CRYPTANALYSIS", "Attack 1 \u2014 Letter Frequency Analysis")
    left = [
        ("Idea: ",
         "English is uneven \u2014 E, T and A dominate; counting letters exposes structure"),
        ("Output: ",
         "per-letter counts, percentages, and a ranked comparison vs standard English"),
        ("Reading it: ",
         "peaks at H, K, O, R are shifted E, T, A, O \u2014 an instant Caesar diagnosis"),
        ("Reuse: ",
         "the same counting powers the chi-square fitness score that ranks candidates"),
    ]
    sl.bullet_list(Inches(0.55), Inches(1.5), Inches(6.55), Inches(4.2), left,
                   size=13.5, line_gap=12)
    sl.rect(Inches(0.55), Inches(5.55), Inches(6.55), Inches(1.1), fill_color=GREEN_PANEL)
    sl.text(Inches(0.8), Inches(5.7), Inches(6.1), Inches(0.85),
            [("Foundation attack: ", 12.5, GREEN, True, BODY_FONT, 0),
             ("frequency counting feeds every later stage of the engine.",
              11.5, WHITE, False, BODY_FONT, 2)])
    sl.screenshot(FIG / "fig08_frequency_1.png", Inches(7.35), Inches(1.45), Inches(5.5), Inches(2.6))
    sl.screenshot(FIG / "fig08_frequency_2.png", Inches(7.35), Inches(4.2), Inches(5.5), Inches(2.65))
    sl.footer("Screenshots: frequency summary and comparison with standard English")
    return sl


def slide_crack_caesar(d: Deck) -> Slide:
    sl = d.add_slide()
    sl.background(NAVY)
    sl.title_bar("04 \u00b7 CRYPTANALYSIS", "Attack 2 \u2014 Automatic Caesar Cracking")
    left = [
        ("Method: ",
         "try all 26 shifts; score each with chi-square + digram fitness vs English"),
        ("Demo input: ",
         "1,287-character ciphertext from sample_data/caesar_sample.txt"),
        ("Result: ",
         "shift 3 ranked #1 with score 70.52 \u2014 runner-up only 22.94"),
        ("Output: ",
         "top-5 ranked candidate plaintexts + the best full decryption"),
        ("Statistical honesty: ",
         "an on-screen note warns that short or odd texts can mislead the ranking"),
    ]
    sl.bullet_list(Inches(0.55), Inches(1.5), Inches(6.55), Inches(4.8), left,
                   size=13.5, line_gap=12)
    sl.screenshot(FIG / "fig09_crack_a_2.png", Inches(7.35), Inches(1.45), Inches(5.5), Inches(2.4))
    sl.screenshot(FIG / "fig10_crack_b_1.png", Inches(7.35), Inches(3.95), Inches(5.5), Inches(2.75))
    sl.footer("Screenshots: ranked candidate table and BEST CANDIDATE block")
    return sl


def slide_ic(d: Deck) -> Slide:
    sl = d.add_slide()
    sl.background(NAVY)
    sl.title_bar("04 \u00b7 CRYPTANALYSIS", "Attack 3 \u2014 Index of Coincidence")
    left = [
        ("Definition: ",
         "IC = \u03a3 f\u1d62(f\u1d62\u22121) / N(N\u22121) \u2014 how unevenly letters are spread"),
        ("Benchmarks: ",
         "English \u2248 0.0667 \u00b7 random \u2248 0.0385"),
        ("Demo: ",
         "Vigen\u00e8re sample scores 0.0435 \u2014 low IC exposes polyalphabetic text"),
        ("Key-length probe: ",
         "average IC per assumed length spikes at the true length (here 5, 10, 15)"),
        ("Caution: ",
         "IC suggests, never proves \u2014 always corroborate with Kasiski evidence"),
    ]
    sl.bullet_list(Inches(0.55), Inches(1.5), Inches(6.55), Inches(4.8), left,
                   size=13.5, line_gap=12)
    sl.screenshot(FIG / "fig11_ic_1.png", Inches(7.35), Inches(1.45), Inches(5.5), Inches(2.8))
    sl.screenshot(FIG / "fig11_ic_2.png", Inches(7.35), Inches(4.4), Inches(5.5), Inches(2.1))
    sl.footer("Screenshots: IC summary and average IC per assumed key length")
    return sl


def slide_kasiski(d: Deck) -> Slide:
    sl = d.add_slide()
    sl.background(NAVY)
    sl.title_bar("04 \u00b7 CRYPTANALYSIS", "Attack 4 \u2014 Kasiski Examination")
    left = [
        ("Idea: ",
         "repeated ciphertext fragments appear where the key realigns with the text"),
        ("Maths: ",
         "distances between repeats are multiples of the key length; common factors are candidates"),
        ("Demo: ",
         "repeats at distances 500 and 395 \u2192 shared factors {5, 10, 20, 25}"),
        ("Ranking: ",
         "evidence-weighted key-length table \u2014 length 5 leads the list"),
        ("Honesty: ",
         "candidates are hypotheses to verify, not proven facts"),
    ]
    sl.bullet_list(Inches(0.55), Inches(1.5), Inches(6.55), Inches(4.8), left,
                   size=13.5, line_gap=12)
    sl.screenshot(FIG / "fig12_kasiski_a_2.png", Inches(7.35), Inches(1.45), Inches(5.5), Inches(2.8))
    sl.screenshot(FIG / "fig13_kasiski_b_2.png", Inches(7.35), Inches(4.4), Inches(5.5), Inches(2.1))
    sl.footer("Screenshots: repeated-sequence table and ranked key-length evidence")
    return sl


def slide_vigenere_attack(d: Deck) -> Slide:
    sl = d.add_slide()
    sl.background(NAVY)
    sl.title_bar("04 \u00b7 CRYPTANALYSIS", "Full Vigen\u00e8re Cryptanalysis Pipeline")
    left = [
        ("Step 1 \u2014 Estimate: ",
         "Kasiski + IC agree on key length 5 (combined score 0.948)"),
        ("Step 2 \u2014 Columns: ",
         "split ciphertext into 5 columns; each behaves like Caesar-shifted English"),
        ("Step 3 \u2014 Solve: ",
         "per-column frequency analysis suggests L, E, M, O, N (scores 50\u201358)"),
        ("Step 4 \u2014 Verify: ",
         "candidate keys ranked by English-likeness; LEMON decrypts to real prose"),
    ]
    sl.bullet_list(Inches(0.55), Inches(1.5), Inches(6.45), Inches(4.2), left,
                   size=13.5, line_gap=12)
    sl.rect(Inches(0.55), Inches(5.7), Inches(6.45), Inches(0.7), fill_color=GREEN_PANEL)
    sl.text(Inches(0.8), Inches(5.85), Inches(6.0), Inches(0.4),
            [("Recovered key: LEMON \u2014 matches the original 100%",
              13, GREEN, True, BODY_FONT, 0)])
    sl.screenshot(FIG / "fig15_vigenere_b_2.png", Inches(7.25), Inches(1.45), Inches(5.6), Inches(2.6))
    sl.screenshot(FIG / "fig16_vigenere_c_1.png", Inches(7.25), Inches(4.2), Inches(5.6), Inches(2.7))
    sl.footer("Screenshots: per-column key letter candidates and the ranked candidate keys")
    return sl


def slide_files(d: Deck) -> Slide:
    sl = d.add_slide()
    sl.background(NAVY)
    sl.title_bar("05 \u00b7 FILES & REPORTS", "File Encryption / Decryption")
    left = [
        ("Whole-file ciphers: ",
         "file-caesar and file-vigenere transform entire text files"),
        ("Safe by default: ",
         "output goes to <input>_out.<ext>; original untouched without --overwrite"),
        ("Round-trip proven: ",
         "decrypt(encrypt(file)) reproduces the exact original \u2014 unit tested"),
        ("Statistics shown: ",
         "file sizes, letter counts and character classes after every run"),
    ]
    sl.bullet_list(Inches(0.55), Inches(1.5), Inches(6.55), Inches(3.2), left,
                   size=13.5, line_gap=12)
    sl.rect(Inches(0.55), Inches(4.85), Inches(6.55), Inches(1.8), fill_color=CODE_BG)
    sl.text(Inches(0.8), Inches(5.05), Inches(6.1), Inches(1.5), [
        ("$ python main.py file-vigenere \\", 12.5, GREEN, True, MONO_FONT, 0),
        ("      --input sample_data/message.txt --key LEMON", 12.5, WHITE, False, MONO_FONT, 2),
        ("  \u2192 writes message_out.txt; original file preserved", 11, MUTED, False, MONO_FONT, 4),
    ])
    sl.screenshot(FIG / "fig18_file_encrypt_1.png", Inches(7.35), Inches(1.45), Inches(5.5), Inches(2.6))
    sl.screenshot(FIG / "fig17_file_decrypt_1.png", Inches(7.35), Inches(4.2), Inches(5.5), Inches(2.65))
    sl.footer("Screenshots: encrypting and decrypting files from the CLI")
    return sl


def slide_reports(d: Deck) -> Slide:
    sl = d.add_slide()
    sl.background(NAVY)
    sl.title_bar("05 \u00b7 FILES & REPORTS", "Timestamped Analysis Reports")
    left = [
        ("One flag: ",
         "append --report to any command to persist the analysis"),
        ("Interactive too: ",
         "menus ask \u201cSave this analysis as a report? [y/n]\u201d"),
        ("Contents: ",
         "inputs, statistics, tables, method notes, security assessment, disclaimer"),
        ("Organised: ",
         "written under reports/ with timestamped filenames"),
        ("Viva-ready: ",
         "reports double as evidence for the demonstration logbook"),
    ]
    sl.bullet_list(Inches(0.55), Inches(1.5), Inches(6.55), Inches(4.8), left,
                   size=13.5, line_gap=12)
    sl.screenshot(FIG / "fig21_report_saved_1.png", Inches(7.35), Inches(1.45), Inches(5.5), Inches(2.6))
    sl.screenshot(FIG / "fig22_report_content_2.png", Inches(7.35), Inches(4.2), Inches(5.5), Inches(2.65))
    sl.footer("Screenshots: saving a report and the generated report contents")
    return sl


def slide_security(d: Deck) -> Slide:
    sl = d.add_slide()
    sl.background(NAVY)
    sl.title_bar("06 \u00b7 SECURITY & TESTING", "Security Analysis Module")
    left = [
        ("Profiles: ",
         "keyspace size, strengths, weaknesses and known attacks per cipher"),
        ("Caesar verdict: ",
         "VERY WEAK \u2014 25 effective keys, broken in milliseconds"),
        ("Vigen\u00e8re verdict: ",
         "WEAK \u2014 resisted attack for 3 centuries until Kasiski (1863)"),
        ("Built-in disclaimer: ",
         "educational use only \u2014 printed on every run"),
    ]
    sl.bullet_list(Inches(0.55), Inches(1.5), Inches(6.55), Inches(3.4), left,
                   size=13.5, line_gap=12)
    sl.rect(Inches(0.55), Inches(5.15), Inches(6.55), Inches(1.5), fill_color=NAVY_2)
    sl.text(Inches(0.8), Inches(5.32), Inches(6.05), Inches(1.2), [
        ("Why teach broken ciphers?", 13, ACCENT, True, BODY_FONT, 0),
        ("They are the only ciphers whose every attack step can be performed and "
         "understood by hand \u2014 the clearest motivation for modern cryptography.",
         11.5, WHITE, False, BODY_FONT, 4),
    ])
    sl.screenshot(FIG / "fig19_security_caesar_2.png", Inches(7.35), Inches(1.45), Inches(5.5), Inches(2.6))
    sl.screenshot(FIG / "fig20_security_vigenere_1.png", Inches(7.35), Inches(4.2), Inches(5.5), Inches(2.65))
    sl.footer("Screenshots: Caesar profile (VERY WEAK) and Vigen\u00e8re profile (WEAK)")
    return sl


def slide_tests(d: Deck) -> Slide:
    sl = d.add_slide()
    sl.background(NAVY)
    sl.title_bar("06 \u00b7 SECURITY & TESTING", "Automated Testing \u2014 163 Tests, All Green")
    sl.text(Inches(0.55), Inches(1.22), Inches(12.2), Inches(0.4),
            [("$ python -m unittest discover -s tests -v   \u2192   Ran 163 tests in 0.606s \u2014 OK",
              14, GREEN, True, MONO_FONT, 0)])
    sl.screenshot(FIG / "fig23_tests_1.png", Inches(0.55), Inches(1.7), Inches(12.2), Inches(3.5))
    coverage = [
        ("Ciphers", "round-trips, wrap-around, invalid input"),
        ("Cryptanalysis", "IC values, Kasiski maths, key recovery"),
        ("CLI", "all commands, errors, interactive flows"),
        ("Files & Reports", "round-trips, overwrite protection"),
    ]
    cx = Inches(0.55)
    cw = Inches(2.95)
    for name, what in coverage:
        sl.rect(cx, Inches(5.45), cw, Inches(1.15), fill_color=NAVY_2)
        sl.rect(cx, Inches(5.45), cw, Inches(0.07), fill_color=GREEN)
        sl.text(cx + Inches(0.15), Inches(5.62), cw - Inches(0.3), Inches(0.35),
                [(name, 12.5, WHITE, True, BODY_FONT, 0)])
        sl.text(cx + Inches(0.15), Inches(5.98), cw - Inches(0.3), Inches(0.55),
                [(what, 10, MUTED, False, BODY_FONT, 0)])
        cx = cx + cw + Inches(0.14)
    sl.footer("Quality practice: tests written alongside every feature module")
    return sl


def slide_conclusion(d: Deck) -> Slide:
    sl = d.add_slide()
    sl.background(NAVY)
    sl.title_bar("07 \u00b7 CONCLUSION", "Results, Limitations & Future Work")
    col_w = Inches(3.95)
    gap = Inches(0.19)
    x = Inches(0.55)
    cols = [
        ("ACHIEVED", GREEN, [
            "Working encrypt/decrypt for 2 ciphers",
            "4 cryptanalysis attacks automated",
            "Key LEMON recovered from ciphertext",
            "163/163 tests passing in 0.6 s",
            "Reports, sample data, docs & PDF guide",
        ]),
        ("LIMITATIONS", ACCENT, [
            "Classical ciphers are inherently insecure",
            "Statistical attacks need enough text",
            "Scoring heuristics are English-only",
            "CLI only \u2014 no GUI",
        ]),
        ("FUTURE WORK", MUTED, [
            "GUI or web front-end",
            "More ciphers: substitution, transposition, XOR",
            "Multilingual frequency tables",
            "Simulated known-plaintext attack demos",
        ]),
    ]
    for name, color, points in cols:
        sl.rect(x, Inches(1.45), col_w, Inches(4.45), fill_color=NAVY_2)
        sl.rect(x, Inches(1.45), col_w, Inches(0.09), fill_color=color)
        sl.text(x + Inches(0.25), Inches(1.64), col_w - Inches(0.5), Inches(0.4),
                [(name, 14, color, True, BODY_FONT, 0)])
        sl.bullet_list(x + Inches(0.25), Inches(2.14), col_w - Inches(0.5), Inches(3.6),
                       [("", p) for p in points], size=11.5, line_gap=9)
        x = x + col_w + gap

    sl.rect(Inches(0.55), Inches(6.15), Inches(12.2), Inches(0.72), fill_color=NAVY_2)
    sl.text(Inches(0.8), Inches(6.32), Inches(11.8), Inches(0.4),
            [("Understanding why classical ciphers fail is the first step towards "
              "understanding why modern encryption works.", 13, WHITE, True, BODY_FONT, 0)])
    sl.footer("Educational use only \u2014 never protect real data with classical ciphers")
    return sl


def slide_thanks(d: Deck) -> Slide:
    sl = d.add_slide()
    sl.background(NAVY)
    for i in range(4):
        x = SLIDE_W / 4 * i
        sl.rect(x, SLIDE_H - Inches(0.06), Inches(3.33), Pt(3), fill_color=ACCENT_DK)
    sl.rect(Inches(0.9), Inches(2.2), Inches(0.14), Inches(3.2), fill_color=ACCENT)
    sl.text(Inches(1.25), Inches(2.3), Inches(11.0), Inches(1.7), [
        ("Thank You", 46, WHITE, True, TITLE_FONT, 0),
        ("Questions & Live Demo", 20, ACCENT, False, BODY_FONT, 8),
    ])
    sl.text(Inches(1.25), Inches(4.4), Inches(11.4), Inches(1.3), [
        ("python main.py          # interactive menu", 15, GREEN, True, MONO_FONT, 0),
        ("python main.py crack-caesar --input sample_data/caesar_sample.txt",
         13, MUTED, False, MONO_FONT, 4),
        ("python main.py analyze-vigenere --input sample_data/vigenere_sample.txt",
         13, MUTED, False, MONO_FONT, 2),
    ])
    sl.text(Inches(1.25), Inches(6.4), Inches(11.0), Inches(0.4),
            [("163 tests \u00b7 9 commands \u00b7 2 ciphers \u00b7 4 attacks \u00b7 100% passing",
              12, MUTED, False, BODY_FONT, 0)])
    return sl


# --------------------------------------------------------------------------- #
# Slide order + speaker notes (timing hints sum to ~10-12 minutes)
# --------------------------------------------------------------------------- #
SLIDE_BUILDERS = [
    ("Title", slide_title),
    ("Agenda", slide_agenda),
    ("Introduction & objectives", slide_intro),
    ("Environment & structure", slide_environment),
    ("Architecture", slide_architecture),
    ("Data flow", slide_data_flow),
    ("Caesar cipher", slide_caesar),
    ("Vigenere cipher", slide_vigenere),
    ("Interactive mode", slide_interactive),
    ("Frequency analysis", slide_frequency),
    ("Caesar cracking", slide_crack_caesar),
    ("Index of Coincidence", slide_ic),
    ("Kasiski examination", slide_kasiski),
    ("Vigenere pipeline", slide_vigenere_attack),
    ("File operations", slide_files),
    ("Reports", slide_reports),
    ("Security analysis", slide_security),
    ("Test suite", slide_tests),
    ("Conclusion", slide_conclusion),
    ("Thank you", slide_thanks),
]

NOTES = {
    "Title": (
        "[~35s] Good morning everyone. My name is ___ (introduce yourself). Today I am presenting my "
        "project, the Cryptographic Cipher Analyzer \u2014 a command-line application written in Python 3. "
        "In one sentence: it can encrypt and decrypt messages with the Caesar and Vigen\u00e8re ciphers, and "
        "then turn around and break those same ciphers automatically using classical cryptanalysis. The "
        "three numbers on this slide summarise the project: 163 automated unit tests, nine command-line "
        "commands, and a strict educational-only scope. Over the next eight to ten minutes I will show "
        "the system design, walk through every feature with real screenshots, and finish with the test "
        "results and conclusions."
    ),
    "Agenda": (
        "[~25s] Here is the plan for the talk. First, the objectives \u2014 what problem the tool solves and "
        "for whom. Second, the system design: the technology stack, the layered architecture and how a "
        "request flows from input to report. Third, the two ciphers in action, including the interactive "
        "menu. Fourth \u2014 the heart of the project \u2014 four cryptanalysis attacks, ending with the full "
        "recovery of a Vigen\u00e8re key. Then file operations and report generation, the security analysis "
        "module, and the automated test suite. I will close with results, limitations and future work."
    ),
    "Introduction & objectives": (
        "[~40s] So what exactly is this project? It is a cryptanalysis laboratory in the terminal. You "
        "can feed it plaintext and get ciphertext back, or feed it ciphertext and recover the plaintext "
        "without ever knowing the key. Four things make it more than a toy. First, every stage of the "
        "attack is automated \u2014 brute force for Caesar, statistics for Vigen\u00e8re. Second, it has two "
        "complete interfaces: a guided menu for beginners and nine scriptable CLI commands. Third, every "
        "analysis can be saved as a timestamped report, which is what the screenshot shows. And fourth, "
        "it is honest: it never pretends these ciphers are secure \u2014 every run prints an educational "
        "disclaimer. The second screenshot shows the built-in command reference."
    ),
    "Environment & structure": (
        "[~35s] The technology choices were deliberately simple. The whole tool is Python 3, standard "
        "library only \u2014 no third-party runtime dependencies \u2014 so it runs on any machine with Python "
        "installed. The code is organised into five packages: ciphers holds the two encryption "
        "algorithms, analysis holds the four cryptanalysis engines, file_operations handles disk I/O, "
        "utils provides validation, text handling and reporting, and tests contains the 163 unit tests. "
        "The screenshots show the verified Python version, the top-level folder structure and the package "
        "contents. This structure was a conscious decision: it keeps presentation, logic and testing in "
        "separate layers, as the next slide shows."
    ),
    "Architecture": (
        "[~45s] Here is the architecture in four layers. At the top, user interaction: main.py with "
        "argparse for the CLI, and banner.py driving the interactive menu. Below that, the operations "
        "layer: encryption, the four analyses, file operations and reports. The core engines live in "
        "their own modules \u2014 caesar.py, vigenere.py, caesar_cracker.py and vigenere_analyzer.py. At the "
        "bottom, shared services: validators, text utilities and the report generator. Why does this "
        "matter? main.py only presents results \u2014 no cryptography lives there. Each analysis module can "
        "be tested in isolation, and the 163 tests map directly onto these module boundaries. Bad input "
        "can never reach the engines because validators run first."
    ),
    "Data flow": (
        "[~35s] This slide shows what happens on every single command, in five steps. Input arrives "
        "typed, from a file, or as CLI flags. Validation normalises it \u2014 shifts must be integers, keys "
        "must be letters, text must not be empty. Then processing: a cipher engine or an analysis engine "
        "runs. Presentation formats the result as tables and ranked candidates. Finally, optionally, a "
        "timestamped report is written. The highlights at the bottom are the engineering guarantees: "
        "invalid input never crashes the program, source files are never modified without explicit "
        "overwrite confirmation, and end-of-input exits the menu cleanly. The same pipeline serves both "
        "the menu and the CLI."
    ),
    "Caesar cipher": (
        "[~40s] Starting with the simplest cipher. The Caesar cipher shifts every letter by a fixed "
        "amount modulo 26 \u2014 HELLO WORLD becomes KHOOR ZRUOG with shift three. The right screenshots "
        "show the real CLI run: the command, the shift used and the output. Decryption is simply the "
        "inverse shift. Note the design details: case is preserved, digits and punctuation pass through "
        "untouched, and negative or oversized shifts are normalised. The crucial number is the keyspace: "
        "only 25 effective keys, because shift zero changes nothing. That is exactly the weakness the "
        "cracking demo will exploit a few slides from now. This cipher takes seconds to implement \u2014 "
        "and seconds to break."
    ),
    "Vigenere cipher": (
        "[~40s] The Vigen\u00e8re cipher fixes Caesar's obvious flaw. Instead of one shift, a repeating "
        "keyword applies a different shift to every letter \u2014 here the classic textbook example: "
        "ATTACKATDAWN with key LEMON produces LXFOPVEFRNHR. The key letter at each position selects which "
        "Caesar alphabet is used. This flattens the letter frequencies that make Caesar trivial to break "
        "\u2014 which is why it was called the indecipherable cipher for three centuries. But it introduces "
        "a new weakness: the keyword repeats, and whenever it realigns with the text, patterns appear in "
        "the ciphertext. That repetition is exactly what the Kasiski examination will detect later. The "
        "screenshots show encryption and decryption through the CLI."
    ),
    "Interactive mode": (
        "[~30s] For demonstrations and users who prefer guidance, there is a full interactive mode. "
        "Running python main.py with no arguments opens this menu with nine options. Every prompt "
        "validates its input and re-asks on mistakes, so the program cannot be crashed by typing "
        "something wrong. Submenus let you choose between typing text or reading it from a file, and "
        "after every analysis the tool offers to save a report. The screenshot shows the banner, the main "
        "menu, and a guided Caesar session. This is also the mode I would use for a live demo \u2014 "
        "everything the CLI does is reachable from the menu."
    ),
    "Frequency analysis": (
        "[~40s] Now the cryptanalysis. Attack one: frequency analysis. The idea is that natural language "
        "is statistically uneven \u2014 in English, E, T and A dominate. The tool counts every letter, shows "
        "percentages, and \u2014 the useful part \u2014 compares the observed frequencies against the standard "
        "English table, sorted by difference. In the screenshot, the ciphertext peaks on H, K, O and R "
        "\u2014 exactly E, T, A and O shifted by three. One glance reveals the shift. Beyond diagnosis, the "
        "same counting logic powers a chi-square fitness score that later ranks candidate plaintexts, "
        "plus a digram scorer for common letter pairs. Frequency analysis is the foundation everything "
        "else builds on."
    ),
    "Caesar cracking": (
        "[~45s] Attack two is where it gets satisfying: automatic Caesar cracking. The command takes "
        "ciphertext only \u2014 no key. The tool tries all 26 shifts and scores each result with a "
        "chi-square statistic against English letter frequencies, combined with a digram score. In the "
        "demo, the input is a 1,287-character ciphertext from the sample data folder. The ranked table "
        "shows the result: shift three scored 70.52 while the runner-up scored only 22.94 \u2014 a decisive "
        "margin. Below the table, the BEST CANDIDATE panel prints the fully recovered plaintext. Notice "
        "the honesty note at the bottom of the terminal output: the ranking is statistical, and short or "
        "unusual texts can mislead it. The tool tells you that on screen."
    ),
    "Index of Coincidence": (
        "[~40s] Attack three: the Index of Coincidence. It is a single number measuring how unevenly "
        "letters are distributed \u2014 the probability that two random letters from the text are identical. "
        "English prose sits around 0.0667; random text around 0.0385. The demo screenshot shows a "
        "Vigen\u00e8re ciphertext scoring 0.0435 \u2014 clearly in the polyalphabetic range, confirming that "
        "naive frequency analysis will not work directly. The real power is the second table: the average "
        "IC computed per assumed key length. When the assumed length matches the true key length, every "
        "column behaves like English and the IC spikes \u2014 here it peaks at 5, 10 and 15, immediately "
        "suggesting a key length of five."
    ),
    "Kasiski examination": (
        "[~40s] Attack four confirms that guess independently: Kasiski examination, published in 1863. "
        "The observation: in a repeating-key cipher, a repeated ciphertext fragment means the key "
        "realigned with the plaintext at that point \u2014 so the distance between the two repeats must be a "
        "multiple of the key length. The tool finds all repeated sequences of length three to five, "
        "computes their distances and factorises them. In the demo, fragments repeat at distances 500 and "
        "395, whose common factors are 5, 10, 20 and 25. The evidence table ranks key lengths by "
        "accumulated factor hits \u2014 length five leads. Important nuance: Kasiski produces candidates, "
        "not proof. That is why the tool always pairs it with the IC evidence."
    ),
    "Vigenere pipeline": (
        "[~45s] Now the full pipeline, combining all three techniques. Step one, estimation: Kasiski "
        "evidence and the per-length IC agree on key length five, with a combined score of 0.948. Step "
        "two: split the ciphertext into five columns \u2014 each column is now a monoalphabetic Caesar "
        "shift, so column IC rises to English levels. Step three: per-column frequency analysis suggests "
        "the most likely letter for each key position \u2014 L, E, M, O, N, each with a fitness score around "
        "50 to 58, far above the runners-up. Step four: the tool assembles candidate keys, decrypts with "
        "each, and ranks them by English-likeness. LEMON comes first \u2014 highlighted in green \u2014 and "
        "the best-guess panel shows the recovered plaintext."
    ),
    "File operations": (
        "[~35s] Beyond single strings, the tool operates on whole files. The file-caesar and "
        "file-vigenere commands encrypt or decrypt an entire text file. Safety was the priority: the "
        "output defaults to a new file with an underscore-out suffix, and the original is never modified "
        "unless you explicitly pass the overwrite flag \u2014 interactively, the tool asks for confirmation "
        "first. The screenshots show a real encryption run with file statistics, and the decryption round "
        "trip, which reproduces the original exactly. This is also covered by dedicated unit tests: the "
        "round trip for both ciphers, and proof that an invalid key leaves the output file untouched."
    ),
    "Reports": (
        "[~30s] Every analysis can be persisted. Adding the report flag \u2014 or answering yes in the "
        "interactive mode \u2014 writes a timestamped text file under the reports folder. The report is "
        "complete: input statistics, all result tables, the cryptanalysis method notes, the security "
        "assessment and the educational disclaimer. The screenshots show the save confirmation and the "
        "actual contents of a generated report. This turned out to be genuinely useful during "
        "development: reports from test runs became the evidence log for the project documentation, and "
        "they give the examiner a reproducible record of every demo shown today."
    ),
    "Security analysis": (
        "[~40s] The security module turns the tool's knowledge into explicit teaching content. For each "
        "cipher it profiles the keyspace, strengths, weaknesses and known attacks. Caesar: rated very "
        "weak \u2014 25 effective keys, broken in milliseconds by brute force, destroyed by frequency "
        "analysis. Vigen\u00e8re: rated weak \u2014 it resisted cryptanalysis for three centuries, but "
        "Kasiski's 1863 examination broke it. The module closes with the disclaimer printed on every run: "
        "educational use only, never protect real data. I want to stress the panel at the bottom left: "
        "broken ciphers are worth teaching precisely because every attack step can be performed and "
        "understood by hand \u2014 that understanding is what motivates modern cryptography."
    ),
    "Test suite": (
        "[~35s] Quality was verified, not assumed. The project has 163 unit tests, all passing in about "
        "six tenths of a second \u2014 fast enough to run on every change. The screenshot shows the verbose "
        "unittest run. Coverage spans four areas, summarised in the chips below: the cipher engines \u2014 "
        "round trips for every shift and multiple keys, case and punctuation preservation, alphabet "
        "wrap-around; the cryptanalysis engines \u2014 known IC values, Kasiski distances and factorisation, "
        "and crucially a test that the analyser recovers a real key; the CLI \u2014 every subcommand, the "
        "report flag, error handling and interactive flows; and file operations \u2014 round trips, "
        "overwrite protection and report structure. Tests were written alongside each module, not "
        "retrofitted."
    ),
    "Conclusion": (
        "[~40s] To conclude. The project achieves what it set out to do: a complete, tested, documented "
        "cryptanalysis tool with two ciphers and four automated attacks \u2014 demonstrated today by "
        "recovering the key LEMON from real ciphertext and cracking a Caesar cipher with a decisive "
        "statistical margin. The limitations are honestly stated: these ciphers are inherently insecure, "
        "statistical attacks need sufficient text, and the scoring is English-only. Future work includes "
        "a graphical interface, more cipher families such as substitution and transposition, "
        "multilingual frequency tables, and simulated known-plaintext attacks. The closing message is the "
        "point of the whole project: understanding why classical ciphers fail is the first step towards "
        "understanding why modern encryption works."
    ),
    "Thank you": (
        "[~15s] Thank you for listening. If there is time, I would be glad to run a live demo \u2014 "
        "cracking a Caesar cipher or recovering a Vigen\u00e8re key takes only seconds. I am happy to take "
        "your questions."
    ),
}


def main() -> None:
    d = Deck()
    for name, builder in SLIDE_BUILDERS:
        sl = builder(d)
        sl.notes(NOTES.get(name, ""))
    d.save()
    words = sum(len(t.split()) for t in NOTES.values())
    print(f"Slides written : {d.count}")
    print(f"Speaker notes  : ~{words} words (~{words // 130 + 1}-{words // 100 + 1} min spoken)")
    print(f"Presentation   : {OUT}")


if __name__ == "__main__":
    main()
