#!/usr/bin/env python3
"""Estimate heat density and flag first-pass thermal risk."""

from __future__ import annotations

import argparse


def classify_density(watts_per_cm3: float) -> str:
    if watts_per_cm3 < 0.05:
        return "low"
    if watts_per_cm3 < 0.12:
        return "moderate"
    if watts_per_cm3 < 0.25:
        return "high"
    return "extreme"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--length-mm", type=float, default=180.0)
    parser.add_argument("--width-mm", type=float, default=95.0)
    parser.add_argument("--thickness-mm", type=float, default=8.8)
    parser.add_argument("--sustained-watts", type=float, default=28.0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    volume_cm3 = args.length_mm * args.width_mm * args.thickness_mm / 1000
    watts_per_cm3 = args.sustained_watts / volume_cm3
    risk = classify_density(watts_per_cm3)

    print("Thermal density estimate")
    print("  note: simple chassis-volume approximation; not a CFD or skin-temperature model")
    print(f"  chassis volume: {volume_cm3:.2f} cm^3")
    print(f"  sustained power: {args.sustained_watts:.2f} W")
    print(f"  heat density: {watts_per_cm3:.3f} W/cm^3")
    print(f"  risk classification: {risk}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
