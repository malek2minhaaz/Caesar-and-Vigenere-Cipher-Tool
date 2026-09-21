"""Input validation helpers.

Every user-supplied value (text, Caesar shift, Vigenère key, menu choice, file
path) passes through this module before it reaches the algorithms, so the
algorithms can assume clean input and the CLI can report friendly messages.
"""

from __future__ import annotations

from typing import Iterable, Sequence

from utils.text_utils import ALPHABET, ALPHABET_SIZE, is_ascii_letter


class ValidationError(ValueError):
    """Raised when user supplied input fails validation."""


def validate_text(text: object, field: str = "text", allow_empty: bool = False) -> str:
    """Return *text* as a string after checking that it is usable.

    Args:
        text: The value supplied by the caller.
        field: Name used in the error message.
        allow_empty: When ``True`` an empty string is accepted.

    Returns:
        The validated text.

    Raises:
        ValidationError: If the value is not a string or is empty when it must
            not be.
    """
    if text is None:
        raise ValidationError(f"No {field} was provided.")
    if not isinstance(text, str):
        raise ValidationError(f"The {field} must be a string.")
    if not allow_empty and not text.strip():
        raise ValidationError(f"The {field} is empty. Please provide some input.")
    return text


def validate_shift(shift: object, modulus: int = ALPHABET_SIZE) -> int:
    """Validate and normalise a Caesar shift into ``0 .. modulus - 1``.

    Negative shifts and shifts larger than the alphabet are accepted and
    reduced modulo *modulus*, which is what makes ``shift=26`` and ``shift=0``
    equivalent.

    Raises:
        ValidationError: If the shift is not an integer value.
    """
    if isinstance(shift, bool):
        raise ValidationError("The shift must be a whole number.")
    if isinstance(shift, int):
        value = shift
    elif isinstance(shift, str):
        text = shift.strip()
        if not text:
            raise ValidationError("The shift is empty. Please provide a number.")
        try:
            value = int(text, 10)
        except ValueError as error:
            raise ValidationError(f"'{shift}' is not a valid shift. Use a whole number.") from error
    else:
        raise ValidationError("The shift must be a whole number.")
    return value % modulus


def validate_key(key: object, field: str = "key") -> str:
    """Validate a Vigenère key and return it in upper case.

    A valid key contains only ASCII letters (``A-Z``/``a-z``); spaces, digits
    and symbols are rejected because they would leave part of the plaintext
    unencrypted.

    Raises:
        ValidationError: If the key is empty or contains non-letter characters.
    """
    if key is None:
        raise ValidationError(f"No {field} was provided.")
    if not isinstance(key, str):
        raise ValidationError(f"The {field} must be a string.")
    candidate = key.strip()
    if not candidate:
        raise ValidationError(f"The {field} is empty. Please provide a keyword.")
    invalid = sorted({char for char in candidate if not is_ascii_letter(char)})
    if invalid:
        shown = " ".join(repr(char) for char in invalid[:5])
        raise ValidationError(
            f"The {field} must contain letters only (A-Z). Remove: {shown}"
        )
    return candidate.upper()


def validate_key_length(
    value: object,
    minimum: int = 1,
    maximum: int = 50,
    field: str = "key length",
) -> int:
    """Validate a key-length argument and return it as an ``int``.

    Raises:
        ValidationError: If the value is not an integer inside the range.
    """
    if isinstance(value, bool):
        raise ValidationError(f"The {field} must be a whole number.")
    if isinstance(value, int):
        number = value
    elif isinstance(value, str):
        try:
            number = int(value.strip(), 10)
        except (ValueError, AttributeError) as error:
            raise ValidationError(f"'{value}' is not a valid {field}.") from error
    else:
        raise ValidationError(f"The {field} must be a whole number.")
    if not minimum <= number <= maximum:
        raise ValidationError(f"The {field} must be between {minimum} and {maximum}.")
    return number


def validate_menu_choice(raw: str, choices: Sequence[str], default: str | None = None) -> str:
    """Return a validated menu selection.

    Args:
        raw: The raw string typed by the user.
        choices: Accepted values, for example ``["1", "2", "9"]``.
        default: Value returned when the user just presses Enter.

    Raises:
        ValidationError: If the selection is not one of *choices*.
    """
    value = (raw or "").strip()
    if not value and default is not None:
        return default
    if value not in choices:
        raise ValidationError(
            f"'{value}' is not a valid selection. Choose one of: {', '.join(choices)}"
        )
    return value


def validate_file_path(path: object, field: str = "path") -> str:
    """Validate that a path-like value is a non-empty string."""
    if path is None:
        raise ValidationError(f"No {field} was provided.")
    if not isinstance(path, str):
        raise ValidationError(f"The {field} must be a string.")
    if not path.strip():
        raise ValidationError(f"The {field} is empty. Please provide a file path.")
    return path.strip().strip('"').strip("'")


def is_yes(answer: str) -> bool:
    """Return ``True`` when *answer* is an affirmative reply."""
    return answer.strip().lower() in {"y", "yes"}


def is_no(answer: str) -> bool:
    """Return ``True`` when *answer* is a negative reply."""
    return answer.strip().lower() in {"n", "no"}
