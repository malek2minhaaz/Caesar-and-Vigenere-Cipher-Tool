"""Security and strength assessment of the implemented classical ciphers.

This module contains the educational content used by the ``Security Analysis``
menu entry and by generated reports. It states plainly that neither cipher is
suitable for protecting real information.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

#: Printed by the CLI and embedded in every generated report.
EDUCATIONAL_DISCLAIMER: str = """EDUCATIONAL USE ONLY

This project demonstrates classical cryptography and cryptanalysis.
Caesar and Vigenere ciphers are historically important but are NOT
secure modern encryption algorithms.

Do not use this project to protect passwords, credentials, financial
information, personal data, or confidential communications."""

#: Short reminder used by the CLI after cryptographic operations.
SHORT_DISCLAIMER: str = (
    "Educational use only: these classical ciphers are not secure for real data."
)


@dataclass(frozen=True)
class SecurityProfile:
    """A structured security assessment of one cipher."""

    name: str
    rating: str
    keyspace: str
    strengths: Sequence[str] = field(default_factory=tuple)
    weaknesses: Sequence[str] = field(default_factory=tuple)
    cryptanalysis: Sequence[str] = field(default_factory=tuple)
    modern_use: str = ""
    verdict: str = ""

    def format_lines(self) -> list[str]:
        """Return the profile as printable ``label: value`` lines."""
        lines = [
            f"Cipher          : {self.name}",
            f"Security rating : {self.rating}",
            f"Keyspace        : {self.keyspace}",
            "",
            "Strengths:",
        ]
        lines.extend(f"  - {item}" for item in self.strengths)
        lines.append("")
        lines.append("Weaknesses:")
        lines.extend(f"  - {item}" for item in self.weaknesses)
        lines.append("")
        lines.append("Known cryptanalytic attacks:")
        lines.extend(f"  - {item}" for item in self.cryptanalysis)
        lines.append("")
        lines.append(f"Modern use      : {self.modern_use}")
        if self.verdict:
            lines.append(f"Verdict         : {self.verdict}")
        return lines


def caesar_profile() -> SecurityProfile:
    """Return the security profile of the Caesar cipher."""
    return SecurityProfile(
        name="Caesar Cipher",
        rating="VERY WEAK",
        keyspace="25 effective keys (26 shifts, shift 0 leaves the text unchanged)",
        strengths=(
            "Trivial to implement and to explain, which makes it a good teaching tool.",
            "Encryption and decryption are fast and need no key exchange infrastructure.",
            "Useful as the building block that the Vigenere cipher generalises.",
        ),
        weaknesses=(
            "Extremely small keyspace: the whole key can be tested in milliseconds.",
            "Easily broken with single-letter frequency analysis.",
            "The shift is preserved by the alphabet, so letter patterns survive intact.",
            "Identical plaintext always produces identical ciphertext (no randomness).",
            "No authentication: ciphertext can be modified without detection.",
        ),
        cryptanalysis=(
            "Exhaustive brute force over all 26 shifts (see the 'Break Caesar Cipher' option).",
            "Chi-square / frequency scoring to rank candidate plaintexts automatically.",
            "Known-plaintext attack: one known letter reveals the entire shift.",
        ),
        modern_use=(
            "Legacy puzzle games, CTF warm-up challenges and cryptography education only."
        ),
        verdict="Never use the Caesar cipher to protect real information.",
    )


def vigenere_profile() -> SecurityProfile:
    """Return the security profile of the Vigenère cipher."""
    return SecurityProfile(
        name="Vigenere Cipher",
        rating="WEAK / EDUCATIONAL ONLY",
        keyspace=(
            "26^L keys for a key of length L (L=8 gives about 2.1e11 keys), "
            "but the keyspace is not the weakness"
        ),
        strengths=(
            "Much larger keyspace than the Caesar cipher; historically called 'le chiffre indechiffrable'.",
            "Defeats naive single-letter frequency analysis when the key is as long as the message.",
            "Introduces the polyalphabetic idea that underlies the one-time pad.",
        ),
        weaknesses=(
            "A repeating key means the same shift is reused, which leaks structure.",
            "Kasiski examination recovers probable key lengths from repeated sequences.",
            "Index of Coincidence per column reveals the key length and enables per-column analysis.",
            "Once the key length is known, each column is an independent Caesar cipher.",
            "Key length is effectively limited by human-memorable words, so real keys are short.",
            "No diffusion, no authentication and no randomness.",
        ),
        cryptanalysis=(
            "Kasiski examination: repeated sequences give distances whose factors suggest the key length.",
            "Index of Coincidence: the average IC of the columns peaks at the true key length.",
            "Per-column frequency analysis (chi-square) guesses each key letter independently.",
            "Friedman / mutual Index of Coincidence estimates the key length statistically.",
        ),
        modern_use=(
            "Cryptography education, puzzle solving and historical study only."
        ),
        verdict="Suitable for teaching polyalphabetic ciphers, never for sensitive data.",
    )


def profiles() -> tuple[SecurityProfile, SecurityProfile]:
    """Return both security profiles in presentation order."""
    return (caesar_profile(), vigenere_profile())


def profile_for(cipher: str) -> SecurityProfile:
    """Return the profile matching *cipher* (``"caesar"`` or ``"vigenere"``)."""
    name = cipher.strip().lower()
    if name.startswith("caesar"):
        return caesar_profile()
    if name.startswith("vigenere") or name.startswith("vigenère"):
        return vigenere_profile()
    raise KeyError(f"Unknown cipher: {cipher}")


def security_summary_lines(cipher: str) -> list[str]:
    """Return a compact one-line-per-fact summary for reports.

    Args:
        cipher: ``"caesar"`` or ``"vigenere"``.

    Returns:
        A list of short assessment lines.
    """
    profile = profile_for(cipher)
    lines = [
        f"Cipher          : {profile.name}",
        f"Security rating : {profile.rating}",
        f"Keyspace        : {profile.keyspace}",
        "Key weaknesses  :",
    ]
    lines.extend(f"  - {item}" for item in profile.weaknesses[:4])
    lines.append(f"Verdict         : {profile.verdict}")
    return lines
