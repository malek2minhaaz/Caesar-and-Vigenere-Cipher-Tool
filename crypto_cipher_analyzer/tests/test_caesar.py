"""Unit tests for :mod:`ciphers.caesar`."""

import os
import sys
import unittest

# Allow the tests to be run from any working directory.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ciphers import caesar  # noqa: E402
from utils.validators import ValidationError  # noqa: E402


class TestCaesarEncryption(unittest.TestCase):
    """Encryption behaviour, including the specification examples."""

    def test_known_example_from_specification(self) -> None:
        self.assertEqual(caesar.encrypt("HELLO WORLD", 3), "KHOOR ZRUOG")

    def test_lowercase_is_preserved(self) -> None:
        self.assertEqual(caesar.encrypt("hello world", 3), "khoor zruog")

    def test_mixed_case_keeps_its_case(self) -> None:
        self.assertEqual(caesar.encrypt("Hello World", 3), "Khoor Zruog")

    def test_shift_zero_returns_identical_text(self) -> None:
        self.assertEqual(caesar.encrypt("HELLO WORLD", 0), "HELLO WORLD")

    def test_shift_26_is_equivalent_to_no_shift(self) -> None:
        self.assertEqual(caesar.encrypt("HELLO WORLD", 26), "HELLO WORLD")

    def test_shift_52_is_equivalent_to_no_shift(self) -> None:
        self.assertEqual(caesar.encrypt("HELLO WORLD", 52), "HELLO WORLD")

    def test_negative_shift_wraps_backwards(self) -> None:
        self.assertEqual(caesar.encrypt("HELLO", -3), "EBIIL")

    def test_shift_larger_than_alphabet_wraps(self) -> None:
        self.assertEqual(caesar.encrypt("HELLO", 29), "KHOOR")

    def test_alphabet_wraps_around(self) -> None:
        self.assertEqual(caesar.encrypt("XYZ", 3), "ABC")

    def test_spaces_are_preserved(self) -> None:
        self.assertEqual(caesar.encrypt("A B  C", 1), "B C  D")

    def test_punctuation_is_preserved(self) -> None:
        self.assertEqual(
            caesar.encrypt("ATTACK AT DAWN!", 2), "CVVCEM CV FCYP!"
        )

    def test_digits_are_preserved(self) -> None:
        self.assertEqual(caesar.encrypt("ROOM 101, FLOOR 3", 1), "SPPN 101, GMPPS 3")

    def test_non_ascii_characters_are_preserved(self) -> None:
        self.assertEqual(caesar.encrypt("café", 3), "fdié")

    def test_newlines_are_preserved(self) -> None:
        self.assertEqual(caesar.encrypt("AB\nCD", 1), "BC\nDE")

    def test_shift_character_directly(self) -> None:
        self.assertEqual(caesar.shift_character("A", 1), "B")
        self.assertEqual(caesar.shift_character("z", 1), "a")
        self.assertEqual(caesar.shift_character("7", 1), "7")

    def test_empty_text_is_rejected(self) -> None:
        for text in ("", "   ", "\n"):
            with self.subTest(text=repr(text)):
                with self.assertRaises(ValidationError):
                    caesar.encrypt(text, 3)

    def test_invalid_shift_is_rejected(self) -> None:
        for shift in ("abc", "", None, 1.5, [3], True):
            with self.subTest(shift=repr(shift)):
                with self.assertRaises(ValidationError):
                    caesar.encrypt("HELLO", shift)


class TestCaesarDecryption(unittest.TestCase):
    """Decryption is the exact inverse of encryption."""

    def test_known_example_from_specification(self) -> None:
        self.assertEqual(caesar.decrypt("KHOOR ZRUOG", 3), "HELLO WORLD")

    def test_round_trip_for_every_shift(self) -> None:
        message = "The Quick Brown Fox Jumps Over 13 Lazy Dogs!"
        for shift in range(26):
            with self.subTest(shift=shift):
                ciphertext = caesar.encrypt(message, shift)
                self.assertEqual(caesar.decrypt(ciphertext, shift), message)

    def test_decrypt_accepts_string_shift(self) -> None:
        self.assertEqual(caesar.decrypt("KHOOR", "3"), "HELLO")

    def test_negative_and_large_shifts_are_normalised(self) -> None:
        self.assertEqual(caesar.decrypt("KHOOR", -23), "HELLO")
        self.assertEqual(caesar.decrypt("KHOOR", 29), "HELLO")


class TestCaesarBruteForce(unittest.TestCase):
    """The brute force helper used by the cracker."""

    def test_returns_all_26_shifts(self) -> None:
        candidates = caesar.brute_force("KHOOR ZRUOG")
        self.assertEqual(len(candidates), 26)
        self.assertEqual([shift for shift, _ in candidates], list(range(26)))

    def test_contains_the_correct_plaintext(self) -> None:
        candidates = dict(caesar.brute_force("KHOOR ZRUOG"))
        self.assertEqual(candidates[3], "HELLO WORLD")

    def test_invalid_input_is_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            caesar.brute_force("")


if __name__ == "__main__":
    unittest.main()
