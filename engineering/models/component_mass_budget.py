#!/usr/bin/env python3
"""Break down Slate pocket v1 mass by component category."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
COMPONENT_LIBRARY_PATH = REPO_ROOT / "engineering" / "components" / "component_library.yaml"
PROFILES = ("conservative", "nominal", "aggressive")


def load_components() -> dict[str, dict[str, Any]]:
    with COMPONENT_LIBRARY_PATH.open("r", encoding="utf-8") as library_file:
        data = yaml.safe_load(library_file)
    if not isinstance(data, dict) or not isinstance(data.get("components"), dict):
        raise ValueError("component library must contain a components mapping")
    return data["components"]


def positive_float(value: str) -> float:
    parsed = float(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("value must be greater than zero")
    return parsed


def profile_value(component: dict[str, Any], field: str, profile: str) -> float:
    values = component.get(field)
    if not isinstance(values, dict) or profile not in values:
        raise ValueError(f"component field {field!r} missing profile {profile!r}")
    return float(values[profile])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=PROFILES, default="nominal")
    parser.add_argument("--target-mass-g", type=positive_float, default=250.0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    components = load_components()
    masses = {name: profile_value(component, "mass_g", args.profile) for name, component in components.items()}
    total_mass_g = sum(masses.values())
    margin_g = args.target_mass_g - total_mass_g
    top_drivers = sorted(masses.items(), key=lambda item: item[1], reverse=True)[:5]

    print("Component mass budget model")
    print("inputs:")
    print(f"  profile: {args.profile}")
    print(f"  target_mass_g: {args.target_mass_g:.1f}")
    print(f"  component_library: {COMPONENT_LIBRARY_PATH.relative_to(REPO_ROOT)}")
    print("assumptions:")
    print("  mass values are placeholder screening ranges, not measured part masses")
    print("  conservative profile represents heavier packaging burden; aggressive is optimistic")
    print("formulas:")
    print("  component_mass_g = component.mass_g[profile]")
    print("  total_mass_g = sum(component_mass_g)")
    print("  margin_vs_target_g = target_mass_g - total_mass_g")
    print("outputs:")
    print("  mass_by_component_g:")
    for name, mass_g in masses.items():
        print(f"    {name}: {mass_g:.1f}")
    print(f"  total_mass_g: {total_mass_g:.1f}")
    print(f"  margin_vs_target_g: {margin_g:.1f}")
    print("  top_5_mass_drivers:")
    for name, mass_g in top_drivers:
        print(f"    - {name}: {mass_g:.1f}")
    print("warnings:")
    if margin_g < 0:
        print(f"  - total component mass exceeds target by {-margin_g:.1f} g")
    else:
        print("  - none for this screening profile")
    print("confidence: low")
    print("basis: placeholder component masses in engineering/components/component_library.yaml")
    print("primary_blocker: vendor part masses, CAD-derived mechanical allowances, and battery pack selection")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
