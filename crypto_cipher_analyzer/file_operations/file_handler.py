"""File input/output for the cipher tool.

All file access in the project goes through this module so that a single place
is responsible for the things that actually go wrong in the real world: missing
files, unreadable files, empty files, unwritable destinations and accidental
overwrites.

By default the source file is never overwritten: writing over an existing file
requires ``overwrite=True``, which the CLI only sets when the user passes
``--overwrite`` or explicitly confirms.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from utils.text_utils import count_letters, normalize_text

__all__ = [
    "FileOperationError",
    "FileOperationResult",
    "read_text",
    "write_text",
    "default_output_path",
    "transform_file",
    "caesar_file",
    "vigenere_file",
    "file_statistics",
]

#: Message shown whenever output would clobber an existing file.
OVERWRITE_HINT: str = "Choose another output path or enable overwrite to replace it."


class FileOperationError(Exception):
    """Raised when a file cannot be read, written or validated."""


@dataclass(frozen=True)
class FileOperationResult:
    """Outcome of a file based operation."""

    source: Path
    destination: Path
    characters_read: int
    characters_written: int
    overwritten: bool = False

    def as_summary_lines(self) -> list[str]:
        """Return the result as printable lines."""
        return [
            f"Input file        : {self.source}",
            f"Output file       : {self.destination}",
            f"Characters read   : {self.characters_read}",
            f"Characters written: {self.characters_written}",
            f"Overwrote existing: {'yes' if self.overwritten else 'no'}",
        ]


def read_text(path: Path | str, encoding: str = "utf-8") -> str:
    """Read a text file, converting every realistic failure into one error type.

    Args:
        path: File to read.
        encoding: Text encoding; undecodable bytes are replaced rather than
            raising, so a slightly mis-encoded file still works.

    Returns:
        The contents of the file.

    Raises:
        FileOperationError: If the path is missing, is a directory, cannot be
            read, is unreadable due to permissions, or is empty.
    """
    if path is None or str(path).strip() == "":
        raise FileOperationError("No input file was provided.")

    target = Path(str(path).strip().strip('"'))
    if not target.exists():
        raise FileOperationError(f"Input file not found: {target}")
    if target.is_dir():
        raise FileOperationError(f"'{target}' is a directory, not a file.")

    try:
        content = target.read_text(encoding=encoding, errors="replace")
    except PermissionError as error:
        raise FileOperationError(f"Permission denied while reading: {target}") from error
    except OSError as error:
        raise FileOperationError(f"Could not read '{target}': {error}") from error

    if not content.strip():
        raise FileOperationError(f"The file '{target}' is empty; nothing to process.")
    return content


def write_text(
    path: Path | str,
    content: str,
    overwrite: bool = False,
    encoding: str = "utf-8",
) -> Path:
    """Write *content* to *path*.

    Args:
        path: Destination file.
        content: Text to write.
        overwrite: Must be ``True`` to replace an existing file.
        encoding: Text encoding used for output.

    Returns:
        The path that was written.

    Raises:
        FileOperationError: If the destination exists and *overwrite* is
            ``False``, the parent directory cannot be created, or the file
            cannot be written.
    """
    if path is None or str(path).strip() == "":
        raise FileOperationError("No output file was provided.")

    target = Path(str(path).strip().strip('"'))
    if target.exists():
        if target.is_dir():
            raise FileOperationError(f"'{target}' is a directory, not a file.")
        if not overwrite:
            raise FileOperationError(f"Output file already exists: {target}. {OVERWRITE_HINT}")

    try:
        if target.parent and not target.parent.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding=encoding)
    except PermissionError as error:
        raise FileOperationError(f"Permission denied while writing: {target}") from error
    except OSError as error:
        raise FileOperationError(f"Could not write '{target}': {error}") from error
    return target


def default_output_path(source: Path | str, suffix: str = "_out") -> Path:
    """Build a non-destructive default output path such as ``notes_out.txt``."""
    target = Path(source)
    return target.with_name(f"{target.stem}{suffix}{target.suffix}")


def transform_file(
    source: Path | str,
    destination: Path | str,
    transform: Callable[[str], str],
    overwrite: bool = False,
    encoding: str = "utf-8",
) -> FileOperationResult:
    """Read *source*, apply *transform* and write the result to *destination*.

    Args:
        source: Input file.
        destination: Output file.
        transform: Function mapping the file contents to new contents.
        overwrite: Allow replacing an existing output file.
        encoding: Text encoding used for both directions.

    Returns:
        A :class:`FileOperationResult`.

    Raises:
        FileOperationError: On any read or write failure, or when source and
            destination are the same file and *overwrite* is ``False``.
    """
    source_path = Path(str(source).strip().strip('"'))
    destination_path = Path(str(destination).strip().strip('"'))

    if source_path.resolve() == destination_path.resolve() and not overwrite:
        raise FileOperationError(
            "The output file is the same as the input file. "
            "Choose a different output path, or confirm overwriting the original file."
        )

    content = read_text(source_path, encoding=encoding)
    result = transform(content)
    if not isinstance(result, str):
        raise FileOperationError("The transformation did not return text.")
    existed = destination_path.exists()
    written_path = write_text(destination_path, result, overwrite=overwrite, encoding=encoding)

    return FileOperationResult(
        source=source_path,
        destination=written_path,
        characters_read=len(content),
        characters_written=len(result),
        overwritten=existed,
    )


def caesar_file(
    source: Path | str,
    destination: Path | str,
    shift: int,
    decrypt: bool = False,
    overwrite: bool = False,
) -> FileOperationResult:
    """Encrypt or decrypt a text file with the Caesar cipher.

    Args:
        source: Input file.
        destination: Output file.
        shift: Caesar shift to use.
        decrypt: When ``True`` the file is decrypted instead of encrypted.
        overwrite: Allow replacing an existing output file.

    Returns:
        A :class:`FileOperationResult`.
    """
    from ciphers import caesar

    operation = caesar.decrypt if decrypt else caesar.encrypt
    return transform_file(
        source,
        destination,
        lambda text: operation(text, shift),
        overwrite=overwrite,
    )


def vigenere_file(
    source: Path | str,
    destination: Path | str,
    key: str,
    decrypt: bool = False,
    overwrite: bool = False,
) -> FileOperationResult:
    """Encrypt or decrypt a text file with the Vigenère cipher.

    Args:
        source: Input file.
        destination: Output file.
        key: Vigenère keyword (letters only).
        decrypt: When ``True`` the file is decrypted instead of encrypted.
        overwrite: Allow replacing an existing output file.

    Returns:
        A :class:`FileOperationResult`.
    """
    from ciphers import vigenere

    operation = vigenere.decrypt if decrypt else vigenere.encrypt
    return transform_file(
        source,
        destination,
        lambda text: operation(text, key),
        overwrite=overwrite,
    )


def file_statistics(path: Path | str) -> dict[str, object]:
    """Return basic statistics about a text file.

    Args:
        path: File to inspect.

    Returns:
        A dictionary with the path, size in bytes, line count, character count
        and alphabetic character count.

    Raises:
        FileOperationError: If the file cannot be read.
    """
    content = read_text(path)
    target = Path(str(path))
    return {
        "path": str(target),
        "bytes": target.stat().st_size,
        "lines": len(content.splitlines()),
        "characters": len(content),
        "letters": len(normalize_text(content)),
        "unique_letters": len(count_letters(content)),
    }
