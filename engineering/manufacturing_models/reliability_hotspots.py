#!/usr/bin/env python3
"""First-pass reliability hotspot identification for thin AI-device architectures."""
from __future__ import annotations

import argparse


def positive_float(value: str) -> float:
    parsed = float(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("value must be positive")
    return parsed


def print_section(title: str, rows: list[str]) -> None:
    print(f"{title}:")
    for row in rows:
        print(f"  - {row}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sustained-power-w", type=positive_float, default=28.0)
    parser.add_argument("--device-thickness-mm", type=positive_float, default=8.8)
    parser.add_argument("--battery-thickness-mm", type=positive_float, default=4.5)
    parser.add_argument("--camera-module-depth-mm", type=positive_float, default=5.0)
    parser.add_argument("--wireless-charging-w", type=positive_float, default=50.0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    hotspots: dict[str, list[str]] = {
        "thermal hotspot zones": [],
        "structural weak zones": [],
        "battery pressure zones": [],
        "connector stress zones": [],
        "camera island stress zones": [],
    }

    if args.sustained_power_w >= 20:
        hotspots["thermal hotspot zones"].append("SoC/NPU, memory packages, vapor chamber interface, and exterior skin above compute region")
    if args.wireless_charging_w >= 30:
        hotspots["thermal hotspot zones"].append("wireless charging coil, ferrite stack, rear glass, and adjacent battery face")
    if args.device_thickness_mm <= 9.0:
        hotspots["structural weak zones"].append("thin midframe rails, antenna window breaks, button cutouts, and large glass spans")
    if args.battery_thickness_mm / args.device_thickness_mm >= 0.45:
        hotspots["battery pressure zones"].append("battery-to-display and battery-to-rear-housing clearance stack")
    hotspots["connector stress zones"].append("flex tails crossing hinge-like bend regions, board-to-board connectors, and charging port anchors")
    if args.camera_module_depth_mm / args.device_thickness_mm >= 0.50:
        hotspots["camera island stress zones"].append("camera bump perimeter, lens stack adhesive, OIS module mounts, and local frame step")

    print("Reliability hotspot screening model")
    print_section("inputs", [
        f"sustained_power_w: {args.sustained_power_w:.0f}",
        f"device_thickness_mm: {args.device_thickness_mm:.1f}",
        f"battery_thickness_mm: {args.battery_thickness_mm:.1f}",
        f"camera_module_depth_mm: {args.camera_module_depth_mm:.1f}",
        f"wireless_charging_w: {args.wireless_charging_w:.0f}",
    ])
    print_section("assumptions", [
        "hotspots are qualitative screens from concentration of heat, load paths, z-height, or repeated assembly stress",
        "drop, vibration, thermal cycling, corrosion, ingress, and connector life are not quantified",
    ])
    for category, rows in hotspots.items():
        print_section(category, rows or ["not triggered by default thresholds"])
    print_section("warnings", [
        "thermal, structural, battery, connector, and camera concentrations should be reviewed together, not independently",
        "hotspot list is not a durability prediction or qualification result",
    ])
    print("confidence: low; physical prototypes, FEA, thermal tests, and reliability qualification are required")
    print("basis: first-pass reliability-critical region screen")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
