#!/usr/bin/env python3
"""Compare Slate Pocket v1 and v1R thermal consequence screening posture."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from engineering.core.calculator import Calculator  # noqa: E402
from engineering.physical_feasibility.physical_feasibility_gate import (  # noqa: E402
    DEFAULT_PROFILE_PATH,
    PhysicalFeasibilityResult,
    evaluate_gate,
)

V1_PROFILE_PATH = REPO_ROOT / "configs" / "devices" / "slate-pocket-v1.yaml"
V1R_PROFILE_PATH = REPO_ROOT / "configs" / "devices" / "slate-pocket-v1r.yaml"

SCREENING_CAVEAT = (
    "This is thermal consequence screening only. It does not claim thermal validation, skin-temperature compliance, "
    "thermal module performance, CFD/FEA correlation, supplier readiness, or prototype behavior."
)


class ThermalPostureDecision(StrEnum):
    """Approved thermal consequence screening decisions."""

    THERMAL_POSTURE_IMPROVED = "THERMAL_POSTURE_IMPROVED"
    THERMAL_POSTURE_DEGRADED = "THERMAL_POSTURE_DEGRADED"
    THERMAL_POSTURE_UNCHANGED = "THERMAL_POSTURE_UNCHANGED"
    THERMAL_POSTURE_UNKNOWN = "THERMAL_POSTURE_UNKNOWN"


class SkinTemperatureRiskDirection(StrEnum):
    """Approved skin-temperature risk directions."""

    IMPROVED = "improved"
    DEGRADED = "degraded"
    UNCHANGED = "unchanged"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class ThermalProfileScreen:
    """Thermal screening metrics for one device profile."""

    profile_id: str
    profile_name: str
    profile_label: str
    gate_decision: str
    volume_allocation_percent: float
    thickness_consumed_percent: float
    thickness_budget_mm: float
    thickness_stackup_mm: float
    thickness_margin_mm: float
    usable_internal_volume_mm3: float
    allocated_component_volume_mm3: float
    external_volume_cm3: float
    external_surface_area_cm2: float
    thickness_mm: float
    sustained_compute_w: float
    peak_compute_w: float
    npu_tops: float
    battery_capacity_mah: float
    battery_nominal_voltage_v: float
    battery_physical_volume_mm3: float
    battery_recovery_volume_delta_mm3: float
    battery_required_density_wh_per_l: float
    heat_density_w_cm3: float
    heat_flux_w_cm2: float
    cooling_strategy: str


@dataclass(frozen=True)
class ThermalConsequenceComparison:
    """Side-by-side thermal consequence comparison result."""

    baseline: ThermalProfileScreen
    recovery: ThermalProfileScreen
    internal_volume_change_mm3: float
    internal_volume_change_percent: float
    thickness_change_mm: float
    heat_density_change_w_cm3: float
    heat_density_change_percent: float
    heat_flux_change_w_cm2: float
    heat_flux_change_percent: float
    battery_volume_change_mm3: float
    battery_volume_change_percent: float
    capacity_if_same_density_mah: float
    thermal_module_implication: str
    battery_tradeoff: str
    skin_temperature_risk_direction: SkinTemperatureRiskDirection
    decision: ThermalPostureDecision
    decision_basis: tuple[str, ...]
    major_unknowns: tuple[str, ...]
    required_evidence_before_validation: tuple[str, ...]


def approved_decision_values() -> tuple[str, ...]:
    """Return approved thermal consequence decision enum values for validation."""
    return tuple(decision.value for decision in ThermalPostureDecision)


def _profile_identity(gate_result: PhysicalFeasibilityResult) -> tuple[str, str, str]:
    profile = gate_result.profile or {}
    identity = profile.get("identity", {})
    return (
        str(identity.get("profile_id", "slate-pocket-v1")),
        str(identity.get("name", "Slate Pocket v1")),
        str(identity.get("label", "canonical")),
    )


def _profile_value(profile: dict[str, Any], section: str, key: str, default: float) -> float:
    value = profile.get(section, {}).get(key, default)
    return float(value)


def _battery_component_volume_mm3(gate_result: PhysicalFeasibilityResult) -> float:
    for component in gate_result.volume_budget["components"]:
        if component.name == "battery_pack":
            return float(component.total_volume_mm3)
    return 0.0


def _battery_density_wh_per_l(capacity_mah: float, voltage_v: float, volume_mm3: float) -> float:
    if volume_mm3 <= 0.0:
        return 0.0
    energy_wh = capacity_mah * voltage_v / 1000.0
    return energy_wh / (volume_mm3 / 1_000_000.0)


def _percent_change(new_value: float, old_value: float) -> float:
    if old_value == 0.0:
        return 0.0
    return (new_value - old_value) / old_value * 100.0


def _screen_profile(profile_path: Path | None) -> ThermalProfileScreen:
    gate_result = evaluate_gate(profile_path=profile_path)
    profile = gate_result.profile or {}
    profile_id, profile_name, profile_label = _profile_identity(gate_result)

    geometry = profile.get("geometry", {})
    length_mm = float(geometry.get("length_mm", 180.0))
    width_mm = float(geometry.get("width_mm", 95.0))
    thickness_mm = float(geometry.get("thickness_mm", gate_result.targets["thickness_mm"]))
    thermal = profile.get("thermal", {})
    sustained_w = float(thermal.get("sustained_w", profile.get("compute", {}).get("sustained_power_w", 28.0)))

    calculator = Calculator()
    inputs = {
        "geometry.length_mm": length_mm,
        "geometry.width_mm": width_mm,
        "geometry.thickness_mm": thickness_mm,
        "thermal.sustained_w": sustained_w,
    }
    external_volume_cm3 = calculator.compute("geometry.volume_cm3", inputs)
    external_surface_area_cm2 = calculator.compute("geometry.surface_area_cm2", inputs)
    heat_density_w_cm3 = calculator.compute("thermal.heat_density_w_cm3", inputs)
    heat_flux_w_cm2 = calculator.compute("thermal.heat_flux_w_cm2", inputs)

    battery_capacity_mah = _profile_value(profile, "battery", "capacity_mah", gate_result.targets["battery_capacity_mah"])
    battery_voltage_v = _profile_value(profile, "battery", "nominal_voltage_v", 3.85)
    battery_volume_mm3 = _battery_component_volume_mm3(gate_result)

    return ThermalProfileScreen(
        profile_id=profile_id,
        profile_name=profile_name,
        profile_label=profile_label,
        gate_decision=gate_result.decision.value,
        volume_allocation_percent=float(gate_result.volume_budget["allocation_percentage"]),
        thickness_consumed_percent=float(gate_result.thickness_budget.consumed_percent),
        thickness_budget_mm=float(gate_result.thickness_budget.budget_mm),
        thickness_stackup_mm=float(gate_result.thickness_budget.total_thickness_mm),
        thickness_margin_mm=float(gate_result.thickness_budget.remaining_margin_mm),
        usable_internal_volume_mm3=float(gate_result.volume_budget["usable_volume_mm3"]),
        allocated_component_volume_mm3=float(gate_result.volume_budget["total_allocated_mm3"]),
        external_volume_cm3=external_volume_cm3,
        external_surface_area_cm2=external_surface_area_cm2,
        thickness_mm=thickness_mm,
        sustained_compute_w=_profile_value(profile, "compute", "sustained_power_w", sustained_w),
        peak_compute_w=_profile_value(profile, "compute", "peak_power_w", 45.0),
        npu_tops=_profile_value(profile, "compute", "npu_tops", gate_result.targets["npu_tops"]),
        battery_capacity_mah=battery_capacity_mah,
        battery_nominal_voltage_v=battery_voltage_v,
        battery_physical_volume_mm3=battery_volume_mm3,
        battery_recovery_volume_delta_mm3=float(profile.get("battery", {}).get("recovery_volume_delta_mm3", 0.0)),
        battery_required_density_wh_per_l=_battery_density_wh_per_l(
            battery_capacity_mah,
            battery_voltage_v,
            battery_volume_mm3,
        ),
        heat_density_w_cm3=heat_density_w_cm3,
        heat_flux_w_cm2=heat_flux_w_cm2,
        cooling_strategy=str(profile.get("component_assumptions", {}).get("cooling_strategy", "not specified")),
    )


def _classify_decision(
    baseline: ThermalProfileScreen,
    recovery: ThermalProfileScreen,
) -> tuple[ThermalPostureDecision, SkinTemperatureRiskDirection, tuple[str, ...]]:
    compute_unchanged = (
        baseline.sustained_compute_w == recovery.sustained_compute_w
        and baseline.peak_compute_w == recovery.peak_compute_w
    )
    heat_density_decreased = recovery.heat_density_w_cm3 < baseline.heat_density_w_cm3
    heat_flux_decreased = recovery.heat_flux_w_cm2 <= baseline.heat_flux_w_cm2
    thickness_margin_improved = recovery.thickness_margin_mm > baseline.thickness_margin_mm
    battery_volume_reduced = recovery.battery_physical_volume_mm3 < baseline.battery_physical_volume_mm3

    basis = [
        "Increased thickness with unchanged compute target can improve spreading volume, but does not prove lower skin temperature.",
        "Reduced battery volume creates possible layout freedom, but may reduce runtime or require higher C-rate if capacity is not retained.",
    ]

    if heat_density_decreased and thickness_margin_improved and compute_unchanged:
        basis.append(
            "Heat density decreases and thickness margin improves, so the screening-level posture is improved before validation."
        )
        if heat_flux_decreased:
            basis.append("Estimated heat flux also decreases slightly because external surface area increases.")
        if battery_volume_reduced:
            basis.append("Battery-volume reduction remains a major unresolved tradeoff rather than a validated thermal benefit.")
        return (
            ThermalPostureDecision.THERMAL_POSTURE_IMPROVED,
            SkinTemperatureRiskDirection.IMPROVED,
            tuple(basis),
        )

    if recovery.heat_density_w_cm3 > baseline.heat_density_w_cm3 or recovery.heat_flux_w_cm2 > baseline.heat_flux_w_cm2:
        basis.append("Estimated heat density or heat flux increases from the baseline profile.")
        return (
            ThermalPostureDecision.THERMAL_POSTURE_DEGRADED,
            SkinTemperatureRiskDirection.DEGRADED,
            tuple(basis),
        )

    if recovery.heat_density_w_cm3 == baseline.heat_density_w_cm3 and recovery.heat_flux_w_cm2 == baseline.heat_flux_w_cm2:
        basis.append("Estimated heat density and heat flux do not change.")
        return (
            ThermalPostureDecision.THERMAL_POSTURE_UNCHANGED,
            SkinTemperatureRiskDirection.UNCHANGED,
            tuple(basis),
        )

    basis.append("Available data is insufficient to assign an improved or degraded thermal posture.")
    return (
        ThermalPostureDecision.THERMAL_POSTURE_UNKNOWN,
        SkinTemperatureRiskDirection.UNKNOWN,
        tuple(basis),
    )


def compare_v1_to_v1r() -> ThermalConsequenceComparison:
    """Build the Slate Pocket v1 vs v1R thermal consequence comparison."""
    baseline = _screen_profile(DEFAULT_PROFILE_PATH if DEFAULT_PROFILE_PATH.exists() else V1_PROFILE_PATH)
    recovery = _screen_profile(V1R_PROFILE_PATH)
    decision, skin_direction, decision_basis = _classify_decision(baseline, recovery)
    capacity_if_same_density_mah = baseline.battery_capacity_mah
    if baseline.battery_physical_volume_mm3 > 0.0:
        capacity_if_same_density_mah = baseline.battery_capacity_mah * (
            recovery.battery_physical_volume_mm3 / baseline.battery_physical_volume_mm3
        )

    return ThermalConsequenceComparison(
        baseline=baseline,
        recovery=recovery,
        internal_volume_change_mm3=recovery.usable_internal_volume_mm3 - baseline.usable_internal_volume_mm3,
        internal_volume_change_percent=_percent_change(
            recovery.usable_internal_volume_mm3,
            baseline.usable_internal_volume_mm3,
        ),
        thickness_change_mm=recovery.thickness_mm - baseline.thickness_mm,
        heat_density_change_w_cm3=recovery.heat_density_w_cm3 - baseline.heat_density_w_cm3,
        heat_density_change_percent=_percent_change(recovery.heat_density_w_cm3, baseline.heat_density_w_cm3),
        heat_flux_change_w_cm2=recovery.heat_flux_w_cm2 - baseline.heat_flux_w_cm2,
        heat_flux_change_percent=_percent_change(recovery.heat_flux_w_cm2, baseline.heat_flux_w_cm2),
        battery_volume_change_mm3=recovery.battery_physical_volume_mm3 - baseline.battery_physical_volume_mm3,
        battery_volume_change_percent=_percent_change(
            recovery.battery_physical_volume_mm3,
            baseline.battery_physical_volume_mm3,
        ),
        capacity_if_same_density_mah=capacity_if_same_density_mah,
        thermal_module_implication=(
            "v1R has more z-height and internal layout headroom for spreader/TIM routing, but the thermal module "
            "cannot be credited without CAD geometry, material stack, interfaces, and measured power data."
        ),
        battery_tradeoff=(
            "v1R keeps the 6000 mAh target while reducing first-pass battery physical volume; that either requires "
            "higher validated cell energy density or implies a lower capacity/runtime target if density is unchanged."
        ),
        skin_temperature_risk_direction=skin_direction,
        decision=decision,
        decision_basis=decision_basis,
        major_unknowns=(
            "Effective heat-spreading area is unknown; rectangular external area is not the same as useful thermal area.",
            "Thermal module geometry, vapor chamber behavior, TIM stack, and contact pressure are not defined.",
            "SoC/NPU sustained and peak power telemetry are targets, not measured workload heat.",
            "Battery-volume reduction may affect cell impedance, C-rate, charging heat, runtime, and safety margins.",
            "Hand contact, orientation, enclosure materials, controls, and ambient conditions are not validated.",
        ),
        required_evidence_before_validation=(
            "thermal module CAD",
            "TIM selection",
            "SoC power telemetry",
            "skin thermocouple map",
            "CFD or FEA model",
        ),
    )
