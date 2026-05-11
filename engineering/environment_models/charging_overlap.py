#!/usr/bin/env python3
"""Estimate risk when AI workload overlaps with wired or wireless charging."""
from __future__ import annotations

import argparse
from collections.abc import Iterable


def positive_float(value: str) -> float:
    parsed = float(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("value must be greater than zero")
    return parsed


def fraction_float(value: str) -> float:
    parsed = float(value)
    if parsed <= 0 or parsed > 1:
        raise argparse.ArgumentTypeError("value must be greater than zero and at most 1")
    return parsed


def bool_arg(value: str) -> bool:
    lowered = value.lower()
    if lowered in {"1", "true", "yes", "y", "on"}:
        return True
    if lowered in {"0", "false", "no", "n", "off"}:
        return False
    raise argparse.ArgumentTypeError("value must be true or false")


def print_section(title: str, rows: Iterable[str]) -> None:
    print(f"{title}:")
    rows = list(rows)
    if not rows:
        print("  none")
        return
    for row in rows:
        print(f"  - {row}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ai-workload-w", type=positive_float, default=28.0)
    parser.add_argument("--charging-power-w", type=positive_float, default=100.0)
    parser.add_argument("--charging-efficiency", type=fraction_float, default=None)
    parser.add_argument("--battery-charge-heat-fraction", type=fraction_float, default=0.08)
    parser.add_argument("--wireless", type=bool_arg, default=False)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    charging_efficiency = args.charging_efficiency
    efficiency_basis = "user supplied"
    if charging_efficiency is None:
        charging_efficiency = 0.78 if args.wireless else 0.88
        efficiency_basis = "wireless default derate" if args.wireless else "wired default"

    charging_loss_w = args.charging_power_w * (1 - charging_efficiency)
    battery_heat_w = args.charging_power_w * args.battery_charge_heat_fraction
    combined_internal_heat_w = args.ai_workload_w + charging_loss_w + battery_heat_w

    warnings: list[str] = []
    if combined_internal_heat_w > 35:
        warnings.append("combined heat exceeds 35 W")
    warnings.append("charging while sustained AI is active should throttle")
    if args.wireless:
        warnings.append("wireless charging plus sustained AI is high risk")

    print("Charging-overlap thermal-risk model")
    print_section("inputs", [
        f"ai_workload_w: {args.ai_workload_w:.1f}",
        f"charging_power_w: {args.charging_power_w:.1f}",
        f"charging_efficiency: {charging_efficiency:.2f} ({efficiency_basis})",
        f"battery_charge_heat_fraction: {args.battery_charge_heat_fraction:.2f}",
        f"wireless: {args.wireless}",
    ])
    print_section("assumptions", [
        "charger conversion loss and battery charge heat add to AI workload heat during overlap",
        "wireless charging receives a lower default efficiency unless the user supplies --charging-efficiency",
        "thermal distribution among adapter, coil, PMIC, battery, and skin is not spatially resolved",
    ])
    print_section("formulas", [
        "charging_loss_w = charging_power_w * (1 - charging_efficiency)",
        "battery_heat_w = charging_power_w * battery_charge_heat_fraction",
        "combined_internal_heat_w = ai_workload_w + charging_loss_w + battery_heat_w",
    ])
    print_section("outputs", [
        f"charging_loss_w: {charging_loss_w:.1f}",
        f"battery_heat_w: {battery_heat_w:.1f}",
        f"combined_internal_heat_w: {combined_internal_heat_w:.1f}",
    ])
    print_section("warnings", warnings)
    print("confidence: low; charger, PMIC, battery, coil, and enclosure thermal tests are required")
    print("basis: first-pass overlap heat budget for AI workload plus active charging")
    print("primary blocker: no charge taper, battery temperature feedback, coil alignment, or PMIC placement model is included")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
