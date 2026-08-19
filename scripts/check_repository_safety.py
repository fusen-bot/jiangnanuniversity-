#!/usr/bin/env python3
"""Fail CI when sensitive source artifacts or likely credentials enter the repository."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BLOCKED_ARTIFACTS = {
    ".csv",
    ".db",
    ".doc",
    ".docx",
    ".pdf",
    ".rar",
    ".sqlite",
    ".sqlite3",
    ".xls",
    ".xlsm",
    ".xlsx",
    ".zip",
}
TEXT_PATTERNS = {
    "private key": re.compile(r"BEGIN (?:RSA |EC )?PRIVATE KEY"),
    "OpenAI-style API key": re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    "GitHub token": re.compile(r"\bgh[opurs]_[A-Za-z0-9]{20,}\b"),
    "AWS access key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "Chinese resident ID": re.compile(r"(?<!\d)\d{17}[\dXx](?!\d)"),
}
SKIP_TEXT_SCAN = {"server/tests/test_security.py", "scripts/check_repository_safety.py"}


def candidate_files() -> list[Path]:
    output = subprocess.check_output(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        cwd=ROOT,
    )
    return [ROOT / item.decode() for item in output.split(b"\0") if item]


def main() -> int:
    findings: list[str] = []
    for path in candidate_files():
        if not path.is_file():
            continue
        relative = path.relative_to(ROOT).as_posix()
        if path.suffix.lower() in BLOCKED_ARTIFACTS:
            findings.append(f"blocked data artifact: {relative}")
            continue
        if relative in SKIP_TEXT_SCAN or path.stat().st_size > 5 * 1024 * 1024:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for label, pattern in TEXT_PATTERNS.items():
            if pattern.search(text):
                findings.append(f"{label}: {relative}")
    if findings:
        print("Repository safety check failed:")
        for finding in findings:
            print(f"- {finding}")
        return 1
    print("Repository safety check passed: no blocked source artifacts or secret patterns found.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
