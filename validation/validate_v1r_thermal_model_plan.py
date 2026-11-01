#!/usr/bin/env python3
"""Validate the Slate Pocket v1R thermal model, test, and correlation plan."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = REPO_ROOT / "simulations" / "thermal" / "slate-pocket-v1r"
MODEL_PATH = PACKAGE_ROOT / "model" / "model.yaml"
TEST_MATRIX_PATH = PACKAGE_ROOT / "test-matrix.yaml"
CORRELATION_PATH = PACKAGE_ROOT / "correlation-plan.md"
GENERATOR_PATH = PACKAGE_ROOT / "generate_thermal_model_readiness_report.py"
REPORT_PATH = REPO_ROOT / "reports" / "slate-pocket-v1r-thermal-model-readiness.txt"


def _load(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as input_file:
        data = yaml.safe_load(input_file)
    if not isinstance(data, dict):
        raise ValueError(f"{path.relative_to(REPO_ROOT)} must contain a mapping")
    return data


def main() -> int:
    failures: list[str] = []
    for path in (MODEL_PATH, TEST_MATRIX_PATH, CORRELATION_PATH, GENERATOR_PATH):
        if path.exists():
            print(f"PASS: v1R thermal artifact exists: {path.relative_to(REPO_ROOT)}")
        else:
            failures.append(f"v1R thermal artifact missing: {path.relative_to(REPO_ROOT)}")

    if not failures:
        try:
            model = _load(MODEL_PATH)
            matrix = _load(TEST_MATRIX_PATH)
            if model["metadata"]["solver_status"] != "not_built":
                failures.append("thermal model must not imply a solver build exists")
            if len(model["heat_sources"]) < 6 or len(model["sensor_map"]) < 9:
                failures.append("thermal model lacks required source or sensor coverage")
            categories = {case["category"] for case in matrix["cases"].values()}
            required_categories = {"sustained", "peak", "hot_ambient", "handheld", "pocket", "bag", "charging_overlap"}
            if not required_categories.issubset(categories):
                failures.append("thermal test matrix lacks required operating-condition coverage")
            if matrix["cases"]["T06_pocket_fault_containment"]["state"] != "prohibited_until_controls_validated":
                failures.append("pocket high-power case must remain prohibited until controls are validated")
            if matrix["cases"]["T10_wireless_charge"]["charging"] != "disabled":
                failures.append("wireless charging must remain disabled for EVT0")
            if matrix["screening_limits"]["maximum_skin_c"] != 43.0:
                failures.append("locked 43 C skin screen changed unexpectedly")
        except (KeyError, TypeError, ValueError) as exc:
            failures.append(str(exc))
        else:
            if not failures:
                print("PASS: v1R thermal geometry, sensor map, cases, and safety posture are valid")

    if not failures:
        result = subprocess.run(
            [sys.executable, str(GENERATOR_PATH)], cwd=REPO_ROOT, capture_output=True, text=True, check=False
        )
        if result.returncode == 0:
            print("PASS: v1R thermal readiness report generator runs")
        else:
            failures.append(f"v1R thermal generator failed: {result.stderr.strip() or result.stdout.strip()}")

    if REPORT_PATH.exists():
        report = REPORT_PATH.read_text(encoding="utf-8")
        markers = (
            "solver status: not_built",
            "pocket sustained AI: PROHIBITED_UNTIL_CONTROLS_VALIDATED",
            "EVT0 wireless charging: DISABLED",
            "THERMAL_MODEL_DECISION: BLOCKED_ON_TRACEABLE_PROPERTIES_SOLVER_BUILD_AND_INSTRUMENTED_HARDWARE",
            "does not prove CFD/FEA completion",
        )
        missing = [marker for marker in markers if marker not in report]
        if missing:
            failures.append(f"v1R thermal report missing markers: {', '.join(missing)}")
        else:
            print("PASS: v1R thermal report preserves model status, prohibitions, decision, and caveat")
    else:
        failures.append(f"v1R thermal report missing: {REPORT_PATH.relative_to(REPO_ROOT)}")

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1
    print("PASS: v1R thermal model and test plan validation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
