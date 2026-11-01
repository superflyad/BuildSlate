#!/usr/bin/env python3
"""Validate final local/public program coverage and external blocker handoff."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = REPO_ROOT / "engineering" / "evidence" / "evidence_registry.yaml"
BLOCKER_PATH = REPO_ROOT / "engineering" / "evidence" / "external_blocker_registry.yaml"
HANDOFF_PATH = REPO_ROOT / "docs" / "engineering" / "slate-pocket-v1r-external-blockers.md"
GENERATOR_PATH = REPO_ROOT / "engineering" / "evidence" / "generate_program_handoff_report.py"
REPORT_PATH = REPO_ROOT / "reports" / "slate-pocket-v1r-program-readiness.txt"


def _load(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as input_file:
        data = yaml.safe_load(input_file)
    if not isinstance(data, dict):
        raise ValueError(f"{path.relative_to(REPO_ROOT)} must contain a mapping")
    return data


def main() -> int:
    failures: list[str] = []
    for path in (REGISTRY_PATH, BLOCKER_PATH, HANDOFF_PATH, GENERATOR_PATH):
        if path.exists():
            print(f"PASS: program handoff artifact exists: {path.relative_to(REPO_ROOT)}")
        else:
            failures.append(f"program handoff artifact missing: {path.relative_to(REPO_ROOT)}")

    if not failures:
        try:
            packages = _load(REGISTRY_PATH)["packages"]
            blockers = _load(BLOCKER_PATH)["blockers"]
            required_fields = {
                "category",
                "affects",
                "missing_evidence",
                "exact_request",
                "acceptance_criteria",
                "fallback",
                "independent_work_complete",
                "authorization_required",
            }
            for blocker_id, blocker in blockers.items():
                missing = required_fields - set(blocker)
                if missing:
                    failures.append(f"blocker {blocker_id} missing fields: {', '.join(sorted(missing))}")
                unknown = set(blocker.get("affects", [])) - set(packages)
                if unknown:
                    failures.append(f"blocker {blocker_id} references unknown packages: {', '.join(sorted(unknown))}")
            covered = {package_id for blocker in blockers.values() for package_id in blocker["affects"]}
            nonverified = {package_id for package_id, package in packages.items() if package["status"] != "verified"}
            uncovered = nonverified - covered
            if uncovered:
                failures.append(f"nonverified packages lack external blockers: {', '.join(sorted(uncovered))}")
            if any(package["status"] == "missing" for package in packages.values()):
                failures.append("evidence registry still contains missing packages")
            status_counts: dict[str, int] = {}
            for package in packages.values():
                status_counts[package["status"]] = status_counts.get(package["status"], 0) + 1
            if status_counts != {"verified": 1, "available": 3, "planned": 6}:
                failures.append(f"unexpected final evidence status counts: {status_counts}")
        except (KeyError, TypeError, ValueError) as exc:
            failures.append(str(exc))
        else:
            if not failures:
                print("PASS: every nonverified package maps to a complete external blocker and no package is missing")

    if not failures:
        result = subprocess.run(
            [sys.executable, str(GENERATOR_PATH)], cwd=REPO_ROOT, capture_output=True, text=True, check=False
        )
        if result.returncode == 0:
            print("PASS: final program handoff report generator runs")
        else:
            failures.append(f"program handoff generator failed: {result.stderr.strip() or result.stdout.strip()}")

    if REPORT_PATH.exists():
        report = REPORT_PATH.read_text(encoding="utf-8")
        markers = (
            "Verified evidence (1)",
            "Available public evidence (3; not verified)",
            "Modeled Phase 2 planning evidence (4; not verified)",
            "Prepared execution packages (2; no physical evidence)",
            "Rejected, removed, or unsupported configurations (6)",
            "Externally blocked work (8)",
            "external messages/purchases/builds/tests performed: none",
            "LOCAL_PROGRAM_DECISION: SUPPLIER_READY_AND_PROTOTYPE_PLAN_READY_EXTERNALLY_BLOCKED",
            "does not yet have selected components",
        )
        missing = [marker for marker in markers if marker not in report]
        if missing:
            failures.append(f"program handoff report missing markers: {', '.join(missing)}")
        else:
            print("PASS: final report separates verified, available, modeled, prepared, rejected, and externally blocked evidence")
    else:
        failures.append(f"program handoff report missing: {REPORT_PATH.relative_to(REPO_ROOT)}")

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1
    print("PASS: final program handoff validation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
