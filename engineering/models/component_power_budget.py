#!/usr/bin/env python3
"""Break down Slate pocket v1 idle and active component power."""

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


def runtime_hours(battery_wh: float, power_w: float) -> float | None:
    if power_w <= 0:
        return None
    return battery_wh / power_w


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=PROFILES, default="nominal")
    parser.add_argument("--battery-wh", type=positive_float, default=23.1)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    components = load_components()
    idle_power = {name: profile_value(component, "idle_power_w", args.profile) for name, component in components.items()}
    active_power = {name: profile_value(component, "active_power_w", args.profile) for name, component in components.items()}
    total_idle_power_w = sum(idle_power.values())
    total_active_power_w = sum(active_power.values())
    idle_runtime_h = runtime_hours(args.battery_wh, total_idle_power_w)
    active_runtime_h = runtime_hours(args.battery_wh, total_active_power_w)
    top_active_drivers = sorted(active_power.items(), key=lambda item: item[1], reverse=True)[:5]

    print("Component power budget model")
    print("inputs:")
    print(f"  profile: {args.profile}")
    print(f"  battery_wh: {args.battery_wh:.1f}")
    print(f"  component_library: {COMPONENT_LIBRARY_PATH.relative_to(REPO_ROOT)}")
    print("assumptions:")
    print("  idle and active power values are placeholder screening ranges, not measured workload data")
    print("  active runtime assumes all listed active loads occur simultaneously, so it is a stress-case estimate")
    print("  runtime excludes conversion losses, aging, temperature derating, and battery reserve")
    print("formulas:")
    print("  total_idle_power_w = sum(component.idle_power_w[profile])")
    print("  total_active_power_w = sum(component.active_power_w[profile])")
    print("  estimated_idle_runtime_h = battery_wh / total_idle_power_w")
    print("  estimated_active_runtime_h = battery_wh / total_active_power_w")
    print("outputs:")
    print("  idle_power_by_component_w:")
    for name, power_w in idle_power.items():
        print(f"    {name}: {power_w:.3f}")
    print("  active_power_by_component_w:")
    for name, power_w in active_power.items():
        print(f"    {name}: {power_w:.3f}")
    print(f"  total_idle_power_w: {total_idle_power_w:.2f}")
    print(f"  total_active_power_w: {total_active_power_w:.2f}")
    print(f"  estimated_idle_runtime_h: {idle_runtime_h:.2f}" if idle_runtime_h else "  estimated_idle_runtime_h: undefined")
    print(f"  estimated_active_runtime_h: {active_runtime_h:.2f}" if active_runtime_h else "  estimated_active_runtime_h: undefined")
    print("  top_5_active_power_drivers:")
    for name, power_w in top_active_drivers:
        print(f"    - {name}: {power_w:.2f}")
    print("warnings:")
    if total_active_power_w > 25:
        print("  - total active power exceeds 25 W placeholder handheld thermal screening level")
    else:
        print("  - none for this screening profile")
    print("confidence: low")
    print("basis: placeholder component power values in engineering/components/component_library.yaml")
    print("primary_blocker: measured workload power, PMIC efficiency, display brightness curves, RF duty cycle, and battery derating")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
