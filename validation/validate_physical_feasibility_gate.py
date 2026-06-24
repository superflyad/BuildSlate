#!/usr/bin/env python3
"""Validate the Slate Pocket physical-feasibility gate report."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
GENERATOR_PATH = REPO_ROOT / "engineering" / "physical_feasibility" / "generate_physical_feasibility_report.py"
GATE_PATH = REPO_ROOT / "engineering" / "physical_feasibility" / "physical_feasibility_gate.py"
REPORT_PATH = REPO_ROOT / "reports" / "slate-pocket-physical-feasibility-gate.txt"

sys.path.insert(0, str(REPO_ROOT))

from engineering.physical_feasibility.physical_feasibility_gate import approved_decision_values  # noqa: E402


def main() -> int:
    failures: list[str] = []

    if GENERATOR_PATH.exists():
        print(f"PASS: generator exists: {GENERATOR_PATH.relative_to(REPO_ROOT)}")
    else:
        failures.append(f"generator missing: {GENERATOR_PATH.relative_to(REPO_ROOT)}")

    if GATE_PATH.exists():
        print(f"PASS: gate module exists: {GATE_PATH.relative_to(REPO_ROOT)}")
    else:
        failures.append(f"gate module missing: {GATE_PATH.relative_to(REPO_ROOT)}")

    if not failures:
        result = subprocess.run(
            [sys.executable, str(GENERATOR_PATH)],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            print("PASS: physical feasibility report generator runs")
        else:
            failures.append(f"generator exited with code {result.returncode}: {result.stderr.strip()}")

    if REPORT_PATH.exists():
        report = REPORT_PATH.read_text(encoding="utf-8")
        match = re.search(r"^\s*GATE_DECISION:\s*([A-Z_]+)\s*$", report, flags=re.MULTILINE)
        if match:
            decision = match.group(1)
            print(f"PASS: report contains gate decision: {decision}")
            approved = set(approved_decision_values())
            if decision in approved:
                print("PASS: gate decision is an approved enum value")
            else:
                failures.append(f"gate decision is not approved: {decision}")
        else:
            failures.append("report does not contain a GATE_DECISION line")
    else:
        failures.append(f"report missing: {REPORT_PATH.relative_to(REPO_ROOT)}")

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1

    print("PASS: physical feasibility gate validation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
