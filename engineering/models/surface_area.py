#!/usr/bin/env python3
"""Estimate external chassis surface area with a rectangular approximation."""

from __future__ import annotations

import argparse


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
    return parser.parse_args()


def rectangular_surface_area_cm2(length_mm: float, width_mm: float, thickness_mm: float) -> float:
    return 2 * (length_mm * width_mm + length_mm * thickness_mm + width_mm * thickness_mm) / 100


def rectangular_volume_cm3(length_mm: float, width_mm: float, thickness_mm: float) -> float:
    return length_mm * width_mm * thickness_mm / 1000


def main() -> int:
    args = parse_args()
    surface_area_cm2 = rectangular_surface_area_cm2(args.length_mm, args.width_mm, args.thickness_mm)
    volume_cm3 = rectangular_volume_cm3(args.length_mm, args.width_mm, args.thickness_mm)

    print("Surface area estimate")
    print("inputs:")
    print(f"  length_mm: {args.length_mm:.1f}")
    print(f"  width_mm: {args.width_mm:.1f}")
    print(f"  thickness_mm: {args.thickness_mm:.1f}")
    print("assumptions:")
    print("  rectangular approximation ignores rounded corners, camera plateau, buttons, ports, display curvature, and internal voids")
    print("  external surface area is not equivalent to effective radiating or user-safe heat-transfer area")
    print("formulas:")
    print("  surface_area_cm2 = 2 * (L*W + L*T + W*T) / 100")
    print("  volume_cm3 = L*W*T / 1000")
    print("outputs:")
    print(f"  surface_area_cm2: {surface_area_cm2:.1f}")
    print(f"  volume_cm3: {volume_cm3:.1f}")
    print("confidence: medium for rectangular geometry; low for actual usable thermal surface")
    print("basis: estimated")
    print("primary blocker: CAD-derived enclosure geometry and validated effective heat-spreading area")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
