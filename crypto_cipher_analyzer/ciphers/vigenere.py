"""Vigenère cipher implementation.

The Vigenère cipher applies a *different* Caesar shift to every letter, taken
from a repeating keyword. Because the same keyword is reused, the cipher leaks
statistical structure that :mod:`analysis.kasiski` and
:mod:`analysis.vigenere_analyzer` can exploit.

Key alignment is important: the keyword only advances on alphabetic characters,
so spaces and punctuation do not desynchronise encryption and decryption.
"""

from __future__ import annotations

from ciphers.caesar import shift_character
from utils.text_utils import ALPHABET, is_ascii_letter
from utils.validators import validate_key, validate_text

__all__ = ["key_offsets", "generate_keystream", "encrypt", "decrypt"]


def key_offsets(key: str) -> list[int]:
    """Convert a keyword into its alphabet offsets.

    Args:
        key: Keyword containing letters only.

    Returns:
        A list of integers in ``0..25``, one per key letter.

    Raises:
        ValidationError: If the key is empty or contains non-letters.
    """
    validated_key = validate_key(key)
    return [ALPHABET.index(letter) for letter in validated_key]


def generate_keystream(text: str, key: str) -> str:
    """Return the keyword repeated to match the letters of *text*.

    Non-alphabetic characters in *text* are skipped, mirroring the way the
    cipher advances its key.

    Args:
        text: The text that will be encrypted or decrypted.
        key: Keyword containing letters only.

    Returns:
        A string of uppercase key letters, one per alphabetic character.

    Raises:
        ValidationError: If the key is invalid.
    """
    validated_key = validate_key(key)
    letters = sum(1 for char in text if is_ascii_letter(char))
    return "".join(validated_key[index % len(validated_key)] for index in range(letters))


def _transform(text: str, key: str, direction: int) -> str:
    """Apply the Vigenère transform in *direction* (``1`` encrypt, ``-1`` decrypt)."""
    validated_text = validate_text(text)
    offsets = key_offsets(key)
    result: list[str] = []
    key_index = 0
    for char in validated_text:
        if is_ascii_letter(char):
            result.append(shift_character(char, direction * offsets[key_index % len(offsets)]))
            key_index += 1
        else:
            result.append(char)
    return "".join(result)


def encrypt(text: str, key: str) -> str:
    """Encrypt *text* with a Vigenère cipher.

    Args:
        text: Plaintext to encrypt.
        key: Keyword containing letters only.

    Returns:
        The ciphertext with spacing and punctuation preserved.

    Raises:
        ValidationError: If *text* is empty or *key* is invalid.

    Example:
        >>> encrypt("ATTACKATDAWN", "LEMON")
        'LXFOPVEFRNHR'
    """
    return _transform(text, key, 1)


def decrypt(text: str, key: str) -> str:
    """Decrypt Vigenère ciphertext.

    Args:
        text: Ciphertext to decrypt.
        key: The keyword that was used to encrypt.

    Returns:
        The recovered plaintext.

    Raises:
        ValidationError: If *text* is empty or *key* is invalid.

    Example:
        >>> decrypt("LXFOPVEFRNHR", "LEMON")
        'ATTACKATDAWN'
    """
    return _transform(text, key, -1)
