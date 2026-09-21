# Cryptographic Cipher Analyzer — Caesar & Vigenère Cipher Tool

A command-line tool for **classical cipher encryption, decryption, and cryptanalysis**, built in pure Python (standard library only — no third-party packages).

It implements the Caesar and Vigenère ciphers from scratch and ships a full cryptanalysis toolkit: automatic Caesar breaking, frequency analysis, Kasiski examination, Index of Coincidence, Vigenère key recovery, file encryption, and security ratings.

> ⚠️ **Educational project.** Caesar and Vigenère ciphers are classical ciphers that offer no real security against modern attacks. This tool exists to demonstrate *how* they work and *how* they are broken — do not use it to protect real data.

---

## Features

| Menu | Feature |
|------|---------|
| 1 | **Caesar Cipher** — encrypt / decrypt text with a shift value |
| 2 | **Vigenère Cipher** — encrypt / decrypt text with a repeating keyword |
| 3 | **Frequency Analysis** — letter counts, chi-squared fitness vs. English |
| 4 | **Break Caesar Cipher** — automatic brute-force + fitness-scored candidates |
| 5 | **Analyze Vigenère Cipher** — Kasiski examination, IC by key length, key recovery |
| 6 | **File Encryption** — encrypt / decrypt whole text files |
| 7 | **Security Analysis** — why each cipher is weak, profile summaries |
| 8–9 | Help / Exit |

Two ways to run it:

- **Interactive mode** — pick options from a menu; every prompt is validated and invalid input never crashes the program.
- **CLI mode** — run a single operation in one command (see below).

Any analysis command accepts `--report` to save a text report under `reports/`.

---

## Getting Started

### Requirements

- Python **3.10+** (no external dependencies)

### Run

```bash
cd crypto_cipher_analyzer

# Interactive menu
python main.py

# Or a single command
python main.py caesar-encrypt --text "HELLO WORLD" --shift 3
```

### Command-line examples

```bash
# Caesar
python main.py caesar-encrypt  --text "HELLO WORLD" --shift 3
python main.py caesar-decrypt  --text "KHOOR ZRUOG" --shift 3
python main.py crack-caesar    --text "KHOOR ZRUOG"          # auto-break

# Vigenère
python main.py vigenere-encrypt --text "ATTACKATDAWN" --key LEMON
python main.py vigenere-decrypt --text "LXFOPVEFRNHR" --key LEMON
python main.py analyze-vigenere --text "<long ciphertext>"    # full cryptanalysis

# Statistics
python main.py frequency --text "KHOOR ZRUOG"
python main.py ic        --text "KHOOR ZRUOG"                 # Index of Coincidence
python main.py kasiski   --text "<long ciphertext>"           # repeated-sequence analysis
python main.py security                                        # cipher security profiles

# Files
python main.py file-caesar   --input notes.txt --shift 3
python main.py file-caesar   --input notes.txt --shift 3 --decrypt
python main.py file-vigenere --input notes.txt --key LEMON
```

All commands also support `--text`, `--input`, `--output`, `--shift`, `--key`, `--report`, and `--overwrite`. See `python main.py --help` for the full list.

---

## Project Structure

```
crypto_cipher_analyzer/
├── main.py                  # CLI + interactive menu entry point
├── ciphers/                 # Caesar & Vigenère implementations (from scratch)
├── analysis/                # Cryptanalysis: frequency, IC, Kasiski, crackers, security
├── file_operations/         # File encryption/decryption helpers
├── utils/                   # Banner, validators, text utilities, report generator
├── tests/                   # Unit tests (unittest, pytest-compatible)
├── sample_data/             # Sample plaintext/ciphertext files
├── docs/                    # COMMANDS.pdf, PROJECT_GUIDE.pdf
└── reports/                 # Generated analysis reports (--report)
report_assets/               # Screenshots, captures, and figures for the written report
tools/                       # Scripts used to build the report/presentation artifacts
```

---

## Running the Tests

From inside the `crypto_cipher_analyzer` directory:

```bash
# with unittest
python -m unittest discover tests

# or with pytest
python -m pytest tests
```

Tests cover the cipher implementations, validators, cryptanalysis modules, file operations, and the CLI.

---

## Cryptanalysis Techniques Used

- **Brute force + chi-squared fitness** — Caesar has only 26 keys; candidates are ranked by how English-like their letter distribution is.
- **Frequency analysis** — English letters are unevenly distributed (E, T, A dominate); ciphered text flattens or shifts this pattern.
- **Kasiski examination** — repeated ciphertext fragments reveal distances that are multiples of the Vigenère key length.
- **Index of Coincidence** — English prose sits near **0.0667**, random text near **0.0385**; IC per column confirms the key length.
- **Key recovery** — once the key length is known, each column is broken as an independent Caesar cipher.

---

## Documentation

- [`crypto_cipher_analyzer/docs/PROJECT_GUIDE.pdf`](crypto_cipher_analyzer/docs/PROJECT_GUIDE.pdf) — full project guide
- [`crypto_cipher_analyzer/docs/COMMANDS.pdf`](crypto_cipher_analyzer/docs/COMMANDS.pdf) — command reference
- [`Cryptographic_Cipher_Analyzer_Project_Report.pdf`](Cryptographic_Cipher_Analyzer_Project_Report.pdf) — written project report
- [`Cryptographic_Cipher_Analyzer_Presentation.pptx`](Cryptographic_Cipher_Analyzer_Presentation.pptx) — presentation slides
