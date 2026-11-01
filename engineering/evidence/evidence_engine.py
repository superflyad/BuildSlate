#!/usr/bin/env python3
"""Evidence readiness modeling for the Slate Pocket engineering program."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

import yaml

from engineering.risks.risk_engine import load_registry as load_risk_registry

REPO_ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = REPO_ROOT / "engineering" / "evidence" / "evidence_registry.yaml"

REQUIRED_FIELDS = (
    "title",
    "phase",
    "priority",
    "status",
    "owner",
    "depends_on",
    "linked_risks",
    "acceptance_criteria",
    "expected_artifacts",
    "notes",
)
STATUS_VALUES = ("missing", "planned", "in_progress", "available", "verified")
PRIORITY_VALUES = ("medium", "high", "critical")


class EvidenceDecision(StrEnum):
    """Program-level evidence gate decisions."""

    BLOCKED_ON_FOUNDATIONAL_EVIDENCE = "BLOCKED_ON_FOUNDATIONAL_EVIDENCE"
    EVIDENCE_ACQUISITION_IN_PROGRESS = "EVIDENCE_ACQUISITION_IN_PROGRESS"
    READY_FOR_PROTOTYPE_GATE = "READY_FOR_PROTOTYPE_GATE"
    EVIDENCE_GATE_COMPLETE = "EVIDENCE_GATE_COMPLETE"


@dataclass(frozen=True)
class EvidencePackage:
    """One evidence package and its verification state."""

    package_id: str
    title: str
    phase: int
    priority: str
    status: str
    owner: str
    depends_on: tuple[str, ...]
    linked_risks: tuple[str, ...]
    acceptance_criteria: tuple[str, ...]
    expected_artifacts: tuple[str, ...]
    notes: str

    @property
    def is_verified(self) -> bool:
        return self.status == "verified"


def load_registry(path: Path = REGISTRY_PATH) -> dict[str, Any]:
    """Load the evidence registry."""
    if not path.exists():
        raise ValueError(f"evidence registry missing: {path.relative_to(REPO_ROOT)}")
    with path.open("r", encoding="utf-8") as input_file:
        data = yaml.safe_load(input_file)
    if not isinstance(data, dict):
        raise ValueError("evidence registry root must be a mapping")
    return data


def _require_string_list(
    entry: dict[str, Any], field: str, package_id: str, *, allow_empty: bool = False
) -> tuple[str, ...]:
    value = entry.get(field)
    if not isinstance(value, list) or (not value and not allow_empty):
        qualifier = "a list" if allow_empty else "a non-empty list"
        raise ValueError(f"{package_id}.{field} must be {qualifier}")
    if not all(isinstance(item, str) and item.strip() for item in value):
        raise ValueError(f"{package_id}.{field} must contain non-empty strings")
    return tuple(item.strip() for item in value)


def _validate_dependency_graph(packages: dict[str, Any]) -> None:
    """Reject unknown dependencies and dependency cycles."""
    for package_id, entry in packages.items():
        dependencies = _require_string_list(entry, "depends_on", package_id, allow_empty=True)
        unknown = [dependency for dependency in dependencies if dependency not in packages]
        if unknown:
            raise ValueError(f"{package_id}.depends_on contains unknown packages: {', '.join(unknown)}")
        if package_id in dependencies:
            raise ValueError(f"{package_id}.depends_on may not reference itself")

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(package_id: str) -> None:
        if package_id in visited:
            return
        if package_id in visiting:
            raise ValueError(f"evidence dependency cycle detected at {package_id}")
        visiting.add(package_id)
        for dependency in packages[package_id]["depends_on"]:
            visit(dependency)
        visiting.remove(package_id)
        visited.add(package_id)

    for package_id in packages:
        visit(package_id)


def validate_registry(registry: dict[str, Any]) -> None:
    """Validate evidence schema, risk links, ownership policy, and dependencies."""
    metadata = registry.get("metadata")
    if not isinstance(metadata, dict):
        raise ValueError("evidence registry must define metadata")
    packages = registry.get("packages")
    if not isinstance(packages, dict) or not packages:
        raise ValueError("evidence registry must define a non-empty packages mapping")
    caveat = registry.get("caveat")
    if not isinstance(caveat, str) or "does not" not in caveat:
        raise ValueError("evidence registry must contain a non-validation caveat")

    known_risks = set(load_risk_registry()["risks"])
    for package_id, entry in packages.items():
        if not isinstance(entry, dict):
            raise ValueError(f"{package_id} must be a mapping")
        missing = [field for field in REQUIRED_FIELDS if field not in entry]
        if missing:
            raise ValueError(f"{package_id} missing required fields: {', '.join(missing)}")
        if not isinstance(entry["phase"], int) or entry["phase"] < 0:
            raise ValueError(f"{package_id}.phase must be a non-negative integer")
        if entry["priority"] not in PRIORITY_VALUES:
            raise ValueError(f"{package_id}.priority must be one of: {', '.join(PRIORITY_VALUES)}")
        if entry["status"] not in STATUS_VALUES:
            raise ValueError(f"{package_id}.status must be one of: {', '.join(STATUS_VALUES)}")
        for text_field in ("title", "owner", "notes"):
            if not isinstance(entry[text_field], str) or not entry[text_field].strip():
                raise ValueError(f"{package_id}.{text_field} must be a non-empty string")
        if entry["status"] in {"in_progress", "available", "verified"} and entry["owner"] == "unassigned":
            raise ValueError(f"{package_id} must have an owner before status {entry['status']}")
        _require_string_list(entry, "depends_on", package_id, allow_empty=True)
        linked_risks = _require_string_list(entry, "linked_risks", package_id)
        _require_string_list(entry, "acceptance_criteria", package_id)
        _require_string_list(entry, "expected_artifacts", package_id)
        unknown_risks = [risk_id for risk_id in linked_risks if risk_id not in known_risks]
        if unknown_risks:
            raise ValueError(f"{package_id}.linked_risks contains unknown risks: {', '.join(unknown_risks)}")

    _validate_dependency_graph(packages)


def build_packages(registry: dict[str, Any] | None = None) -> tuple[EvidencePackage, ...]:
    """Build ordered evidence-package rows."""
    data = registry if registry is not None else load_registry()
    validate_registry(data)
    rows: list[EvidencePackage] = []
    for package_id, entry in data["packages"].items():
        rows.append(
            EvidencePackage(
                package_id=package_id,
                title=entry["title"].strip(),
                phase=entry["phase"],
                priority=entry["priority"],
                status=entry["status"],
                owner=entry["owner"].strip(),
                depends_on=_require_string_list(entry, "depends_on", package_id, allow_empty=True),
                linked_risks=_require_string_list(entry, "linked_risks", package_id),
                acceptance_criteria=_require_string_list(entry, "acceptance_criteria", package_id),
                expected_artifacts=_require_string_list(entry, "expected_artifacts", package_id),
                notes=entry["notes"].strip(),
            )
        )
    return tuple(sorted(rows, key=lambda row: (row.phase, row.package_id)))


def readiness_decision(packages: tuple[EvidencePackage, ...]) -> EvidenceDecision:
    """Calculate the current program evidence gate."""
    if all(package.is_verified for package in packages):
        return EvidenceDecision.EVIDENCE_GATE_COMPLETE

    critical = [package for package in packages if package.priority == "critical"]
    foundational = [package for package in critical if package.phase <= 2]
    if any(package.status in {"missing", "planned"} for package in foundational):
        return EvidenceDecision.BLOCKED_ON_FOUNDATIONAL_EVIDENCE
    if all(package.is_verified for package in foundational):
        return EvidenceDecision.READY_FOR_PROTOTYPE_GATE
    return EvidenceDecision.EVIDENCE_ACQUISITION_IN_PROGRESS


def status_counts(packages: tuple[EvidencePackage, ...]) -> Counter[str]:
    """Count packages by status."""
    return Counter(package.status for package in packages)


def unblocked_packages(packages: tuple[EvidencePackage, ...]) -> tuple[EvidencePackage, ...]:
    """Return unfinished packages whose dependencies are verified."""
    by_id = {package.package_id: package for package in packages}
    return tuple(
        package
        for package in packages
        if not package.is_verified
        and all(by_id[dependency].is_verified for dependency in package.depends_on)
    )
