#!/usr/bin/env python3
"""Run the complete deterministic BuildSlate CI gate."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def run(command: list[str], label: str) -> None:
    print(f"\n=== {label} ===", flush=True)
    result = subprocess.run(command, cwd=REPO_ROOT, check=False)
    if result.returncode != 0:
        raise SystemExit(f"FAIL: {label} (exit {result.returncode})")


def main() -> int:
    npm = shutil.which("npm")
    if npm is None:
        raise SystemExit("FAIL: npm is required to validate the assembly viewer")
    run(
        [
            sys.executable,
            "-m",
            "compileall",
            "-q",
            "buildslate",
            "engineering",
            "validation",
            "manufacturing",
        ],
        "Python compilation",
    )
    run([sys.executable, "-m", "ruff", "check", "."], "Python static analysis")
    run(
        [
            sys.executable,
            "-m",
            "ruff",
            "format",
            "--check",
            "buildslate",
            "scripts/ci_validate.py",
            "validation/validate_repository.py",
        ],
        "Core Python formatting",
    )
    run(["git", "diff", "--check"], "Git whitespace check")
    run([sys.executable, "validation/run_all.py"], "Repository validation")
    run(
        [sys.executable, "-m", "buildslate.assembly", "--check"],
        "Assembly export currency",
    )
    run([npm, "ci", "--prefix", "viewer"], "Viewer dependency install")
    run([npm, "run", "format:check", "--prefix", "viewer"], "Viewer formatting")
    run([npm, "run", "check:model", "--prefix", "viewer"], "Viewer geometry load")
    run([npm, "run", "build", "--prefix", "viewer"], "Viewer build")
    run([sys.executable, "-m", "buildslate", "stale"], "Generated-output staleness")
    run(["git", "diff", "--exit-code"], "Deterministic tracked outputs")
    status = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=all"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if status.returncode != 0:
        raise SystemExit("FAIL: unable to inspect worktree")
    if status.stdout.strip():
        raise SystemExit("FAIL: CI left a dirty worktree:\n" + status.stdout)
    print("\nPASS: BuildSlate CI gate")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
