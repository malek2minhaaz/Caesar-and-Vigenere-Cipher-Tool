"""Unit tests for :mod:`file_operations.file_handler` and report generation."""

import os
import sys
import tempfile
import unittest
from pathlib import Path

# Allow the tests to be run from any working directory.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ciphers import caesar, vigenere  # noqa: E402
from file_operations import file_handler  # noqa: E402
from utils.report_generator import ReportBuilder, reports_directory, save_report, timestamped_filename  # noqa: E402


class FileHandlerTestCase(unittest.TestCase):
    """Base class that provides a temporary directory for file tests."""

    def setUp(self) -> None:
        self._temporary = tempfile.TemporaryDirectory()
        self.directory = Path(self._temporary.name)

    def tearDown(self) -> None:
        self._temporary.cleanup()

    def path(self, name: str) -> Path:
        return self.directory / name


class TestReadWrite(FileHandlerTestCase):
    """Reading and writing text files."""

    def test_round_trip(self) -> None:
        target = self.path("note.txt")
        file_handler.write_text(target, "hello world")
        self.assertEqual(file_handler.read_text(target), "hello world")

    def test_missing_file_is_reported_clearly(self) -> None:
        with self.assertRaises(file_handler.FileOperationError) as context:
            file_handler.read_text(self.path("missing.txt"))
        self.assertIn("not found", str(context.exception))

    def test_directory_instead_of_file_is_reported(self) -> None:
        with self.assertRaises(file_handler.FileOperationError):
            file_handler.read_text(self.directory)

    def test_empty_file_is_reported(self) -> None:
        target = self.path("empty.txt")
        target.write_text("   \n  ", encoding="utf-8")
        with self.assertRaises(file_handler.FileOperationError) as context:
            file_handler.read_text(target)
        self.assertIn("empty", str(context.exception))

    def test_existing_file_is_not_overwritten_by_default(self) -> None:
        target = self.path("existing.txt")
        target.write_text("original", encoding="utf-8")
        with self.assertRaises(file_handler.FileOperationError):
            file_handler.write_text(target, "new content")
        self.assertEqual(target.read_text(encoding="utf-8"), "original")

    def test_overwrite_when_requested(self) -> None:
        target = self.path("existing.txt")
        target.write_text("original", encoding="utf-8")
        file_handler.write_text(target, "replacement", overwrite=True)
        self.assertEqual(target.read_text(encoding="utf-8"), "replacement")

    def test_parent_directories_are_created(self) -> None:
        target = self.path("nested/deeper/note.txt")
        file_handler.write_text(target, "content")
        self.assertTrue(target.exists())

    def test_empty_path_is_rejected(self) -> None:
        with self.assertRaises(file_handler.FileOperationError):
            file_handler.read_text("")
        with self.assertRaises(file_handler.FileOperationError):
            file_handler.write_text("", "content")


class TestTransformFile(FileHandlerTestCase):
    """Encrypting and decrypting files."""

    def test_caesar_round_trip(self) -> None:
        source = self.path("plain.txt")
        encrypted = self.path("cipher.txt")
        decrypted = self.path("restored.txt")
        source.write_text("Hello World, 42!", encoding="utf-8")

        first = file_handler.caesar_file(source, encrypted, 3)
        self.assertEqual(first.characters_read, first.characters_written)
        self.assertEqual(file_handler.read_text(encrypted), caesar.encrypt("Hello World, 42!", 3))

        file_handler.caesar_file(encrypted, decrypted, 3, decrypt=True)
        self.assertEqual(file_handler.read_text(decrypted), "Hello World, 42!")

    def test_vigenere_round_trip(self) -> None:
        source = self.path("plain.txt")
        encrypted = self.path("cipher.txt")
        decrypted = self.path("restored.txt")
        message = "Attack at dawn!"
        source.write_text(message, encoding="utf-8")

        file_handler.vigenere_file(source, encrypted, "LEMON")
        self.assertEqual(file_handler.read_text(encrypted), vigenere.encrypt(message, "LEMON"))
        file_handler.vigenere_file(encrypted, decrypted, "LEMON", decrypt=True)
        self.assertEqual(file_handler.read_text(decrypted), message)

    def test_original_file_is_never_changed_without_permission(self) -> None:
        source = self.path("plain.txt")
        source.write_text("Keep me", encoding="utf-8")
        with self.assertRaises(file_handler.FileOperationError):
            file_handler.transform_file(source, source, lambda text: text.upper())
        self.assertEqual(file_handler.read_text(source), "Keep me")

    def test_transform_can_write_back_with_permission(self) -> None:
        source = self.path("plain.txt")
        source.write_text("Keep me", encoding="utf-8")
        result = file_handler.transform_file(
            source, source, lambda text: text.upper(), overwrite=True
        )
        self.assertTrue(result.overwritten)
        self.assertEqual(file_handler.read_text(source), "KEEP ME")

    def test_default_output_path(self) -> None:
        self.assertEqual(
            file_handler.default_output_path(self.path("notes.txt")).name,
            "notes_out.txt",
        )

    def test_invalid_key_does_not_touch_the_output(self) -> None:
        source = self.path("plain.txt")
        source.write_text("Attack", encoding="utf-8")
        output = self.path("out.txt")
        with self.assertRaises(Exception):
            file_handler.vigenere_file(source, output, "BAD KEY")
        self.assertFalse(output.exists())

    def test_file_statistics(self) -> None:
        source = self.path("plain.txt")
        source.write_text("Hello World\nSecond line", encoding="utf-8")
        stats = file_handler.file_statistics(source)
        self.assertEqual(stats["lines"], 2)
        self.assertEqual(stats["letters"], len("HelloWorldSecondline"))


class TestReportGeneration(FileHandlerTestCase):
    """Report building and saving."""

    def test_report_has_the_expected_header(self) -> None:
        builder = ReportBuilder(cipher="Caesar Cipher", operation="Encryption")
        builder.add_key_value("Shift", 3)
        builder.add_section("Output", ["KHOOR ZRUOG"])
        text = builder.render()
        self.assertIn("CRYPTOGRAPHIC CIPHER ANALYSIS REPORT", text)
        self.assertIn("Caesar Cipher", text)
        self.assertIn("KHOOR ZRUOG", text)
        self.assertIn("EDUCATIONAL USE ONLY", text)

    def test_report_contains_every_section(self) -> None:
        builder = ReportBuilder(cipher="Vigenere", operation="Cryptanalysis")
        builder.add_section("Input statistics", ["letters: 100"])
        builder.add_section("Candidate solutions", ["LEMON"])
        text = builder.render()
        self.assertIn("Input statistics:", text)
        self.assertIn("Candidate solutions:", text)

    def test_paragraph_helper(self) -> None:
        builder = ReportBuilder(cipher="Caesar", operation="Test")
        builder.add_paragraph("Educational notes", "Line one.\nLine two.")
        self.assertIn("Line one.", builder.render())

    def test_timestamped_filename_format(self) -> None:
        name = timestamped_filename()
        self.assertTrue(name.startswith("analysis_"))
        self.assertTrue(name.endswith(".txt"))
        self.assertEqual(len(name), len("analysis_YYYYMMDD_HHMMSS.txt"))

    def test_save_report_writes_a_file(self) -> None:
        target = save_report("content", directory=self.directory)
        self.assertTrue(target.exists())
        self.assertEqual(target.read_text(encoding="utf-8"), "content")
        self.assertTrue(target.name.startswith("analysis_"))

    def test_reports_directory_is_inside_the_project(self) -> None:
        self.assertEqual(reports_directory(create=False).name, "reports")


if __name__ == "__main__":
    unittest.main()
