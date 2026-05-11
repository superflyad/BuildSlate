#!/usr/bin/env python3
"""Create first-pass throttle policy recommendations from skin temperature and workload."""
from __future__ import annotations

import argparse
from collections.abc import Iterable


def positive_float(value: str) -> float:
    parsed = float(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("value must be greater than zero")
    return parsed


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
    parser.add_argument("--skin-temp-c", type=positive_float, default=43.0)
    parser.add_argument("--battery-temp-c", type=positive_float, default=40.0)
    parser.add_argument("--soc-temp-c", type=positive_float, default=85.0)
    parser.add_argument("--ai-workload-w", type=positive_float, default=28.0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    warnings: list[str] = []

    skin_level = "normal"
    if args.skin_temp_c >= 45:
        skin_level = "critical"
        warnings.append("skin temperature is at or above critical threshold")
    elif args.skin_temp_c >= 43:
        skin_level = "limit"
        warnings.append("skin temperature is at or above limit threshold")
    elif args.skin_temp_c >= 40:
        skin_level = "caution"
        warnings.append("skin temperature is at or above caution threshold")

    battery_level = "normal"
    if args.battery_temp_c >= 45:
        battery_level = "limit"
        warnings.append("battery temperature is at or above limit threshold")
    elif args.battery_temp_c >= 40:
        battery_level = "caution"
        warnings.append("battery temperature is at or above caution threshold")

    soc_level = "normal"
    if args.soc_temp_c >= 90:
        soc_level = "limit"
        warnings.append("SoC temperature is at or above limit threshold")
    elif args.soc_temp_c >= 80:
        soc_level = "caution"
        warnings.append("SoC temperature is at or above caution threshold")

    if skin_level == "critical":
        recommended_mode = "emergency_cooldown"
    elif battery_level == "limit":
        recommended_mode = "stop_charging"
    elif skin_level == "limit" or soc_level == "limit":
        recommended_mode = "burst_only"
    elif skin_level == "caution" or battery_level == "caution" or soc_level == "caution" or args.ai_workload_w >= 28:
        recommended_mode = "reduce_ai_power"
    else:
        recommended_mode = "unrestricted"

    print("Thermal throttle policy model")
    print_section("inputs", [
        f"skin_temp_c: {args.skin_temp_c:.1f}",
        f"battery_temp_c: {args.battery_temp_c:.1f}",
        f"soc_temp_c: {args.soc_temp_c:.1f}",
        f"ai_workload_w: {args.ai_workload_w:.1f}",
    ])
    print_section("assumptions", [
        "skin thresholds: caution >= 40 C, limit >= 43 C, critical >= 45 C",
        "battery thresholds: caution >= 40 C, limit >= 45 C",
        "SoC thresholds: caution >= 80 C, limit >= 90 C",
        "policy recommends the most conservative mode triggered by measured thermal state",
    ])
    print_section("formulas", [
        "threshold comparisons assign skin, battery, and SoC thermal levels",
        "recommended_mode is selected from unrestricted, reduce_ai_power, burst_only, stop_charging, emergency_cooldown",
    ])
    print_section("outputs", [
        f"skin_level: {skin_level}",
        f"battery_level: {battery_level}",
        f"soc_level: {soc_level}",
        f"recommended_mode: {recommended_mode}",
    ])
    print_section("warnings", warnings)
    print("confidence: low; firmware policy must be validated against sensors, user comfort, safety, and workload behavior")
    print("basis: first-pass threshold policy for thermal screening and control intent")
    print("primary blocker: thresholds are placeholder engineering assumptions, not certified safety limits or product firmware")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
