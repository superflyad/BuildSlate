"""Lint maintained Markdown; generated reports and archived snapshots are excluded."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_PREFIXES = ("reports/", "docs/archive/")
MARKDOWNLINT_VERSION = "0.23.2"


def main() -> int:
    npx = shutil.which("npx")
    if npx is None:
        raise SystemExit("npx is required for documentation linting")
    tracked = subprocess.run(
        ["git", "ls-files", "*.md"],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    files = [
        path
        for path in tracked.stdout.splitlines()
        if not path.startswith(EXCLUDED_PREFIXES)
    ]
    if not files:
        raise SystemExit("no maintained Markdown files found")
    result = subprocess.run(
        [npx, "--yes", f"markdownlint-cli2@{MARKDOWNLINT_VERSION}", *files],
        cwd=REPO_ROOT,
        check=False,
    )
    if result.returncode == 0:
        print(f"PASS: {len(files)} maintained Markdown files")
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
