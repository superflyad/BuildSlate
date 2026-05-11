#!/usr/bin/env python3
"""Estimate skin-temperature margin under different ambient conditions."""
from __future__ import annotations

import argparse
from collections.abc import Iterable


def positive_float(value: str) -> float:
    parsed = float(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("value must be greater than zero")
    return parsed


def print_section(title: str, rows: Iterable[str]) -> None:
    print(f"{title}:")
    rows = list(rows)
    if not rows:
        print("  none")
        return
    for row in rows:
        print(f"  - {row}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ambient-c", type=positive_float, default=25.0)
    parser.add_argument("--skin-rise-c", type=positive_float, default=18.0)
    parser.add_argument("--max-skin-c", type=positive_float, default=43.0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    estimated_skin_c = args.ambient_c + args.skin_rise_c
    margin_c = args.max_skin_c - estimated_skin_c

    warnings: list[str] = []
    if margin_c < 5:
        warnings.append("skin-temperature margin is below 5 C; workload or cooling assumptions need review")
    if estimated_skin_c > args.max_skin_c:
        warnings.append("estimated skin temperature exceeds the maximum skin-temperature target")
    if args.ambient_c >= 35:
        warnings.append("ambient temperature is at or above 35 C; hot-environment operation materially reduces thermal headroom")

    print("Ambient temperature skin-margin model")
    print_section("inputs", [
        f"ambient_c: {args.ambient_c:.1f}",
        f"skin_rise_c: {args.skin_rise_c:.1f}",
        f"max_skin_c: {args.max_skin_c:.1f}",
    ])
    print_section("assumptions", [
        "skin rise is treated as a fixed workload-driven delta above ambient",
        "ambient air is uniform around the device with no sunlight, enclosure, or hand-contact penalty",
        "maximum skin temperature is a screening target, not a compliance or certification limit",
    ])
    print_section("formulas", [
        "estimated_skin_c = ambient_c + skin_rise_c",
        "margin_c = max_skin_c - estimated_skin_c",
    ])
    print_section("outputs", [
        f"estimated_skin_c: {estimated_skin_c:.1f}",
        f"margin_c: {margin_c:.1f}",
    ])
    print_section("warnings", warnings)
    print("confidence: low; requires thermal chamber testing, skin-temperature mapping, and workload calibration")
    print("basis: first-pass environmental derating from ambient temperature to exterior skin margin")
    print("primary blocker: fixed skin-rise assumption does not capture enclosure, airflow, solar load, or dynamic throttling")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
