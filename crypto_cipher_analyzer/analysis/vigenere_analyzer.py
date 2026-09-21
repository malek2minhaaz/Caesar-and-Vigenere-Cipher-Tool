"""Vigenère cryptanalysis.

This module combines the three classical techniques into one workflow:

1. **Index of Coincidence per key length** - the average IC of the columns
   peaks at the true key length because each column is then a single Caesar
   shift of English text.
2. **Kasiski examination** - repeated sequences give distances whose common
   factors are key-length candidates.
3. **Per-column frequency analysis** - once a key length is assumed, every
   column can be scored independently and the best key letter chosen for it.

Nothing here proves anything. The output is explicitly labelled *estimated*,
*candidate* and *likely*, and the caller is expected to compare several
candidates. A wrong key length produces a plausible-looking but wrong key, so
the tool always shows alternatives.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from analysis.frequency import fitness_score
from analysis.ic_analysis import (
    EXPECTED_ENGLISH_IC,
    analyze_index_of_coincidence,
    ic_by_key_length,
)
from analysis.kasiski import KasiskiResult, kasiski_examination
from ciphers import vigenere
from ciphers.caesar import shift_character
from utils.text_utils import ALPHABET, key_length_columns, normalize_text
from utils.validators import ValidationError, validate_text

__all__ = [
    "KeyLengthCandidate",
    "PositionSuggestion",
    "KeyCandidate",
    "VigenereAnalysis",
    "suggest_key_lengths",
    "suggest_key_characters",
    "recover_key_candidates",
    "analyze_vigenere",
    "key_length_rows",
    "key_candidate_rows",
    "RECOVERY_NOTE",
]

#: Printed with key recovery output.
RECOVERY_NOTE: str = (
    "Estimated values are statistical guesses, not decrypted facts. Verify a "
    "candidate key by reading the recovered plaintext: if it is meaningless, the "
    "key length was probably wrong or the text is too short for cryptanalysis."
)

#: Weight given to the Index of Coincidence evidence when ranking key lengths.
#: The IC gets the dominant share because it is the sharper signal: every
#: divisor of the true key length also collects Kasiski evidence (a distance
#: that is a multiple of 6 is automatically a multiple of 3), so the Kasiski
#: count alone tends to prefer the smallest divisor of the real key length.
IC_WEIGHT: float = 0.85

#: Weight given to the Kasiski evidence when ranking key lengths. Kept small
#: on purpose: it confirms and breaks ties between key lengths that the IC
#: already ranks closely together.
KASISKI_WEIGHT: float = 0.15


@dataclass(frozen=True)
class KeyLengthCandidate:
    """A possible Vigenère key length with the evidence supporting it."""

    key_length: int
    average_ic: float
    ic_score: float
    kasiski_evidence: int
    combined_score: float

    def to_row(self) -> tuple[str, str, str, str]:
        """Return a ``(key length, average IC, Kasiski evidence, score)`` row."""
        return (
            str(self.key_length),
            f"{self.average_ic:.5f}",
            str(self.kasiski_evidence),
            f"{self.combined_score:.3f}",
        )


@dataclass(frozen=True)
class PositionSuggestion:
    """The most likely key letters for one position of the key."""

    position: int
    suggestions: tuple[tuple[str, float], ...] = field(default_factory=tuple)

    def best(self) -> str:
        """Return the highest scoring key letter for this position."""
        return self.suggestions[0][0] if self.suggestions else "A"

    def letters(self) -> str:
        """Return all suggested letters as a string, best first."""
        return "".join(letter for letter, _ in self.suggestions)

    def describe(self, limit: int = 3) -> str:
        """Return ``A (93.10), B (41.20)`` style output for the CLI."""
        return ", ".join(
            f"{letter} ({score:.2f})" for letter, score in self.suggestions[:limit]
        )


@dataclass(frozen=True)
class KeyCandidate:
    """A candidate keyword together with the plaintext it produces."""

    key: str
    plaintext: str
    score: float

    def to_row(self, rank: int, preview_width: int = 60) -> tuple[str, str, str, str]:
        """Return a ``(rank, key, score, preview)`` row for table output."""
        preview = self.plaintext.replace("\n", " ").strip()
        if len(preview) > preview_width:
            preview = preview[: preview_width - 3] + "..."
        return (str(rank), self.key, f"{self.score:.2f}", preview)

    def as_summary_lines(self) -> list[str]:
        """Return the candidate as report lines."""
        return [
            f"Candidate key     : {self.key}",
            f"Fitness score     : {self.score:.2f}",
            f"Decrypted preview : {self.plaintext.strip()}",
        ]


@dataclass(frozen=True)
class VigenereAnalysis:
    """The combined result of the Vigenère cryptanalysis workflow."""

    total_letters: int
    overall_ic: float
    ic_interpretation: str
    key_lengths: tuple[KeyLengthCandidate, ...] = field(default_factory=tuple)
    kasiski: KasiskiResult | None = None

    def best_key_length(self) -> int | None:
        """Return the highest scoring key-length candidate, if any."""
        return self.key_lengths[0].key_length if self.key_lengths else None

    def format_lines(self, limit: int = 5) -> list[str]:
        """Return printable lines describing the analysis."""
        lines = [
            f"Characters analysed          : {self.total_letters}",
            f"Index of Coincidence         : {self.overall_ic:.5f}",
            f"IC interpretation            : {self.ic_interpretation}",
        ]
        if self.kasiski is not None:
            lines.append(
                f"Repeated sequences found     : {len(self.kasiski.sequences)}"
            )
        lines.append("")
        lines.append("Candidate key lengths (combined evidence, estimated):")
        lines.append("  Key length   Avg IC     Kasiski hits   Score")
        lines.append("  ----------   --------   ------------   -----")
        for candidate in self.key_lengths[:limit]:
            key_length, average_ic, evidence, score = candidate.to_row()
            lines.append(
                f"  {key_length:>10}   {average_ic:>8}   {evidence:>12}   {score:>5}"
            )
        if not self.key_lengths:
            lines.append("  No usable key-length candidates (the text is probably too short).")
        lines.append("")
        lines.append("Reminder: key lengths above are estimates from statistics, not facts.")
        return lines


def suggest_key_lengths(
    ciphertext: str,
    max_key_length: int = 20,
    top_n: int = 5,
    minimum_letters_per_column: int = 4,
) -> list[KeyLengthCandidate]:
    """Rank candidate Vigenère key lengths.

    The ranking blends the per-column Index of Coincidence (weighted 0.85) with
    the Kasiski evidence (weighted 0.15). The IC dominates because it is what
    separates the true key length from its own divisors, while the Kasiski count
    is used to confirm the result and to break ties.

    Args:
        ciphertext: Ciphertext to analyse.
        max_key_length: Largest key length to consider.
        top_n: How many candidates to return.
        minimum_letters_per_column: Key lengths that would leave fewer letters
            than this in a column are ignored as statistically meaningless.

    Returns:
        Candidates ordered from most to least likely.

    Raises:
        ValidationError: If the ciphertext contains fewer than two letters.
    """
    normalized = normalize_text(ciphertext)
    if len(normalized) < 2:
        raise ValidationError("At least two letters are required for key-length analysis.")
    if top_n < 1:
        raise ValidationError("At least one key-length candidate must be requested.")

    ic_values = ic_by_key_length(
        normalized,
        max_key_length=max_key_length,
        minimum_letters_per_column=minimum_letters_per_column,
    )
    kasiski = kasiski_examination(normalized, max_key_length=max_key_length)
    kasiski_scores = dict(kasiski.ranked_key_lengths)
    highest_kasiski = max(kasiski_scores.values(), default=1) or 1

    candidates: list[KeyLengthCandidate] = []
    for key_length, average_ic in ic_values.items():
        ic_score = max(0.0, 1.0 - abs(average_ic - EXPECTED_ENGLISH_IC) / EXPECTED_ENGLISH_IC)
        evidence = kasiski_scores.get(key_length, 0)
        combined = IC_WEIGHT * ic_score + KASISKI_WEIGHT * (evidence / highest_kasiski)
        candidates.append(
            KeyLengthCandidate(
                key_length=key_length,
                average_ic=average_ic,
                ic_score=ic_score,
                kasiski_evidence=evidence,
                combined_score=combined,
            )
        )

    candidates.sort(key=lambda candidate: (-candidate.combined_score, candidate.key_length))
    return candidates[:top_n]


def suggest_key_characters(
    ciphertext: str, key_length: int, top_n: int = 3
) -> list[PositionSuggestion]:
    """Suggest key letters for every position of an assumed key length.

    For each column the ciphertext letters were shifted with one key letter.
    Trying all 26 possible letters and scoring the resulting text with the same
    English-likeness measure used by the Caesar cracker produces a ranked list
    of key letters for that column.

    Args:
        ciphertext: Ciphertext to analyse.
        key_length: Assumed key length (must be at least 1).
        top_n: How many key letters to suggest per position.

    Returns:
        One :class:`PositionSuggestion` per key position, positions numbered
        from 1.

    Raises:
        ValidationError: If the key length is invalid or *top_n* is not positive.
    """
    if key_length < 1:
        raise ValidationError("The key length must be at least 1.")
    if top_n < 1:
        raise ValidationError("At least one key letter must be suggested.")

    normalized = normalize_text(ciphertext)
    if len(normalized) < key_length:
        raise ValidationError(
            "The ciphertext is shorter than the requested key length; choose a smaller length."
        )

    suggestions: list[PositionSuggestion] = []
    for position, column in enumerate(key_length_columns(normalized, key_length), start=1):
        scored: list[tuple[str, float]] = []
        for offset, letter in enumerate(ALPHABET):
            candidate_plaintext = "".join(shift_character(char, -offset) for char in column)
            scored.append((letter, fitness_score(candidate_plaintext)))
        scored.sort(key=lambda item: (-item[1], item[0]))
        suggestions.append(
            PositionSuggestion(position=position, suggestions=tuple(scored[:top_n]))
        )
    return suggestions


def recover_key_candidates(
    ciphertext: str,
    key_length: int,
    top_n_per_position: int = 3,
    max_candidates: int = 8,
) -> list[KeyCandidate]:
    """Build and rank candidate keys for an assumed key length.

    The best key (the top letter of every position) is produced first, then
    variants that swap a single position for its second or third suggestion.
    Every variant is scored by decrypting the whole ciphertext, which is a much
    stronger signal than the per-column score alone.

    Args:
        ciphertext: Ciphertext to attack.
        key_length: Assumed key length.
        top_n_per_position: How many key letters to consider per position.
        max_candidates: Maximum number of candidates to return.

    Returns:
        Candidate keys sorted by descending plaintext fitness.
    """
    suggestions = suggest_key_characters(ciphertext, key_length, top_n=top_n_per_position)
    best_key = "".join(suggestion.best() for suggestion in suggestions)

    keys: list[str] = [best_key]
    for index, suggestion in enumerate(suggestions):
        for letter, _score in suggestion.suggestions[1:]:
            variant = list(best_key)
            variant[index] = letter
            keys.append("".join(variant))

    seen: set[str] = set()
    candidates: list[KeyCandidate] = []
    for key in keys:
        if key in seen:
            continue
        seen.add(key)
        plaintext = vigenere.decrypt(ciphertext, key)
        candidates.append(
            KeyCandidate(key=key, plaintext=plaintext, score=fitness_score(plaintext))
        )

    candidates.sort(key=lambda candidate: (-candidate.score, candidate.key))
    return candidates[:max_candidates]


def analyze_vigenere(
    ciphertext: str, max_key_length: int = 20, top_n: int = 5
) -> VigenereAnalysis:
    """Run the full Vigenère analysis workflow without the per-column step.

    Args:
        ciphertext: Ciphertext to analyse.
        max_key_length: Largest key length to consider.
        top_n: How many key-length candidates to keep.

    Returns:
        A :class:`VigenereAnalysis`.

    Raises:
        ValidationError: If the ciphertext has fewer than eight letters.
    """
    validate_text(ciphertext)
    normalized = normalize_text(ciphertext)
    if len(normalized) < 8:
        raise ValidationError(
            "At least eight letters are required for meaningful Vigenere analysis."
        )

    overall = analyze_index_of_coincidence(normalized)
    return VigenereAnalysis(
        total_letters=overall.total_letters,
        overall_ic=overall.ic,
        ic_interpretation=overall.interpretation,
        key_lengths=tuple(
            suggest_key_lengths(normalized, max_key_length=max_key_length, top_n=top_n)
        ),
        kasiski=kasiski_examination(normalized, max_key_length=max_key_length),
    )


def key_length_rows(
    analysis: VigenereAnalysis, limit: int = 10
) -> list[tuple[str, str, str, str]]:
    """Format the key-length candidates of *analysis* as table rows."""
    return [candidate.to_row() for candidate in analysis.key_lengths[:limit]]


def key_candidate_rows(
    candidates: list[KeyCandidate], limit: int = 10
) -> list[tuple[str, str, str, str]]:
    """Format recovered key candidates as table rows with ranks from 1."""
    return [
        candidate.to_row(rank=index + 1)
        for index, candidate in enumerate(candidates[:limit])
    ]


def position_suggestion_rows(
    suggestions: list[PositionSuggestion], limit: int = 3
) -> list[tuple[str, str]]:
    """Format per-position key letter suggestions as table rows."""
    return [
        (str(suggestion.position), suggestion.describe(limit=limit))
        for suggestion in suggestions
    ]
