"""Unit tests for :mod:`analysis.caesar_cracker`."""

import os
import sys
import unittest

# Allow the tests to be run from any working directory.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from analysis import caesar_cracker  # noqa: E402
from ciphers import caesar  # noqa: E402
from utils.validators import ValidationError  # noqa: E402

ENGLISH_SAMPLE = (
    "Cryptography is the practice and study of techniques for secure communication "
    "in the presence of adversaries. Classical ciphers such as the Caesar cipher and "
    "the Vigenere cipher are not secure, but they remain excellent teaching tools "
    "because every step of their cryptanalysis can be performed by hand. Understanding "
    "these attacks explains why modern systems rely on large random keys instead."
)


class TestCrackCaesar(unittest.TestCase):
    """Recovering the shift from ciphertext alone."""

    def test_short_known_example(self) -> None:
        best = caesar_cracker.crack_caesar("KHOOR ZRUOG")[0]
        self.assertEqual(best.shift, 3)
        self.assertEqual(best.plaintext, "HELLO WORLD")

    def test_punctuation_and_spacing_survive_cracking(self) -> None:
        best = caesar_cracker.crack_caesar("KHOOR, ZRUOG!")[0]
        self.assertEqual(best.shift, 3)
        self.assertEqual(best.plaintext, "HELLO, WORLD!")

    def test_longer_text_for_several_shifts(self) -> None:
        for shift in (1, 3, 7, 13, 19, 25):
            with self.subTest(shift=shift):
                ciphertext = caesar.encrypt(ENGLISH_SAMPLE, shift)
                best = caesar_cracker.crack_caesar(ciphertext)[0]
                self.assertEqual(best.shift, shift)
                self.assertEqual(best.plaintext, ENGLISH_SAMPLE)

    def test_best_candidate_helper(self) -> None:
        best = caesar_cracker.best_candidate(caesar.encrypt(ENGLISH_SAMPLE, 11))
        self.assertEqual(best.shift, 11)

    def test_candidates_are_ranked_by_score(self) -> None:
        candidates = caesar_cracker.crack_caesar(caesar.encrypt(ENGLISH_SAMPLE, 4))
        scores = [candidate.score for candidate in candidates]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_top_n_is_respected(self) -> None:
        for top_n in (1, 3, 26):
            with self.subTest(top_n=top_n):
                self.assertEqual(len(caesar_cracker.crack_caesar("KHOOR ZRUOG", top_n)), top_n)

    def test_scores_are_bounded(self) -> None:
        for candidate in caesar_cracker.crack_caesar(ENGLISH_SAMPLE, top_n=26):
            self.assertGreaterEqual(candidate.score, 0.0)
            self.assertLessEqual(candidate.score, 100.0)

    def test_rows_are_formatted_for_display(self) -> None:
        rows = caesar_cracker.candidate_rows(caesar_cracker.crack_caesar("KHOOR ZRUOG"))
        self.assertEqual(rows[0][0], "1")
        self.assertEqual(rows[0][1], "3")
        self.assertEqual(rows[0][3], "HELLO WORLD")

    def test_invalid_input_is_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            caesar_cracker.crack_caesar("")
        with self.assertRaises(ValidationError):
            caesar_cracker.crack_caesar("1234 5678")
        with self.assertRaises(ValidationError):
            caesar_cracker.crack_caesar("KHOOR", top_n=0)

    def test_score_plaintext_is_a_statistical_measure(self) -> None:
        self.assertGreater(
            caesar_cracker.score_plaintext(ENGLISH_SAMPLE),
            caesar_cracker.score_plaintext(caesar.encrypt(ENGLISH_SAMPLE, 13)),
        )


if __name__ == "__main__":
    unittest.main()
