#!/usr/bin/env python3
"""Validate Slate Pocket engineering risk register artifacts."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = REPO_ROOT / "engineering" / "risks" / "risk_register.yaml"
ENGINE_PATH = REPO_ROOT / "engineering" / "risks" / "risk_engine.py"
GENERATOR_PATH = REPO_ROOT / "engineering" / "risks" / "generate_risk_report.py"
REPORT_PATH = REPO_ROOT / "reports" / "slate-pocket-risk-register.txt"

sys.path.insert(0, str(REPO_ROOT))

from engineering.risks.risk_engine import (  # noqa: E402
    IMPACT_VALUES,
    LIKELIHOOD_VALUES,
    MATURITY_VALUES,
    PROFILE_SCOPES,
    REQUIRED_FIELDS,
    REQUIRED_RISKS,
    STATUS_VALUES,
    build_risks,
    load_registry,
    validate_registry,
)


def main() -> int:
    failures: list[str] = []

    for path, label in (
        (REGISTRY_PATH, "risk register"),
        (ENGINE_PATH, "risk engine"),
        (GENERATOR_PATH, "risk report generator"),
    ):
        if path.exists():
            print(f"PASS: {label} exists: {path.relative_to(REPO_ROOT)}")
        else:
            failures.append(f"{label} missing: {path.relative_to(REPO_ROOT)}")

    if not failures:
        try:
            registry = load_registry(REGISTRY_PATH)
            validate_registry(registry)
            print("PASS: risk register shape and enums are valid")
        except ValueError as exc:
            failures.append(str(exc))

    if not failures:
        risks = registry["risks"]
        missing = [risk_id for risk_id in REQUIRED_RISKS if risk_id not in risks]
        if not missing:
            print("PASS: required risks exist")
        else:
            failures.append(f"required risks missing: {', '.join(missing)}")

        for risk_id in REQUIRED_RISKS:
            entry = risks[risk_id]
            missing_fields = [field for field in REQUIRED_FIELDS if field not in entry]
            if missing_fields:
                failures.append(f"{risk_id} missing fields: {', '.join(missing_fields)}")
            if entry.get("profile_scope") not in PROFILE_SCOPES:
                failures.append(f"{risk_id} has invalid profile_scope: {entry.get('profile_scope')}")
            if entry.get("likelihood") not in LIKELIHOOD_VALUES:
                failures.append(f"{risk_id} has invalid likelihood: {entry.get('likelihood')}")
            if entry.get("impact") not in IMPACT_VALUES:
                failures.append(f"{risk_id} has invalid impact: {entry.get('impact')}")
            if entry.get("maturity") not in MATURITY_VALUES:
                failures.append(f"{risk_id} has invalid maturity: {entry.get('maturity')}")
            if entry.get("status") not in STATUS_VALUES:
                failures.append(f"{risk_id} has invalid status: {entry.get('status')}")
        if not failures:
            print("PASS: required fields and enum values are present for required risks")

    if not failures:
        scored_risks = build_risks(registry)
        if any(risk.severity.value in {"HIGH", "CRITICAL"} for risk in scored_risks):
            print("PASS: risk scoring produces at least one HIGH or CRITICAL risk")
        else:
            failures.append("risk scoring did not produce a HIGH or CRITICAL risk")

    if not failures:
        result = subprocess.run(
            [sys.executable, str(GENERATOR_PATH)],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            print("PASS: risk report generator runs")
        else:
            failures.append(f"generator exited with code {result.returncode}: {result.stderr.strip()}")

    if REPORT_PATH.exists():
        report = REPORT_PATH.read_text(encoding="utf-8")
        required_markers = (
            "Executive risk summary",
            "Top 10 risks",
            "Blocked/critical risks",
            "Evidence required",
            "screening-level risk register, not formal FMEA",
        )
        missing_markers = [marker for marker in required_markers if marker not in report]
        if not missing_markers:
            print("PASS: report contains required sections and caveat")
        else:
            failures.append(f"report missing required sections: {', '.join(missing_markers)}")
        if "HIGH" in report or "CRITICAL" in report:
            print("PASS: report contains at least one HIGH or CRITICAL risk")
        else:
            failures.append("report does not contain a HIGH or CRITICAL risk")
    else:
        failures.append(f"report missing: {REPORT_PATH.relative_to(REPO_ROOT)}")

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1

    print("PASS: engineering risk register validation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
