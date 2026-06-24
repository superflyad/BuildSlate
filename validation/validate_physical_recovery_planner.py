#!/usr/bin/env python3
"""Validate the Slate Pocket physical recovery planner."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCENARIO_PATH = REPO_ROOT / "engineering" / "recovery" / "recovery_scenarios.yaml"
PLANNER_PATH = REPO_ROOT / "engineering" / "recovery" / "physical_recovery_planner.py"
GENERATOR_PATH = REPO_ROOT / "engineering" / "recovery" / "generate_physical_recovery_report.py"
REPORT_PATH = REPO_ROOT / "reports" / "slate-pocket-physical-recovery-plan.txt"

sys.path.insert(0, str(REPO_ROOT))

from engineering.recovery.physical_recovery_planner import (  # noqa: E402
    load_scenarios,
    validate_scenario_registry,
)


def main() -> int:
    failures: list[str] = []

    for path, label in (
        (SCENARIO_PATH, "scenario registry"),
        (PLANNER_PATH, "planner module"),
        (GENERATOR_PATH, "report generator"),
    ):
        if path.exists():
            print(f"PASS: {label} exists: {path.relative_to(REPO_ROOT)}")
        else:
            failures.append(f"{label} missing: {path.relative_to(REPO_ROOT)}")

    if not failures:
        try:
            validate_scenario_registry(SCENARIO_PATH)
            print("PASS: recovery scenario registry schema and enums are valid")
        except ValueError as exc:
            failures.append(str(exc))

    if not failures:
        scenarios = load_scenarios(SCENARIO_PATH)
        if len(scenarios) >= 12:
            print(f"PASS: recovery scenario count: {len(scenarios)}")
        else:
            failures.append(f"expected at least 12 recovery scenarios, found {len(scenarios)}")

    if not failures:
        result = subprocess.run(
            [sys.executable, str(GENERATOR_PATH)],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            print("PASS: physical recovery report generator runs")
        else:
            failures.append(f"generator exited with code {result.returncode}: {result.stderr.strip()}")

    if REPORT_PATH.exists():
        report = REPORT_PATH.read_text(encoding="utf-8")
        if re.search(r"Recommended recovery path:\n\s+status:\s+(SUFFICIENT|INSUFFICIENT)", report):
            print("PASS: recovery report contains a recommendation status")
        else:
            failures.append("recovery report does not contain a recommendation status")
        if "screening-level tradeoffs, not validated design changes" in report:
            print("PASS: recovery report contains screening caveat")
        else:
            failures.append("recovery report does not contain the explicit screening caveat")
    else:
        failures.append(f"report missing: {REPORT_PATH.relative_to(REPO_ROOT)}")

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1

    print("PASS: physical recovery planner validation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
