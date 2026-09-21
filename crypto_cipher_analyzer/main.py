#!/usr/bin/env python3
"""Cryptographic Cipher Analyzer - command line entry point.

Two ways to use the tool:

* **Interactive mode** - run ``python main.py`` with no arguments and pick an
  option from the menu. Every step asks for what it needs and no invalid input
  can crash the program.
* **Command line mode** - run a single operation, for example
  ``python main.py caesar-encrypt --text "HELLO WORLD" --shift 3``.

The cryptanalysis algorithms live in the ``ciphers``, ``analysis`` and
``file_operations`` packages; this module only handles user interaction,
argument parsing and presentation.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Callable, Sequence

from analysis.caesar_cracker import CRACKING_NOTE, crack_caesar
from analysis.frequency import (
    compare_with_english,
    fitness_score,
    frequency_analysis,
    letter_rows,
)
from analysis.ic_analysis import (
    analyze_index_of_coincidence,
    ic_as_rows,
    ic_by_key_length,
    index_of_coincidence,
    interpret_ic,
)
from analysis.kasiski import kasiski_examination, kasiski_rows, key_length_rows as kasiski_key_rows
from analysis.security import SHORT_DISCLAIMER, profiles, security_summary_lines
from analysis.vigenere_analyzer import (
    RECOVERY_NOTE,
    analyze_vigenere,
    key_candidate_rows,
    key_length_rows,
    position_suggestion_rows,
    recover_key_candidates,
    suggest_key_characters,
)
from ciphers import caesar, vigenere
from file_operations import file_handler
from file_operations.file_handler import FileOperationError
from utils import banner
from utils.report_generator import ReportBuilder, format_frequency_report_lines, save_report
from utils.text_utils import normalize_text, total_letters
from utils.validators import (
    ValidationError,
    validate_key,
    validate_key_length,
    validate_menu_choice,
    validate_shift,
    validate_text,
)

VERSION = "1.0.0"
TOOL_TITLE = "CRYPTOGRAPHIC CIPHER ANALYZER"
TOOL_SUBTITLE = "Caesar & Vigenère Cryptanalysis Tool"

MENU_OPTIONS: tuple[tuple[str, str], ...] = (
    ("1", "Caesar Cipher (encrypt / decrypt)"),
    ("2", "Vigenère Cipher (encrypt / decrypt)"),
    ("3", "Frequency Analysis"),
    ("4", "Break Caesar Cipher (automatic)"),
    ("5", "Analyze Vigenère Cipher (cryptanalysis)"),
    ("6", "File Encryption / Decryption"),
    ("7", "Security Analysis"),
    ("8", "Help"),
    ("9", "Exit"),
)

CAESAR_EXPLANATION = (
    "The Caesar cipher shifts each alphabetic character by a fixed number of "
    "positions. Because there are only 26 possible shifts, an attacker can "
    "easily test every possibility."
)

VIGENERE_EXPLANATION = (
    "The Vigenère cipher uses a repeating keyword to apply different Caesar "
    "shifts. Repeated-key behaviour leaks statistical patterns, which is what "
    "Kasiski examination and Index of Coincidence analysis exploit."
)

FREQUENCY_EXPLANATION = (
    "Frequency analysis counts how often each letter occurs. Ordinary English "
    "text is very uneven (E, T and A dominate) while most classical ciphers "
    "flatten that distribution, so the shape of the distribution is a strong "
    "hint about what kind of cipher was used."
)

IC_EXPLANATION = (
    "The Index of Coincidence measures how unevenly the letters are spread, "
    "using IC = sum(fi(fi-1)) / N(N-1). English prose sits near 0.0667, random "
    "text near 0.0385. A value close to English suggests monoalphabetic text "
    "(or a polyalphabetic cipher whose key length you have guessed correctly), "
    "but the IC alone never proves the cipher type."
)

KASISKI_EXPLANATION = (
    "Kasiski examination looks for ciphertext fragments that repeat. In a "
    "repeating-key cipher such a repeat means the key realigned with the text, "
    "so the distance between the repeats is a multiple of the key length. The "
    "common factors of those distances are candidate key lengths - hypotheses "
    "to be verified, not facts."
)

HELP_LINES: tuple[str, ...] = (
    "Interactive mode:      python main.py",
    "Caesar encrypt:        python main.py caesar-encrypt --text \"HELLO WORLD\" --shift 3",
    "Caesar decrypt:        python main.py caesar-decrypt --text \"KHOOR ZRUOG\" --shift 3",
    "Vigenere encrypt:      python main.py vigenere-encrypt --text \"ATTACKATDAWN\" --key LEMON",
    "Vigenere decrypt:      python main.py vigenere-decrypt --text \"LXFOPVEFRNHR\" --key LEMON",
    "Frequency analysis:    python main.py frequency --text \"KHOOR ZRUOG\"",
    "Break Caesar:          python main.py crack-caesar --text \"KHOOR ZRUOG\"",
    "Analyze Vigenere:      python main.py analyze-vigenere --text \"...\"",
    "Index of Coincidence:  python main.py ic --text \"KHOOR ZRUOG\"",
    "Kasiski examination:   python main.py kasiski --text \"...\"",
    "Security analysis:     python main.py security",
    "Encrypt a file:        python main.py file-caesar --input notes.txt --shift 3",
    "Decrypt a file:        python main.py file-caesar --input notes.txt --shift 3 --decrypt",
    "Vigenere file:         python main.py file-vigenere --input notes.txt --key LEMON",
    "",
    "Common options: --text, --input, --output, --shift, --key, --report, --overwrite",
    "Add --report to any analysis command to save a text report under reports/.",
)


# --------------------------------------------------------------------------- #
# Argument parsing
# --------------------------------------------------------------------------- #
class FriendlyArgumentParser(argparse.ArgumentParser):
    """ArgumentParser that reports errors in the tool's own style."""

    def error(self, message: str) -> None:  # type: ignore[override]
        banner.print_error(message)
        banner.print_info("Run 'python main.py --help' to see the available commands.")
        raise SystemExit(2)


