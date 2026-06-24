#!/usr/bin/env python3
"""Run all local BuildSlate validation checks."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

VALIDATION_CHECKS = (
    "validation/validate_specs.py",
    "validation/validate_calculation_registry.py",
    "validation/validate_core_formula_outputs.py",
    "validation/validate_calculation_core_integration.py",
    "validation/validate_core_formula_migration.py",
    "validation/dimensional_constraints.py",
    "validation/validate_device_profiles.py",
    "validation/validate_coverage_registry.py",
    "validation/validate_no_merge_conflicts.py",
    "engineering/stackup/generate_stackup_report.py",
    "validation/validate_cad_envelope_volume_registry.py",
    "validation/validate_physical_feasibility_gate.py",
    "validation/validate_physical_recovery_planner.py",
)


def run_check(script_path: str) -> bool:
    """Run one validation script from the repository root."""
    print(f"\n=== RUN {script_path} ===", flush=True)
    result = subprocess.run(
        [sys.executable, script_path],
        cwd=REPO_ROOT,
        check=False,
    )

    if result.returncode == 0:
        print(f"PASS {script_path}", flush=True)
        return True

    print(f"FAIL {script_path} (exit code {result.returncode})", flush=True)
    return False


def main() -> int:
    results: list[tuple[str, bool]] = []

    for script_path in VALIDATION_CHECKS:
        results.append((script_path, run_check(script_path)))

    passed = [script_path for script_path, success in results if success]
    failed = [script_path for script_path, success in results if not success]

    print("\n=== Validation summary ===")
    print(f"Passed: {len(passed)}")
    for script_path in passed:
        print(f"  PASS {script_path}")

    print(f"Failed: {len(failed)}")
    for script_path in failed:
        print(f"  FAIL {script_path}")

    if failed:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
