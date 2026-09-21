"""Kasiski examination for Vigenère ciphertext.

Friedrich Kasiski's 1863 observation is simple and powerful: in a repeating-key
cipher, a plaintext fragment that happens to align with the key twice will
produce the *same* ciphertext fragment twice, and the distance between the two
occurrences is a multiple of the key length.

The algorithm implemented here:

1. normalise the ciphertext to letters only;
2. find every word of length 3-5 that occurs more than once;
3. record the positions and the distances between the occurrences;
4. factorise those distances;
5. rank the factors - a factor that divides many distances is a good key-length
   candidate.

Kasiski examination yields *candidate* key lengths. It is not guaranteed to
find the true length, and it should always be combined with Index of
Coincidence evidence before a key length is assumed.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Iterable, Sequence

from utils.text_utils import normalize_text

__all__ = [
    "RepeatedSequence",
    "KasiskiResult",
    "factorize",
    "distances_from_positions",
    "find_repeated_sequences",
    "rank_key_lengths",
    "kasiski_examination",
    "kasiski_rows",
]


@dataclass(frozen=True)
class RepeatedSequence:
    """A word that occurs at least twice in the ciphertext."""

    sequence: str
    positions: tuple[int, ...]
    distances: tuple[int, ...]
    factors: dict[int, int] = field(default_factory=dict)

    @property
    def occurrences(self) -> int:
        """How many times the sequence occurs."""
        return len(self.positions)

    def describe(self, limit: int = 6) -> str:
        """Return a compact one-line description of the repetitions."""
        positions = ", ".join(str(position) for position in self.positions[:limit])
        if len(self.positions) > limit:
            positions += ", ..."
        return f"'{self.sequence}' at {positions}"

    def factor_summary(self, limit: int = 8) -> str:
        """Return the factors shared by the distances, most common first."""
        ordered = sorted(self.factors.items(), key=lambda item: (-item[1], item[0]))
        return ", ".join(str(factor) for factor, _ in ordered[:limit])


@dataclass(frozen=True)
class KasiskiResult:
    """The complete result of a Kasiski examination."""

    total_letters: int
    min_length: int
    max_length: int
    sequences: tuple[RepeatedSequence, ...] = field(default_factory=tuple)
    factor_counts: dict[int, int] = field(default_factory=dict)
    ranked_key_lengths: tuple[tuple[int, int], ...] = field(default_factory=tuple)

    @property
    def has_evidence(self) -> bool:
        """``True`` when at least one repeated sequence was found."""
        return bool(self.sequences)

    def format_lines(self, max_sequences: int = 8, max_factors: int = 10) -> list[str]:
        """Return printable lines describing the examination."""
        lines = [
            f"Characters analysed          : {self.total_letters}",
            f"Sequence length searched     : {self.min_length}-{self.max_length}",
            f"Repeated sequences found     : {len(self.sequences)}",
        ]
        if not self.sequences:
            lines.append(
                "No repeated sequences were found: the text is short, the key is long, "
                "or the repetition is missing. Use the Index of Coincidence results instead."
            )
            return lines

        lines.append("")
        lines.append("Repeated sequences (positions are 0-based indices into the letters):")
        for sequence in self.sequences[:max_sequences]:
            lines.append(
                f"  {sequence.sequence:<6} x{sequence.occurrences}  positions: "
                f"{', '.join(str(p) for p in sequence.positions)}"
            )
            lines.append(
                f"         distances: {', '.join(str(d) for d in sequence.distances)}"
                f"  ->  factors: {sequence.factor_summary()}"
            )
        if len(self.sequences) > max_sequences:
            lines.append(f"  ... and {len(self.sequences) - max_sequences} more")

        lines.append("")
        top_factors = ", ".join(
            f"{factor} ({count} hits)"
            for factor, count in sorted(
                self.factor_counts.items(), key=lambda item: (-item[1], item[0])
            )[:max_factors]
        )
        lines.append(f"Most common distance factors : {top_factors}")
        lines.append(
            "Likely key lengths           : "
            + ", ".join(str(length) for length, _ in self.ranked_key_lengths[:max_factors])
        )
        lines.append("")
        lines.append(
            "Reminder: these are candidate key lengths derived from repeated sequences. "
            "Kasiski examination does not prove the key length and does not recover the key."
        )
        return lines


def factorize(value: int) -> list[int]:
    """Return the divisors of *value* greater than 1, ascending.

    Example:
        >>> factorize(30)
        [2, 3, 5, 6, 10, 15, 30]
    """
    if value < 2:
        return []
    divisors = [divisor for divisor in range(2, value + 1) if value % divisor == 0]
    return divisors


def distances_from_positions(positions: Sequence[int]) -> list[int]:
    """Return the gaps between consecutive *positions*.

    Example:
        >>> distances_from_positions([12, 42, 72])
        [30, 30]
    """
    return [
        positions[index + 1] - positions[index] for index in range(len(positions) - 1)
    ]


def find_repeated_sequences(
    text: str,
    min_length: int = 3,
    max_length: int = 5,
    max_sequences: int = 50,
) -> list[RepeatedSequence]:
    """Find words of length *min_length*..*max_length* that occur more than once.

    Args:
        text: Ciphertext to scan.
        min_length: Shortest repeated word to report.
        max_length: Longest repeated word to report.
        max_sequences: Upper bound on the number of sequences returned, longest
            and most frequent first.

    Returns:
        A list of :class:`RepeatedSequence` objects.
    """
    if min_length < 2:
        min_length = 2
    if max_length < min_length:
        max_length = min_length

    normalized = normalize_text(text)
    if len(normalized) < min_length * 2:
        return []

    positions_by_word: dict[str, list[int]] = {}
    for size in range(min_length, max_length + 1):
        for start in range(len(normalized) - size + 1):
            word = normalized[start : start + size]
            positions_by_word.setdefault(word, []).append(start)

    sequences: list[RepeatedSequence] = []
    for word, positions in positions_by_word.items():
        if len(positions) < 2:
            continue
        distances = distances_from_positions(positions)
        factors: Counter[int] = Counter()
        for distance in distances:
            # Only factors that could still be a plausible key length are counted.
            for factor in factorize(distance):
                if factor <= 40:
                    factors[factor] += 1
        sequences.append(
            RepeatedSequence(
                sequence=word,
                positions=tuple(positions),
                distances=tuple(distances),
                factors=dict(factors),
            )
        )

    sequences.sort(key=lambda item: (-len(item.sequence), -item.occurrences, item.sequence))
    return sequences[:max_sequences]


def rank_key_lengths(
    factor_counts: dict[int, int],
    max_key_length: int = 20,
    minimum_length: int = 2,
) -> list[tuple[int, int]]:
    """Rank candidate key lengths from the factor evidence.

    A key length ``L`` is plausible whenever ``L`` divides a distance between
    two repeated sequences. This function therefore adds up the evidence of
    every factor that is a multiple of ``L``: a true key length of 5 is
    supported by distances of 10, 15, 20 and so on, while an accidental factor
    of 2 is only supported by even distances.

    Args:
        factor_counts: ``{factor: occurrences}`` produced by the examination.
        max_key_length: Largest key length to consider.
        minimum_length: Smallest key length to consider.

    Returns:
        ``(key_length, evidence)`` pairs sorted by descending evidence, with
        ties broken by the shorter key length.
    """
    if max_key_length < minimum_length:
        return []
    scores: dict[int, int] = {}
    for length in range(minimum_length, max_key_length + 1):
        score = sum(count for factor, count in factor_counts.items() if factor % length == 0)
        if score:
            scores[length] = score
    return sorted(scores.items(), key=lambda item: (-item[1], item[0]))


def kasiski_examination(
    text: str,
    min_length: int = 3,
    max_length: int = 5,
    max_key_length: int = 20,
    max_sequences: int = 50,
) -> KasiskiResult:
    """Run a complete Kasiski examination on *text*.

    Args:
        text: Ciphertext to analyse.
        min_length: Shortest repeated word to look for.
        max_length: Longest repeated word to look for.
        max_key_length: Largest candidate key length to rank.
        max_sequences: Upper bound on repeated sequences kept.

    Returns:
        A :class:`KasiskiResult`; when no repetition exists the result simply
        carries empty evidence instead of raising, because that is a normal
        outcome for short messages.
    """
    normalized = normalize_text(text)
    sequences = find_repeated_sequences(
        normalized, min_length=min_length, max_length=max_length, max_sequences=max_sequences
    )
    factor_counts: Counter[int] = Counter()
    for sequence in sequences:
        for factor, occurrences in sequence.factors.items():
            factor_counts[factor] += occurrences

    return KasiskiResult(
        total_letters=len(normalized),
        min_length=min_length,
        max_length=max_length,
        sequences=tuple(sequences),
        factor_counts=dict(factor_counts),
        ranked_key_lengths=tuple(rank_key_lengths(factor_counts, max_key_length)),
    )


def kasiski_rows(result: KasiskiResult, limit: int = 10) -> list[tuple[str, str, str, str]]:
    """Format the repeated sequences of *result* as table rows."""
    rows: list[tuple[str, str, str, str]] = []
    for sequence in result.sequences[:limit]:
        rows.append(
            (
                sequence.sequence,
                str(sequence.occurrences),
                ", ".join(str(distance) for distance in sequence.distances),
                sequence.factor_summary(limit=6),
            )
        )
    return rows


def key_length_rows(result: KasiskiResult, limit: int = 10) -> list[tuple[str, str]]:
    """Format the ranked key lengths of *result* as table rows."""
    return [
        (str(length), str(evidence)) for length, evidence in result.ranked_key_lengths[:limit]
    ]
