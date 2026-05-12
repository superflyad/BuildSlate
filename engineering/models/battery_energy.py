#!/usr/bin/env python3
"""Calculate first-pass battery energy, runtime, volume, and mass ranges."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from engineering.core.calculator import Calculator
from engineering.core.explanation_engine import ExplanationEngine

BATTERY_CONSTANTS_PATH = REPO_ROOT / "engineering" / "constants" / "battery.yaml"
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
    parser.add_argument("--capacity-mah", type=positive_float, default=6000.0)
    parser.add_argument("--nominal-voltage-v", type=positive_float, default=3.85)
    parser.add_argument("--workload-w", type=positive_float, default=28.0)
    parser.add_argument(
        "--explain",
        action="store_true",
        help="Print the centralized battery energy calculation explanation",
    )
    return parser.parse_args()


def base_core_inputs(args: argparse.Namespace) -> dict[str, float]:
    return {
        "battery.capacity_mah": args.capacity_mah,
        "battery.nominal_voltage_v": args.nominal_voltage_v,
    }


def main() -> int:
    args = parse_args()
    constants = load_constants()
    calculator = Calculator()

    core_inputs = base_core_inputs(args)
    total_wh = calculator.compute("battery.energy_wh", core_inputs)

    print("Battery energy model")
    print("inputs:")
    print(f"  capacity_mAh: {args.capacity_mah:.0f}")
    print(f"  nominal_voltage_v: {args.nominal_voltage_v:.2f}")
    print(f"  workload_w: {args.workload_w:.2f}")
    print("assumptions:")
    print("  constants_source: engineering/constants/battery.yaml")
    print("  battery chemistry represented as nominal lithium-ion voltage")
    print("  usable capacity varies by reserve margin, discharge rate, temperature, and aging")
    print("formulas:")
    print("  Ah = mAh / 1000")
    print("  Wh = Ah * V")
    print("  usable_Wh = Wh * usable_capacity_factor")
    print("  runtime_h = usable_Wh / workload_w")
    print("  volume_L = Wh / volumetric_energy_density")
    print("  mass_kg = Wh / gravimetric_energy_density")
    print("outputs:")
    print(f"  total_energy_wh: {total_wh:.2f}")

    for profile in PROFILES:
        usable_factor = constants["usable_capacity_factor"][profile]
        volumetric_density = constants["battery_volumetric_energy_density_wh_per_l"][profile]
        gravimetric_density = constants["battery_gravimetric_energy_density_wh_per_kg"][profile]
        profile_inputs = {
            **core_inputs,
            "battery.usable_factor": usable_factor,
            "compute.sustained_power_w": args.workload_w,
            "battery.gravimetric_energy_density_wh_per_kg": gravimetric_density,
        }
        usable_wh = calculator.compute("battery.usable_wh", profile_inputs)
        runtime_h = calculator.compute("battery.runtime_h", profile_inputs)
        volume_l = total_wh / volumetric_density
        mass_g = calculator.compute("battery.mass_g", profile_inputs)
        mass_kg = mass_g / 1000
        print(f"  {profile}:")
        print(f"    usable_capacity_factor: {usable_factor:.2f}")
        print(f"    usable_wh: {usable_wh:.2f}")
        print(f"    runtime_h: {runtime_h:.2f}")
        print(f"    runtime_min: {runtime_h * 60:.0f}")
        print(f"    battery_volume_l: {volume_l:.3f}")
        print(f"    battery_volume_cm3: {volume_l * 1000:.1f}")
        print(f"    battery_mass_kg: {mass_kg:.3f}")
        print(f"    battery_mass_g: {mass_g:.1f}")

    if args.explain:
        print("explanation:")
        print(ExplanationEngine().explain("battery.energy_wh", core_inputs))

    print("confidence: medium for energy arithmetic; low for real-world runtime")
    print("basis: estimated")
    print(
        "primary blocker: validated workload power, cell packaging, thermal limits, "
        "and usable discharge policy"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
