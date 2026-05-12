#!/usr/bin/env python3
"""Estimate heat density and flag first-pass thermal risk."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from engineering.core.calculator import Calculator
from engineering.core.explanation_engine import ExplanationEngine


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
    parser.add_argument("--explain", action="store_true", help="Print centralized thermal density calculation explanation")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    inputs = {
        "geometry.length_mm": args.length_mm,
        "geometry.width_mm": args.width_mm,
        "geometry.thickness_mm": args.thickness_mm,
        "thermal.sustained_w": args.sustained_watts,
    }
    calculator = Calculator()
    volume_cm3 = calculator.compute("geometry.volume_cm3", inputs)
    watts_per_cm3 = calculator.compute("thermal.heat_density_w_cm3", inputs)
    risk = classify_density(watts_per_cm3)

    print("Thermal density estimate")
    print("  note: simple chassis-volume approximation; not a CFD or skin-temperature model")
    print(f"  chassis volume: {volume_cm3:.2f} cm^3")
    print(f"  sustained power: {args.sustained_watts:.2f} W")
    print(f"  heat density: {watts_per_cm3:.3f} W/cm^3")
    print(f"  risk classification: {risk}")
    if args.explain:
        print("  explanation:")
        print(ExplanationEngine().explain("thermal.heat_density_w_cm3", inputs))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