def _add_input_options(
    parser: argparse.ArgumentParser,
    *,
    shift: bool = False,
    key: bool = False,
    report: bool = True,
) -> None:
    """Add the standard text input options to a sub-command parser."""
    parser.add_argument("--text", help="Text to process (use quotes)")
    parser.add_argument("--input", help="Read the text from this file instead of --text")
    if shift:
        parser.add_argument("--shift", help="Caesar shift, for example 3 (negative values are allowed)")
    if key:
        parser.add_argument("--key", help="Vigenere keyword containing letters only")
    if report:
        parser.add_argument("--report", action="store_true", help="Save a text report under reports/")


def build_parser() -> argparse.ArgumentParser:
    """Build the command line parser for the tool."""
    parser = FriendlyArgumentParser(
        prog="main.py",
        description=f"{TOOL_TITLE} - {TOOL_SUBTITLE}",
        epilog="Educational use only: Caesar and Vigenere are not secure modern ciphers.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {VERSION}")
    parser.add_argument("--no-color", action="store_true", help="Disable ANSI colours")
    subparsers = parser.add_subparsers(dest="command", metavar="COMMAND")

    subparsers.add_parser("interactive", help="Start the interactive menu")

    for name, help_text in (
        ("caesar-encrypt", "Encrypt text with the Caesar cipher"),
        ("caesar-decrypt", "Decrypt Caesar ciphertext"),
    ):
        sub = subparsers.add_parser(name, help=help_text)
        _add_input_options(sub, shift=True)

    for name, help_text in (
        ("vigenere-encrypt", "Encrypt text with the Vigenere cipher"),
        ("vigenere-decrypt", "Decrypt Vigenere ciphertext"),
    ):
        sub = subparsers.add_parser(name, help=help_text)
        _add_input_options(sub, key=True)

    sub = subparsers.add_parser("frequency", help="Single letter frequency analysis")
    _add_input_options(sub)

    sub = subparsers.add_parser("crack-caesar", help="Break Caesar ciphertext automatically")
    _add_input_options(sub)
    sub.add_argument("--top", default="5", help="How many candidates to display (default: 5)")

    sub = subparsers.add_parser("analyze-vigenere", help="Full Vigenere cryptanalysis")
    _add_input_options(sub)
    sub.add_argument("--max-key-length", default="20", help="Largest key length to consider (default: 20)")
    sub.add_argument("--key-length", help="Skip key-length estimation and use this length for key recovery")
    sub.add_argument("--top", default="5", help="How many key-length candidates to display (default: 5)")

    sub = subparsers.add_parser("ic", help="Index of Coincidence analysis")
    _add_input_options(sub)
    sub.add_argument("--max-key-length", default="12", help="Also show the average IC per key length up to this value")

    sub = subparsers.add_parser("kasiski", help="Kasiski examination for repeated sequences")
    _add_input_options(sub)
    sub.add_argument("--min-length", default="3", help="Shortest repeated sequence (default: 3)")
    sub.add_argument("--max-length", default="5", help="Longest repeated sequence (default: 5)")
    sub.add_argument("--max-key-length", default="20", help="Largest key length to rank (default: 20)")

    sub = subparsers.add_parser("security", help="Security assessment of the classical ciphers")
    sub.add_argument("--cipher", choices=["caesar", "vigenere"], help="Show only one cipher")
    sub.add_argument("--report", action="store_true", help="Save a text report under reports/")

    for name, help_text in (
        ("file-caesar", "Encrypt or decrypt a text file with the Caesar cipher"),
        ("file-vigenere", "Encrypt or decrypt a text file with the Vigenere cipher"),
    ):
        sub = subparsers.add_parser(name, help=help_text)
        sub.add_argument("--input", required=True, help="Input file")
        sub.add_argument("--output", help="Output file (defaults to <input>_out.<ext>)")
        if name == "file-caesar":
            sub.add_argument("--shift", required=True, help="Caesar shift")
        else:
            sub.add_argument("--key", required=True, help="Vigenere keyword")
        sub.add_argument("--decrypt", action="store_true", help="Decrypt instead of encrypt")
        sub.add_argument("--overwrite", action="store_true", help="Allow replacing an existing output file")

    return parser


# --------------------------------------------------------------------------- #
# Shared helpers
# --------------------------------------------------------------------------- #
def _require_shift(args: argparse.Namespace) -> int:
    """Return the validated shift from CLI arguments."""
    if getattr(args, "shift", None) is None:
        raise ValidationError("Provide a shift, for example --shift 3.")
    return validate_shift(args.shift)


def _require_key(args: argparse.Namespace) -> str:
    """Return the validated Vigenère key from CLI arguments."""
    if getattr(args, "key", None) is None:
        raise ValidationError("Provide a keyword, for example --key LEMON.")
    return validate_key(args.key)


def _resolve_text(args: argparse.Namespace, field: str = "text") -> str:
    """Return the input text from ``--text`` or ``--input``."""
    text = getattr(args, "text", None)
    if text:
        return validate_text(text, field=field)
    source = getattr(args, "input", None)
    if source:
        return file_handler.read_text(source)
    raise ValidationError('Provide the input with --text "..." or --input <file>.')


def _report_requested(args: argparse.Namespace) -> bool:
    """Return ``True`` when ``--report`` was passed."""
    return bool(getattr(args, "report", False))


