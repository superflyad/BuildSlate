#!/usr/bin/env python3
"""Generate the Slate Pocket v1R thermal consequence screening report."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from engineering.thermal_consequence.thermal_consequence_model import (  # noqa: E402
    SCREENING_CAVEAT,
    ThermalConsequenceComparison,
    ThermalProfileScreen,
    compare_v1_to_v1r,
)

REPORT_PATH = REPO_ROOT / "reports" / "slate-pocket-v1r-thermal-consequence.txt"


def _fmt_mm3(value_mm3: float) -> str:
    return f"{value_mm3:,.1f} mm^3 ({value_mm3 / 1000.0:,.2f} cm^3)"


def _fmt_signed(value: float, suffix: str = "") -> str:
    sign = "+" if value > 0 else ""
    return f"{sign}{value:.2f}{suffix}"


def _profile_summary(profile: ThermalProfileScreen) -> list[str]:
    return [
        f"  profile_id: {profile.profile_id}",
        f"  label: {profile.profile_label}",
        f"  physical gate: {profile.gate_decision}",
        f"  external surface area: {profile.external_surface_area_cm2:.1f} cm^2",
        f"  external envelope volume: {profile.external_volume_cm3:.1f} cm^3",
        f"  usable internal volume: {_fmt_mm3(profile.usable_internal_volume_mm3)}",
        f"  volume allocation: {profile.volume_allocation_percent:.1f}%",
        f"  thickness: {profile.thickness_mm:.2f} mm",
        f"  thickness consumption: {profile.thickness_consumed_percent:.1f}%",
        f"  thickness margin: {profile.thickness_margin_mm:.2f} mm",
        f"  sustained compute target: {profile.sustained_compute_w:.1f} W",
        f"  peak compute target: {profile.peak_compute_w:.1f} W",
        f"  estimated heat density: {profile.heat_density_w_cm3:.3f} W/cm^3",
        f"  estimated heat flux: {profile.heat_flux_w_cm2:.3f} W/cm^2",
        f"  battery target: {profile.battery_capacity_mah:.0f} mAh at {profile.battery_nominal_voltage_v:.2f} V",
        f"  battery physical volume: {_fmt_mm3(profile.battery_physical_volume_mm3)}",
        f"  implied battery density: {profile.battery_required_density_wh_per_l:.0f} Wh/L",
        f"  cooling strategy: {profile.cooling_strategy}",
    ]


def _comparison_table(comparison: ThermalConsequenceComparison) -> list[str]:
    baseline = comparison.baseline
    recovery = comparison.recovery
    return [
        "| Metric | slate-pocket-v1 | slate-pocket-v1r | Change |",
        "| --- | ---: | ---: | ---: |",
        (
            f"| external surface area | {baseline.external_surface_area_cm2:.1f} cm^2 | "
            f"{recovery.external_surface_area_cm2:.1f} cm^2 | "
            f"{_fmt_signed(recovery.external_surface_area_cm2 - baseline.external_surface_area_cm2, ' cm^2')} |"
        ),
        (
            f"| usable internal volume | {baseline.usable_internal_volume_mm3 / 1000.0:.2f} cm^3 | "
            f"{recovery.usable_internal_volume_mm3 / 1000.0:.2f} cm^3 | "
            f"{_fmt_signed(comparison.internal_volume_change_mm3 / 1000.0, ' cm^3')} "
            f"({_fmt_signed(comparison.internal_volume_change_percent, '%')}) |"
        ),
        (
            f"| thickness | {baseline.thickness_mm:.2f} mm | {recovery.thickness_mm:.2f} mm | "
            f"{_fmt_signed(comparison.thickness_change_mm, ' mm')} |"
        ),
        (
            f"| estimated heat density | {baseline.heat_density_w_cm3:.3f} W/cm^3 | "
            f"{recovery.heat_density_w_cm3:.3f} W/cm^3 | "
            f"{_fmt_signed(comparison.heat_density_change_w_cm3, ' W/cm^3')} "
            f"({_fmt_signed(comparison.heat_density_change_percent, '%')}) |"
        ),
        (
            f"| estimated heat flux | {baseline.heat_flux_w_cm2:.3f} W/cm^2 | "
            f"{recovery.heat_flux_w_cm2:.3f} W/cm^2 | "
            f"{_fmt_signed(comparison.heat_flux_change_w_cm2, ' W/cm^2')} "
            f"({_fmt_signed(comparison.heat_flux_change_percent, '%')}) |"
        ),
        (
            f"| sustained compute target | {baseline.sustained_compute_w:.1f} W | "
            f"{recovery.sustained_compute_w:.1f} W | unchanged |"
        ),
        (
            f"| peak compute target | {baseline.peak_compute_w:.1f} W | "
            f"{recovery.peak_compute_w:.1f} W | unchanged |"
        ),
        (
            f"| battery physical volume | {baseline.battery_physical_volume_mm3 / 1000.0:.2f} cm^3 | "
            f"{recovery.battery_physical_volume_mm3 / 1000.0:.2f} cm^3 | "
            f"{_fmt_signed(comparison.battery_volume_change_mm3 / 1000.0, ' cm^3')} "
            f"({_fmt_signed(comparison.battery_volume_change_percent, '%')}) |"
        ),
    ]


def render_report(comparison: ThermalConsequenceComparison) -> str:
    """Render a plain-text thermal consequence screening report."""
    lines = [
        "Slate Pocket v1R Thermal Consequence Screening",
        "================================================",
        "",
        "Scope:",
        "  compare: slate-pocket-v1 -> slate-pocket-v1r",
        "  purpose: evaluate whether the v1R physical recovery changes thermal risk posture before detailed thermal modeling",
        "  input basis: device profiles, physical feasibility gate outputs, and centralized geometry/thermal formulas",
        "",
        "v1 baseline summary:",
    ]
    lines.extend(_profile_summary(comparison.baseline))
    lines.extend(["", "v1R recovery summary:"])
    lines.extend(_profile_summary(comparison.recovery))
    lines.extend(["", "Comparison table:"])
    lines.extend(_comparison_table(comparison))
    lines.extend(
        [
            "",
            "Battery volume/capacity tradeoff:",
            f"  battery volume change: {_fmt_mm3(comparison.battery_volume_change_mm3)} "
            f"({_fmt_signed(comparison.battery_volume_change_percent, '%')})",
            f"  same-density capacity estimate: {comparison.capacity_if_same_density_mah:.0f} mAh",
            f"  interpretation: {comparison.battery_tradeoff}",
            "",
            "Thermal module implication:",
            f"  {comparison.thermal_module_implication}",
            "",
            "Skin temperature risk direction:",
            f"  {comparison.skin_temperature_risk_direction.value}",
            "",
            "Thermal consequence decision:",
            f"  THERMAL_DECISION: {comparison.decision.value}",
            "  decision confidence: screening-level only",
            "  basis:",
        ]
    )
    lines.extend(f"    - {basis}" for basis in comparison.decision_basis)
    lines.extend(["", "Major unknowns:"])
    lines.extend(f"  - {unknown}" for unknown in comparison.major_unknowns)
    lines.extend(["", "Required evidence before thermal validation:"])
    lines.extend(f"  - {item}" for item in comparison.required_evidence_before_validation)
    lines.extend(["", "Caveat:", f"  {SCREENING_CAVEAT}", ""])
    return "\n".join(lines)


def build_report() -> str:
    return render_report(compare_v1_to_v1r())


def main() -> int:
    report = build_report()
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(report, encoding="utf-8")
    print(f"Wrote {REPORT_PATH.relative_to(REPO_ROOT)}")
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
