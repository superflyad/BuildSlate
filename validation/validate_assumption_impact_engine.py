#!/usr/bin/env python3
"""Validate the Slate Pocket assumption impact engine artifacts."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = REPO_ROOT / "engineering" / "assumptions" / "assumption_registry.yaml"
ENGINE_PATH = REPO_ROOT / "engineering" / "assumptions" / "assumption_impact_engine.py"
GENERATOR_PATH = REPO_ROOT / "engineering" / "assumptions" / "generate_assumption_impact_report.py"
REPORT_PATH = REPO_ROOT / "reports" / "slate-pocket-assumption-impact-report.txt"

sys.path.insert(0, str(REPO_ROOT))

from engineering.assumptions.assumption_impact_engine import (  # noqa: E402
    CONFIDENCE_VALUES,
    MATURITY_VALUES,
    PROFILE_SCOPES,
    REQUIRED_ASSUMPTIONS,
    REQUIRED_FIELDS,
    build_impacts,
    load_registry,
    validate_registry,
)


def main() -> int:
    failures: list[str] = []

    for path, label in (
        (REGISTRY_PATH, "assumption registry"),
        (ENGINE_PATH, "assumption impact engine"),
        (GENERATOR_PATH, "assumption impact report generator"),
    ):
        if path.exists():
            print(f"PASS: {label} exists: {path.relative_to(REPO_ROOT)}")
        else:
            failures.append(f"{label} missing: {path.relative_to(REPO_ROOT)}")

    if not failures:
        try:
            registry = load_registry(REGISTRY_PATH)
            validate_registry(registry)
            print("PASS: assumption registry shape and enums are valid")
        except ValueError as exc:
            failures.append(str(exc))

    if not failures:
        assumptions = registry["assumptions"]
        missing = [assumption_id for assumption_id in REQUIRED_ASSUMPTIONS if assumption_id not in assumptions]
        if not missing:
            print("PASS: required assumptions exist")
        else:
            failures.append(f"required assumptions missing: {', '.join(missing)}")

        for assumption_id in REQUIRED_ASSUMPTIONS:
            entry = assumptions[assumption_id]
            missing_fields = [field for field in REQUIRED_FIELDS if field not in entry]
            if missing_fields:
                failures.append(f"{assumption_id} missing fields: {', '.join(missing_fields)}")
            if entry.get("confidence") not in CONFIDENCE_VALUES:
                failures.append(f"{assumption_id} has invalid confidence: {entry.get('confidence')}")
            if entry.get("maturity") not in MATURITY_VALUES:
                failures.append(f"{assumption_id} has invalid maturity: {entry.get('maturity')}")
            if entry.get("profile_scope") not in PROFILE_SCOPES:
                failures.append(f"{assumption_id} has invalid profile_scope: {entry.get('profile_scope')}")
        if not failures:
            print("PASS: required fields and enum values are present for required assumptions")

    if not failures:
        impacts = build_impacts(registry)
        if any(impact.fragility.value in {"CRITICAL", "HIGH"} for impact in impacts):
            print("PASS: impact scoring produces at least one CRITICAL or HIGH item")
        else:
            failures.append("impact scoring did not produce a CRITICAL or HIGH item")

    if not failures:
        result = subprocess.run(
            [sys.executable, str(GENERATOR_PATH)],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            print("PASS: assumption impact report generator runs")
        else:
            failures.append(f"generator exited with code {result.returncode}: {result.stderr.strip()}")

    if REPORT_PATH.exists():
        report = REPORT_PATH.read_text(encoding="utf-8")
        required_markers = (
            "Top fragile assumptions",
            "What breaks first",
            "Evidence required",
        )
        missing_markers = [marker for marker in required_markers if marker not in report]
        if not missing_markers:
            print("PASS: report contains required sections")
        else:
            failures.append(f"report missing required sections: {', '.join(missing_markers)}")
        if "CRITICAL" in report or "HIGH" in report:
            print("PASS: report contains at least one CRITICAL or HIGH item")
        else:
            failures.append("report does not contain a CRITICAL or HIGH item")
        if "static traceability layer" in report and "does not validate assumptions" in report:
            print("PASS: report contains static-traceability caveat")
        else:
            failures.append("report does not contain the static-traceability caveat")
    else:
        failures.append(f"report missing: {REPORT_PATH.relative_to(REPO_ROOT)}")

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1

    print("PASS: assumption impact engine validation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
