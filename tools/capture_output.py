#!/usr/bin/env python3
"""Capture the real console output of the Cipher Analyzer tool.

Every command used in the project report is executed here, exactly as a user
would run it, and the combined stdout/stderr is stored under
``report_assets/captures``.  The screenshots in the report are rendered from
these files, so the figures always match the actual behaviour of the tool.

Run from the repository root::

    python tools/capture_output.py
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
APP_DIR = PROJECT / "crypto_cipher_analyzer"
CAPTURE_DIR = PROJECT / "report_assets" / "captures"

#: Files produced by earlier runs that must not exist when the session starts,
#: otherwise the tool would (correctly) refuse to overwrite them.
ARTEFACTS = [
    APP_DIR / "sample_data" / "caesar_sample_out.txt",
    APP_DIR / "sample_data" / "message_vigenere.txt",
]


def clean_artefacts() -> None:
    """Remove previously generated output files so every run is repeatable."""
    for path in ARTEFACTS:
        path.unlink(missing_ok=True)
    reports = APP_DIR / "reports"
    if reports.exists():
        for path in reports.glob("*.txt"):
            path.unlink()

#: Each case is a shell session: one or more commands executed in order.
CASES: list[dict] = [
    {
        "name": "01_environment",
        "title": "Windows PowerShell - project environment",
        "cwd": str(PROJECT),
        "commands": [
            {"display": "python --version", "argv": ["python", "--version"]},
            {
                "display": "python -c \"import sys; print('Environment:', sys.executable); print('Dependencies: standard library only')\"",
                "argv": [
                    "python", "-c",
                    "import sys; print('Environment:', sys.executable); "
                    "print('Dependencies: standard library only')",
                ],
            },
        ],
    },
    {
        "name": "02_structure",
        "title": "Windows PowerShell - project structure",
        "cwd": str(APP_DIR),
        "commands": [
            {
                "display": "ls -1",
                "argv": ["ls", "-1"],
                "shell": True,
            },
            {
                "display": "ls -1 analysis ciphers file_operations utils",
                "argv": ["ls", "-1", "analysis", "ciphers", "file_operations", "utils"],
                "shell": True,
            },
        ],
    },
    {
        "name": "03_launch",
        "title": "Command Prompt - python main.py",
        "cwd": str(APP_DIR),
        "stdin": "9\n",
        "commands": [{"display": "python main.py", "argv": ["python", "main.py"]}],
    },
    {
        "name": "04_caesar_cli",
        "title": "Command Prompt - Caesar cipher",
        "cwd": str(APP_DIR),
        "commands": [
            {
                "display": 'python main.py caesar-encrypt --text "ATTACK AT DAWN" --shift 3',
                "argv": ["python", "main.py", "caesar-encrypt", "--text", "ATTACK AT DAWN", "--shift", "3"],
            },
            {
                "display": 'python main.py caesar-decrypt --text "DWWDFN DW GDZQ" --shift 3',
                "argv": ["python", "main.py", "caesar-decrypt", "--text", "DWWDFN DW GDZQ", "--shift", "3"],
            },
        ],
    },
    {
        "name": "05_vigenere_cli",
        "title": "Command Prompt - Vigenere cipher",
        "cwd": str(APP_DIR),
        "commands": [
            {
                "display": 'python main.py vigenere-encrypt --text "ATTACKATDAWN" --key LEMON',
                "argv": ["python", "main.py", "vigenere-encrypt", "--text", "ATTACKATDAWN", "--key", "LEMON"],
            },
            {
                "display": 'python main.py vigenere-decrypt --text "LXFOPVEFRNHR" --key LEMON',
                "argv": ["python", "main.py", "vigenere-decrypt", "--text", "LXFOPVEFRNHR", "--key", "LEMON"],
            },
        ],
    },
    {
        "name": "06_interactive_caesar",
        "title": "Command Prompt - python main.py (interactive menu)",
        "cwd": str(APP_DIR),
        # menu: 1 Caesar -> 1 Encrypt -> 1 Type the text -> HELLO WORLD -> shift 3 -> no report -> exit
        "stdin": "1\n1\n1\nHELLO WORLD\n3\nn\n9\n",
        "commands": [{"display": "python main.py", "argv": ["python", "main.py"]}],
    },
    {
        "name": "07_frequency",
        "title": "Command Prompt - frequency analysis",
        "cwd": str(APP_DIR),
        "commands": [
            {
                "display": "python main.py frequency --input sample_data/caesar_sample.txt",
                "argv": ["python", "main.py", "frequency", "--input", "sample_data/caesar_sample.txt"],
            }
        ],
    },
    {
        "name": "08_crack_caesar",
        "title": "Command Prompt - breaking the Caesar cipher",
        "cwd": str(APP_DIR),
        "commands": [
            {
                "display": "python main.py crack-caesar --input sample_data/caesar_sample.txt --top 5",
                "argv": [
                    "python", "main.py", "crack-caesar",
                    "--input", "sample_data/caesar_sample.txt", "--top", "5",
                ],
            }
        ],
    },
    {
        "name": "09_ic",
        "title": "Command Prompt - index of coincidence",
        "cwd": str(APP_DIR),
        "commands": [
            {
                "display": "python main.py ic --input sample_data/caesar_sample.txt --max-key-length 12",
                "argv": [
                    "python", "main.py", "ic",
                    "--input", "sample_data/caesar_sample.txt", "--max-key-length", "12",
                ],
            }
        ],
    },
    {
        "name": "10_kasiski",
        "title": "Command Prompt - Kasiski examination",
        "cwd": str(APP_DIR),
        "commands": [
            {
                "display": "python main.py kasiski --input sample_data/vigenere_sample.txt",
                "argv": ["python", "main.py", "kasiski", "--input", "sample_data/vigenere_sample.txt"],
            }
        ],
    },
    {
        "name": "11_vigenere_analysis",
        "title": "Command Prompt - full Vigenere cryptanalysis",
        "cwd": str(APP_DIR),
        "commands": [
            {
                "display": "python main.py analyze-vigenere --input sample_data/vigenere_sample.txt",
                "argv": [
                    "python", "main.py", "analyze-vigenere",
                    "--input", "sample_data/vigenere_sample.txt",
                ],
            }
        ],
    },
    {
        "name": "12_file_decrypt",
        "title": "Command Prompt - file decryption",
        "cwd": str(APP_DIR),
        "commands": [
            {
                "display": "python main.py file-caesar --input sample_data/caesar_sample.txt --shift 3 --decrypt",
                "argv": [
                    "python", "main.py", "file-caesar",
                    "--input", "sample_data/caesar_sample.txt", "--shift", "3", "--decrypt",
                ],
            },
            {
                "display": "head -c 320 sample_data/caesar_sample_out.txt",
                "argv": ["head", "-c", "320", "sample_data/caesar_sample_out.txt"],
                "shell": True,
            },
        ],
    },
    {
        "name": "13_file_encrypt",
        "title": "Command Prompt - file encryption",
        "cwd": str(APP_DIR),
        "commands": [
            {
                "display": "python main.py file-vigenere --input sample_data/caesar_sample_out.txt --key LEMON --output sample_data/message_vigenere.txt",
                "argv": [
                    "python", "main.py", "file-vigenere",
                    "--input", "sample_data/caesar_sample_out.txt",
                    "--key", "LEMON",
                    "--output", "sample_data/message_vigenere.txt",
                ],
            },
            {
                "display": "head -c 240 sample_data/message_vigenere.txt",
                "argv": ["head", "-c", "240", "sample_data/message_vigenere.txt"],
                "shell": True,
            },
        ],
    },
    {
        "name": "14_security_caesar",
        "title": "Command Prompt - security assessment (Caesar)",
        "cwd": str(APP_DIR),
        "commands": [
            {
                "display": "python main.py security --cipher caesar",
                "argv": ["python", "main.py", "security", "--cipher", "caesar"],
            }
        ],
    },
    {
        "name": "15_security_vigenere",
        "title": "Command Prompt - security assessment (Vigenere)",
        "cwd": str(APP_DIR),
        "commands": [
            {
                "display": "python main.py security --cipher vigenere",
                "argv": ["python", "main.py", "security", "--cipher", "vigenere"],
            }
        ],
    },
    {
        "name": "16_report_file",
        "title": "Command Prompt - saving an analysis report",
        "cwd": str(APP_DIR),
        "commands": [
            {
                "display": "python main.py crack-caesar --input sample_data/caesar_sample.txt --report",
                "argv": [
                    "python", "main.py", "crack-caesar",
                    "--input", "sample_data/caesar_sample.txt", "--report",
                ],
            },
            {
                "display": "ls -1 reports",
                "argv": ["ls", "-1", "reports"],
                "shell": True,
            },
        ],
    },
    {
        "name": "17_report_content",
        "title": "Command Prompt - generated report contents",
        "cwd": str(APP_DIR),
        "commands": [
            {
                "display": "cat $(ls -t reports/*.txt | head -1)   # newest generated report",
                "argv": ["bash", "-lc", "cat $(ls -t reports/*.txt | head -1)"],
                "shell": True,
            }
        ],
    },
    {
        "name": "18_test_suite",
        "title": "Command Prompt - automated test suite",
        "cwd": str(APP_DIR),
        "commands": [
            {
                "display": "python -m unittest discover -s tests -v",
                "argv": ["python", "-m", "unittest", "discover", "-s", "tests", "-v"],
            }
        ],
    },
]


def clean(text: str) -> str:
    """Normalise line endings and trim trailing whitespace-only lines."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.rstrip() for line in text.split("\n")]
    while lines and not lines[-1]:
        lines.pop()
    return "\n".join(lines)


