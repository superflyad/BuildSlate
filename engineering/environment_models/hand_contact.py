#!/usr/bin/env python3
"""Estimate thermal risk when hand contact reduces effective heat dissipation."""
from __future__ import annotations

import argparse
from collections.abc import Iterable


def positive_float(value: str) -> float:
    parsed = float(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("value must be greater than zero")
    return parsed


def percent_float(value: str) -> float:
    parsed = float(value)
    if parsed < 0 or parsed >= 100:
        raise argparse.ArgumentTypeError("value must be at least 0 and less than 100")
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
    parser.add_argument("--sustained-w", type=positive_float, default=28.0)
    parser.add_argument("--skin-area-cm2", type=positive_float, default=250.0)
    parser.add_argument("--hand-contact-percent", type=percent_float, default=35.0)
    parser.add_argument("--insulation-factor", type=positive_float, default=1.25)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    effective_area = args.skin_area_cm2 * (1 - args.hand_contact_percent / 100)
    heat_flux = args.sustained_w / effective_area
    adjusted_heat_flux = heat_flux * args.insulation_factor

    warnings: list[str] = []
    if effective_area < 150:
        warnings.append("effective area is too low for comfortable sustained heat spreading")
    if adjusted_heat_flux > 0.05:
        warnings.append("adjusted heat flux exceeds 0.05 W/cm2")
    if args.hand_contact_percent > 0:
        warnings.append("hand contact likely increases perceived temperature and reduces useful heat rejection")

    print("Hand-contact heat-flux model")
    print_section("inputs", [
        f"sustained_w: {args.sustained_w:.1f}",
        f"skin_area_cm2: {args.skin_area_cm2:.1f}",
        f"hand_contact_percent: {args.hand_contact_percent:.1f}",
        f"insulation_factor: {args.insulation_factor:.2f}",
    ])
    print_section("assumptions", [
        "hand coverage removes contacted skin area from effective heat-spreading surface",
        "insulation factor represents poorer convection and higher perceived temperature at contacted areas",
        "heat is treated as uniformly spread across the remaining area, which is optimistic for local hotspots",
    ])
    print_section("formulas", [
        "effective_area_cm2 = skin_area_cm2 * (1 - hand_contact_percent / 100)",
        "heat_flux_w_per_cm2 = sustained_w / effective_area_cm2",
        "adjusted_heat_flux_w_per_cm2 = heat_flux_w_per_cm2 * insulation_factor",
    ])
    print_section("outputs", [
        f"effective_area_cm2: {effective_area:.1f}",
        f"heat_flux_w_per_cm2: {heat_flux:.3f}",
        f"adjusted_heat_flux_w_per_cm2: {adjusted_heat_flux:.3f}",
    ])
    print_section("warnings", warnings)
    print("confidence: low; human grip, posture, material texture, and local hotspot tests are required")
    print("basis: first-pass contact-area derating for handheld thermal screening")
    print("primary blocker: uniform-area approximation ignores local SoC, battery, and display heat paths")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
