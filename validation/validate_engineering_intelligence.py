#!/usr/bin/env python3
"""Validate the Slate Pocket v1R engineering intelligence report."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
GENERATOR_PATH = REPO_ROOT / "engineering" / "intelligence" / "generate_engineering_intelligence_report.py"
REPORT_PATH = REPO_ROOT / "reports" / "slate-pocket-v1r-engineering-intelligence.txt"


def main() -> int:
    failures: list[str] = []

    if GENERATOR_PATH.exists():
        print(f"PASS: engineering intelligence report generator exists: {GENERATOR_PATH.relative_to(REPO_ROOT)}")
    else:
        failures.append(f"generator missing: {GENERATOR_PATH.relative_to(REPO_ROOT)}")

    if not failures:
        result = subprocess.run(
            [sys.executable, str(GENERATOR_PATH)],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            print("PASS: engineering intelligence report generator runs")
        else:
            failures.append(f"generator exited with code {result.returncode}: {result.stderr.strip()}")

    if REPORT_PATH.exists():
        report = REPORT_PATH.read_text(encoding="utf-8")
        required_markers = (
            "What changed",
            "Why it changed",
            "Decision trace",
            "Fragile assumptions",
            "Evidence required",
        )
        missing_markers = [marker for marker in required_markers if marker not in report]
        if not missing_markers:
            print("PASS: report contains required intelligence sections")
        else:
            failures.append(f"report missing required sections: {', '.join(missing_markers)}")

        if "slate-pocket-v1" in report and "slate-pocket-v1r" in report:
            print("PASS: report mentions both slate-pocket-v1 and slate-pocket-v1r")
        else:
            failures.append("report does not mention both slate-pocket-v1 and slate-pocket-v1r")

        if "not validated engineering proof" in report and "does not claim manufacturability" in report:
            print("PASS: report contains explicit non-validation caveat")
        else:
            failures.append("report does not contain the explicit non-validation caveat")

        required_assumptions = (
            "battery energy density",
            "reduced battery volume",
            "28 W sustained compute",
            "45 W peak compute",
            "thermal module effectiveness",
            "43°C max skin target",
            "512 GB memory packaging",
            "4 TB storage packaging",
        )
        missing_assumptions = [assumption for assumption in required_assumptions if assumption not in report]
        if not missing_assumptions:
            print("PASS: report lists required fragile assumptions")
        else:
            failures.append(f"report missing fragile assumptions: {', '.join(missing_assumptions)}")

        required_evidence = (
            "battery cell datasheet",
            "CAD stackup",
            "thermal module CAD",
            "SoC package spec",
            "sustained power telemetry",
            "thermocouple map",
            "supplier DFM review",
        )
        missing_evidence = [evidence for evidence in required_evidence if evidence not in report]
        if not missing_evidence:
            print("PASS: report lists required next evidence")
        else:
            failures.append(f"report missing required evidence: {', '.join(missing_evidence)}")
    else:
        failures.append(f"report missing: {REPORT_PATH.relative_to(REPO_ROOT)}")

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1

    print("PASS: engineering intelligence validation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
