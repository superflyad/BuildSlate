#!/usr/bin/env python3
"""First-pass repairability pressure screen."""
from __future__ import annotations

import argparse

LEVEL_SCORES = {"low": 1, "medium": 2, "high": 3}
INVERSE_LEVEL_SCORES = {"low": 3, "medium": 2, "high": 1}


def positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("value must be positive")
    return parsed


def print_section(title: str, rows: list[str]) -> None:
    print(f"{title}:")
    for row in rows:
        print(f"  - {row}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    levels = ("low", "medium", "high")
    parser.add_argument("--adhesive-level", choices=levels, default="high")
    parser.add_argument("--battery-removability", choices=levels, default="low")
    parser.add_argument("--screen-removal-risk", choices=levels, default="high")
    parser.add_argument("--modular-component-count", type=positive_int, default=2)
    parser.add_argument("--internal-layer-complexity", choices=levels, default="high")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    raw_score = (
        LEVEL_SCORES[args.adhesive_level] * 20
        + INVERSE_LEVEL_SCORES[args.battery_removability] * 18
        + LEVEL_SCORES[args.screen_removal_risk] * 18
        + LEVEL_SCORES[args.internal_layer_complexity] * 16
        - min(args.modular_component_count, 8) * 4
    )
    repairability_pressure_score = max(0, raw_score)

    blockers: list[str] = []
    if args.battery_removability == "low":
        blockers.append("battery difficult to replace")
    if args.internal_layer_complexity == "high":
        blockers.append("stacked thermal assembly may require destructive or high-risk disassembly")
    if args.adhesive_level == "high" or args.screen_removal_risk == "high":
        blockers.append("bonded glass/frame complexity raises breakage risk")
    if args.modular_component_count <= 2:
        blockers.append("few modular replaceable subassemblies")

    print("Repairability pressure screening model")
    print_section("inputs", [
        f"adhesive_level: {args.adhesive_level}",
        f"battery_removability: {args.battery_removability}",
        f"screen_removal_risk: {args.screen_removal_risk}",
        f"modular_component_count: {args.modular_component_count}",
        f"internal_layer_complexity: {args.internal_layer_complexity}",
    ])
    print_section("formulas", [
        "score increases with adhesive, low battery removability, screen removal risk, and layer complexity",
        "score decreases with modular replaceable component count",
    ])
    print_section("outputs", [f"repairability_pressure_score: {repairability_pressure_score}"])
    print_section("likely repair blockers", blockers or ["none"])
    print_section("warnings", blockers or ["none"])
    print("confidence: low; service procedure design and teardown validation are required")
    print("basis: first-pass repairability pressure screen")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