def offer_report(
    builder: ReportBuilder,
    *,
    ask: bool = False,
    forced: bool = False,
    prompt_text: str = "Save this analysis as a report? [y/n]",
) -> Path | None:
    """Offer to save a report and write it when the user agrees.

    Args:
        builder: The prepared report.
        ask: Ask the user for confirmation (interactive mode).
        forced: Save without asking (``--report`` on the command line).
        prompt_text: Question shown when *ask* is ``True``.

    Returns:
        The path written, or ``None`` when nothing was saved.
    """
    if not forced:
        if not ask:
            return None
        if not banner.confirm(prompt_text, default=False):
            return None
    try:
        path = save_report(builder.render())
    except OSError as error:
        banner.print_error(f"Could not save the report: {error}")
        return None
    banner.print_success(f"Report saved: {path}")
    return path


def _show_output(label: str, text: str) -> None:
    """Print a labelled block of text."""
    banner.print_section(label)
    banner.print_block(text)


def _basic_stats(text: str) -> list[tuple[str, object]]:
    """Return ``(label, value)`` pairs describing the input text."""
    return [
        ("Total characters", len(text)),
        ("Alphabetic characters", total_letters(text)),
        ("Unique letters", len(set(normalize_text(text)))),
        ("Text length (letters only)", len(normalize_text(text))),
    ]


# --------------------------------------------------------------------------- #
# Operations
# --------------------------------------------------------------------------- #
def perform_caesar(
    text: str,
    shift: int,
    decrypt: bool,
    *,
    ask_report: bool = False,
    force_report: bool = False,
) -> str:
    """Encrypt or decrypt *text* and present the result."""
    validate_text(text, field="ciphertext" if decrypt else "plaintext")
    normalized_shift = validate_shift(shift)
    result = caesar.decrypt(text, normalized_shift) if decrypt else caesar.encrypt(text, normalized_shift)

    mode = "Decryption" if decrypt else "Encryption"
    banner.print_section(f"CAESAR {mode.upper()}")
    banner.print_key_values(
        [("Shift used", normalized_shift), ("Input length", len(text)), ("Output length", len(result))]
    )
    _show_output("OUTPUT", result)
    banner.print_note(CAESAR_EXPLANATION)

    builder = ReportBuilder(cipher="Caesar Cipher", operation=f"Text {mode.lower()}")
    builder.add_key_value("Shift", normalized_shift)
    for label, value in _basic_stats(text):
        builder.add_key_value(label, value)
    builder.add_section("Input", [text])
    builder.add_section("Output", [result])
    builder.add_paragraph("Educational notes", CAESAR_EXPLANATION)
    builder.add_section("Security assessment", security_summary_lines("caesar"))
    offer_report(builder, ask=ask_report, forced=force_report)
    return result


def perform_vigenere(
    text: str,
    key: str,
    decrypt: bool,
    *,
    ask_report: bool = False,
    force_report: bool = False,
) -> str:
    """Encrypt or decrypt *text* with the Vigenère cipher and present the result."""
    validate_text(text, field="ciphertext" if decrypt else "plaintext")
    normalized_key = validate_key(key)
    result = (
        vigenere.decrypt(text, normalized_key) if decrypt else vigenere.encrypt(text, normalized_key)
    )

    mode = "Decryption" if decrypt else "Encryption"
    banner.print_section(f"VIGENERE {mode.upper()}")
    banner.print_key_values(
        [
            ("Key", normalized_key),
            ("Key length", len(normalized_key)),
            ("Input length", len(text)),
            ("Output length", len(result)),
        ]
    )
    _show_output("OUTPUT", result)
    banner.print_note(VIGENERE_EXPLANATION)

    builder = ReportBuilder(cipher="Vigenere Cipher", operation=f"Text {mode.lower()}")
    builder.add_key_value("Key", normalized_key)
    builder.add_key_value("Key length", len(normalized_key))
    for label, value in _basic_stats(text):
        builder.add_key_value(label, value)
    builder.add_section("Input", [text])
    builder.add_section("Output", [result])
    builder.add_paragraph("Educational notes", VIGENERE_EXPLANATION)
    builder.add_section("Security assessment", security_summary_lines("vigenere"))
    offer_report(builder, ask=ask_report, forced=force_report)
    return result


def perform_frequency(
    text: str,
    *,
    ask_report: bool = False,
    force_report: bool = False,
) -> None:
    """Run and display a single-letter frequency analysis."""
    result = frequency_analysis(text)

    banner.print_section("FREQUENCY ANALYSIS")
    banner.print_block("\n".join(result.as_summary_lines()))
    banner.print_table(
        ("Letter", "Count", "Frequency"),
        letter_rows(result),
        aligns=["<", ">", ">"],
        title="Ciphertext letter frequency",
    )
    banner.print_table(
        ("Letter", "Observed", "English", "Difference"),
        compare_with_english(result, top_n=10),
        aligns=["<", ">", ">", ">"],
        title="Compared with standard English frequencies",
    )

    ic_value = index_of_coincidence(normalize_text(text))
    banner.print_section("INDEX OF COINCIDENCE (supporting evidence)")
    banner.print_key_values(
        [("IC value", f"{ic_value:.5f}"), ("Interpretation", interpret_ic(ic_value))]
    )
    banner.print_note(FREQUENCY_EXPLANATION)
    banner.print_note(IC_EXPLANATION)

    builder = ReportBuilder(cipher="Not applicable (analysis only)", operation="Frequency analysis")
    for label, value in _basic_stats(text):
        builder.add_key_value(label, value)
    builder.add_section("Most frequent letters", [
        f"{letter}: {count} ({percentage:.2f}%)" for letter, count, percentage in result.most_common
    ])
    builder.add_section("Least frequent letters", [
        f"{letter}: {count} ({percentage:.2f}%)" for letter, count, percentage in result.least_common
    ])
    builder.add_section(
        "Frequency analysis",
        format_frequency_report_lines(
            total_characters=result.total_characters,
            total_letters=result.total_letters,
            rows=letter_rows(result),
        ),
    )
    builder.add_section(
        "Comparison with English",
        [
            f"{letter:<3} observed {observed:>7}   english {expected:>7}   difference {difference:>8}"
            for letter, observed, expected, difference in compare_with_english(result, top_n=10)
        ],
    )
    builder.add_section(
        "Cryptanalysis",
        [
            f"Index of Coincidence : {ic_value:.5f}",
            f"Interpretation       : {interpret_ic(ic_value)}",
        ],
    )
    builder.add_paragraph("Educational notes", FREQUENCY_EXPLANATION + "\n\n" + IC_EXPLANATION)
    offer_report(builder, ask=ask_report, forced=force_report)


