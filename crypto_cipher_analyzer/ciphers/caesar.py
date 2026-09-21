"""Caesar cipher implementation.

The Caesar cipher shifts every alphabetic character by a fixed number of
positions in the alphabet. Because there are only 26 possible shifts an
attacker can simply test every possibility, which is exactly what
:mod:`analysis.caesar_cracker` automates.

The implementation preserves the case of every letter and leaves spaces,
punctuation, digits and non-ASCII characters untouched.
"""

from __future__ import annotations

from utils.text_utils import ALPHABET_SIZE, is_ascii_letter
from utils.validators import validate_shift, validate_text

__all__ = ["shift_character", "encrypt", "decrypt", "brute_force"]


def shift_character(char: str, shift: int) -> str:
    """Shift a single character by *shift* positions.

    Characters that are not ASCII letters are returned unchanged, which is what
    preserves spaces, punctuation and digits.

    Args:
        char: A single character.
        shift: Number of alphabet positions to move (may be negative).

    Returns:
        The shifted character, or *char* when it is not a letter.
    """
    if not is_ascii_letter(char):
        return char
    base = ord("A") if char.isupper() else ord("a")
    return chr((ord(char) - base + shift) % ALPHABET_SIZE + base)


def encrypt(text: str, shift: int) -> str:
    """Encrypt *text* using a Caesar cipher.

    Args:
        text: Plaintext to encrypt.
        shift: Number of positions to shift; normalised modulo 26.

    Returns:
        The ciphertext with original spacing and punctuation preserved.

    Raises:
        ValidationError: If *text* is empty or *shift* is not a whole number.

    Example:
        >>> encrypt("HELLO WORLD", 3)
        'KHOOR ZRUOG'
    """
    validated_shift = validate_shift(shift)
    validated_text = validate_text(text)
    return "".join(shift_character(char, validated_shift) for char in validated_text)


def decrypt(text: str, shift: int) -> str:
    """Decrypt Caesar ciphertext.

    Decryption is encryption with the inverse shift, so this is an exact
    inverse of :func:`encrypt`.

    Args:
        text: Ciphertext to decrypt.
        shift: The shift that was used to encrypt.

    Returns:
        The recovered plaintext.

    Raises:
        ValidationError: If *text* is empty or *shift* is not a whole number.

    Example:
        >>> decrypt("KHOOR ZRUOG", 3)
        'HELLO WORLD'
    """
    validated_shift = validate_shift(shift)
    validated_text = validate_text(text)
    return "".join(shift_character(char, -validated_shift) for char in validated_text)


def brute_force(text: str) -> list[tuple[int, str]]:
    """Return all 26 possible decryptions of *text*.

    Args:
        text: Ciphertext to attack.

    Returns:
        A list of ``(shift, plaintext)`` pairs ordered by shift from 0 to 25.

    Raises:
        ValidationError: If *text* is empty.
    """
    validated_text = validate_text(text)
    return [
        (shift, "".join(shift_character(char, -shift) for char in validated_text))
        for shift in range(ALPHABET_SIZE)
    ]
