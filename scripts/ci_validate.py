#!/usr/bin/env python3
"""Run the complete deterministic BuildSlate CI gate."""

from __future__ import annotations

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
    run([sys.executable, "-m", "compileall", "-q", "buildslate", "engineering", "validation", "manufacturing"], "Python compilation")
    run(["git", "diff", "--check"], "Git whitespace check")
    run([sys.executable, "validation/run_all.py"], "Repository validation")
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