def perform_crack_caesar(
    text: str,
    top_n: int = 5,
    *,
    ask_report: bool = False,
    force_report: bool = False,
) -> None:
    """Break Caesar ciphertext without knowing the shift."""
    candidates = crack_caesar(text, top_n=top_n)

    banner.print_section("CAESAR CRACKING")
    banner.print_key_values(
        [("Ciphertext length", len(text)), ("Candidates evaluated", 26), ("Candidates shown", len(candidates))]
    )
    banner.print_block(f"Ciphertext: {text.strip()}")
    banner.print_table(
        ("Rank", "Shift", "Score", "Candidate plaintext"),
        [candidate.to_row(rank=index + 1) for index, candidate in enumerate(candidates)],
        aligns=["<", ">", ">", "<"],
        title="Possible solutions (ranked by English-likeness)",
    )
    best = candidates[0]
    banner.print_section("BEST CANDIDATE")
    banner.print_key_values(
        [("Estimated shift", best.shift), ("Score", f"{best.score:.2f}")]
    )
    banner.print_block(best.plaintext)
    banner.print_note(CRACKING_NOTE)
    banner.print_note(SHORT_DISCLAIMER)

    builder = ReportBuilder(cipher="Caesar Cipher", operation="Automatic cracking")
    builder.add_key_value("Ciphertext length", len(text))
    builder.add_key_value("Alphabetic characters", total_letters(text))
    builder.add_section("Input", [text])
    builder.add_section(
        "Candidate solutions (estimated)",
        [
            f"{index + 1}. shift {candidate.shift}  score {candidate.score:.2f}  {candidate.plaintext.strip()}"
            for index, candidate in enumerate(candidates)
        ],
    )
    builder.add_section(
        "Best candidate (estimated)",
        [f"Estimated shift : {best.shift}", f"Score           : {best.score:.2f}", f"Plaintext       : {best.plaintext.strip()}"],
    )
    builder.add_section("Cryptanalysis method", [
        "Exhaustive search over all 26 shifts, each candidate scored with the",
        "chi-square statistic against standard English letter frequencies.",
        "Ranking is statistical and may be wrong for short or unusual text.",
    ])
    builder.add_section("Security assessment", security_summary_lines("caesar"))
    offer_report(builder, ask=ask_report, forced=force_report)


def perform_ic(
    text: str,
    max_key_length: int = 12,
    *,
    ask_report: bool = False,
    force_report: bool = False,
) -> None:
    """Display Index of Coincidence evidence for the text."""
    analysis = analyze_index_of_coincidence(text)
    banner.print_section("INDEX OF COINCIDENCE")
    banner.print_block("\n".join(analysis.format_lines()))
    normalized = normalize_text(text)
    if len(normalized) >= 2:
        values = ic_by_key_length(normalized, max_key_length=max_key_length)
        banner.print_table(
            ("Key length", "Average IC of columns"),
            ic_as_rows(values, limit=max_key_length),
            aligns=["<", ">"],
            title="Average IC per assumed key length (closest to English first)",
        )
    banner.print_note(IC_EXPLANATION)

    builder = ReportBuilder(cipher="Not applicable (analysis only)", operation="Index of Coincidence")
    builder.add_key_value("Alphabetic characters", len(normalized))
    builder.add_section("Input statistics", analysis.format_lines())
    if len(normalized) >= 2:
        builder.add_section(
            "Average IC per key length",
            [
                f"key length {length:<4} average IC {value}"
                for length, value in ic_as_rows(
                    ic_by_key_length(normalized, max_key_length), limit=max_key_length
                )
            ],
        )
    builder.add_paragraph("Cryptanalysis", IC_EXPLANATION)
    offer_report(builder, ask=ask_report, forced=force_report)


def perform_kasiski(
    text: str,
    min_length: int = 3,
    max_length: int = 5,
    max_key_length: int = 20,
    *,
    ask_report: bool = False,
    force_report: bool = False,
) -> None:
    """Run and display a Kasiski examination."""
    result = kasiski_examination(
        text, min_length=min_length, max_length=max_length, max_key_length=max_key_length
    )
    banner.print_section("KASISKI EXAMINATION")
    banner.print_block("\n".join(result.format_lines()))
    if result.sequences:
        banner.print_table(
            ("Sequence", "Count", "Distances", "Shared factors"),
            kasiski_rows(result),
            aligns=["<", ">", "<", "<"],
            title="Repeated sequences",
        )
        banner.print_table(
            ("Key length", "Evidence"),
            kasiski_key_rows(result, limit=10),
            aligns=["<", ">"],
            title="Likely key lengths ranked by evidence",
        )
    banner.print_note(KASISKI_EXPLANATION)

    builder = ReportBuilder(cipher="Vigenere (assuming a repeating key)", operation="Kasiski examination")
    builder.add_key_value("Alphabetic characters", result.total_letters)
    builder.add_key_value("Sequence lengths searched", f"{min_length}-{max_length}")
    builder.add_section("Input statistics", result.format_lines())
    if result.sequences:
        builder.add_section(
            "Repeated sequences",
            [
                f"{row[0]:<6} count {row[1]:<3} distances: {row[2]}  factors: {row[3]}"
                for row in kasiski_rows(result)
            ],
        )
    builder.add_section(
        "Cryptanalysis",
        [
            "Kasiski examination provides candidate key lengths only. It does not",
            "prove the key length and does not recover the key. Combine it with the",
            "Index of Coincidence results and per-column frequency analysis.",
        ],
    )
    offer_report(builder, ask=ask_report, forced=force_report)


