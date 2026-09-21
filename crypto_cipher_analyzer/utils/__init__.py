"""Utility helpers: text handling, validation, terminal output and reports.

The package deliberately has no dependencies outside the Python standard
library so that the tool runs unchanged on Windows, Linux, Ubuntu and Kali.
"""

from utils.text_utils import (
    ALPHABET,
    ALPHABET_SIZE,
    ENGLISH_LETTER_FREQUENCIES,
    count_letters,
    is_ascii_letter,
    key_length_columns,
    normalize_text,
    total_letters,
)
from utils.validators import (
    ValidationError,
    validate_key,
    validate_key_length,
    validate_menu_choice,
    validate_shift,
    validate_text,
)

__all__ = [
    "ALPHABET",
    "ALPHABET_SIZE",
    "ENGLISH_LETTER_FREQUENCIES",
    "ValidationError",
    "count_letters",
    "is_ascii_letter",
    "key_length_columns",
    "normalize_text",
    "total_letters",
    "validate_key",
    "validate_key_length",
    "validate_menu_choice",
    "validate_shift",
    "validate_text",
]
