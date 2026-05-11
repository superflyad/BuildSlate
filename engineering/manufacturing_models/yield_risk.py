#!/usr/bin/env python3
"""First-pass manufacturing yield pressure indicator for dense thin-device assemblies."""
from __future__ import annotations

import argparse

LEVEL_SCORES = {"low": 1, "medium": 2, "high": 3}


def positive_float(value: str) -> float:
    parsed = float(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("value must be positive")
    return parsed


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
    parser.add_argument("--pcb-layer-count", type=positive_int, default=12)
    parser.add_argument("--memory-package-count", type=positive_int, default=16)
    parser.add_argument("--device-thickness-mm", type=positive_float, default=8.8)
    parser.add_argument("--thermal-stack-complexity", choices=("low", "medium", "high"), default="high")
    parser.add_argument("--antenna-window-count", type=positive_int, default=4)
    parser.add_argument("--camera-module-complexity", choices=("low", "medium", "high"), default="high")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    base_score = (
        args.pcb_layer_count * 3
        + args.memory_package_count * 2
        + LEVEL_SCORES[args.thermal_stack_complexity] * 14
        + args.antenna_window_count * 5
        + LEVEL_SCORES[args.camera_module_complexity] * 12
    )
    thin_device_multiplier = 1.30 if args.device_thickness_mm <= 9.0 else 1.10
    yield_risk_score = round(base_score * thin_device_multiplier)
    complexity_escalation = "high" if yield_risk_score >= 150 else "medium" if yield_risk_score >= 100 else "low"

    warnings: list[str] = []
    if args.memory_package_count >= 16 or args.pcb_layer_count >= 12:
        warnings.append("high packaging density")
    if args.device_thickness_mm <= 9.0:
        warnings.append("likely assembly sensitivity from thin-device clearance and inspection limits")
    if complexity_escalation == "high" or args.thermal_stack_complexity == "high" or args.camera_module_complexity == "high":
        warnings.append("high integration risk; factory yield cannot be inferred from this screen")

    print("Yield risk pressure screening model")
    print_section("inputs", [
        f"pcb_layer_count: {args.pcb_layer_count}",
        f"memory_package_count: {args.memory_package_count}",
        f"device_thickness_mm: {args.device_thickness_mm:.1f}",
        f"thermal_stack_complexity: {args.thermal_stack_complexity}",
        f"antenna_window_count: {args.antenna_window_count}",
        f"camera_module_complexity: {args.camera_module_complexity}",
    ])
    print_section("formulas", [
        "base_score = 3*pcb_layers + 2*memory_packages + thermal_complexity + antenna_windows + camera_complexity terms",
        "yield_risk_score = round(base_score * thin_device_multiplier)",
    ])
    print_section("outputs", [
        f"base_score: {base_score}",
        f"thin_device_multiplier: {thin_device_multiplier:.2f}",
        f"yield_risk_score: {yield_risk_score}",
        f"complexity_escalation: {complexity_escalation}",
    ])
    print_section("warnings", warnings or ["none"])
    print("confidence: low; indicator only, not a first-pass yield percentage or manufacturing feasibility claim")
    print("basis: conservative first-order yield pressure screen")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