def perform_vigenere_analysis(
    text: str,
    max_key_length: int = 20,
    top_n: int = 5,
    key_length: int | None = None,
    *,
    ask_report: bool = False,
    force_report: bool = False,
) -> None:
    """Run the combined Vigenère cryptanalysis workflow."""
    analysis = analyze_vigenere(text, max_key_length=max_key_length, top_n=top_n)

    banner.print_section("VIGENERE CRYPTANALYSIS")
    banner.print_block("\n".join(analysis.format_lines(limit=top_n)))

    if analysis.kasiski is not None and analysis.kasiski.sequences:
        banner.print_table(
            ("Sequence", "Count", "Distances", "Shared factors"),
            kasiski_rows(analysis.kasiski),
            aligns=["<", ">", "<", "<"],
            title="Repeated sequences found by Kasiski examination",
        )

    banner.print_table(
        ("Key length", "Average IC", "Kasiski hits", "Combined score"),
        key_length_rows(analysis, limit=top_n),
        aligns=["<", ">", ">", ">"],
        title="Candidate key lengths (estimated)",
    )

    chosen = key_length if key_length is not None else analysis.best_key_length()
    if chosen is None:
        banner.print_warning("No usable key length could be estimated; the text is probably too short.")
        return

    banner.print_section(f"KEY RECOVERY ASSUMING KEY LENGTH {chosen} (estimated)")
    suggestions = suggest_key_characters(text, chosen, top_n=3)
    banner.print_table(
        ("Key position", "Suggested letters (score)"),
        position_suggestion_rows(suggestions),
        aligns=["<", "<"],
        title="Per-column key letter candidates",
    )
    candidates = recover_key_candidates(text, chosen, top_n_per_position=3, max_candidates=8)
    banner.print_table(
        ("Rank", "Candidate key", "Score", "Decrypted preview"),
        key_candidate_rows(candidates),
        aligns=["<", "<", ">", "<"],
        title="Candidate keys and their decryptions (estimated)",
    )
    banner.print_section("BEST GUESS (unconfirmed)")
    banner.print_block("\n".join(candidates[0].as_summary_lines()))
    banner.print_note(RECOVERY_NOTE)
    banner.print_note(SHORT_DISCLAIMER)

    builder = ReportBuilder(
        cipher="Vigenere Cipher",
        operation=f"Cryptanalysis (assumed key length {chosen})",
    )
    builder.add_key_value("Alphabetic characters", analysis.total_letters)
    builder.add_key_value("Index of Coincidence", f"{analysis.overall_ic:.5f}")
    builder.add_key_value("Assumed key length", chosen)
    builder.add_section("Input statistics", analysis.format_lines(limit=top_n))
    if analysis.kasiski is not None:
        builder.add_section("Kasiski examination", analysis.kasiski.format_lines())
    builder.add_section(
        "Candidate key lengths (estimated)",
        [
            f"key length {candidate.key_length}: avg IC {candidate.average_ic:.5f}, "
            f"kasiski hits {candidate.kasiski_evidence}, combined {candidate.combined_score:.3f}"
            for candidate in analysis.key_lengths
        ],
    )
    builder.add_section(
        "Per-column key letter candidates",
        [f"position {suggestion.position}: {suggestion.describe()}" for suggestion in suggestions],
    )
    builder.add_section(
        "Candidate keys (estimated)",
        [
            f"{index + 1}. key {candidate.key}  score {candidate.score:.2f}  {candidate.plaintext.strip()}"
            for index, candidate in enumerate(candidates)
        ],
    )
    builder.add_paragraph("Cryptanalysis", VIGENERE_EXPLANATION + "\n\n" + RECOVERY_NOTE)
    builder.add_section("Security assessment", security_summary_lines("vigenere"))
    offer_report(builder, ask=ask_report, forced=force_report)


