"""Shared text helpers used by the cipher and cryptanalysis modules.

Keeping the definition of "what counts as a letter" in a single place means the
ciphers and the analysers can never disagree about it: the ciphers preserve
every character they do not understand, while the analysers work on the
normalised (letters only, upper case) version of the same text.
"""

from __future__ import annotations

import textwrap
import unicodedata
from collections import Counter
from typing import Iterable, Sequence

#: The classical Latin alphabet used by both implemented ciphers.
ALPHABET: str = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

#: Number of distinct symbols in :data:`ALPHABET`.
ALPHABET_SIZE: int = len(ALPHABET)

#: Approximate single-letter frequencies of English prose, in percent.
#: Source: standard cryptanalysis reference values (Lewand / Cornell).
ENGLISH_LETTER_FREQUENCIES: dict[str, float] = {
    "A": 8.167,
    "B": 1.492,
    "C": 2.782,
    "D": 4.253,
    "E": 12.702,
    "F": 2.228,
    "G": 2.015,
    "H": 6.094,
    "I": 6.966,
    "J": 0.153,
    "K": 0.772,
    "L": 4.025,
    "M": 2.406,
    "N": 6.749,
    "O": 7.507,
    "P": 1.929,
    "Q": 0.095,
    "R": 5.987,
    "S": 6.327,
    "T": 9.056,
    "U": 2.758,
    "V": 0.978,
    "W": 2.360,
    "X": 0.150,
    "Y": 1.974,
    "Z": 0.074,
}

#: Letters of English sorted from most to least frequent.
ENGLISH_LETTER_ORDER: tuple[str, ...] = tuple(
    sorted(ENGLISH_LETTER_FREQUENCIES, key=lambda letter: ENGLISH_LETTER_FREQUENCIES[letter], reverse=True)
)


def is_ascii_letter(char: str) -> bool:
    """Return ``True`` when *char* is a single A-Z/a-z character.

    Only ASCII letters are considered: accented characters, digits and
    punctuation are treated as "not a letter" and are preserved unchanged by
    the cipher implementations.
    """
    return len(char) == 1 and char.isascii() and char.isalpha()


def normalize_text(text: str) -> str:
    """Return the upper-case letters of *text* with everything else removed.

    Accented characters are decomposed first, so ``"café"`` normalises to
    ``"CAFE"`` instead of ``"CAF"``.

    Args:
        text: Any string.

    Returns:
        A string containing only characters from :data:`ALPHABET`.
    """
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(char.upper() for char in decomposed if is_ascii_letter(char))


def count_letters(text: str) -> Counter[str]:
    """Count the occurrences of every letter in *text* (case insensitive)."""
    return Counter(normalize_text(text))


def total_letters(text: str) -> int:
    """Return the number of alphabetic characters in *text*."""
    return len(normalize_text(text))


def letter_percentages(text: str) -> dict[str, float]:
    """Return the percentage of every letter of the alphabet in *text*.

    Letters that do not occur are present with a value of ``0.0`` so callers
    always get all 26 keys.
    """
    counts = count_letters(text)
    total = sum(counts.values())
    if total == 0:
        return {letter: 0.0 for letter in ALPHABET}
    return {letter: counts.get(letter, 0) * 100.0 / total for letter in ALPHABET}


def split_into_chunks(text: str, size: int) -> list[str]:
    """Split *text* into consecutive chunks of *size* characters."""
    if size < 1:
        raise ValueError("Chunk size must be at least 1")
    return [text[index : index + size] for index in range(0, len(text), size)]


def key_length_columns(normalized_text: str, key_length: int) -> list[str]:
    """Split *normalized_text* into the columns implied by a repeating key.

    With a Vigenère key of length *key_length* every ciphertext letter at index
    ``i`` was shifted with the key letter at index ``i % key_length``. This
    function returns one string per key position, i.e. all the letters that were
    encrypted with the same key letter.

    Args:
        normalized_text: Text already reduced to ``A-Z``.
        key_length: Assumed length of the repeating key.

    Returns:
        A list of ``key_length`` strings.
    """
    if key_length < 1:
        raise ValueError("Key length must be at least 1")
    return [normalized_text[index::key_length] for index in range(key_length)]


def truncate(text: str, width: int = 40, suffix: str = "...") -> str:
    """Shorten *text* to *width* characters, adding *suffix* when truncated."""
    if width < len(suffix) + 1:
        return text[:width]
    if len(text) <= width:
        return text
    return text[: width - len(suffix)] + suffix


def wrap_text(text: str, width: int = 70) -> list[str]:
    """Wrap *text* into lines of at most *width* characters."""
    return textwrap.wrap(text, width=width) or [""]


def unique_in_order(items: Iterable[str]) -> list[str]:
    """Return the items of *items* with duplicates removed, order preserved."""
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def busiest_letters(counts: Counter[str], top_n: int = 5) -> list[tuple[str, int]]:
    """Return the *top_n* most frequent ``(letter, count)`` pairs.

    Ties are broken alphabetically so results are always deterministic.
    """
    return sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:top_n]
