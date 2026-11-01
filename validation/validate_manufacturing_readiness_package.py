#!/usr/bin/env python3
"""Validate the Slate Pocket v1R DFM, pilot, quality, and manufacturing handoff."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
MFG_ROOT = REPO_ROOT / "manufacturing"
GENERATOR_PATH = MFG_ROOT / "generate_manufacturing_readiness_report.py"
REPORT_PATH = REPO_ROOT / "reports" / "slate-pocket-v1r-manufacturing-readiness.txt"


def _load(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as input_file:
        data = yaml.safe_load(input_file)
    if not isinstance(data, dict):
        raise ValueError(f"{path.relative_to(REPO_ROOT)} must contain a mapping")
    return data


def main() -> int:
    failures: list[str] = []
    required = (
        MFG_ROOT / "dfm-review.md",
        MFG_ROOT / "assembly-plan.md",
        MFG_ROOT / "pilot-build-plan.yaml",
        MFG_ROOT / "defect-taxonomy.yaml",
        MFG_ROOT / "reliability-plan.yaml",
        MFG_ROOT / "compliance-pretest-plan.yaml",
        MFG_ROOT / "serviceability-plan.md",
        MFG_ROOT / "quality-gate.md",
        MFG_ROOT / "supplier-dfm-response.yaml",
        MFG_ROOT / "pilot-results" / "README.md",
        GENERATOR_PATH,
    )
    for path in required:
        if path.exists():
            print(f"PASS: manufacturing artifact exists: {path.relative_to(REPO_ROOT)}")
        else:
            failures.append(f"manufacturing artifact missing: {path.relative_to(REPO_ROOT)}")

    if not failures:
        try:
            pilot = _load(MFG_ROOT / "pilot-build-plan.yaml")
            defects = _load(MFG_ROOT / "defect-taxonomy.yaml")
            response = _load(MFG_ROOT / "supplier-dfm-response.yaml")
            if pilot["metadata"]["status"] != "proposed_not_authorized":
                failures.append("pilot plan must remain proposed and unauthorized")
            if pilot["lot"]["proposed_input_units"] != 100:
                failures.append("pilot plan must preserve its declared 100-unit denominator")
            gates = pilot["provisional_yield_gates"]
            if gates["critical_safety_or_regulatory_defects"]["maximum_count"] != 0:
                failures.append("pilot gate must allow zero critical safety/regulatory defects")
            if gates["first_pass_yield_percent"]["minimum"] != 90.0 or gates["final_yield_percent"]["minimum"] != 95.0:
                failures.append("pilot yield thresholds changed unexpectedly")
            if gates["traceability_completeness_percent"]["minimum"] != 100.0:
                failures.append("pilot traceability must be complete")
            if len(defects["codes"]) < 10 or len(defects["required_record_fields"]) < 10:
                failures.append("defect taxonomy lacks code or record-field coverage")
            if response["review"]["status"] != "template_not_completed":
                failures.append("supplier DFM template must not imply a completed review")
            real_results = [
                path
                for path in (MFG_ROOT / "pilot-results").rglob("*")
                if path.is_file() and path.name.lower() != "readme.md"
            ]
            if real_results:
                failures.append("manufacturing package contains unvalidated files presented as pilot results")
        except (KeyError, TypeError, ValueError) as exc:
            failures.append(str(exc))
        else:
            if not failures:
                print("PASS: pilot authorization, lot, yield gates, traceability, defect taxonomy, supplier template, and empty evidence state are valid")

    if not failures:
        result = subprocess.run(
            [sys.executable, str(GENERATOR_PATH)], cwd=REPO_ROOT, capture_output=True, text=True, check=False
        )
        if result.returncode == 0:
            print("PASS: manufacturing readiness report generator runs")
        else:
            failures.append(f"manufacturing generator failed: {result.stderr.strip() or result.stdout.strip()}")

    if REPORT_PATH.exists():
        report = REPORT_PATH.read_text(encoding="utf-8")
        markers = (
            "supplier DFM response status: template_not_completed",
            "pilot authorized: no",
            "pilot result files excluding instructions: 0",
            "measured yield: no evidence",
            "MANUFACTURING_GATE: BLOCKED_ON_VERIFIED_EVT0_SUPPLIER_DFM_RELEASED_PROCESS_AND_PILOT_EVIDENCE",
            "does not prove manufacturability",
        )
        missing = [marker for marker in markers if marker not in report]
        if missing:
            failures.append(f"manufacturing report missing markers: {', '.join(missing)}")
        else:
            print("PASS: manufacturing report preserves supplier, authorization, evidence, gate, and caveat states")
    else:
        failures.append(f"manufacturing report missing: {REPORT_PATH.relative_to(REPO_ROOT)}")

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1
    print("PASS: manufacturing readiness package validation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