def perform_file_operation(
    cipher_name: str,
    source: str,
    destination: str | None,
    secret: str | int,
    decrypt: bool,
    *,
    overwrite: bool = False,
    ask_overwrite: bool = False,
    force_report: bool = False,
) -> None:
    """Encrypt or decrypt a file and report the outcome."""
    validate_text(source, field="input file path")
    target = destination or str(file_handler.default_output_path(source))
    use_overwrite = overwrite

    if Path(target).exists() and not use_overwrite:
        if ask_overwrite and banner.confirm(
            f"'{target}' already exists. Overwrite it? [y/n]", default=False
        ):
            use_overwrite = True
        else:
            raise FileOperationError(
                f"Output file already exists: {target}. {file_handler.OVERWRITE_HINT}"
            )

    if cipher_name == "caesar":
        result = file_handler.caesar_file(
            source, target, validate_shift(secret), decrypt=decrypt, overwrite=use_overwrite
        )
        detail = f"Shift: {validate_shift(secret)}"
    else:
        result = file_handler.vigenere_file(
            source, target, validate_key(secret), decrypt=decrypt, overwrite=use_overwrite
        )
        detail = f"Key: {validate_key(secret)}"

    banner.print_section("FILE OPERATION COMPLETE")
    banner.print_key_values(
        [("Cipher", "Caesar" if cipher_name == "caesar" else "Vigenere"),
         ("Mode", "Decrypt" if decrypt else "Encrypt"),
         ("Detail", detail)]
    )
    banner.print_block("\n".join(result.as_summary_lines()))
    banner.print_note(
        "The original file was left untouched unless you explicitly chose to overwrite it."
    )

    builder = ReportBuilder(
        cipher="Caesar Cipher" if cipher_name == "caesar" else "Vigenere Cipher",
        operation=f"File {'decryption' if decrypt else 'encryption'}",
    )
    builder.add_key_value("Cipher", "Caesar" if cipher_name == "caesar" else "Vigenere")
    builder.add_key_value("Mode", detail)
    builder.add_section("Input statistics", result.as_summary_lines())
    builder.add_section("Security assessment", security_summary_lines(cipher_name))
    offer_report(builder, ask=False, forced=force_report)


# --------------------------------------------------------------------------- #
# Interactive mode
# --------------------------------------------------------------------------- #
SOURCE_MENU: tuple[tuple[str, str], ...] = (
    ("1", "Type or paste the text"),
    ("2", "Read the text from a file"),
)


def read_user_text(subject: str) -> str | None:
    """Ask the user for text, typed or read from a file.

    Returns:
        The text, or ``None`` when the user goes back.
    """
    while True:
        banner.print_menu(SOURCE_MENU, title=f"INPUT SOURCE - {subject.upper()}")
        choice = banner.prompt("Selection", default="1")
        if banner.eof_reached():
            return None
        if choice == "1":
            value = banner.prompt(f"Enter the {subject}")
            if banner.eof_reached():
                return None
            try:
                return validate_text(value, field=subject)
            except ValidationError as error:
                banner.print_error(str(error))
                continue
        if choice == "2":
            path = banner.prompt("Path to the input file")
            if banner.eof_reached():
                return None
            try:
                return file_handler.read_text(path)
            except FileOperationError as error:
                banner.print_error(str(error))
                continue
        if choice.lower() in {"b", "back", "q"}:
            return None
        banner.print_error(f"'{choice}' is not a valid selection. Enter 1, 2 or b to go back.")


def ask_shift(default: int = 3) -> int | None:
    """Ask the user for a Caesar shift."""
    while True:
        raw = banner.prompt("Caesar shift (for example 3)", default=str(default))
        if banner.eof_reached():
            return None
        try:
            return validate_shift(raw)
        except ValidationError as error:
            banner.print_error(str(error))


def ask_key() -> str | None:
    """Ask the user for a Vigenère keyword."""
    while True:
        raw = banner.prompt("Vigenère keyword (letters only, for example LEMON)")
        if banner.eof_reached():
            return None
        try:
            return validate_key(raw)
        except ValidationError as error:
            banner.print_error(str(error))


def ask_key_length(default: int | None = None) -> int | None:
    """Ask the user for a key length."""
    default_text = str(default) if default is not None else None
    while True:
        raw = banner.prompt("Key length to test", default=default_text)
        if banner.eof_reached():
            return None
        if not raw:
            return None
        try:
            return validate_key_length(raw, minimum=1, maximum=50)
        except ValidationError as error:
            banner.print_error(str(error))


def submenu(title: str, options: Sequence[tuple[str, str]], default: str) -> str | None:
    """Show a small submenu and return the validated choice."""
    while True:
        banner.print_menu(options, title=title)
        choice = banner.prompt("Selection", default=default)
        if banner.eof_reached():
            return None
        try:
            return validate_menu_choice(choice, [number for number, _ in options], default=default)
        except ValidationError as error:
            banner.print_error(str(error))


def menu_caesar() -> None:
    """Interactive Caesar cipher menu."""
    banner.print_section("CAESAR CIPHER")
    banner.print_note(CAESAR_EXPLANATION)
    choice = submenu(
        "CAESAR CIPHER OPTIONS",
        (("1", "Encrypt text"), ("2", "Decrypt text"), ("3", "Back to the main menu")),
        default="1",
    )
    if choice in {None, "3"}:
        return
    decrypt = choice == "2"
    text = read_user_text("ciphertext" if decrypt else "plaintext")
    if text is None:
        return
    shift = ask_shift()
    if shift is None:
        return
    perform_caesar(text, shift, decrypt, ask_report=True)


def menu_vigenere() -> None:
    """Interactive Vigenère cipher menu."""
    banner.print_section("VIGENERE CIPHER")
    banner.print_note(VIGENERE_EXPLANATION)
    choice = submenu(
        "VIGENERE CIPHER OPTIONS",
        (("1", "Encrypt text"), ("2", "Decrypt text"), ("3", "Back to the main menu")),
        default="1",
    )
    if choice in {None, "3"}:
        return
    decrypt = choice == "2"
    text = read_user_text("ciphertext" if decrypt else "plaintext")
    if text is None:
        return
    key = ask_key()
    if key is None:
        return
    perform_vigenere(text, key, decrypt, ask_report=True)


def menu_frequency() -> None:
    """Interactive frequency analysis."""
    text = read_user_text("text to analyse")
    if text is None:
        return
    perform_frequency(text, ask_report=True)


