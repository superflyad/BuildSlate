#!/usr/bin/env python3
"""Estimate heat density, surface heat flux, and thermal risk."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
THERMAL_CONSTANTS_PATH = REPO_ROOT / "engineering" / "constants" / "thermal.yaml"


def load_constants() -> dict[str, Any]:
    with THERMAL_CONSTANTS_PATH.open("r", encoding="utf-8") as constants_file:
        data = yaml.safe_load(constants_file)
    if not isinstance(data, dict):
        raise ValueError("thermal constants must be a mapping")
    return data


def positive_float(value: str) -> float:
    parsed = float(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("value must be greater than zero")
    return parsed


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--length-mm", type=positive_float, default=180.0)
    parser.add_argument("--width-mm", type=positive_float, default=95.0)
    parser.add_argument("--thickness-mm", type=positive_float, default=8.8)
    parser.add_argument("--sustained-w", type=positive_float, default=28.0)
    return parser.parse_args()


def rectangular_surface_area_cm2(length_mm: float, width_mm: float, thickness_mm: float) -> float:
    return 2 * (length_mm * width_mm + length_mm * thickness_mm + width_mm * thickness_mm) / 100


def rectangular_volume_cm3(length_mm: float, width_mm: float, thickness_mm: float) -> float:
    return length_mm * width_mm * thickness_mm / 1000


def classify_risk(heat_density_w_cm3: float, thresholds: dict[str, float]) -> str:
    if heat_density_w_cm3 <= thresholds["low_max"]:
        return "low"
    if heat_density_w_cm3 <= thresholds["moderate_max"]:
        return "moderate"
    if heat_density_w_cm3 <= thresholds["high_max"]:
        return "high"
    return "extreme"


def main() -> int:
    args = parse_args()
    constants = load_constants()
    thresholds = constants["thermal_risk_heat_density_w_cm3"]
    pocket_reference = constants["passive_sustained_power_w"]["pocket_device"]

    volume_cm3 = rectangular_volume_cm3(args.length_mm, args.width_mm, args.thickness_mm)
    surface_area_cm2 = rectangular_surface_area_cm2(args.length_mm, args.width_mm, args.thickness_mm)
    heat_density_w_cm3 = args.sustained_w / volume_cm3
    heat_flux_w_cm2 = args.sustained_w / surface_area_cm2
    risk = classify_risk(heat_density_w_cm3, thresholds)

    print("Thermal limits estimate")
    print("inputs:")
    print(f"  length_mm: {args.length_mm:.1f}")
    print(f"  width_mm: {args.width_mm:.1f}")
    print(f"  thickness_mm: {args.thickness_mm:.1f}")
    print(f"  sustained_w: {args.sustained_w:.1f}")
    print("assumptions:")
    print("  constants_source: engineering/constants/thermal.yaml")
    print("  rectangular geometry is a screening approximation, not CAD or CFD")
    print("  all sustained electrical power is treated as heat inside the chassis")
    print("  passive references are conservative screening values, not device-specific limits")
    print("formulas:")
    print("  volume_cm3 = L*W*T / 1000")
    print("  heat_density_w_cm3 = sustained_w / volume_cm3")
    print("  surface_area_cm2 = 2 * (L*W + L*T + W*T) / 100")
    print("  heat_flux_w_cm2 = sustained_w / surface_area_cm2")
    print("outputs:")
    print(f"  volume_cm3: {volume_cm3:.1f}")
    print(f"  surface_area_cm2: {surface_area_cm2:.1f}")
    print(f"  heat_density_w_cm3: {heat_density_w_cm3:.3f}")
    print(f"  heat_flux_w_cm2: {heat_flux_w_cm2:.3f}")
    print("  passive_sustained_pocket_device_reference_w:")
    for profile, watts in pocket_reference.items():
        print(f"    {profile}: {watts}")
    print(f"  risk: {risk}")
    print("confidence: low")
    print("basis: estimated")
    print("primary blocker: thermal stack design, contact conditions, ambient temperature, controls, and measured skin temperature")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
