"""File handling: reading, writing and encrypting or decrypting text files."""

from file_operations.file_handler import (
    FileOperationError,
    FileOperationResult,
    caesar_file,
    default_output_path,
    file_statistics,
    read_text,
    transform_file,
    vigenere_file,
    write_text,
)

__all__ = [
    "FileOperationError",
    "FileOperationResult",
    "caesar_file",
    "default_output_path",
    "file_statistics",
    "read_text",
    "transform_file",
    "vigenere_file",
    "write_text",
]
