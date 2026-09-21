"""Unit tests for :mod:`analysis.frequency`."""

import os
import sys
import unittest

# Allow the tests to be run from any working directory.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from analysis import frequency  # noqa: E402
from utils.text_utils import ENGLISH_LETTER_FREQUENCIES  # noqa: E402
from utils.validators import ValidationError  # noqa: E402

ENGLISH_PASSAGE = (
    "Cryptography is the practice and study of techniques for secure communication "
    "in the presence of adversaries. Classical ciphers such as the Caesar cipher and "
    "the Vigenere cipher are not secure, but they remain excellent teaching tools "
    "because every step of their cryptanalysis can be performed by hand."
)


class TestFrequencyCounts(unittest.TestCase):
    """Counts and percentages."""

    def test_letter_counts(self) -> None:
        result = frequency.frequency_analysis("HELLO")
        self.assertEqual(result.total_letters, 5)
        self.assertEqual(result.counts["L"], 2)
        self.assertEqual(result.counts["H"], 1)
        self.assertEqual(result.counts["Z"], 0)

    def test_percentages(self) -> None:
        result = frequency.frequency_analysis("HELLO")
        self.assertAlmostEqual(result.percentages["L"], 40.0)
        self.assertAlmostEqual(result.percentages["H"], 20.0)
        self.assertAlmostEqual(result.percentages["Z"], 0.0)

    def test_percentages_sum_to_one_hundred(self) -> None:
        result = frequency.frequency_analysis(ENGLISH_PASSAGE)
        self.assertAlmostEqual(sum(result.percentages.values()), 100.0, places=6)

    def test_non_letters_are_counted_but_not_analysed(self) -> None:
        # "A1! B2?" is 7 characters, only two of which are letters.
        result = frequency.frequency_analysis("A1! B2?")
        self.assertEqual(result.total_characters, 7)
        self.assertEqual(result.total_letters, 2)
        self.assertEqual(result.counts["A"], 1)
        self.assertEqual(result.counts["B"], 1)

    def test_case_is_ignored(self) -> None:
        lower = frequency.frequency_analysis("hello")
        upper = frequency.frequency_analysis("HELLO")
        self.assertEqual(lower.counts, upper.counts)

    def test_most_and_least_common(self) -> None:
        result = frequency.frequency_analysis("THE QUICK BROWN FOX JUMPS OVER THE LAZY DOG")
        self.assertEqual(result.most_common[0][0], "O")
        self.assertGreaterEqual(result.most_common[0][1], result.most_common[1][1])
        self.assertLessEqual(result.least_common[0][1], result.least_common[1][1])

    def test_text_without_letters_is_rejected(self) -> None:
        for text in ("", "12345", "!!! ???"):
            with self.subTest(text=repr(text)):
                with self.assertRaises(ValidationError):
                    frequency.frequency_analysis(text)

    def test_letter_rows_are_ordered_by_count(self) -> None:
        rows = frequency.letter_rows(frequency.frequency_analysis("AABBBC"))
        self.assertEqual([row[0] for row in rows], ["B", "A", "C"])

    def test_letter_rows_format_percentages(self) -> None:
        rows = frequency.letter_rows(frequency.frequency_analysis("HELLO"))
        self.assertEqual(rows[0][2], "40.00%")

    def test_summary_lines_are_produced(self) -> None:
        lines = frequency.frequency_analysis("HELLO").as_summary_lines()
        self.assertTrue(any("Alphabetic characters" in line for line in lines))

    def test_comparison_with_english_uses_reference_table(self) -> None:
        result = frequency.frequency_analysis("EEEEE")
        rows = frequency.compare_with_english(result)
        self.assertEqual(rows[0][0], "E")
        self.assertEqual(rows[0][2], f"{ENGLISH_LETTER_FREQUENCIES['E']:.2f}%")

    def test_formatted_frequency_lines(self) -> None:
        lines = frequency.formatted_frequency_lines(frequency.frequency_analysis("HELLO"))
        self.assertEqual(lines[0].split()[0], "Letter")
        # Two table lines (heading and rule) plus one row per distinct letter:
        # HELLO contains H, E, L and O.
        self.assertEqual(len(lines), 2 + 4)


class TestEnglishScoring(unittest.TestCase):
    """The statistics used to rank candidate plaintexts."""

    def test_chi_squared_is_lower_for_english_text(self) -> None:
        english = frequency.chi_squared(ENGLISH_PASSAGE)
        random_like = frequency.chi_squared("QWXZ JVKQ PZXJ VQKZ WXPJ QZKX")
        self.assertLess(english, random_like)

    def test_chi_squared_of_text_without_letters_is_zero(self) -> None:
        self.assertEqual(frequency.chi_squared("12345"), 0.0)

    def test_fitness_score_prefers_english(self) -> None:
        english = frequency.fitness_score(ENGLISH_PASSAGE)
        shifted = frequency.fitness_score("QEB NRFZH YOLTK CLU GRJMP LSBO QEB IXWV ALD")
        self.assertGreater(english, shifted)

    def test_fitness_score_is_bounded(self) -> None:
        for text in (ENGLISH_PASSAGE, "ZZZZ", "A", "HELLO WORLD"):
            with self.subTest(text=text):
                score = frequency.fitness_score(text)
                self.assertGreaterEqual(score, 0.0)
                self.assertLessEqual(score, 100.0)

    def test_fitness_score_of_empty_text_is_zero(self) -> None:
        self.assertEqual(frequency.fitness_score(""), 0.0)

    def test_digram_score_recognises_common_digrams(self) -> None:
        self.assertGreater(
            frequency.digram_score("THEANDING"),
            frequency.digram_score("QXZJVQKXZ"),
        )

    def test_digram_score_of_single_letter_is_zero(self) -> None:
        self.assertEqual(frequency.digram_score("A"), 0.0)

    def test_digram_score_bounds(self) -> None:
        score = frequency.digram_score(ENGLISH_PASSAGE)
        self.assertGreater(score, 0.0)
        self.assertLessEqual(score, 100.0)

    def test_frequency_correlation_of_english_is_high(self) -> None:
        self.assertGreater(frequency.frequency_correlation(ENGLISH_PASSAGE), 0.8)

    def test_frequency_correlation_of_uniform_text_is_low(self) -> None:
        uniform = "ABCDEFGHIJKLMNOPQRSTUVWXYZ" * 3
        self.assertLess(frequency.frequency_correlation(uniform), 0.5)


if __name__ == "__main__":
    unittest.main()
