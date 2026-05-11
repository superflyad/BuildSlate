#!/usr/bin/env python3
"""First-pass manufacturing and assembly complexity pressure screen."""
from __future__ import annotations

import argparse


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
    parser.add_argument("--component-count", type=positive_int, default=25)
    parser.add_argument("--pcb-layer-count", type=positive_int, default=12)
    parser.add_argument("--camera-count", type=positive_int, default=3)
    parser.add_argument("--antenna-window-count", type=positive_int, default=4)
    parser.add_argument("--thermal-stack-layers", type=positive_int, default=5)
    parser.add_argument("--repairability-target", choices=("low", "medium", "high"), default="low")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repairability_factor = {"low": 8, "medium": 4, "high": 0}[args.repairability_target]
    base_score = (
        args.component_count
        + args.pcb_layer_count * 2
        + args.camera_count * 4
        + args.antenna_window_count * 3
        + args.thermal_stack_layers * 5
        + repairability_factor
    )
    thin_device_multiplier = 1.25 if args.pcb_layer_count >= 12 and args.thermal_stack_layers >= 5 else 1.10
    assembly_complexity_score = round(base_score * thin_device_multiplier)

    warnings: list[str] = []
    if assembly_complexity_score >= 90:
        warnings.append("high integration complexity")
    if args.pcb_layer_count >= 12 or args.component_count >= 25:
        warnings.append("likely yield pressure from dense assembly and inspection sensitivity")
    if args.repairability_target == "low" or args.thermal_stack_layers >= 5:
        warnings.append("repair difficulty: bonded or stacked assemblies may block clean disassembly")

    print("Assembly complexity screening model")
    print_section("inputs", [
        f"component_count: {args.component_count}",
        f"pcb_layer_count: {args.pcb_layer_count}",
        f"camera_count: {args.camera_count}",
        f"antenna_window_count: {args.antenna_window_count}",
        f"thermal_stack_layers: {args.thermal_stack_layers}",
        f"repairability_target: {args.repairability_target}",
    ])
    print_section("formulas", [
        "base_score = components + 2*pcb_layers + 4*cameras + 3*antenna_windows + 5*thermal_layers + repairability_factor",
        "assembly_complexity_score = round(base_score * thin_device_multiplier)",
    ])
    print_section("outputs", [
        f"base_score: {base_score}",
        f"thin_device_difficulty_multiplier: {thin_device_multiplier:.2f}",
        f"assembly_complexity_score: {assembly_complexity_score}",
    ])
    print_section("warnings", warnings or ["none"])
    print("confidence: low; this is a comparative pressure index, not a factory yield predictor")
    print("basis: first-pass manufacturing complexity screen")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
