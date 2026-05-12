#!/usr/bin/env python3
"""Estimate external chassis surface area with a rectangular approximation."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from engineering.core.calculator import Calculator
from engineering.core.explanation_engine import ExplanationEngine


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
    parser.add_argument("--explain", action="store_true", help="Print centralized geometry calculation explanations")
    return parser.parse_args()


def core_inputs(length_mm: float, width_mm: float, thickness_mm: float) -> dict[str, float]:
    return {
        "geometry.length_mm": length_mm,
        "geometry.width_mm": width_mm,
        "geometry.thickness_mm": thickness_mm,
    }


def main() -> int:
    args = parse_args()
    calculator = Calculator()
    inputs = core_inputs(args.length_mm, args.width_mm, args.thickness_mm)
    surface_area_cm2 = calculator.compute("geometry.surface_area_cm2", inputs)
    volume_cm3 = calculator.compute("geometry.volume_cm3", inputs)

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
    if args.explain:
        explanation_engine = ExplanationEngine()
        print("explanation:")
        print(explanation_engine.explain("geometry.surface_area_cm2", inputs))
        print(explanation_engine.explain("geometry.volume_cm3", inputs))
    print("confidence: medium for rectangular geometry; low for actual usable thermal surface")
    print("basis: estimated")
    print("primary blocker: CAD-derived enclosure geometry and validated effective heat-spreading area")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
