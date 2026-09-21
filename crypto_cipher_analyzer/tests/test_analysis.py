"""Unit tests for the cryptanalysis modules.

Covers :mod:`analysis.ic_analysis`, :mod:`analysis.kasiski`,
:mod:`analysis.vigenere_analyzer` and :mod:`analysis.security`.
"""

import os
import sys
import unittest
from pathlib import Path

# Allow the tests to be run from any working directory.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from analysis import ic_analysis, kasiski, security, vigenere_analyzer  # noqa: E402
from ciphers import vigenere  # noqa: E402
from file_operations import file_handler  # noqa: E402
from utils.validators import ValidationError  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parent.parent
VIGENERE_SAMPLE_PATH = PROJECT_ROOT / "sample_data" / "vigenere_sample.txt"

#: The shipped sample is a single Vigenère encryption with the key ``LEMON``.
VIGENERE_SAMPLE = file_handler.read_text(VIGENERE_SAMPLE_PATH)

ENGLISH_PASSAGE = (
    "Cryptography is the practice and study of techniques for secure communication "
    "in the presence of adversaries. Classical ciphers such as the Caesar cipher and "
    "the Vigenere cipher are not secure, but they remain excellent teaching tools "
    "because every step of their cryptanalysis can be performed by hand."
)


class TestIndexOfCoincidence(unittest.TestCase):
    """IC values and their interpretation."""

    def test_single_repeated_letter_gives_maximum_ic(self) -> None:
        self.assertAlmostEqual(ic_analysis.index_of_coincidence("AAAAAAAAAA"), 1.0)

    def test_known_value_for_hello_world(self) -> None:
        # HELLO WORLD has 10 letters: L is repeated 3 times and O twice,
        # so IC = (3*2 + 2*1) / (10*9) = 8/90.
        self.assertAlmostEqual(
            ic_analysis.index_of_coincidence("HELLO WORLD"), 8 / 90
        )

    def test_english_text_is_close_to_the_reference_value(self) -> None:
        value = ic_analysis.index_of_coincidence(ENGLISH_PASSAGE)
        self.assertGreater(value, 0.05)
        self.assertLess(value, 0.08)

    def test_very_short_input_returns_zero(self) -> None:
        self.assertEqual(ic_analysis.index_of_coincidence("A"), 0.0)
        self.assertEqual(ic_analysis.index_of_coincidence("!!!"), 0.0)

    def test_interpretation_covers_the_whole_range(self) -> None:
        self.assertIn("Not enough", ic_analysis.interpret_ic(0.0))
        self.assertIn("monoalphabetic", ic_analysis.interpret_ic(0.07))
        self.assertIn("polyalphabetic", ic_analysis.interpret_ic(0.04))

    def test_analysis_result_formatting(self) -> None:
        result = ic_analysis.analyze_index_of_coincidence(ENGLISH_PASSAGE)
        # Only letters are counted, so the punctuation and spaces are excluded.
        self.assertEqual(result.total_letters, sum(1 for char in ENGLISH_PASSAGE if char.isalpha()))
        self.assertTrue(any("Index of Coincidence" in line for line in result.format_lines()))

    def test_too_short_text_is_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            ic_analysis.analyze_index_of_coincidence("A")

    def test_column_ic_of_correct_key_length_is_english_like(self) -> None:
        self.assertGreater(ic_analysis.ic_for_key_length(VIGENERE_SAMPLE, 5), 0.06)

    def test_column_ic_of_wrong_key_length_is_low(self) -> None:
        self.assertLess(ic_analysis.ic_for_key_length(VIGENERE_SAMPLE, 7), 0.055)

    def test_ic_by_key_length_returns_every_length(self) -> None:
        values = ic_analysis.ic_by_key_length(VIGENERE_SAMPLE, max_key_length=10)
        self.assertEqual(sorted(values), list(range(1, 11)))

    def test_true_key_length_ranks_near_the_top(self) -> None:
        values = ic_analysis.ic_by_key_length(VIGENERE_SAMPLE, max_key_length=12)
        best = sorted(values.items(), key=lambda item: -item[1])
        self.assertIn(5, [length for length, _ in best[:3]])

    def test_invalid_key_length_is_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            ic_analysis.ic_for_key_length(VIGENERE_SAMPLE, 0)

    def test_rows_helper(self) -> None:
        rows = ic_analysis.ic_as_rows({1: 0.06, 2: 0.04})
        self.assertEqual(rows[0][0], "1")


