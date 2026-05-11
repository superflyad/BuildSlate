#!/usr/bin/env python3
"""Estimate additional display power and thermal load in sunlight or high-brightness modes."""
from __future__ import annotations

import argparse
from collections.abc import Iterable

BRIGHTNESS_MODES = {
    "dim": 0.5,
    "normal": 1.0,
    "bright": 1.5,
    "sunlight": 2.2,
}


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
    parser.add_argument("--base-display-w", type=positive_float, default=3.5)
    parser.add_argument("--brightness-mode", choices=sorted(BRIGHTNESS_MODES), default="normal")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    multiplier = BRIGHTNESS_MODES[args.brightness_mode]
    display_power_w = args.base_display_w * multiplier
    additional_power_w = display_power_w - args.base_display_w

    warnings: list[str] = []
    if args.brightness_mode == "sunlight":
        warnings.append("sunlight mode adds meaningful thermal load")
    if display_power_w >= 5.0:
        warnings.append("display power competes with AI sustained load and battery runtime")
    if args.brightness_mode in {"bright", "sunlight"}:
        warnings.append("high brightness plus charging plus AI is high risk")

    print("Sunlight display-load model")
    print_section("inputs", [
        f"base_display_w: {args.base_display_w:.1f}",
        f"brightness_mode: {args.brightness_mode}",
    ])
    print_section("assumptions", [
        f"brightness_multiplier: {multiplier:.2f}",
        "display power scales with a coarse brightness-mode multiplier",
        "solar heating of the enclosure is not included, so sunlight mode understates total outdoor thermal risk",
    ])
    print_section("formulas", [
        "display_power_w = base_display_w * multiplier",
        "additional_power_w = display_power_w - base_display_w",
    ])
    print_section("outputs", [
        f"display_power_w: {display_power_w:.1f}",
        f"additional_power_w: {additional_power_w:.1f}",
    ])
    print_section("warnings", warnings)
    print("confidence: low; panel, driver, brightness, APL, and sunlight readability data are required")
    print("basis: first-pass brightness multiplier for display thermal and runtime screening")
    print("primary blocker: no panel-specific luminance, APL, reflectance, or solar absorption model is included")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
