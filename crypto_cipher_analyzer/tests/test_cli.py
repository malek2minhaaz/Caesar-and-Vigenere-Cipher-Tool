"""Integration tests for the command line interface in :mod:`main`."""

import contextlib
import io
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

# Allow the tests to be run from any working directory.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import main  # noqa: E402
from utils import banner  # noqa: E402
from utils.report_generator import reports_directory  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CAESAR_SAMPLE = PROJECT_ROOT / "sample_data" / "caesar_sample.txt"
VIGENERE_SAMPLE = PROJECT_ROOT / "sample_data" / "vigenere_sample.txt"


def run_cli(*arguments: str) -> tuple[int, str]:
    """Run the CLI with *arguments* and return ``(exit code, captured output)``."""
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer), contextlib.redirect_stderr(buffer):
        code = main.main(list(arguments))
    return code, buffer.getvalue()


class CliTestCase(unittest.TestCase):
    """Shared set-up for the interface tests."""

    def setUp(self) -> None:
        banner.disable_color()
        self._temporary = tempfile.TemporaryDirectory()
        self.directory = Path(self._temporary.name)

    def tearDown(self) -> None:
        self._temporary.cleanup()


class TestCipherCommands(CliTestCase):
    """Encryption and decryption commands."""

    def test_caesar_encrypt(self) -> None:
        code, output = run_cli("caesar-encrypt", "--text", "HELLO WORLD", "--shift", "3")
        self.assertEqual(code, 0)
        self.assertIn("KHOOR ZRUOG", output)

    def test_caesar_decrypt(self) -> None:
        code, output = run_cli("caesar-decrypt", "--text", "KHOOR ZRUOG", "--shift", "3")
        self.assertEqual(code, 0)
        self.assertIn("HELLO WORLD", output)

    def test_vigenere_encrypt(self) -> None:
        code, output = run_cli("vigenere-encrypt", "--text", "ATTACKATDAWN", "--key", "LEMON")
        self.assertEqual(code, 0)
        self.assertIn("LXFOPVEFRNHR", output)

    def test_vigenere_decrypt(self) -> None:
        code, output = run_cli("vigenere-decrypt", "--text", "LXFOPVEFRNHR", "--key", "LEMON")
        self.assertEqual(code, 0)
        self.assertIn("ATTACKATDAWN", output)

    def test_text_can_be_read_from_a_file(self) -> None:
        code, output = run_cli("caesar-encrypt", "--input", str(CAESAR_SAMPLE), "--shift", "3")
        self.assertEqual(code, 0)
        self.assertIn("NKRRU CUXRJ", output)  # the sample's KHOOR ZRUOG shifted by another 3


class TestAnalysisCommands(CliTestCase):
    """Frequency, cracking, IC, Kasiski and security commands."""

    def test_frequency(self) -> None:
        code, output = run_cli("frequency", "--text", "KHOOR ZRUOG")
        self.assertEqual(code, 0)
        self.assertIn("FREQUENCY ANALYSIS", output)
        self.assertIn("Ciphertext letter frequency", output)
        self.assertIn("Index of Coincidence", output)

    def test_crack_caesar(self) -> None:
        code, output = run_cli("crack-caesar", "--text", "KHOOR ZRUOG")
        self.assertEqual(code, 0)
        self.assertIn("HELLO WORLD", output)
        self.assertIn("Estimated shift : 3", output)

    def test_crack_caesar_from_the_sample_file(self) -> None:
        code, output = run_cli("crack-caesar", "--input", str(CAESAR_SAMPLE))
        self.assertEqual(code, 0)
        self.assertIn("CRYPTOGRAPHY", output)

    def test_index_of_coincidence(self) -> None:
        code, output = run_cli("ic", "--text", "KHOOR ZRUOG")
        self.assertEqual(code, 0)
        self.assertIn("INDEX OF COINCIDENCE", output)

    def test_kasiski(self) -> None:
        code, output = run_cli("kasiski", "--text", "ABC" + "D" * 27 + "ABC")
        self.assertEqual(code, 0)
        self.assertIn("KASISKI EXAMINATION", output)
        self.assertIn("ABC", output)

    def test_analyze_vigenere(self) -> None:
        code, output = run_cli(
            "analyze-vigenere",
            "--input",
            str(VIGENERE_SAMPLE),
            "--max-key-length",
            "8",
            "--key-length",
            "5",
        )
        self.assertEqual(code, 0)
        self.assertIn("VIGENERE CRYPTANALYSIS", output)
        self.assertIn("LEMON", output)

    def test_security(self) -> None:
        code, output = run_cli("security")
        self.assertEqual(code, 0)
        self.assertIn("VERY WEAK", output)
        self.assertIn("EDUCATIONAL USE ONLY", output)

    def test_report_flag_saves_a_report(self) -> None:
        existing = set(reports_directory(create=True).glob("analysis_*.txt"))
        code, output = run_cli("frequency", "--text", "KHOOR ZRUOG", "--report")
        created = set(reports_directory().glob("analysis_*.txt")) - existing
        self.assertEqual(code, 0)
        self.assertIn("Report saved", output)
        self.assertTrue(created, "expected a report file to be created")
        for path in created:
            path.unlink()


