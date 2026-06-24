#!/usr/bin/env python3
"""Fail if unresolved Git merge conflict markers are present in repository text files."""

from __future__ import annotations

import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CONFLICT_MARKERS = ("<<<<<<<", "=======", ">>>>>>>")
SKIP_SUFFIXES = {
    ".gif",
    ".ico",
    ".jpg",
    ".jpeg",
    ".pdf",
    ".png",
    ".webp",
}


def repository_files() -> list[Path]:
    """Return tracked and untracked non-ignored repository files."""
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return [REPO_ROOT / line for line in result.stdout.splitlines() if line]


def marker_at_line(line: str) -> str | None:
    """Return the conflict marker prefix when a line is an unresolved marker."""
    stripped = line.strip()
    for marker in CONFLICT_MARKERS:
        if stripped.startswith(marker) and (len(stripped) == len(marker) or stripped[len(marker)].isspace()):
            return marker
    return None


def main() -> int:
    findings: list[str] = []
    for path in repository_files():
        if path.suffix.lower() in SKIP_SUFFIXES:
            continue
        try:
            contents = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for line_number, line in enumerate(contents.splitlines(), start=1):
            marker = marker_at_line(line)
            if marker is not None:
                findings.append(f"{path.relative_to(REPO_ROOT)}:{line_number}: {marker}")

    if findings:
        print("FAIL: unresolved merge conflict markers found")
        for finding in findings:
            print(f"  {finding}")
        return 1

    print("PASS: no unresolved merge conflict markers found in repository text files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
