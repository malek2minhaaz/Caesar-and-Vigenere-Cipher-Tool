"""Unit tests for :mod:`ciphers.vigenere`."""

import os
import sys
import unittest

# Allow the tests to be run from any working directory.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ciphers import vigenere  # noqa: E402
from utils.validators import ValidationError  # noqa: E402


class TestVigenereEncryption(unittest.TestCase):
    """Encryption behaviour, including the specification example."""

    def test_known_example_from_specification(self) -> None:
        self.assertEqual(vigenere.encrypt("ATTACKATDAWN", "LEMON"), "LXFOPVEFRNHR")

    def test_lowercase_input_is_supported(self) -> None:
        self.assertEqual(vigenere.encrypt("attackatdawn", "lemon"), "lxfopvefrnhr")

    def test_spaces_do_not_desynchronise_the_key(self) -> None:
        with_spaces = vigenere.encrypt("ATTACK AT DAWN", "LEMON")
        self.assertEqual(with_spaces.replace(" ", ""), "LXFOPVEFRNHR")
        self.assertEqual(with_spaces, "LXFOPV EF RNHR")

    def test_punctuation_is_preserved(self) -> None:
        self.assertEqual(vigenere.encrypt("ATTACK AT DAWN!", "LEMON"), "LXFOPV EF RNHR!")

    def test_digits_are_preserved_and_skipped(self) -> None:
        self.assertEqual(vigenere.encrypt("A1B2", "LEMON"), "L1F2")

    def test_key_is_case_insensitive(self) -> None:
        self.assertEqual(
            vigenere.encrypt("ATTACKATDAWN", "lemon"),
            vigenere.encrypt("ATTACKATDAWN", "LEMON"),
        )

    def test_newlines_are_preserved(self) -> None:
        # The newline is copied through and does not consume a key letter, so
        # "CD" is encrypted with the start of the key: C+M=O, D+O=R.
        self.assertEqual(vigenere.encrypt("AB\nCD", "LEMON"), "LF\nOR")

    def test_repeating_key_wraps_correctly(self) -> None:
        # 12 letters with a 5-letter key: LEMON LEMON LE
        self.assertEqual(vigenere.generate_keystream("ATTACKATDAWN", "LEMON"), "LEMONLEMONLE")

    def test_keystream_skips_non_letters(self) -> None:
        self.assertEqual(vigenere.generate_keystream("A B!C", "LEMON"), "LEM")

    def test_key_offsets(self) -> None:
        self.assertEqual(vigenere.key_offsets("LEMON"), [11, 4, 12, 14, 13])

    def test_empty_text_is_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            vigenere.encrypt("", "LEMON")

    def test_invalid_keys_are_rejected(self) -> None:
        for key in ("", "   ", "LE MON", "LEMON4", "LE-MON", None, 123, "LÉMON"):
            with self.subTest(key=repr(key)):
                with self.assertRaises(ValidationError):
                    vigenere.encrypt("ATTACKATDAWN", key)

    def test_single_letter_key_behaves_like_a_caesar_cipher(self) -> None:
        from ciphers import caesar

        self.assertEqual(
            vigenere.encrypt("HELLO WORLD", "D"),
            caesar.encrypt("HELLO WORLD", 3),
        )

    def test_longer_known_example(self) -> None:
        self.assertEqual(
            vigenere.encrypt("THEQUICKBROWNFOXJUMPSOVERTHELAZYDOG", "KEY"),
            "DLCAYGMOZBSUXJMHNSWTQYZCBXFOPYJCBYK",
        )


class TestVigenereDecryption(unittest.TestCase):
    """Decryption is the exact inverse of encryption."""

    def test_known_example_from_specification(self) -> None:
        self.assertEqual(vigenere.decrypt("LXFOPVEFRNHR", "LEMON"), "ATTACKATDAWN")

    def test_round_trip_for_several_keys(self) -> None:
        message = "Meet me at the Old Bridge, 42 Wallaby Way, at 19:00!"
        for key in ("A", "KEY", "LEMON", "CYBERSECURITY"):
            with self.subTest(key=key):
                ciphertext = vigenere.encrypt(message, key)
                self.assertEqual(vigenere.decrypt(ciphertext, key), message)

    def test_key_of_length_one_is_a_caesar_shift(self) -> None:
        self.assertEqual(vigenere.decrypt("KHOOR", "D"), "HELLO")

    def test_invalid_key_is_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            vigenere.decrypt("LXFOPVEFRNHR", "LE MON")


if __name__ == "__main__":
    unittest.main()
