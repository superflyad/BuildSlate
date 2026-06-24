#!/usr/bin/env python3
"""Unified Slate Pocket v1 physical-feasibility gate."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from engineering.cad_envelope.slate_pocket_volume_budget import calculate_from_registry as calculate_volume_budget  # noqa: E402
from engineering.stackup.thickness_budget import calculate_thickness_budget, load_registry as load_stackup_registry  # noqa: E402

VOLUME_REGISTRY_PATH = REPO_ROOT / "engineering" / "cad_envelope" / "component_volume_registry.yaml"
STACKUP_REGISTRY_PATH = REPO_ROOT / "engineering" / "stackup" / "thickness_stack_registry.yaml"
COMPONENT_CANDIDATES_PATH = REPO_ROOT / "research" / "components" / "component_candidates.yaml"
COMPONENT_SELECTION_STATUS_PATH = REPO_ROOT / "research" / "components" / "component_selection_status.yaml"
SPEC_PATH = REPO_ROOT / "specs" / "slate-pocket-v1.yaml"

SCREENING_CAVEAT = (
    "This gate is a screening decision only. It does not prove manufacturability, "
    "CAD validity, thermal viability, RF compliance, certification readiness, or supplier availability."
)


class GateDecision(StrEnum):
    """Approved physical-feasibility gate decisions."""

    PASS_TO_THERMAL_SCREENING = "PASS_TO_THERMAL_SCREENING"
    CONDITIONAL_PASS = "CONDITIONAL_PASS"
    BLOCKED_BY_VOLUME = "BLOCKED_BY_VOLUME"
    BLOCKED_BY_THICKNESS = "BLOCKED_BY_THICKNESS"
    BLOCKED_BY_COMPONENT_UNCERTAINTY = "BLOCKED_BY_COMPONENT_UNCERTAINTY"
    BLOCKED_BY_MULTIPLE_CONSTRAINTS = "BLOCKED_BY_MULTIPLE_CONSTRAINTS"


@dataclass(frozen=True)
class ComponentMaturitySummary:
    """Candidate-registry maturity counts used by the gate."""

    category_count: int
    candidate_count: int
    candidate_status_counts: dict[str, int]
    category_status_counts: dict[str, int]
    confidence_counts: dict[str, int]
    selected_category_count: int
    supplier_backed_candidate_count: int
    speculative_or_placeholder_count: int
    most_components_speculative_or_placeholder: bool
    required_evidence: tuple[str, ...]


@dataclass(frozen=True)
class PhysicalFeasibilityResult:
    """Combined gate result for physical-package screening."""

    volume_budget: dict[str, Any]
    thickness_budget: Any
    component_maturity: ComponentMaturitySummary
    decision: GateDecision
    major_blockers: tuple[str, ...]
    required_evidence: tuple[str, ...]
    targets: dict[str, Any]


def _load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as input_file:
        data = yaml.safe_load(input_file)
    if not isinstance(data, dict):
        raise ValueError(f"{path.relative_to(REPO_ROOT)} must contain a mapping")
    return data


def _increment(counter: dict[str, int], key: str) -> None:
    counter[key] = counter.get(key, 0) + 1


def load_targets(path: Path = SPEC_PATH) -> dict[str, Any]:
    """Load the canonical Slate Pocket v1 physical target subset."""
    spec = _load_yaml(path)
    return {
        "display_size_in": spec["display"]["size_in"],
        "battery_capacity_mah": spec["battery"]["capacity_mah"],
        "memory_capacity_gb": spec["memory"]["capacity_gb"],
        "storage_capacity_tb": spec["storage"]["capacity_tb"],
        "cooling": ", ".join(spec["thermal"]["cooling"]),
        "npu_tops": spec["compute"]["npu"]["tops"],
        "target_mass_g": spec["weight"]["target_g"],
        "thickness_mm": spec["dimensions"]["thickness_mm"],
    }


def summarize_component_maturity(
    candidates_path: Path = COMPONENT_CANDIDATES_PATH,
    selection_status_path: Path = COMPONENT_SELECTION_STATUS_PATH,
) -> ComponentMaturitySummary:
    """Summarize candidate and selection maturity without claiming part availability."""
    candidates = _load_yaml(candidates_path)
    selection_status = _load_yaml(selection_status_path)

    categories = candidates.get("categories")
    status_categories = selection_status.get("categories")
    if not isinstance(categories, dict) or not categories:
        raise ValueError("component candidates registry must have non-empty categories")
    if not isinstance(status_categories, dict) or not status_categories:
        raise ValueError("component selection status registry must have non-empty categories")

    candidate_status_counts: dict[str, int] = {}
    category_status_counts: dict[str, int] = {}
    confidence_counts: dict[str, int] = {}
    candidate_count = 0
    supplier_backed_candidate_count = 0
    speculative_or_placeholder_count = 0

    for category, entries in categories.items():
        if not isinstance(entries, list) or not entries:
            raise ValueError(f"component candidate category {category} must be a non-empty list")
        for entry in entries:
            if not isinstance(entry, dict):
                raise ValueError(f"component candidate category {category} contains a non-mapping entry")
            candidate_count += 1
            status = str(entry.get("status", "speculative"))
            confidence = str(entry.get("confidence", "low"))
            _increment(candidate_status_counts, status)
            _increment(confidence_counts, confidence)
            if entry.get("vendor") and entry.get("source"):
                supplier_backed_candidate_count += 1
            if status == "speculative" or confidence == "low":
                speculative_or_placeholder_count += 1

    selected_category_count = 0
    required_evidence: list[str] = []
    for category, entry in status_categories.items():
        if not isinstance(entry, dict):
            raise ValueError(f"component selection category {category} must be a mapping")
        status = str(entry.get("current_status", "speculative"))
        _increment(category_status_counts, status)
        if entry.get("selected_candidate"):
            selected_category_count += 1
        next_actions = entry.get("next_actions", [])
        if isinstance(next_actions, list):
            for action in next_actions[:2]:
                if isinstance(action, str) and action.strip():
                    required_evidence.append(f"{category}: {action.strip()}")

    most_speculative = speculative_or_placeholder_count > candidate_count / 2
    return ComponentMaturitySummary(
        category_count=len(categories),
        candidate_count=candidate_count,
        candidate_status_counts=dict(sorted(candidate_status_counts.items())),
        category_status_counts=dict(sorted(category_status_counts.items())),
        confidence_counts=dict(sorted(confidence_counts.items())),
        selected_category_count=selected_category_count,
        supplier_backed_candidate_count=supplier_backed_candidate_count,
        speculative_or_placeholder_count=speculative_or_placeholder_count,
        most_components_speculative_or_placeholder=most_speculative,
        required_evidence=tuple(required_evidence),
    )


def make_gate_decision(
    volume_status: str,
    thickness_status: str,
    component_maturity: ComponentMaturitySummary,
) -> GateDecision:
    """Apply the approved v1 gate decision rules."""
    volume_failed = volume_status == "FAIL"
    thickness_failed = thickness_status == "FAIL"
    volume_warned = volume_status == "WARNING"
    thickness_warned = thickness_status == "WARNING"

    if volume_failed and thickness_failed:
        return GateDecision.BLOCKED_BY_MULTIPLE_CONSTRAINTS
    if volume_failed:
        return GateDecision.BLOCKED_BY_VOLUME
    if thickness_failed:
        return GateDecision.BLOCKED_BY_THICKNESS
    if volume_warned or thickness_warned:
        return GateDecision.CONDITIONAL_PASS
    if component_maturity.most_components_speculative_or_placeholder:
        return GateDecision.BLOCKED_BY_COMPONENT_UNCERTAINTY
    return GateDecision.PASS_TO_THERMAL_SCREENING


def _major_blockers(volume_budget: dict[str, Any], thickness_budget: Any, maturity: ComponentMaturitySummary) -> tuple[str, ...]:
    blockers: list[str] = []
    if volume_budget["status"] == "FAIL":
        blockers.append(
            f"Volume allocation consumes {volume_budget['allocation_percentage']:.1f}% of estimated usable internal volume."
        )
    elif volume_budget["status"] == "WARNING":
        blockers.append(
            f"Volume allocation has limited margin at {volume_budget['allocation_percentage']:.1f}% of estimated usable internal volume."
        )

    if thickness_budget.status == "FAIL":
        blockers.append(
            f"Thickness stackup consumes {thickness_budget.consumed_percent:.1f}% of the {thickness_budget.budget_mm:.2f} mm budget."
        )
    elif thickness_budget.status == "WARNING":
        blockers.append(
            f"Thickness stackup has limited margin at {thickness_budget.consumed_percent:.1f}% of the {thickness_budget.budget_mm:.2f} mm budget."
        )

    if maturity.most_components_speculative_or_placeholder:
        blockers.append(
            f"Component registry remains immature: {maturity.speculative_or_placeholder_count} of "
            f"{maturity.candidate_count} candidates are speculative or low-confidence."
        )
    if maturity.selected_category_count == 0:
        blockers.append("No component category has a selected candidate.")

    return tuple(blockers) if blockers else ("No physical-package blocker detected by this screening gate.",)


def _required_evidence(maturity: ComponentMaturitySummary) -> tuple[str, ...]:
    evidence = [
        "CAD-derived internal volume allocation with keepouts, flexes, shields, fasteners, seals, and service allowances.",
        "Mechanical stackup drawing with overlap zones, local camera/connector protrusions, compression, and tolerance ranges.",
        "Supplier package drawings or datasheets for display, battery, SoC/NPU, memory, storage, RF, wireless charging, and thermal materials.",
        "Mass rollup tied to selected or shortlisted parts before manufacturing feasibility claims.",
    ]
    evidence.extend(maturity.required_evidence[:10])
    return tuple(evidence)


def evaluate_gate() -> PhysicalFeasibilityResult:
    """Evaluate the physical-feasibility gate from current source registries."""
    volume_budget = calculate_volume_budget(VOLUME_REGISTRY_PATH)
    stackup_registry = load_stackup_registry(STACKUP_REGISTRY_PATH)
    thickness_budget = calculate_thickness_budget(stackup_registry)
    component_maturity = summarize_component_maturity()
    decision = make_gate_decision(volume_budget["status"], thickness_budget.status, component_maturity)

    return PhysicalFeasibilityResult(
        volume_budget=volume_budget,
        thickness_budget=thickness_budget,
        component_maturity=component_maturity,
        decision=decision,
        major_blockers=_major_blockers(volume_budget, thickness_budget, component_maturity),
        required_evidence=_required_evidence(component_maturity),
        targets=load_targets(),
    )


def approved_decision_values() -> tuple[str, ...]:
    """Return approved gate decision enum values for validation."""
    return tuple(decision.value for decision in GateDecision)