def run_case(case: dict) -> list[dict]:
    """Execute every command of *case* and return the recorded sessions."""
    env = dict(os.environ, FORCE_COLOR="1", PYTHONIOENCODING="utf-8")
    recorded: list[dict] = []
    stdin_text = case.get("stdin")
    for index, command in enumerate(case["commands"]):
        cwd = command.get("cwd", case["cwd"])
        result = subprocess.run(
            command["argv"],
            cwd=cwd,
            shell=bool(command.get("shell")),
            input=stdin_text if index == 0 else None,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
        )
        output = clean(result.stdout) + ("\n" + clean(result.stderr) if result.stderr.strip() else "")
        recorded.append({"display": command["display"], "output": output.strip("\n")})
    return recorded


def main() -> int:
    CAPTURE_DIR.mkdir(parents=True, exist_ok=True)
    clean_artefacts()
    manifest: list[dict] = []
    for case in CASES:
        try:
            sessions = run_case(case)
        except Exception as error:  # noqa: BLE001 - report and keep going
            print(f"!! {case['name']} failed: {error}", file=sys.stderr)
            continue

        payload = {"name": case["name"], "title": case["title"], "sessions": sessions}
        (CAPTURE_DIR / f"{case['name']}.json").write_text(
            json.dumps(payload, indent=2), encoding="utf-8"
        )

        joined = "\n\n".join(
            f"$ {session['display']}\n{session['output']}" for session in sessions
        )
        (CAPTURE_DIR / f"{case['name']}.txt").write_text(joined + "\n", encoding="utf-8")

        width = max((len(line) for line in joined.splitlines()), default=0)
        manifest.append(
            {
                "name": case["name"],
                "title": case["title"],
                "lines": len(joined.splitlines()),
                "max_width": width,
            }
        )
        print(f"{case['name']:<22} lines={len(joined.splitlines()):>4}  max_width={width:>3}")

    (CAPTURE_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"\nCaptured {len(manifest)} sessions into {CAPTURE_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