class TestFileCommands(CliTestCase):
    """File based encryption and decryption through the CLI."""

    def test_file_caesar_round_trip(self) -> None:
        source = self.directory / "plain.txt"
        encrypted = self.directory / "cipher.txt"
        decrypted = self.directory / "restored.txt"
        source.write_text("Attack at dawn!", encoding="utf-8")

        code, output = run_cli(
            "file-caesar", "--input", str(source), "--output", str(encrypted), "--shift", "3"
        )
        self.assertEqual(code, 0)
        self.assertIn("FILE OPERATION COMPLETE", output)
        self.assertNotEqual(encrypted.read_text(encoding="utf-8"), "Attack at dawn!")

        code, _ = run_cli(
            "file-caesar",
            "--input",
            str(encrypted),
            "--output",
            str(decrypted),
            "--shift",
            "3",
            "--decrypt",
        )
        self.assertEqual(code, 0)
        self.assertEqual(decrypted.read_text(encoding="utf-8"), "Attack at dawn!")

    def test_file_vigenere_round_trip(self) -> None:
        source = self.directory / "plain.txt"
        encrypted = self.directory / "cipher.txt"
        decrypted = self.directory / "restored.txt"
        source.write_text("Attack at dawn!", encoding="utf-8")

        self.assertEqual(
            run_cli(
                "file-vigenere",
                "--input",
                str(source),
                "--output",
                str(encrypted),
                "--key",
                "LEMON",
            )[0],
            0,
        )
        self.assertEqual(
            run_cli(
                "file-vigenere",
                "--input",
                str(encrypted),
                "--output",
                str(decrypted),
                "--key",
                "LEMON",
                "--decrypt",
            )[0],
            0,
        )
        self.assertEqual(decrypted.read_text(encoding="utf-8"), "Attack at dawn!")

    def test_default_output_path_is_used(self) -> None:
        source = self.directory / "plain.txt"
        source.write_text("Attack at dawn!", encoding="utf-8")
        code, output = run_cli("file-caesar", "--input", str(source), "--shift", "3")
        self.assertEqual(code, 0)
        self.assertIn("plain_out.txt", output)
        self.assertTrue((self.directory / "plain_out.txt").exists())

    def test_existing_output_requires_overwrite(self) -> None:
        source = self.directory / "plain.txt"
        output = self.directory / "cipher.txt"
        source.write_text("Attack at dawn!", encoding="utf-8")
        output.write_text("existing", encoding="utf-8")

        code, message = run_cli(
            "file-caesar", "--input", str(source), "--output", str(output), "--shift", "3"
        )
        self.assertEqual(code, 1)
        self.assertIn("already exists", message)
        self.assertEqual(output.read_text(encoding="utf-8"), "existing")

        code, _ = run_cli(
            "file-caesar",
            "--input",
            str(source),
            "--output",
            str(output),
            "--shift",
            "3",
            "--overwrite",
        )
        self.assertEqual(code, 0)


class TestErrorHandling(CliTestCase):
    """Invalid input must produce a friendly message and a non-zero exit code."""

    def test_missing_text_is_reported(self) -> None:
        code, output = run_cli("caesar-encrypt", "--shift", "3")
        self.assertEqual(code, 1)
        self.assertIn("Provide the input", output)
        self.assertNotIn("Traceback", output)

    def test_missing_shift_is_reported(self) -> None:
        code, output = run_cli("caesar-encrypt", "--text", "HELLO")
        self.assertEqual(code, 1)
        self.assertIn("Provide a shift", output)

    def test_invalid_shift_is_reported(self) -> None:
        code, output = run_cli("caesar-encrypt", "--text", "HELLO", "--shift", "banana")
        self.assertEqual(code, 1)
        self.assertIn("not a valid shift", output)

    def test_invalid_key_is_reported(self) -> None:
        code, output = run_cli("vigenere-encrypt", "--text", "HELLO", "--key", "LE MON")
        self.assertEqual(code, 1)
        self.assertIn("letters only", output)

    def test_missing_input_file_is_reported(self) -> None:
        code, output = run_cli("frequency", "--input", str(self.directory / "nope.txt"))
        self.assertEqual(code, 1)
        self.assertIn("not found", output)

    def test_text_without_letters_is_reported(self) -> None:
        code, output = run_cli("frequency", "--text", "12345")
        self.assertEqual(code, 1)
        self.assertIn("No letters", output)

    def test_unknown_command_is_rejected_by_argparse(self) -> None:
        code, output = run_cli("banana")
        self.assertEqual(code, 2)
        self.assertNotIn("Traceback", output)


class TestGeneralOptions(CliTestCase):
    """Help, version and interactive behaviour."""

    def test_help_exits_successfully(self) -> None:
        code, output = run_cli("--help")
        self.assertEqual(code, 0)
        self.assertIn("COMMAND", output)

    def test_version_exits_successfully(self) -> None:
        code, output = run_cli("--version")
        self.assertEqual(code, 0)
        self.assertIn(main.VERSION, output)

    def test_subcommand_help(self) -> None:
        code, output = run_cli("crack-caesar", "--help")
        self.assertEqual(code, 0)
        self.assertIn("--text", output)

    def test_interactive_mode_exits_on_end_of_input(self) -> None:
        with mock.patch("builtins.input", side_effect=EOFError):
            code, output = run_cli()
        self.assertEqual(code, 0)
        self.assertIn("End of input detected", output)

    def test_interactive_mode_rejects_invalid_selection(self) -> None:
        answers = iter(["42", "9"])
        with mock.patch("builtins.input", side_effect=lambda *_: next(answers, "9")):
            code, output = run_cli()
        self.assertEqual(code, 0)
        self.assertIn("not a valid selection", output)
        self.assertIn("Exiting", output)

    def test_interactive_caesar_flow(self) -> None:
        # main menu -> Caesar, submenu -> encrypt, input source -> type the text
        answers = iter(["1", "1", "1", "HELLO WORLD", "3", "n", "9"])
        with mock.patch("builtins.input", side_effect=lambda *_: next(answers, "9")):
            code, output = run_cli()
        self.assertEqual(code, 0)
        self.assertIn("KHOOR ZRUOG", output)


if __name__ == "__main__":
    unittest.main()
