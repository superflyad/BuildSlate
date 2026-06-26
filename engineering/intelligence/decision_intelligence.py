#!/usr/bin/env python3
"""Cross-report decision intelligence for the Slate Pocket v1R recovery path."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from engineering.physical_feasibility.physical_feasibility_gate import evaluate_gate  # noqa: E402
from engineering.recovery.physical_recovery_planner import build_recovery_plan  # noqa: E402
from engineering.thermal_consequence.thermal_consequence_model import compare_v1_to_v1r  # noqa: E402

V1_PROFILE_ID = "slate-pocket-v1"
V1R_PROFILE_ID = "slate-pocket-v1r"
V1_PROFILE_PATH = REPO_ROOT / "configs" / "devices" / "slate-pocket-v1.yaml"
V1R_PROFILE_PATH = REPO_ROOT / "configs" / "devices" / "slate-pocket-v1r.yaml"

SOURCE_REPORTS = (
    "reports/slate-pocket-physical-feasibility-gate.txt",
    "reports/slate-pocket-v1r-physical-feasibility-gate.txt",
    "reports/slate-pocket-physical-recovery-plan.txt",
    "reports/device-profile-slate-pocket-v1r.txt",
    "reports/slate-pocket-v1r-thermal-consequence.txt",
)

SCREENING_CAVEAT = (
    "This report demonstrates cross-report reasoning across existing screening artifacts. It is not validated "
    "engineering proof and does not claim manufacturability, CAD validity, thermal validation, supplier readiness, "
    "certification readiness, prototype readiness, or production readiness."
)

FRAGILE_ASSUMPTIONS = (
    "battery energy density",
    "reduced battery volume",
    "28 W sustained compute",
    "45 W peak compute",
    "thermal module effectiveness",
    "43°C max skin target",
    "512 GB memory packaging",
    "4 TB storage packaging",
)

EVIDENCE_REQUIRED = (
    "battery cell datasheet",
    "CAD stackup",
    "thermal module CAD",
    "SoC package spec",
    "sustained power telemetry",
    "thermocouple map",
    "supplier DFM review",
)


@dataclass(frozen=True)
class EngineeringIntelligence:
    """Decision chain summary for the first Slate Pocket v1R intelligence report."""

    v1_gate_decision: str
    v1r_gate_decision: str
    recovery_path: str
    recovery_status: str
    thermal_decision: str
    v1_volume_allocation_percent: float
    v1r_volume_allocation_percent: float
    v1_thickness_mm: float
    v1r_thickness_mm: float
    v1_thickness_consumed_percent: float
    v1r_thickness_consumed_percent: float
    v1r_profile: dict[str, Any]
    source_reports: tuple[str, ...]


def _load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as input_file:
        data = yaml.safe_load(input_file)
    if not isinstance(data, dict):
        raise ValueError(f"{path.relative_to(REPO_ROOT)} must contain a mapping")
    return data


def _scenario_label(scenario_ids: tuple[str, ...]) -> str:
    return " + ".join(scenario_ids)


def build_engineering_intelligence() -> EngineeringIntelligence:
    """Build the current v1 -> v1R decision intelligence from source models."""
    v1_gate = evaluate_gate(V1_PROFILE_PATH)
    v1r_gate = evaluate_gate(V1R_PROFILE_PATH)
    recovery_plan = build_recovery_plan()
    thermal = compare_v1_to_v1r()
    v1r_profile = _load_yaml(V1R_PROFILE_PATH)

    recovery_status = "SUFFICIENT" if recovery_plan.recommendation_is_sufficient else "INSUFFICIENT"
    return EngineeringIntelligence(
        v1_gate_decision=v1_gate.decision.value,
        v1r_gate_decision=v1r_gate.decision.value,
        recovery_path=_scenario_label(recovery_plan.recommendation.scenario_ids),
        recovery_status=recovery_status,
        thermal_decision=thermal.decision.value,
        v1_volume_allocation_percent=float(v1_gate.volume_budget["allocation_percentage"]),
        v1r_volume_allocation_percent=float(v1r_gate.volume_budget["allocation_percentage"]),
        v1_thickness_mm=float(v1_gate.targets["thickness_mm"]),
        v1r_thickness_mm=float(v1r_gate.targets["thickness_mm"]),
        v1_thickness_consumed_percent=float(v1_gate.thickness_budget.consumed_percent),
        v1r_thickness_consumed_percent=float(v1r_gate.thickness_budget.consumed_percent),
        v1r_profile=v1r_profile,
        source_reports=SOURCE_REPORTS,
    )


def render_report(intelligence: EngineeringIntelligence) -> str:
    """Render the first-pass engineering intelligence report."""
    profile = intelligence.v1r_profile
    battery = profile["battery"]
    compute = profile["compute"]
    memory = profile["memory"]
    storage = profile["storage"]
    thermal = profile["thermal"]

    lines = [
        "Slate Pocket v1R Engineering Intelligence Demo v1",
        "===================================================",
        "",
        "Scope:",
        f"  compare: {V1_PROFILE_ID} -> {V1R_PROFILE_ID}",
        "  purpose: explain why Slate Pocket v1R exists, what changed from v1, what evidence supports the decision, and what assumptions remain fragile",
        "  intelligence type: cross-report reasoning over screening artifacts",
        "",
        "Source reports referenced:",
    ]
    lines.extend(f"  - {report}" for report in intelligence.source_reports)
    lines.extend(
        [
            "",
            "What changed:",
            f"  - {V1R_PROFILE_ID} is a recovery profile derived from {V1_PROFILE_ID}, not a new validated hardware generation.",
            f"  - Thickness target changed from {intelligence.v1_thickness_mm:.1f} mm to {intelligence.v1r_thickness_mm:.1f} mm.",
            f"  - Battery physical volume changed to {battery['physical_volume_mm3']:.0f} mm3 with a {battery['recovery_volume_delta_mm3']:.0f} mm3 recovery delta.",
            f"  - Recovery strategy: {', '.join(profile.get('recovery_strategy', []))}.",
            f"  - Compute targets remained {compute['sustained_power_w']:.0f} W sustained and {compute['peak_power_w']:.0f} W peak.",
            f"  - Memory and storage targets remained {memory['capacity_gb']:.0f} GB and {storage['capacity_tb']:.0f} TB.",
            "",
            "Why it changed:",
            f"  - {V1_PROFILE_ID} was physically blocked by the feasibility gate: {intelligence.v1_gate_decision}.",
            "  - The recovery planner searched screening-level packaging tradeoffs for the least disruptive path that recovered both volume and thickness.",
            f"  - The selected recovery path was {intelligence.recovery_path}, with recommendation status {intelligence.recovery_status}.",
            "  - The recovered profile exists to preserve the product intent while making the physical package eligible for conditional downstream screening.",
            "",
            "Triggering previous report:",
            "  - reports/slate-pocket-physical-feasibility-gate.txt triggered the recovery workflow by reporting the v1 physical gate failure.",
            "  - reports/slate-pocket-physical-recovery-plan.txt identified the recovery path that became the v1R profile assumptions.",
            "",
            "What improved:",
            f"  - Physical gate decision changed from {intelligence.v1_gate_decision} to {intelligence.v1r_gate_decision}.",
            f"  - Volume allocation changed from {intelligence.v1_volume_allocation_percent:.1f}% to {intelligence.v1r_volume_allocation_percent:.1f}%.",
            f"  - Thickness consumption changed from {intelligence.v1_thickness_consumed_percent:.1f}% to {intelligence.v1r_thickness_consumed_percent:.1f}%.",
            f"  - Thermal consequence screening reported {intelligence.thermal_decision}.",
            "  - Added z-height and reduced battery package volume improve screening posture for layout and thermal spreading headroom.",
            "",
            "What got worse or remains uncertain:",
            "  - The device becomes thicker, so industrial design, ergonomics, sealing, RF, camera protrusions, and accessories must be rechecked.",
            "  - Reduced battery volume may require higher validated energy density or force a later capacity/runtime tradeoff.",
            f"  - The {compute['sustained_power_w']:.0f} W sustained and {compute['peak_power_w']:.0f} W peak compute targets remain unmeasured workload assumptions.",
            f"  - The {thermal['max_skin_c']:.0f}°C max skin target remains a screening target until mapped on hardware.",
            f"  - {memory['capacity_gb']:.0f} GB memory and {storage['capacity_tb']:.0f} TB storage remain package, sourcing, routing, power, cost, and thermal risks.",
            "",
            "Decision trace:",
            f"  {V1_PROFILE_ID} failed physical feasibility",
            f"  -> Recovery planner recommended {intelligence.recovery_path}",
            f"  -> {V1R_PROFILE_ID} was created",
            f"  -> v1R physical gate produced {intelligence.v1r_gate_decision}",
            f"  -> thermal consequence screening reported {intelligence.thermal_decision}",
            "",
            "Fragile assumptions:",
        ]
    )
    lines.extend(f"  - {assumption}" for assumption in FRAGILE_ASSUMPTIONS)
    lines.extend(["", "Most fragile assumptions:"])
    lines.extend(
        [
            "  - battery energy density: must support the retained 6000 mAh target in the smaller battery package.",
            "  - reduced battery volume: may improve package fit while worsening runtime, C-rate, charging heat, swelling, and safety margin.",
            "  - thermal module effectiveness: current thermal improvement is only a geometry-level posture, not a proven heat path.",
            "  - 28 W sustained compute and 45 W peak compute: require measured SoC/NPU telemetry and throttle behavior.",
            "  - 512 GB memory packaging and 4 TB storage packaging: require supplier package data, board area, routing, power, and thermal review.",
            "",
            "Evidence required next:",
        ]
    )
    lines.extend(f"  - {evidence}" for evidence in EVIDENCE_REQUIRED)
    lines.extend(
        [
            "",
            "Decision interpretation:",
            "  v1R is justified as a screening recovery profile because the prior physical gate blocked v1 and the recovery path produced a conditional physical pass.",
            "  The decision is not a validation claim; it is a traceable reason to continue evidence gathering around the recovered assumptions.",
            "",
            "Caveat:",
            f"  {SCREENING_CAVEAT}",
            "",
        ]
    )
    return "\n".join(lines)


def build_report() -> str:
    """Build the rendered engineering intelligence report."""
    return render_report(build_engineering_intelligence())
