"""Letter frequency analysis and English-likeness scoring.

Frequency analysis is the workhorse of classical cryptanalysis: natural
language is very uneven in its letter usage (E, T and A dominate English) while
a good cipher flattens that distribution. Two measurements are provided here:

* :func:`frequency_analysis` - the descriptive table shown to the user.
* :func:`chi_squared` / :func:`fitness_score` - the numeric measure used by the
  Caesar cracker and the Vigenère key recoverer to rank candidates.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Sequence

from utils.text_utils import (
    ALPHABET,
    ENGLISH_LETTER_FREQUENCIES,
    count_letters,
    normalize_text,
)
from utils.validators import ValidationError

__all__ = [
    "FrequencyResult",
    "frequency_analysis",
    "letter_rows",
    "compare_with_english",
    "chi_squared",
    "digram_score",
    "fitness_score",
]

#: Two-letter combinations that occur often in English, used as a supplementary
#: scoring signal. The values are *relative weights*, not corpus frequencies:
#: ``1.0`` for the most common digrams, ``0.7`` for common ones and ``0.4`` for
#: moderately common ones. Combining this with the letter-distribution score
#: makes candidate ranking far more reliable on short texts, where a single
#: letter count is not enough evidence (for example ``LL`` is normal English
#: while ``II`` is not).
COMMON_DIGRAMS: dict[str, float] = {
    # Very common
    "TH": 1.0, "HE": 1.0, "IN": 1.0, "ER": 1.0, "AN": 1.0, "RE": 1.0,
    "ON": 1.0, "AT": 1.0, "EN": 1.0, "ND": 1.0, "TI": 1.0, "ES": 1.0,
    "OR": 1.0, "TE": 1.0, "OF": 1.0, "ED": 1.0, "IS": 1.0, "IT": 1.0,
    "AL": 1.0, "AR": 1.0, "ST": 1.0, "TO": 1.0, "NT": 1.0, "NG": 1.0,
    # Common
    "SE": 0.7, "HA": 0.7, "AS": 0.7, "OU": 0.7, "IO": 0.7, "LE": 0.7,
    "VE": 0.7, "CO": 0.7, "ME": 0.7, "DE": 0.7, "HI": 0.7, "RI": 0.7,
    "RO": 0.7, "IC": 0.7, "NE": 0.7, "EA": 0.7, "RA": 0.7, "CE": 0.7,
    "LI": 0.7, "CH": 0.7, "LL": 0.7, "BE": 0.7, "MA": 0.7, "SI": 0.7,
    "OM": 0.7, "UR": 0.7, "LD": 0.7, "RS": 0.7, "TA": 0.7, "NS": 0.7,
    # Moderately common
    "EL": 0.4, "LO": 0.4, "AC": 0.4, "IL": 0.4, "OT": 0.4, "LA": 0.4,
    "EC": 0.4, "NO": 0.4, "UT": 0.4, "SS": 0.4, "RT": 0.4, "ET": 0.4,
    "TR": 0.4, "OL": 0.4, "NC": 0.4, "OW": 0.4, "OO": 0.4, "WO": 0.4,
    "EE": 0.4, "LY": 0.4, "MO": 0.4, "PO": 0.4, "PR": 0.4, "PL": 0.4,
    "GR": 0.4, "BR": 0.4, "CR": 0.4, "DR": 0.4, "FR": 0.4, "WH": 0.4,
    "SH": 0.4, "CK": 0.4, "GH": 0.4, "PH": 0.4, "QU": 0.4, "TT": 0.4,
    "FF": 0.4, "NN": 0.4, "RR": 0.4, "PP": 0.4, "AG": 0.4, "IG": 0.4,
    "UG": 0.4, "OY": 0.4, "AY": 0.4, "EY": 0.4, "OB": 0.4, "OC": 0.4,
    "OD": 0.4, "SP": 0.4, "SC": 0.4, "SL": 0.4, "SM": 0.4, "SN": 0.4,
}

#: Weight of the letter-distribution component of :func:`fitness_score`.
UNIGRAM_WEIGHT: float = 0.5

#: Weight of the digram component of :func:`fitness_score`.
DIGRAM_WEIGHT: float = 0.5


@dataclass(frozen=True)
class FrequencyResult:
    """The result of a single-letter frequency analysis."""

    total_characters: int
    total_letters: int
    counts: dict[str, int]
    percentages: dict[str, float]
    most_common: tuple[tuple[str, int, float], ...] = field(default_factory=tuple)
    least_common: tuple[tuple[str, int, float], ...] = field(default_factory=tuple)

    def as_summary_lines(self) -> list[str]:
        """Return a short human readable summary of the analysis."""
        top = ", ".join(f"{letter} ({count})" for letter, count, _ in self.most_common)
        least = ", ".join(f"{letter} ({count})" for letter, count, _ in self.least_common)
        return [
            f"Total characters      : {self.total_characters}",
            f"Alphabetic characters : {self.total_letters}",
            f"Most frequent letters : {top}",
            f"Least frequent letters: {least}",
        ]


def frequency_analysis(text: str, top_n: int = 5) -> FrequencyResult:
    """Analyse the letter frequency of *text*.

    Args:
        text: Text to analyse; non-letter characters are ignored but counted in
            ``total_characters``.
        top_n: How many letters to include in the most/least common lists.

    Returns:
        A :class:`FrequencyResult`.

    Raises:
        ValidationError: If *text* contains no letters at all.
    """
    if not isinstance(text, str):
        raise ValidationError("The text must be a string.")
    normalized = normalize_text(text)
    if not normalized:
        raise ValidationError("No letters were found in the input; nothing to analyse.")

    counts_raw = count_letters(text)
    total = len(normalized)
    counts = {letter: counts_raw.get(letter, 0) for letter in ALPHABET}
    percentages = {letter: counts[letter] * 100.0 / total for letter in ALPHABET}

    ranked = sorted(
        ((letter, counts[letter]) for letter in ALPHABET if counts[letter] > 0),
        key=lambda item: (-item[1], item[0]),
    )
    most_common = tuple(
        (letter, count, percentages[letter]) for letter, count in ranked[: max(top_n, 0)]
    )
    least_common = tuple(
        (letter, count, percentages[letter]) for letter, count in reversed(ranked[-max(top_n, 0) :])
    )

    return FrequencyResult(
        total_characters=len(text),
        total_letters=total,
        counts=counts,
        percentages=percentages,
        most_common=most_common,
        least_common=least_common,
    )


def letter_rows(result: FrequencyResult, only_present: bool = True) -> list[tuple[str, int, str]]:
    """Return ``(letter, count, percentage)`` rows ordered by frequency.

    Args:
        result: A frequency result.
        only_present: When ``True``, letters that never occur are omitted.

    Returns:
        Rows ready to be handed to :func:`utils.banner.print_table`.
    """
    letters = [letter for letter, count, _ in result.most_common]
    if not only_present:
        letters = [letter for letter in ALPHABET if result.counts[letter] > 0]
    ordered = sorted(letters, key=lambda letter: (-result.counts[letter], letter))
    return [
        (letter, result.counts[letter], f"{result.percentages[letter]:.2f}%")
        for letter in ordered
    ]


def compare_with_english(
    result: FrequencyResult, top_n: int = 10
) -> list[tuple[str, str, str, str]]:
    """Compare observed frequencies with the standard English distribution.

    Returns:
        Rows of ``(letter, observed %, expected English %, difference)`` for the
        *top_n* most frequent letters found in the input.
    """
    rows: list[tuple[str, str, str, str]] = []
    for letter, _count, percentage in result.most_common[:top_n]:
        expected = ENGLISH_LETTER_FREQUENCIES[letter]
        difference = percentage - expected
        sign = "+" if difference >= 0 else ""
        rows.append(
            (
                letter,
                f"{percentage:.2f}%",
                f"{expected:.2f}%",
                f"{sign}{difference:.2f}%",
            )
        )
    return rows


def chi_squared(text: str) -> float:
    """Return the chi-square statistic of *text* against English frequencies.

    The statistic compares the observed count of each letter with the count
    expected if the text were English prose. A *low* value means the text looks
    English; a high value means it does not.

    Args:
        text: Any text; only its letters are considered.

    Returns:
        The chi-square statistic, or ``0.0`` when the text has no letters.
    """
    normalized = normalize_text(text)
    total = len(normalized)
    if total == 0:
        return 0.0
    counts = Counter(normalized)
    statistic = 0.0
    for letter, percentage in ENGLISH_LETTER_FREQUENCIES.items():
        expected = total * percentage / 100.0
        observed = counts.get(letter, 0)
        statistic += (observed - expected) ** 2 / expected
    return statistic


def digram_score(text: str) -> float:
    """Score the two-letter combinations of *text* against common English digrams.

    Args:
        text: Candidate plaintext.

    Returns:
        A value between ``0`` (no recognisable English digram) and ``100``
        (every digram is among the most common ones).
    """
    normalized = normalize_text(text)
    if len(normalized) < 2:
        return 0.0
    total = sum(
        COMMON_DIGRAMS.get(normalized[index : index + 2], 0.0)
        for index in range(len(normalized) - 1)
    )
    return 100.0 * total / (len(normalized) - 1)


def fitness_score(text: str) -> float:
    """Score how much *text* looks like English, on a ``0..100`` scale.

    The score blends two independent signals:

    * a letter-distribution component derived from :func:`chi_squared` using
      ``100 * (1 - chi / (chi + letters))``; and
    * a digram component, :func:`digram_score`, which recognises that ``LL``
      is ordinary English while ``II`` is not.

    Both components lie in ``0..100`` and are weighted with
    :data:`UNIGRAM_WEIGHT` and :data:`DIGRAM_WEIGHT`. The result is a
    *statistical estimate*, not proof: short texts, names, technical terms and
    non-English text can still be misjudged.

    Args:
        text: Candidate plaintext.

    Returns:
        A fitness value between ``0`` and ``100``.
    """
    normalized = normalize_text(text)
    letters = len(normalized)
    if letters == 0:
        return 0.0
    statistic = chi_squared(normalized)
    unigram_component = 100.0 * (1.0 - statistic / (statistic + letters))
    digram_component = digram_score(normalized)
    return UNIGRAM_WEIGHT * unigram_component + DIGRAM_WEIGHT * digram_component


def formatted_frequency_lines(result: FrequencyResult, top_n: int | None = None) -> list[str]:
    """Return frequency table lines for embedding in a text report."""
    rows = letter_rows(result)
    if top_n is not None:
        rows = rows[:top_n]
    widths = [len("Letter"), len("Count"), len("Frequency")]
    string_rows = [[letter, str(count), percentage] for letter, count, percentage in rows]
    for row in string_rows:
        for index, cell in enumerate(row):
            widths[index] = max(widths[index], len(cell))
    lines = [
        f"{'Letter':<{widths[0]}}  {'Count':<{widths[1]}}  {'Frequency':<{widths[2]}}".rstrip(),
        "-" * (sum(widths) + 4),
    ]
    lines.extend(
        f"{letter:<{widths[0]}}  {count:<{widths[1]}}  {percentage:<{widths[2]}}".rstrip()
        for letter, count, percentage in string_rows
    )
    return lines


def frequency_correlation(text: str) -> float:
    """Return the correlation between observed and expected English frequencies.

    Values close to ``1.0`` indicate English-like text; values near ``0``
    indicate a flat or random distribution. Used as a secondary signal by the
    Vigenère analyser.
    """
    normalized = normalize_text(text)
    total = len(normalized)
    if total == 0:
        return 0.0
    counts = Counter(normalized)
    observed = [counts.get(letter, 0) * 100.0 / total for letter in ALPHABET]
    expected = [ENGLISH_LETTER_FREQUENCIES[letter] for letter in ALPHABET]
    mean_observed = sum(observed) / len(observed)
    mean_expected = sum(expected) / len(expected)
    covariance = sum(
        (observed[index] - mean_observed) * (expected[index] - mean_expected)
        for index in range(len(observed))
    )
    variance_observed = sum((value - mean_observed) ** 2 for value in observed)
    variance_expected = sum((value - mean_expected) ** 2 for value in expected)
    denominator = (variance_observed * variance_expected) ** 0.5
    if denominator == 0:
        return 0.0
    return covariance / denominator


def score_rows(candidates: Sequence[tuple[str, float]]) -> list[tuple[str, str]]:
    """Format ``(label, score)`` pairs for table output."""
    return [(label, f"{score:.2f}") for label, score in candidates]
