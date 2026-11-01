#!/usr/bin/env python3
"""Validate Slate Pocket evidence readiness artifacts."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = REPO_ROOT / "engineering" / "evidence" / "evidence_registry.yaml"
ENGINE_PATH = REPO_ROOT / "engineering" / "evidence" / "evidence_engine.py"
GENERATOR_PATH = REPO_ROOT / "engineering" / "evidence" / "generate_evidence_readiness_report.py"
REPORT_PATH = REPO_ROOT / "reports" / "slate-pocket-evidence-readiness.txt"

sys.path.insert(0, str(REPO_ROOT))

from engineering.evidence.evidence_engine import (  # noqa: E402
    EvidenceDecision,
    build_packages,
    load_registry,
    readiness_decision,
    validate_registry,
)


def main() -> int:
    failures: list[str] = []

    for path, label in (
        (REGISTRY_PATH, "evidence registry"),
        (ENGINE_PATH, "evidence engine"),
        (GENERATOR_PATH, "evidence report generator"),
    ):
        if path.exists():
            print(f"PASS: {label} exists: {path.relative_to(REPO_ROOT)}")
        else:
            failures.append(f"{label} missing: {path.relative_to(REPO_ROOT)}")

    packages = ()
    if not failures:
        try:
            registry = load_registry(REGISTRY_PATH)
            validate_registry(registry)
            packages = build_packages(registry)
            print("PASS: evidence registry shape, dependencies, risk links, and ownership rules are valid")
        except ValueError as exc:
            failures.append(str(exc))

    if packages:
        phases = {package.phase for package in packages}
        if phases == {0, 1, 2, 3, 4}:
            print("PASS: evidence roadmap covers phases 0 through 4")
        else:
            failures.append(f"evidence phases must cover 0 through 4; found {sorted(phases)}")
        decision = readiness_decision(packages)
        if decision in set(EvidenceDecision):
            print(f"PASS: evidence decision is an approved enum value: {decision.value}")
        else:
            failures.append(f"invalid evidence decision: {decision}")

    if not failures:
        result = subprocess.run(
            [sys.executable, str(GENERATOR_PATH)],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            print("PASS: evidence readiness report generator runs")
        else:
            failures.append(f"generator exited with code {result.returncode}: {result.stderr.strip()}")

    if REPORT_PATH.exists():
        report = REPORT_PATH.read_text(encoding="utf-8")
        markers = (
            "Executive summary",
            "Attack now",
            "Phase 0 evidence packages",
            "Phase 4 evidence packages",
            "EVIDENCE_DECISION:",
            "Gate rules",
            "does not create supplier approval",
        )
        missing = [marker for marker in markers if marker not in report]
        if missing:
            failures.append(f"evidence report missing required sections: {', '.join(missing)}")
        else:
            print("PASS: evidence readiness report contains required sections and caveat")
    else:
        failures.append(f"evidence report missing: {REPORT_PATH.relative_to(REPO_ROOT)}")

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1

    print("PASS: evidence readiness validation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
