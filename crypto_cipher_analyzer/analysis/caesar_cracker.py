"""Automatic Caesar cipher cracking.

Because a Caesar cipher has only 26 keys, it can simply be brute forced. The
interesting part is ranking the 26 candidates without a human reading them all:
each decryption is scored with :func:`analysis.frequency.fitness_score`, which
measures how closely the letter distribution of the candidate matches English.

The technique is statistical. Very short ciphertexts, unusual subjects, proper
nouns or non-English text can rank the wrong candidate first, so the top few
candidates are always shown rather than a single "answer".
"""

from __future__ import annotations

from dataclasses import dataclass

from analysis.frequency import fitness_score
from ciphers import caesar
from utils.text_utils import normalize_text
from utils.validators import ValidationError, validate_text

__all__ = [
    "CaesarCandidate",
    "score_plaintext",
    "crack_caesar",
    "best_candidate",
    "candidate_rows",
    "CRACKING_NOTE",
]

#: Printed alongside cracking results so the limitations are always visible.
CRACKING_NOTE: str = (
    "Automated cracking is statistical: the ranking is based on how much each "
    "candidate looks like English. Short messages, names, technical terms or "
    "non-English text can rank the wrong shift first, so compare the top "
    "candidates rather than trusting the first row blindly."
)


@dataclass(frozen=True)
class CaesarCandidate:
    """One possible plaintext produced by shifting the ciphertext."""

    shift: int
    score: float
    plaintext: str

    def to_row(self, rank: int, preview_width: int = 60) -> tuple[str, str, str, str]:
        """Return a ``(rank, shift, score, preview)`` row for table output."""
        preview = self.plaintext.replace("\n", " ").strip()
        if len(preview) > preview_width:
            preview = preview[: preview_width - 3] + "..."
        return (str(rank), str(self.shift), f"{self.score:.2f}", preview)


def score_plaintext(text: str) -> float:
    """Score *text* for how much it looks like English (``0..100``)."""
    return fitness_score(text)


def crack_caesar(ciphertext: str, top_n: int = 5) -> list[CaesarCandidate]:
    """Rank every possible Caesar decryption of *ciphertext*.

    Args:
        ciphertext: Text to attack.
        top_n: How many candidates to return.

    Returns:
        Candidates sorted from most to least English-like, ties broken by the
        smaller shift.

    Raises:
        ValidationError: If the ciphertext is empty, contains no letters, or
            *top_n* is not positive.

    Example:
        >>> candidates = crack_caesar("KHOOR ZRUOG")
        >>> candidates[0].shift
        3
        >>> candidates[0].plaintext
        'HELLO WORLD'
    """
    validate_text(ciphertext)
    if not normalize_text(ciphertext):
        raise ValidationError("No letters were found in the ciphertext.")
    if top_n < 1:
        raise ValidationError("At least one candidate must be requested.")

    candidates = [
        CaesarCandidate(shift=shift, score=score_plaintext(plaintext), plaintext=plaintext)
        for shift, plaintext in caesar.brute_force(ciphertext)
    ]
    candidates.sort(key=lambda candidate: (-candidate.score, candidate.shift))
    return candidates[:top_n]


def best_candidate(ciphertext: str) -> CaesarCandidate:
    """Return the single highest scoring Caesar candidate."""
    return crack_caesar(ciphertext, top_n=1)[0]


def candidate_rows(candidates: list[CaesarCandidate]) -> list[tuple[str, str, str, str]]:
    """Format candidates as table rows with ranks starting at 1."""
    return [
        candidate.to_row(rank=index + 1)
        for index, candidate in enumerate(candidates)
    ]
