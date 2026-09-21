"""Cryptanalysis toolkit: frequency analysis, Caesar cracking, Vigenère
cryptanalysis, Kasiski examination, Index of Coincidence and security ratings.

Everything in this package is statistics and classical cryptanalysis: no
modern cryptographic primitive is used anywhere.
"""

from analysis.caesar_cracker import CaesarCandidate, crack_caesar
from analysis.frequency import FrequencyResult, chi_squared, fitness_score, frequency_analysis
from analysis.ic_analysis import (
    EXPECTED_ENGLISH_IC,
    RANDOM_TEXT_IC,
    index_of_coincidence,
    interpret_ic,
)
from analysis.kasiski import RepeatedSequence, kasiski_examination
from analysis.security import (
    EDUCATIONAL_DISCLAIMER,
    SecurityProfile,
    caesar_profile,
    profiles,
    vigenere_profile,
)
from analysis.vigenere_analyzer import (
    KeyCandidate,
    VigenereAnalysis,
    analyze_vigenere,
    recover_key_candidates,
    suggest_key_characters,
    suggest_key_lengths,
)

__all__ = [
    "CaesarCandidate",
    "EDUCATIONAL_DISCLAIMER",
    "EXPECTED_ENGLISH_IC",
    "FrequencyResult",
    "KeyCandidate",
    "RANDOM_TEXT_IC",
    "RepeatedSequence",
    "SecurityProfile",
    "VigenereAnalysis",
    "analyze_vigenere",
    "caesar_profile",
    "chi_squared",
    "crack_caesar",
    "fitness_score",
    "frequency_analysis",
    "index_of_coincidence",
    "interpret_ic",
    "kasiski_examination",
    "profiles",
    "recover_key_candidates",
    "suggest_key_characters",
    "suggest_key_lengths",
    "vigenere_profile",
]
