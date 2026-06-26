#!/usr/bin/env python3
"""Validate Slate Pocket v1R thermal consequence screening artifacts."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = REPO_ROOT / "engineering" / "thermal_consequence" / "thermal_consequence_model.py"
GENERATOR_PATH = REPO_ROOT / "engineering" / "thermal_consequence" / "generate_thermal_consequence_report.py"
REPORT_PATH = REPO_ROOT / "reports" / "slate-pocket-v1r-thermal-consequence.txt"

sys.path.insert(0, str(REPO_ROOT))

from engineering.thermal_consequence.thermal_consequence_model import approved_decision_values  # noqa: E402


def main() -> int:
    failures: list[str] = []

    for path, label in (
        (MODEL_PATH, "thermal consequence model"),
        (GENERATOR_PATH, "thermal consequence report generator"),
    ):
        if path.exists():
            print(f"PASS: {label} exists: {path.relative_to(REPO_ROOT)}")
        else:
            failures.append(f"{label} missing: {path.relative_to(REPO_ROOT)}")

    if not failures:
        result = subprocess.run(
            [sys.executable, str(GENERATOR_PATH)],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            print("PASS: thermal consequence report generator runs")
        else:
            failures.append(f"generator exited with code {result.returncode}: {result.stderr.strip()}")

    if REPORT_PATH.exists():
        report = REPORT_PATH.read_text(encoding="utf-8")
        decision_pattern = r"THERMAL_DECISION:\s+(" + "|".join(approved_decision_values()) + r")\b"
        if re.search(decision_pattern, report):
            print("PASS: report contains one approved thermal decision enum")
        else:
            failures.append("report does not contain an approved thermal decision enum")
        if "slate-pocket-v1" in report and "slate-pocket-v1r" in report:
            print("PASS: report comparison includes both v1 and v1R")
        else:
            failures.append("report comparison does not include both slate-pocket-v1 and slate-pocket-v1r")
        if "This is thermal consequence screening only" in report and "does not claim thermal validation" in report:
            print("PASS: report contains thermal screening caveat")
        else:
            failures.append("report does not contain the explicit thermal screening caveat")
        if all(
            required in report
            for required in (
                "thermal module CAD",
                "TIM selection",
                "SoC power telemetry",
                "skin thermocouple map",
                "CFD or FEA model",
            )
        ):
            print("PASS: report lists required evidence before thermal validation")
        else:
            failures.append("report is missing required evidence before thermal validation")
    else:
        failures.append(f"report missing: {REPORT_PATH.relative_to(REPO_ROOT)}")

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1

    print("PASS: thermal consequence screening validation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