def menu_crack_caesar() -> None:
    """Interactive Caesar cracking."""
    banner.print_section("BREAK CAESAR CIPHER")
    banner.print_note(
        "Provide the ciphertext only - no shift is needed. All 26 shifts are tried and "
        "ranked by how much each result looks like English."
    )
    text = read_user_text("ciphertext")
    if text is None:
        return
    perform_crack_caesar(text, top_n=5, ask_report=True)


def menu_analyze_vigenere() -> None:
    """Interactive Vigenère cryptanalysis."""
    banner.print_section("ANALYZE VIGENERE CIPHER")
    banner.print_note(
        "The analyser combines frequency analysis, the Index of Coincidence and Kasiski "
        "examination. Estimated values are hypotheses to be verified, not decrypted facts."
    )
    text = read_user_text("ciphertext")
    if text is None:
        return
    analysis = analyze_vigenere(text, max_key_length=20, top_n=5)
    chosen = analysis.best_key_length()
    if chosen is not None and banner.confirm(
        f"Use the estimated key length {chosen} for key recovery? [y/n]", default=True
    ):
        pass
    elif chosen is None:
        banner.print_warning("No key length could be estimated; the text is probably too short.")
        return
    else:
        answer = ask_key_length(default=chosen)
        if not answer:
            return
        chosen = answer
    perform_vigenere_analysis(text, key_length=chosen, ask_report=True)


def menu_file_operations() -> None:
    """Interactive file encryption and decryption."""
    banner.print_section("FILE ENCRYPTION / DECRYPTION")
    banner.print_note(
        "The original file is never modified unless you explicitly confirm overwriting it. "
        "By default the output is written next to the input with an '_out' suffix."
    )
    choice = submenu(
        "FILE OPERATIONS",
        (
            ("1", "Encrypt a file with Caesar"),
            ("2", "Decrypt a file with Caesar"),
            ("3", "Encrypt a file with Vigenere"),
            ("4", "Decrypt a file with Vigenere"),
            ("5", "Back to the main menu"),
        ),
        default="1",
    )
    if choice in {None, "5"}:
        return

    cipher_name = "caesar" if choice in {"1", "2"} else "vigenere"
    decrypt = choice in {"2", "4"}

    source = banner.prompt("Path to the input file")
    if banner.eof_reached():
        return
    try:
        file_handler.read_text(source)
    except FileOperationError as error:
        banner.print_error(str(error))
        return

    default_target = str(file_handler.default_output_path(source))
    target = banner.prompt("Path to the output file", default=default_target)
    if banner.eof_reached():
        return
    if cipher_name == "caesar":
        secret: str | int | None = ask_shift()
    else:
        secret = ask_key()
    if secret is None:
        return

    perform_file_operation(
        cipher_name,
        source,
        target,
        secret,
        decrypt,
        ask_overwrite=True,
    )


def menu_security() -> None:
    """Interactive security assessment."""
    banner.print_section("SECURITY / STRENGTH ANALYSIS")
    for profile in profiles():
        banner.print_section(profile.name.upper())
        banner.print_block("\n".join(profile.format_lines()))
    banner.print_disclaimer()

    builder = ReportBuilder(cipher="Classical ciphers", operation="Security assessment")
    for profile in profiles():
        builder.add_section(profile.name, profile.format_lines())
    builder.add_paragraph(
        "Disclaimer",
        "These algorithms are implemented for educational purposes and must NOT be used "
        "to protect real confidential information.",
    )
    offer_report(builder, ask=True)


def menu_help() -> None:
    """Interactive help."""
    banner.print_section("HELP AND COMMAND REFERENCE")
    banner.print_block("\n".join(HELP_LINES))
    banner.print_section("HOW THE TOOL WORKS")
    banner.print_note(
        "Every menu entry can also be reached from the command line, which makes the tool "
        "easy to script and easy to demonstrate during a viva. Use --report to save any "
        "analysis into a timestamped text file inside the reports/ folder."
    )
    banner.print_note(IC_EXPLANATION)
    banner.print_note(KASISKI_EXPLANATION)


def interactive_mode() -> int:
    """Run the menu driven interface until the user exits."""
    banner.print_banner(TOOL_TITLE, TOOL_SUBTITLE)
    banner.print_disclaimer()

    actions: dict[str, Callable[[], None]] = {
        "1": menu_caesar,
        "2": menu_vigenere,
        "3": menu_frequency,
        "4": menu_crack_caesar,
        "5": menu_analyze_vigenere,
        "6": menu_file_operations,
        "7": menu_security,
        "8": menu_help,
    }

    while True:
        banner.print_menu(MENU_OPTIONS)
        choice = banner.prompt("Enter your choice")
        if banner.eof_reached():
            banner.print_info("End of input detected. Exiting.")
            return 0
        try:
            choice = validate_menu_choice(choice, [number for number, _ in MENU_OPTIONS])
        except ValidationError as error:
            banner.print_error(str(error))
            continue

        if choice == "9":
            banner.print_info("Exiting. Remember: educational use only.")
            return 0

        try:
            actions[choice]()
        except ValidationError as error:
            banner.print_error(str(error))
        except FileOperationError as error:
            banner.print_error(str(error))
        except KeyboardInterrupt:
            banner.print_warning("Operation cancelled by the user.")
        except Exception as error:  # pragma: no cover - final safety net
            banner.print_error(f"Unexpected error: {error}")

        if banner.eof_reached():
            return 0
        banner.pause()


# --------------------------------------------------------------------------- #
# Command handlers
# --------------------------------------------------------------------------- #
def _command_caesar(args: argparse.Namespace, decrypt: bool) -> int:
    perform_caesar(
        _resolve_text(args, "plaintext" if not decrypt else "ciphertext"),
        _require_shift(args),
        decrypt,
        force_report=_report_requested(args),
    )
    return 0


