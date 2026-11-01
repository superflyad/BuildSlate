#!/usr/bin/env python3
"""Validate CI wiring, architecture, operator workflows, examples, and handoff docs."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def passed(message: str) -> None:
    print(f"PASS: {message}")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)
    passed(message)


def main() -> int:
    required = (
        "scripts/ci_validate.py",
        ".github/workflows/validation.yml",
        "docs/engineering/platform_architecture.md",
        "docs/engineering/operator_workflows.md",
        "docs/engineering/platform_handoff.md",
        "examples/README.md",
    )
    for relative in required:
        require((REPO_ROOT / relative).is_file(), f"CI/handoff artifact exists: {relative}")

    ci_script = (REPO_ROOT / "scripts/ci_validate.py").read_text(encoding="utf-8")
    for marker in ("compileall", "git", "diff", "validation/run_all.py", "buildslate", "stale", "status", "--porcelain"):
        require(marker in ci_script, f"CI entry point includes: {marker}")

    workflow = (REPO_ROOT / ".github/workflows/validation.yml").read_text(encoding="utf-8")
    for marker in ("push:", "pull_request:", "actions/checkout@v4", "actions/setup-python@v5", "requirements.txt", "scripts/ci_validate.py"):
        require(marker in workflow, f"GitHub workflow includes: {marker}")

    architecture = (REPO_ROOT / "docs/engineering/platform_architecture.md").read_text(encoding="utf-8")
    for marker in ("Authority layers", "Controlled evidence stores", "Resolution and contracts", "Deterministic generation", "Failure behavior"):
        require(marker in architecture, f"architecture documentation covers: {marker}")

    operations = (REPO_ROOT / "docs/engineering/operator_workflows.md").read_text(encoding="utf-8")
    for marker in ("Supplier response", "EVT0 run bundle", "Pilot bundle", "Recovery from an error", "never rewrite it into a pass"):
        require(marker in operations, f"operator workflow covers: {marker}")

    handoff = (REPO_ROOT / "docs/engineering/platform_handoff.md").read_text(encoding="utf-8")
    for marker in ("Protected baseline", "Empty evidence stores", "External boundary", "Change handoff checklist", "128 GB", "30 W"):
        require(marker in handoff, f"handoff documents: {marker}")

    help_result = subprocess.run(
        [sys.executable, "-m", "buildslate", "--help"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    for command in ("suppliers", "configuration", "contracts", "evt0", "manufacturing", "dashboard", "migrations", "impact", "regenerate"):
        require(help_result.returncode == 0 and command in help_result.stdout, f"CLI help exposes workflow: {command}")
    passed("CI and operator handoff validation")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AssertionError, OSError, ValueError, KeyError, TypeError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)

