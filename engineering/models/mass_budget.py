#!/usr/bin/env python3
"""Create a first-pass mass budget for Slate pocket v1."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
BATTERY_CONSTANTS_PATH = REPO_ROOT / "engineering" / "constants" / "battery.yaml"
COMPONENT_MASSES_G = {
    "display_module_g": 45,
    "pcb_and_soc_g": 35,
    "thermal_module_g": 35,
    "chassis_and_back_g": 55,
    "cameras_and_sensors_g": 15,
    "speakers_haptics_antennas_g": 15,
    "fasteners_adhesives_misc_g": 15,
}
PROFILES = ("conservative", "nominal", "aggressive")


def load_constants() -> dict[str, Any]:
    with BATTERY_CONSTANTS_PATH.open("r", encoding="utf-8") as constants_file:
        data = yaml.safe_load(constants_file)
    if not isinstance(data, dict):
        raise ValueError("battery constants must be a mapping")
    return data


def positive_float(value: str) -> float:
    parsed = float(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("value must be greater than zero")
    return parsed


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target-mass-g", type=positive_float, default=250.0)
    parser.add_argument("--battery-wh", type=positive_float, default=23.1)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    constants = load_constants()
    non_battery_mass_g = sum(COMPONENT_MASSES_G.values())

    print("Mass budget estimate")
    print("inputs:")
    print(f"  target_mass_g: {args.target_mass_g:.0f}")
    print(f"  battery_wh: {args.battery_wh:.1f}")
    print("assumptions:")
    print("  constants_source: engineering/constants/battery.yaml")
    print("  component masses are rough placeholders until CAD, BOM, and vendor data replace them")
    print("  battery mass uses pack-level gravimetric density as a screening range")
    print("formulas:")
    print("  battery_mass_g = battery_wh / Wh_per_kg * 1000")
    print("  total_mass_g = non_battery_component_mass_g + battery_mass_g")
    print("  margin_vs_target_g = target_mass_g - total_mass_g")
    print("outputs:")
    print("  estimated_component_masses_g:")
    for name, mass_g in COMPONENT_MASSES_G.items():
        print(f"    {name}: {mass_g}")
    print(f"  non_battery_component_mass_g: {non_battery_mass_g:.1f}")

    densities = constants["battery_gravimetric_energy_density_wh_per_kg"]
    for profile in PROFILES:
        battery_mass_g = args.battery_wh / densities[profile] * 1000
        total_mass_g = non_battery_mass_g + battery_mass_g
        margin_g = args.target_mass_g - total_mass_g
        print(f"  {profile}:")
        print(f"    battery_gravimetric_density_wh_per_kg: {densities[profile]}")
        print(f"    battery_mass_g: {battery_mass_g:.1f}")
        print(f"    total_mass_g: {total_mass_g:.1f}")
        print(f"    margin_vs_target_g: {margin_g:.1f}")
        print(f"    target_status: {'within target' if margin_g >= 0 else 'over target'}")

    print("confidence: low")
    print("basis: estimated")
    print("primary blocker: CAD-derived part masses, vendor component masses, battery packaging, and thermal-module design")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
