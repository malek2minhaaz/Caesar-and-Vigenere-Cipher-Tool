"""Index of Coincidence (IC) analysis.

The Index of Coincidence measures how unevenly the letters of a text are
distributed::

    IC = sum(fi * (fi - 1)) / (N * (N - 1))

where ``fi`` is the count of letter ``i`` and ``N`` the number of letters.

Reference values:

* monoalphabetic English (unencrypted prose): about ``0.0667``
* Vigenère ciphertext with the *correct* key length: the average IC of the
  columns rises back towards ``0.0667``
* random text: about ``0.0385`` (1/26)

The IC is evidence, not proof. It narrows down what is likely and must always
be combined with other techniques (Kasiski examination, chi-square scoring)
before any conclusion is drawn.
"""

from __future__ import annotations

from dataclasses import dataclass
from collections import Counter

from utils.text_utils import key_length_columns, normalize_text
from utils.validators import ValidationError

#: IC of ordinary English prose.
EXPECTED_ENGLISH_IC: float = 0.0667

#: IC of uniformly random text (1 / 26).
RANDOM_TEXT_IC: float = 0.0385

__all__ = [
    "EXPECTED_ENGLISH_IC",
    "RANDOM_TEXT_IC",
    "ICResult",
    "index_of_coincidence",
    "ic_for_key_length",
    "ic_by_key_length",
    "interpret_ic",
    "analyze_index_of_coincidence",
]


@dataclass(frozen=True)
class ICResult:
    """Outcome of an Index of Coincidence measurement."""

    total_letters: int
    ic: float
    interpretation: str
    expected_english_ic: float = EXPECTED_ENGLISH_IC
    random_text_ic: float = RANDOM_TEXT_IC

    def format_lines(self) -> list[str]:
        """Return printable lines describing the measurement."""
        return [
            f"Characters analysed      : {self.total_letters}",
            f"Index of Coincidence     : {self.ic:.5f}",
            f"Reference (English prose): {self.expected_english_ic:.4f}",
            f"Reference (random text)  : {self.random_text_ic:.4f}",
            f"Interpretation           : {self.interpretation}",
        ]


def index_of_coincidence(text: str) -> float:
    """Return the Index of Coincidence of *text*.

    Args:
        text: Any text; only its letters are used.

    Returns:
        The IC value, or ``0.0`` when there are fewer than two letters.

    Example:
        >>> round(index_of_coincidence("HELLO WORLD"), 5)
        0.08889
    """
    normalized = normalize_text(text)
    total = len(normalized)
    if total < 2:
        return 0.0
    counts = Counter(normalized)
    numerator = sum(count * (count - 1) for count in counts.values())
    return numerator / (total * (total - 1))


def ic_for_key_length(text: str, key_length: int) -> float:
    """Return the average IC of the columns implied by *key_length*.

    For the true Vigenère key length, every column was encrypted with a single
    Caesar shift, so each column behaves like English prose and its IC is close
    to 0.0667. The columns are averaged with the ``N(N-1)`` weighting used by
    the IC formula itself, which is more accurate than a plain mean.

    Args:
        text: Ciphertext to analyse.
        key_length: Assumed length of the repeating key.

    Returns:
        The weighted average IC, or ``0.0`` when no usable columns exist.
    """
    if key_length < 1:
        raise ValidationError("The key length must be at least 1.")
    normalized = normalize_text(text)
    if len(normalized) < 2:
        return 0.0

    numerator = 0.0
    denominator = 0
    for column in key_length_columns(normalized, key_length):
        size = len(column)
        if size < 2:
            continue
        counts = Counter(column)
        numerator += sum(count * (count - 1) for count in counts.values())
        denominator += size * (size - 1)
    if denominator == 0:
        return 0.0
    return numerator / denominator


def ic_by_key_length(
    text: str, max_key_length: int = 20, minimum_letters_per_column: int = 2
) -> dict[int, float]:
    """Return ``{key_length: average IC}`` for lengths ``1..max_key_length``.

    Key lengths that leave fewer than *minimum_letters_per_column* letters in
    some column are skipped because their IC is statistically meaningless.
    """
    normalized = normalize_text(text)
    results: dict[int, float] = {}
    for length in range(1, max_key_length + 1):
        if len(normalized) // length < minimum_letters_per_column:
            continue
        results[length] = ic_for_key_length(normalized, length)
    return results


def interpret_ic(ic: float) -> str:
    """Return a plain-language interpretation of an IC value.

    The wording deliberately avoids claiming that the IC proves anything: it
    describes which cipher family the value is *consistent with*.
    """
    if ic <= 0.0:
        return "Not enough letters to measure."
    if ic >= 0.075:
        return (
            "High: consistent with monoalphabetic text (ordinary language or a "
            "simple substitution / Caesar cipher)."
        )
    if ic >= 0.060:
        return (
            "Close to English: consistent with monoalphabetic text, or with a "
            "polyalphabetic cipher when the key length used here is correct."
        )
    if ic >= 0.050:
        return (
            "Below English but above random: consistent with a polyalphabetic "
            "cipher, a short text, or mixed content."
        )
    if ic >= 0.043:
        return (
            "Low: consistent with polyalphabetic or otherwise randomised text; "
            "letter frequencies have been flattened."
        )
    return (
        "Very low: little or none of the original letter distribution is left, "
        "which is consistent with a polyalphabetic cipher using a long key or "
        "with randomised text. For a column average it also means the assumed "
        "key length is very likely wrong."
    )


def analyze_index_of_coincidence(text: str) -> ICResult:
    """Measure and interpret the IC of *text*.

    Args:
        text: Text to analyse.

    Returns:
        An :class:`ICResult`.

    Raises:
        ValidationError: If the text contains fewer than two letters.
    """
    normalized = normalize_text(text)
    if len(normalized) < 2:
        raise ValidationError("At least two letters are required for IC analysis.")
    value = index_of_coincidence(normalized)
    return ICResult(
        total_letters=len(normalized),
        ic=value,
        interpretation=interpret_ic(value),
    )


def ic_as_rows(values: dict[int, float], limit: int | None = None) -> list[tuple[str, str]]:
    """Format ``{key_length: ic}`` as ``(key length, IC)`` table rows."""
    items = sorted(values.items(), key=lambda item: (-item[1], item[0]))
    if limit is not None:
        items = items[:limit]
    return [(f"{length}", f"{value:.5f}") for length, value in items]
