#!/usr/bin/env python3
"""Generate the Slate Pocket v1R EVT0 execution-readiness and evidence gate."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
EVT_ROOT = REPO_ROOT / "validation" / "evt0"
SPEC_PATH = EVT_ROOT / "evt0-spec.yaml"
BOM_PATH = EVT_ROOT / "bom-strategy.yaml"
MATRIX_PATH = EVT_ROOT / "test-matrix.yaml"
WORKLOAD_PATH = EVT_ROOT / "workloads.yaml"
REGISTRY_PATH = REPO_ROOT / "engineering" / "evidence" / "evidence_registry.yaml"
REPORT_PATH = REPO_ROOT / "reports" / "slate-pocket-v1r-evt0-gate.txt"


def _load(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as input_file:
        data = yaml.safe_load(input_file)
    if not isinstance(data, dict):
        raise ValueError(f"{path.relative_to(REPO_ROOT)} must contain a mapping")
    return data


def _real_result_files() -> list[Path]:
    result_root = EVT_ROOT / "test-results"
    return sorted(path for path in result_root.rglob("*") if path.is_file() and path.name.lower() != "readme.md")


def build_report() -> str:
    spec = _load(SPEC_PATH)
    bom = _load(BOM_PATH)
    matrix = _load(MATRIX_PATH)
    workloads = _load(WORKLOAD_PATH)
    registry = _load(REGISTRY_PATH)

    prerequisite_ids: list[str] = []
    for gate in spec["prerequisite_gates"].values():
        if isinstance(gate, dict) and "packages" in gate:
            prerequisite_ids.extend(gate["packages"])
    package_statuses = {package_id: registry["packages"][package_id]["status"] for package_id in prerequisite_ids}
    unverified = [package_id for package_id, status in package_statuses.items() if status != "verified"]

    authorization = spec["prerequisite_gates"]["authorization"]
    safety = spec["prerequisite_gates"]["safety"]
    false_authorizations = [field for field, value in authorization.items() if field.endswith("_authorized") and value is not True]
    false_safety_gates = [field for field, value in safety.items() if value is not True]

    roles = bom["roles"]
    selected_roles = [role_id for role_id, role in roles.items() if role["status"] == "selected"]
    removed_or_deferred = [
        role_id for role_id, role in roles.items() if role["status"] in {"removed_from_EVT0", "deferred_from_EVT0"}
    ]
    real_results = _real_result_files()
    tests = matrix["sequence"]
    required_test_ids = matrix["required_for_evt0_evidence_gate"]
    unresolved_workloads = [
        workload_id
        for workload_id, workload in workloads["workloads"].items()
        if any(value is None for value in workload.values())
    ]

    lines = [
        "Slate Pocket v1R EVT0 Gate",
        "============================",
        "",
        "Program state:",
        f"  specification status: {spec['metadata']['status']}",
        "  physical prototype exists: no evidence",
        "  physical work authorized: no",
        "  purchases authorized: no",
        "  energized testing authorized: no",
        "",
        "Prerequisite evidence:",
        f"  required packages: {len(prerequisite_ids)}",
        f"  verified packages: {len(prerequisite_ids) - len(unverified)}",
        f"  unverified packages: {len(unverified)}",
    ]
    for package_id in prerequisite_ids:
        lines.append(f"  - {package_id}: {package_statuses[package_id]}")

    lines.extend(
        [
            "",
            "Build readiness:",
            f"  BOM roles: {len(roles)}",
            f"  selected roles: {len(selected_roles)}",
            f"  intentionally removed/deferred roles: {', '.join(removed_or_deferred)}",
            f"  unmet authorization gates: {', '.join(false_authorizations)}",
            f"  unmet safety gates: {', '.join(false_safety_gates)}",
            "  EVT0 memory configuration: 128 GB fallback",
            "  EVT0 storage configuration: 1 TB planning baseline",
            "  wireless charging: REMOVED",
            "  cellular: DEFERRED",
            "",
            "Executable test package:",
            f"  planned tests: {len(tests)}",
            f"  tests required for evidence gate: {len(required_test_ids)}",
            f"  workload definitions: {len(workloads['workloads'])}",
            f"  workload definitions awaiting content hashes: {len(unresolved_workloads)}",
            "  run manifest schema: available",
            "  test result schema: available",
            "  build traveler: available",
            "  model-correlation workflow: available",
            "",
            "Measured evidence:",
            f"  result files excluding instructions: {len(real_results)}",
            "  schema-valid completed required tests: 0",
            "  model correlation completed: no",
            "",
            "Gate blockers:",
            "  - Supplier packages and Phase 2 integration packages are not verified.",
            "  - No selected BOM, released hardware design, approved battery/charge limits, or calibrated setup exists.",
            "  - Purchase, build, and energized-test authorization have not been granted.",
            "  - No physical unit, raw measurement campaign, reviewed result, or correlation evidence exists.",
            "",
            "EVT0_GATE: BLOCKED_ON_SUPPLIER_PHASE2_VERIFICATION_BUILD_AUTHORIZATION_AND_RESULTS",
            "",
            "Caveat:",
            "  The EVT0 package is executable planning evidence only. It does not claim a component selection, prototype build, measurement, correlated model, safety validation, certification, or prototype readiness.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    try:
        report = build_report()
    except (KeyError, TypeError, ValueError) as exc:
        print(f"FAIL: {exc}")
        return 1
    REPORT_PATH.write_text(report, encoding="utf-8")
    print(f"Wrote {REPORT_PATH.relative_to(REPO_ROOT)}")
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
