#!/usr/bin/env python3
"""First-pass current delivery and power rail pressure screen."""
from __future__ import annotations

import argparse
from common import positive_float, print_section


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--soc-power-w", type=positive_float, default=28.0)
    parser.add_argument("--memory-power-w", type=positive_float, default=12.0)
    parser.add_argument("--storage-power-w", type=positive_float, default=5.0)
    parser.add_argument("--display-power-w", type=positive_float, default=4.0)
    parser.add_argument("--charging-power-w", type=positive_float, default=100.0)
    parser.add_argument("--battery-voltage-v", type=positive_float, default=3.85)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    total_system_power_w = args.soc_power_w + args.memory_power_w + args.storage_power_w + args.display_power_w
    battery_side_current_a = total_system_power_w / args.battery_voltage_v
    charging_current_a = args.charging_power_w / args.battery_voltage_v
    overlap_power_w = total_system_power_w + args.charging_power_w
    overlap_battery_equivalent_current_a = overlap_power_w / args.battery_voltage_v
    pd_rail_stress_index = overlap_power_w / 100.0

    warnings: list[str] = []
    if battery_side_current_a > 10.0:
        warnings.append(">10A battery-side current during sustained internal load")
    if total_system_power_w > 30.0:
        warnings.append(">30W sustained internal dissipation requires aggressive thermal and rail design")
    if args.charging_power_w > 0 and total_system_power_w > 30.0:
        warnings.append("charging plus sustained AI overlap can stress thermals, battery protection, PMICs, and USB-PD policy")
    if overlap_battery_equivalent_current_a > 20.0:
        warnings.append("combined charge/load current equivalent is very high for a thin pocket device")

    print("Power delivery screening model")
    print_section("assumptions", [
        "loads are summed as a conservative simultaneous-use case",
        "battery-side current uses nominal battery voltage and ignores regulator efficiency",
        "USB-PD rail stress is represented by a normalized overlap-power index, not connector or charger qualification",
        "thermal, charging policy, cable limits, PMIC selection, and battery cell limits require later detailed design",
    ])
    print_section("formulas", [
        "total_system_power_W = SoC + memory + storage + display",
        "battery_side_current_A = total_system_power_W / battery_voltage_V",
        "charging_current_A = charging_power_W / battery_voltage_V",
        "overlap_power_W = total_system_power_W + charging_power_W",
        "pd_rail_stress_index = overlap_power_W / 100 W",
    ])
    print_section("outputs", [
        f"total_system_power_w: {total_system_power_w:.1f}",
        f"battery_side_current_a: {battery_side_current_a:.1f}",
        f"charging_current_a_at_battery_voltage_equivalent: {charging_current_a:.1f}",
        f"overlap_power_w: {overlap_power_w:.1f}",
        f"overlap_battery_equivalent_current_a: {overlap_battery_equivalent_current_a:.1f}",
        f"pd_rail_stress_index: {pd_rail_stress_index:.2f}",
    ])
    print_section("warnings", warnings)
    print("confidence: medium for current arithmetic; low for real rail/PMIC implementation")
    print("basis: first-order thin-device power delivery and charging-overlap screen")
    print("primary blocker: current density, connector/PMIC limits, and thermal dissipation during overlap events")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