def _command_vigenere(args: argparse.Namespace, decrypt: bool) -> int:
    perform_vigenere(
        _resolve_text(args, "plaintext" if not decrypt else "ciphertext"),
        _require_key(args),
        decrypt,
        force_report=_report_requested(args),
    )
    return 0


def _command_frequency(args: argparse.Namespace) -> int:
    perform_frequency(_resolve_text(args), force_report=_report_requested(args))
    return 0


def _command_crack_caesar(args: argparse.Namespace) -> int:
    top = validate_key_length(args.top, minimum=1, maximum=26, field="candidate count")
    perform_crack_caesar(_resolve_text(args, "ciphertext"), top_n=top, force_report=_report_requested(args))
    return 0


def _command_analyze_vigenere(args: argparse.Namespace) -> int:
    max_key_length = validate_key_length(args.max_key_length, minimum=2, maximum=60, field="maximum key length")
    top = validate_key_length(args.top, minimum=1, maximum=20, field="candidate count")
    key_length = None
    if args.key_length is not None:
        key_length = validate_key_length(args.key_length, minimum=1, maximum=60)
    perform_vigenere_analysis(
        _resolve_text(args, "ciphertext"),
        max_key_length=max_key_length,
        top_n=top,
        key_length=key_length,
        force_report=_report_requested(args),
    )
    return 0


def _command_ic(args: argparse.Namespace) -> int:
    max_key_length = validate_key_length(args.max_key_length, minimum=1, maximum=60, field="maximum key length")
    perform_ic(_resolve_text(args), max_key_length=max_key_length, force_report=_report_requested(args))
    return 0


def _command_kasiski(args: argparse.Namespace) -> int:
    min_length = validate_key_length(args.min_length, minimum=2, maximum=10, field="minimum sequence length")
    max_length = validate_key_length(args.max_length, minimum=min_length, maximum=10, field="maximum sequence length")
    max_key_length = validate_key_length(args.max_key_length, minimum=2, maximum=60, field="maximum key length")
    perform_kasiski(
        _resolve_text(args, "ciphertext"),
        min_length=min_length,
        max_length=max_length,
        max_key_length=max_key_length,
        force_report=_report_requested(args),
    )
    return 0


def _command_security(args: argparse.Namespace) -> int:
    selected = args.cipher
    chosen = [profile for profile in profiles() if selected is None or profile.name.lower().startswith(selected)]
    banner.print_section("SECURITY / STRENGTH ANALYSIS")
    for profile in chosen:
        banner.print_section(profile.name.upper())
        banner.print_block("\n".join(profile.format_lines()))
    banner.print_disclaimer()

    builder = ReportBuilder(cipher="Classical ciphers", operation="Security assessment")
    for profile in chosen:
        builder.add_section(profile.name, profile.format_lines())
    offer_report(builder, forced=_report_requested(args))
    return 0


def _command_file_caesar(args: argparse.Namespace) -> int:
    perform_file_operation(
        "caesar",
        args.input,
        args.output,
        validate_shift(args.shift),
        args.decrypt,
        overwrite=args.overwrite,
    )
    return 0


def _command_file_vigenere(args: argparse.Namespace) -> int:
    perform_file_operation(
        "vigenere",
        args.input,
        args.output,
        validate_key(args.key),
        args.decrypt,
        overwrite=args.overwrite,
    )
    return 0


COMMANDS: dict[str, Callable[[argparse.Namespace], int]] = {
    "caesar-encrypt": lambda args: _command_caesar(args, False),
    "caesar-decrypt": lambda args: _command_caesar(args, True),
    "vigenere-encrypt": lambda args: _command_vigenere(args, False),
    "vigenere-decrypt": lambda args: _command_vigenere(args, True),
    "frequency": _command_frequency,
    "crack-caesar": _command_crack_caesar,
    "analyze-vigenere": _command_analyze_vigenere,
    "ic": _command_ic,
    "kasiski": _command_kasiski,
    "security": _command_security,
    "file-caesar": _command_file_caesar,
    "file-vigenere": _command_file_vigenere,
}


# --------------------------------------------------------------------------- #
# Entry point
# --------------------------------------------------------------------------- #
def main(argv: Sequence[str] | None = None) -> int:
    """Run the tool.

    Args:
        argv: Argument list; defaults to ``sys.argv[1:]``.

    Returns:
        A process exit code: ``0`` on success, ``1`` on a handled error and
        ``2`` for invalid command line usage.
    """
    _configure_output_encoding()
    arguments = list(sys.argv[1:] if argv is None else argv)

    parser = build_parser()
    try:
        args = parser.parse_args(arguments)
    except SystemExit as exit_error:  # --help, --version and usage errors
        return int(exit_error.code or 0)

    banner.reset_eof_flag()
    if getattr(args, "no_color", False):
        banner.disable_color()

    command = getattr(args, "command", None)
    if command is None or command == "interactive":
        return interactive_mode()

    handler = COMMANDS.get(command)
    if handler is None:  # pragma: no cover - argparse prevents this
        banner.print_error(f"Unsupported operation: {command}")
        return 2

    try:
        return handler(args)
    except ValidationError as error:
        banner.print_error(str(error))
        return 1
    except FileOperationError as error:
        banner.print_error(str(error))
        return 1
    except KeyboardInterrupt:
        banner.print_warning("Cancelled by the user.")
        return 130
    except Exception as error:  # pragma: no cover - final safety net
        banner.print_error(f"Unexpected error: {error}")
        return 1


def _configure_output_encoding() -> None:
    """Avoid UnicodeEncodeError on consoles with a limited code page."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(errors="replace")
        except (ValueError, OSError):  # pragma: no cover - defensive
            continue


if __name__ == "__main__":
    raise SystemExit(main())
