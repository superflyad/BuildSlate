#!/usr/bin/env python3
"""First-pass tolerance stackup screening for thin device assemblies."""
from __future__ import annotations

import argparse
import math


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
    parser.add_argument("--component-count", type=positive_int, default=12)
    parser.add_argument("--avg-tolerance-mm", type=positive_float, default=0.05)
    parser.add_argument("--target-clearance-mm", type=positive_float, default=0.30)
    parser.add_argument("--target-thickness-mm", type=positive_float, default=8.8)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    worst_case_mm = args.component_count * args.avg_tolerance_mm
    rss_mm = math.sqrt(args.component_count) * args.avg_tolerance_mm
    remaining_clearance_mm = args.target_clearance_mm - worst_case_mm
    passes = remaining_clearance_mm >= 0

    warnings: list[str] = []
    if remaining_clearance_mm < 0.2:
        warnings.append("remaining clearance is below 0.2 mm; tolerance stack should be reviewed before packaging claims")
    if worst_case_mm > args.target_clearance_mm:
        warnings.append("worst-case tolerance exceeds target clearance")
    if args.target_thickness_mm <= 9.0 and args.target_clearance_mm <= 0.4:
        warnings.append("thin-device assembly risk: small z-height reserve amplifies every tolerance contributor")

    print("Tolerance stackup screening model")
    print_section("inputs", [
        f"component_count: {args.component_count}",
        f"avg_tolerance_mm: {args.avg_tolerance_mm:.2f}",
        f"target_clearance_mm: {args.target_clearance_mm:.2f}",
        f"target_thickness_mm: {args.target_thickness_mm:.1f}",
    ])
    print_section("formulas", [
        "worst_case_mm = component_count * avg_tolerance_mm",
        "rss_mm = sqrt(component_count) * avg_tolerance_mm",
        "remaining_clearance_mm = target_clearance_mm - worst_case_mm",
    ])
    print_section("outputs", [
        f"worst_case_tolerance_mm: {worst_case_mm:.2f}",
        f"rss_tolerance_mm: {rss_mm:.2f}",
        f"remaining_clearance_mm: {remaining_clearance_mm:.2f}",
        f"screening_result: {'pass' if passes else 'fail'}",
    ])
    print_section("warnings", warnings or ["none"])
    print("confidence: medium for arithmetic; low for real assembly without measured part distributions")
    print("basis: conservative first-order tolerance stackup screen")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
