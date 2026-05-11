#!/usr/bin/env python3
"""First-pass battery pack physics screening model."""

from __future__ import annotations

import argparse

from common import positive_float, print_section


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capacity-mah", type=positive_float, default=6000.0)
    parser.add_argument("--nominal-voltage-v", type=positive_float, default=3.85)
    parser.add_argument("--workload-w", type=positive_float, default=28.0)
    parser.add_argument("--charging-w", type=positive_float, default=100.0)
    parser.add_argument("--footprint-area-mm2", type=positive_float, default=7500.0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    wh = args.capacity_mah / 1000.0 * args.nominal_voltage_v
    usable_wh_low = wh * 0.82
    usable_wh_high = wh * 0.90
    runtime_min_low = usable_wh_low / args.workload_w * 60.0
    runtime_min_high = usable_wh_high / args.workload_w * 60.0
    volume_cm3_low = wh / 0.72
    volume_cm3_high = wh / 0.58
    mass_g_low = wh / 0.26
    mass_g_high = wh / 0.22
    thickness_low = volume_cm3_low * 1000.0 / args.footprint_area_mm2
    thickness_high = volume_cm3_high * 1000.0 / args.footprint_area_mm2
    charge_current_a = args.charging_w / args.nominal_voltage_v
    heat_low = args.charging_w * 0.08
    heat_high = args.charging_w * 0.18
    warnings = []
    if args.workload_w >= 20:
        warnings.append("workload is laptop-class for a phone pack; runtime and cell temperature are aggressive")
    if args.charging_w >= 60:
        warnings.append("fast charging may create roughly %.0f-%.0f W of pack/electronics heat" % (heat_low, heat_high))
    if thickness_high > 4.5:
        warnings.append("pack thickness estimate exceeds common thin-phone battery allowances")
    if not warnings:
        warnings.append("no aggressive warning from defaults; still requires vendor cell data")

    print("Battery pack physics model")
    print_section("inputs", [
        f"capacity_mAh: {args.capacity_mah:.0f}",
        f"nominal_voltage_v: {args.nominal_voltage_v:.2f}",
        f"workload_w: {args.workload_w:.0f}",
        f"charging_w: {args.charging_w:.0f}",
        f"footprint_area_mm2: {args.footprint_area_mm2:.0f}",
    ])
    print_section("assumptions", [
        "usable energy is 82-90% after reserve, aging, voltage cutoffs, and high-load losses",
        "pack volumetric density range is 580-720 Wh/L (0.58-0.72 Wh/cm3) including pouch and tabs",
        "pack gravimetric density range is 220-260 Wh/kg including packaging",
        "charge heat uses 8-18% loss as a screening range, not a validated charge curve",
    ])
    print_section("formulas", [
        "Wh = capacity_mAh / 1000 * nominal_voltage_V",
        "usable_Wh = Wh * usable_fraction",
        "runtime_h = usable_Wh / workload_W",
        "volume_cm3 = Wh / volumetric_density_Wh_per_cm3",
        "mass_g = Wh / Wh_per_kg * 1000 g/kg",
        "thickness_mm = volume_mm3 / footprint_area_mm2",
        "charge_current_A = charging_W / nominal_voltage_V",
    ])
    print_section("outputs", [
        f"total_energy_wh: {wh:.1f}",
        f"usable_energy_wh_range: {usable_wh_low:.0f}-{usable_wh_high:.0f}",
        f"runtime_min_range_at_workload: {runtime_min_low:.0f}-{runtime_min_high:.0f}",
        f"pack_volume_cm3_range: {volume_cm3_low:.0f}-{volume_cm3_high:.0f}",
        f"pack_mass_g_range: {mass_g_low:.0f}-{mass_g_high:.0f}",
        f"estimated_pack_thickness_mm_range: {thickness_low:.1f}-{thickness_high:.1f}",
        f"charge_current_a_estimate: {charge_current_a:.0f}",
        f"charging_loss_heat_w_range: {heat_low:.0f}-{heat_high:.0f}",
    ])
    print_section("warnings", warnings)
    print("confidence: medium for energy arithmetic; low for packaging, cycle life, and fast-charge thermals")
    print("basis: conservative first-pass lithium-ion pack screening ranges")
    print("primary blocker: fitting high energy and high charge heat into safe cell thickness and thermal limits")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
