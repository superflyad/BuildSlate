#!/usr/bin/env python3
"""First-pass battery swelling allowance pressure screen."""
from __future__ import annotations

import argparse


def positive_float(value: str) -> float:
    parsed = float(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("value must be positive")
    return parsed


def percent(value: str) -> float:
    parsed = float(value)
    if parsed < 0 or parsed > 100:
        raise argparse.ArgumentTypeError("value must be between 0 and 100")
    return parsed


def print_section(title: str, rows: list[str]) -> None:
    print(f"{title}:")
    for row in rows:
        print(f"  - {row}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--battery-thickness-mm", type=positive_float, default=4.5)
    parser.add_argument("--swelling-percent", type=percent, default=8.0)
    parser.add_argument("--available-clearance-mm", type=positive_float, default=0.4)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    required_clearance_mm = args.battery_thickness_mm * args.swelling_percent / 100.0
    expanded_thickness_mm = args.battery_thickness_mm + required_clearance_mm
    remaining_allowance_mm = args.available_clearance_mm - required_clearance_mm
    passes = remaining_allowance_mm >= 0

    warnings: list[str] = []
    if required_clearance_mm > args.available_clearance_mm:
        warnings.append("swelling allowance is exceeded")
    if remaining_allowance_mm < 0.1:
        warnings.append("low swelling margin can transfer pressure into the display or rear housing")
    if args.swelling_percent >= 8.0:
        warnings.append("long-term reliability concern: swelling allowance should not be consumed by nominal stackup")

    print("Battery swelling allowance screening model")
    print_section("inputs", [
        f"battery_thickness_mm: {args.battery_thickness_mm:.1f}",
        f"swelling_percent: {args.swelling_percent:.0f}",
        f"available_clearance_mm: {args.available_clearance_mm:.1f}",
    ])
    print_section("formulas", [
        "required_clearance_mm = battery_thickness_mm * swelling_percent / 100",
        "expanded_thickness_mm = battery_thickness_mm + required_clearance_mm",
        "remaining_allowance_mm = available_clearance_mm - required_clearance_mm",
    ])
    print_section("outputs", [
        f"expanded_thickness_mm: {expanded_thickness_mm:.2f}",
        f"required_swelling_clearance_mm: {required_clearance_mm:.2f}",
        f"remaining_allowance_mm: {remaining_allowance_mm:.2f}",
        f"screening_result: {'pass' if passes else 'fail'}",
    ])
    print_section("warnings", warnings or ["none"])
    print("confidence: low; actual swelling depends on cell chemistry, age, charge policy, temperature, and mechanical preload")
    print("basis: first-pass clearance allowance screen, not a cell safety qualification")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