class TestKasiski(unittest.TestCase):
    """Repeated sequences, distances and factor ranking."""

    def test_factorize(self) -> None:
        self.assertEqual(kasiski.factorize(30), [2, 3, 5, 6, 10, 15, 30])
        self.assertEqual(kasiski.factorize(1), [])
        self.assertEqual(kasiski.factorize(0), [])
        self.assertEqual(kasiski.factorize(13), [13])

    def test_distances_from_positions(self) -> None:
        self.assertEqual(kasiski.distances_from_positions([12, 42, 72]), [30, 30])
        self.assertEqual(kasiski.distances_from_positions([5]), [])

    def test_repeated_sequence_positions_and_distances(self) -> None:
        text = "ABC" + "D" * 27 + "ABC"
        sequences = kasiski.find_repeated_sequences(text, min_length=3, max_length=3)
        found = next(item for item in sequences if item.sequence == "ABC")
        self.assertEqual(found.positions, (0, 30))
        self.assertEqual(found.distances, (30,))
        self.assertIn(5, found.factors)
        self.assertIn(15, found.factors)
        self.assertEqual(found.occurrences, 2)

    def test_no_repetition_yields_no_sequences(self) -> None:
        self.assertEqual(kasiski.find_repeated_sequences("ABCDEFGHIJKLMNOP"), [])

    def test_examination_reports_candidates_for_the_sample(self) -> None:
        result = kasiski.kasiski_examination(VIGENERE_SAMPLE, max_key_length=10)
        self.assertTrue(result.has_evidence)
        self.assertIn(5, [length for length, _ in result.ranked_key_lengths[:3]])

    def test_examination_without_repetition_is_graceful(self) -> None:
        result = kasiski.kasiski_examination("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
        self.assertFalse(result.has_evidence)
        self.assertEqual(result.ranked_key_lengths, ())
        self.assertTrue(any("No repeated sequences" in line for line in result.format_lines()))

    def test_rank_key_lengths_prefers_divisors_of_factors(self) -> None:
        ranked = kasiski.rank_key_lengths({10: 3, 15: 3}, max_key_length=5)
        self.assertEqual(ranked[0][0], 5)

    def test_row_helpers(self) -> None:
        result = kasiski.kasiski_examination(VIGENERE_SAMPLE, max_key_length=10)
        rows = kasiski.kasiski_rows(result, limit=3)
        self.assertEqual(len(rows), 3)
        self.assertTrue(kasiski.key_length_rows(result, limit=2))

    def test_specification_example_of_distances(self) -> None:
        # "ABC" at positions 12, 42 and 72 -> distances 30 and 30 -> factors 2,3,5,...
        result = kasiski.rank_key_lengths({factor: 1 for factor in kasiski.factorize(30)})
        self.assertEqual([length for length, _ in result][:6], [2, 3, 5, 6, 10, 15])


class TestVigenereAnalyzer(unittest.TestCase):
    """The combined cryptanalysis workflow."""

    def test_key_length_estimation(self) -> None:
        best = vigenere_analyzer.suggest_key_lengths(VIGENERE_SAMPLE)[0]
        self.assertEqual(best.key_length, 5)
        self.assertGreater(best.average_ic, 0.06)

    def test_key_length_candidates_are_ranked(self) -> None:
        candidates = vigenere_analyzer.suggest_key_lengths(VIGENERE_SAMPLE, top_n=10)
        scores = [candidate.combined_score for candidate in candidates]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_per_column_key_letters(self) -> None:
        suggestions = vigenere_analyzer.suggest_key_characters(VIGENERE_SAMPLE, 5)
        self.assertEqual(len(suggestions), 5)
        self.assertEqual([suggestion.best() for suggestion in suggestions], list("LEMON"))
        self.assertEqual(suggestions[0].position, 1)
        self.assertEqual(len(suggestions[0].suggestions), 3)

    def test_key_recovery_recovers_the_real_key(self) -> None:
        candidates = vigenere_analyzer.recover_key_candidates(VIGENERE_SAMPLE, 5)
        self.assertEqual(candidates[0].key, "LEMON")
        self.assertTrue(candidates[0].plaintext.startswith("CRYPTOGRAPHY IS THE PRACTICE"))
        self.assertEqual(candidates[0].score, max(candidate.score for candidate in candidates))

    def test_full_analysis(self) -> None:
        analysis = vigenere_analyzer.analyze_vigenere(VIGENERE_SAMPLE)
        self.assertIsNotNone(analysis.kasiski)
        self.assertEqual(analysis.best_key_length(), 5)
        self.assertLess(analysis.overall_ic, 0.05)
        self.assertTrue(any("Candidate key lengths" in line for line in analysis.format_lines()))

    def test_analysis_written_from_a_known_key(self) -> None:
        ciphertext = vigenere.encrypt(ENGLISH_PASSAGE * 2, "SECRET")
        analysis = vigenere_analyzer.analyze_vigenere(ciphertext, max_key_length=10, top_n=3)
        self.assertEqual(analysis.best_key_length(), 6)
        candidates = vigenere_analyzer.recover_key_candidates(ciphertext, 6)
        self.assertEqual(candidates[0].key, "SECRET")

    def test_too_short_input_is_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            vigenere_analyzer.analyze_vigenere("ABC")
        with self.assertRaises(ValidationError):
            vigenere_analyzer.suggest_key_lengths("A")

    def test_invalid_arguments_are_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            vigenere_analyzer.suggest_key_characters(VIGENERE_SAMPLE, key_length=0)
        with self.assertRaises(ValidationError):
            vigenere_analyzer.suggest_key_characters(VIGENERE_SAMPLE, 5, top_n=0)
        with self.assertRaises(ValidationError):
            vigenere_analyzer.suggest_key_lengths(VIGENERE_SAMPLE, top_n=0)

    def test_row_helpers(self) -> None:
        analysis = vigenere_analyzer.analyze_vigenere(VIGENERE_SAMPLE, top_n=3)
        self.assertEqual(len(vigenere_analyzer.key_length_rows(analysis)), 3)
        candidates = vigenere_analyzer.recover_key_candidates(VIGENERE_SAMPLE, 5)
        rows = vigenere_analyzer.key_candidate_rows(candidates)
        self.assertEqual(rows[0][0], "1")
        self.assertEqual(rows[0][1], "LEMON")
        suggestions = vigenere_analyzer.suggest_key_characters(VIGENERE_SAMPLE, 5)
        self.assertEqual(vigenere_analyzer.position_suggestion_rows(suggestions)[0][0], "1")


class TestSecurityProfiles(unittest.TestCase):
    """The educational security assessment content."""

    def test_both_profiles_are_available(self) -> None:
        profiles = security.profiles()
        self.assertEqual(len(profiles), 2)
        self.assertEqual(profiles[0].name, "Caesar Cipher")
        self.assertEqual(profiles[1].name, "Vigenere Cipher")

    def test_ratings_are_weak(self) -> None:
        self.assertEqual(security.caesar_profile().rating, "VERY WEAK")
        self.assertIn("WEAK", security.vigenere_profile().rating)

    def test_profiles_describe_attacks(self) -> None:
        caesar_attacks = " ".join(security.caesar_profile().cryptanalysis).lower()
        self.assertIn("brute force", caesar_attacks)
        vigenere_attacks = " ".join(security.vigenere_profile().cryptanalysis).lower()
        self.assertIn("kasiski", vigenere_attacks)
        self.assertIn("index of coincidence", vigenere_attacks)

    def test_profile_lines_include_the_rating(self) -> None:
        lines = security.caesar_profile().format_lines()
        self.assertTrue(any("Security rating" in line for line in lines))

    def test_disclaimer_mentions_educational_use(self) -> None:
        self.assertIn("EDUCATIONAL USE ONLY", security.EDUCATIONAL_DISCLAIMER)
        self.assertIn("NOT", security.EDUCATIONAL_DISCLAIMER)

    def test_profile_lookup(self) -> None:
        self.assertEqual(security.profile_for("caesar").name, "Caesar Cipher")
        self.assertEqual(security.profile_for("Vigenere").name, "Vigenere Cipher")
        with self.assertRaises(KeyError):
            security.profile_for("unknown")

    def test_security_summary_lines(self) -> None:
        lines = security.security_summary_lines("caesar")
        self.assertTrue(any("VERY WEAK" in line for line in lines))


if __name__ == "__main__":
    unittest.main()
