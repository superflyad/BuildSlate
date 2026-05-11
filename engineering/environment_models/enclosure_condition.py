#!/usr/bin/env python3
"""Model device thermal risk for open-air, handheld, pocket, bag, and car-console conditions."""
from __future__ import annotations

import argparse
from collections.abc import Iterable

CONDITIONS = {
    "open_air": {"heat_escape_factor": 1.0, "risk_multiplier": 1.0},
    "handheld": {"heat_escape_factor": 0.75, "risk_multiplier": 1.25},
    "pocket": {"heat_escape_factor": 0.35, "risk_multiplier": 2.0},
    "bag": {"heat_escape_factor": 0.25, "risk_multiplier": 2.5},
    "car_console_sun": {"heat_escape_factor": 0.20, "risk_multiplier": 3.0},
}


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
    parser.add_argument("--condition", choices=sorted(CONDITIONS), default="open_air")
    parser.add_argument("--sustained-w", type=positive_float, default=28.0)
    parser.add_argument("--ambient-c", type=positive_float, default=25.0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    condition = CONDITIONS[args.condition]
    heat_escape_factor = condition["heat_escape_factor"]
    risk_multiplier = condition["risk_multiplier"]
    effective_dissipation_w = args.sustained_w * heat_escape_factor
    thermal_risk_score = args.sustained_w * risk_multiplier

    warnings: list[str] = []
    if args.condition in {"pocket", "bag"}:
        warnings.append("pocket/bag sustained AI should be disallowed or aggressively throttled")
    if args.condition == "car_console_sun":
        warnings.append("car console sun condition is high risk and should force cooldown or shutdown behavior")
    if args.condition in {"pocket", "bag", "car_console_sun"}:
        warnings.append("charging under enclosed conditions is unsafe without throttling")
    if args.ambient_c >= 35:
        warnings.append("hot ambient temperature compounds enclosure risk")

    print("Enclosure condition thermal-risk model")
    print_section("inputs", [
        f"condition: {args.condition}",
        f"sustained_w: {args.sustained_w:.1f}",
        f"ambient_c: {args.ambient_c:.1f}",
    ])
    print_section("assumptions", [
        f"heat_escape_factor: {heat_escape_factor:.2f}",
        f"risk_multiplier: {risk_multiplier:.2f}",
        "enclosed conditions reduce convection and trap heat around the device",
        "risk score is a relative screening metric, not a calibrated temperature prediction",
    ])
    print_section("formulas", [
        "effective_dissipation_w = sustained_w * heat_escape_factor",
        "thermal_risk_score = sustained_w * risk_multiplier",
    ])
    print_section("outputs", [
        f"effective_dissipation_w: {effective_dissipation_w:.1f}",
        f"thermal_risk_score: {thermal_risk_score:.1f}",
    ])
    print_section("warnings", warnings)
    print("confidence: low; enclosure, textile, bag, sunlight, and airflow measurements are required")
    print("basis: first-pass heat-escape derating by operating condition")
    print("primary blocker: real enclosure thermal impedance depends on fabric, orientation, airflow, and solar loading")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
