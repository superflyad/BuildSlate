#!/usr/bin/env python3
"""Validate the Slate Pocket v1R EVT0 execution package and evidence posture."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
EVT_ROOT = REPO_ROOT / "validation" / "evt0"
REPORT_PATH = REPO_ROOT / "reports" / "slate-pocket-v1r-evt0-gate.txt"
GENERATOR_PATH = EVT_ROOT / "generate_evt0_gate_report.py"


def _load(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as input_file:
        data = yaml.safe_load(input_file)
    if not isinstance(data, dict):
        raise ValueError(f"{path.relative_to(REPO_ROOT)} must contain a mapping")
    return data


def main() -> int:
    failures: list[str] = []
    required_paths = (
        EVT_ROOT / "README.md",
        EVT_ROOT / "evt0-spec.yaml",
        EVT_ROOT / "bom-strategy.yaml",
        EVT_ROOT / "instrumentation.yaml",
        EVT_ROOT / "workloads.yaml",
        EVT_ROOT / "test-matrix.yaml",
        EVT_ROOT / "build-traveler.md",
        EVT_ROOT / "model-correlation.md",
        EVT_ROOT / "schemas" / "run-manifest.schema.yaml",
        EVT_ROOT / "schemas" / "test-result.schema.yaml",
        EVT_ROOT / "test-results" / "README.md",
        GENERATOR_PATH,
    )
    for path in required_paths:
        if path.exists():
            print(f"PASS: EVT0 artifact exists: {path.relative_to(REPO_ROOT)}")
        else:
            failures.append(f"EVT0 artifact missing: {path.relative_to(REPO_ROOT)}")

    if not failures:
        try:
            spec = _load(EVT_ROOT / "evt0-spec.yaml")
            bom = _load(EVT_ROOT / "bom-strategy.yaml")
            instrumentation = _load(EVT_ROOT / "instrumentation.yaml")
            workloads = _load(EVT_ROOT / "workloads.yaml")
            matrix = _load(EVT_ROOT / "test-matrix.yaml")
            manifest_schema = _load(EVT_ROOT / "schemas" / "run-manifest.schema.yaml")
            result_schema = _load(EVT_ROOT / "schemas" / "test-result.schema.yaml")
            if spec["metadata"]["status"] != "planned_not_authorized":
                failures.append("EVT0 spec must remain planned and unauthorized")
            authorization = spec["prerequisite_gates"]["authorization"]
            if any(value is True for field, value in authorization.items() if field.endswith("_authorized")):
                failures.append("EVT0 package may not imply purchase, build, or test authorization")
            if spec["configuration_rules"]["memory_tier_gb"] != 128:
                failures.append("EVT0 must use the locked 128 GB fallback")
            if spec["configuration_rules"]["wireless_charging"] != "removed":
                failures.append("wireless charging must remain removed from EVT0")
            if bom["metadata"]["selected_parts"] != 0:
                failures.append("EVT0 BOM may not imply selected parts")
            if len(instrumentation["channel_groups"]) < 5:
                failures.append("EVT0 instrumentation lacks required channel coverage")
            if len(workloads["workloads"]) < 6:
                failures.append("EVT0 workload set is incomplete")
            if len(matrix["required_for_evt0_evidence_gate"]) < 15:
                failures.append("EVT0 test gate lacks required test coverage")
            if matrix["global_pass_fail"]["hard_stops"]["maximum_skin_c"] != 43.0:
                failures.append("EVT0 locked 43 C skin hard stop changed unexpectedly")
            for schema, name in ((manifest_schema, "manifest"), (result_schema, "result")):
                if schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema" or not schema.get("required"):
                    failures.append(f"EVT0 {name} schema lacks Draft 2020-12 identity or required fields")
            real_results = [
                path
                for path in (EVT_ROOT / "test-results").rglob("*")
                if path.is_file() and path.name.lower() != "readme.md"
            ]
            if real_results:
                failures.append("EVT0 package contains unvalidated files presented as test results")
        except (KeyError, TypeError, ValueError) as exc:
            failures.append(str(exc))
        else:
            if not failures:
                print("PASS: EVT0 fallbacks, authorization, BOM, instrumentation, workloads, tests, schemas, and empty evidence state are valid")

    if not failures:
        result = subprocess.run(
            [sys.executable, str(GENERATOR_PATH)], cwd=REPO_ROOT, capture_output=True, text=True, check=False
        )
        if result.returncode == 0:
            print("PASS: EVT0 gate report generator runs")
        else:
            failures.append(f"EVT0 gate generator failed: {result.stderr.strip() or result.stdout.strip()}")

    if REPORT_PATH.exists():
        report = REPORT_PATH.read_text(encoding="utf-8")
        markers = (
            "specification status: planned_not_authorized",
            "physical prototype exists: no evidence",
            "selected roles: 0",
            "result files excluding instructions: 0",
            "campaign gate: EMPTY_CAMPAIGN",
            "EVT0_GATE: BLOCKED_ON_SUPPLIER_PHASE2_VERIFICATION_BUILD_AUTHORIZATION_AND_RESULTS",
            "does not claim a component selection",
        )
        missing = [marker for marker in markers if marker not in report]
        if missing:
            failures.append(f"EVT0 gate report missing markers: {', '.join(missing)}")
        else:
            print("PASS: EVT0 gate report preserves readiness blockers and non-evidence caveat")
    else:
        failures.append(f"EVT0 gate report missing: {REPORT_PATH.relative_to(REPO_ROOT)}")

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1
    print("PASS: EVT0 execution package validation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
