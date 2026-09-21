"""Classical cipher implementations (Caesar and Vigenère).

Both ciphers are implemented from scratch with the standard library only: no
cryptographic library is used anywhere in the project, because the point is to
demonstrate how the algorithms work.
"""

from ciphers.caesar import (
    brute_force as caesar_brute_force,
    decrypt as caesar_decrypt,
    encrypt as caesar_encrypt,
    shift_character,
)
from ciphers.vigenere import (
    decrypt as vigenere_decrypt,
    encrypt as vigenere_encrypt,
    generate_keystream,
)

__all__ = [
    "caesar_brute_force",
    "caesar_decrypt",
    "caesar_encrypt",
    "generate_keystream",
    "shift_character",
    "vigenere_decrypt",
    "vigenere_encrypt",
]
