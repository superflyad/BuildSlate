#!/usr/bin/env python3
"""Estimate first-pass component packaging pressure for Slate pocket v1."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
COMPONENT_LIBRARY_PATH = REPO_ROOT / "engineering" / "components" / "component_library.yaml"
PROFILES = ("conservative", "nominal", "aggressive")
DEVICE_LENGTH_MM = 180.0
DEVICE_WIDTH_MM = 95.0
PCB_AREA_FRACTION = 0.35
TARGET_THICKNESS_MM = 8.8
RIGID_THICKNESS_WARNING_MM = 2.5
HOTSPOT_TERMS = ("hotspot", "distributed hotspot", "charging heat", "rf heat")
PLACEMENT_COMPONENTS = (
    "soc_package",
    "memory_packages",
    "battery_pack",
    "vapor_chamber",
    "antenna_modules",
    "wireless_charging_coil",
    "rear_camera_module",
)
RIGID_COMPONENTS = (
    "main_pcb",
    "soc_package",
    "memory_packages",
    "storage_package",
    "rear_camera_module",
    "front_camera_module",
    "speakers",
    "haptics",
    "usb_c_port",
    "sensors",
    "tpm_or_security_chip",
)


def load_components() -> dict[str, dict[str, Any]]:
    with COMPONENT_LIBRARY_PATH.open("r", encoding="utf-8") as library_file:
        data = yaml.safe_load(library_file)
    if not isinstance(data, dict) or not isinstance(data.get("components"), dict):
        raise ValueError("component library must contain a components mapping")
    return data["components"]


def profile_value(component: dict[str, Any], field: str, profile: str) -> float:
    values = component.get(field)
    if not isinstance(values, dict) or profile not in values:
        raise ValueError(f"component field {field!r} missing profile {profile!r}")
    return float(values[profile])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=PROFILES, default="nominal")
    return parser.parse_args()


def thermal_hotspots(components: dict[str, dict[str, Any]]) -> list[str]:
    hotspots: list[str] = []
    for name, component in components.items():
        relevance = str(component.get("thermal_relevance", "")).lower()
        if any(term in relevance for term in HOTSPOT_TERMS):
            hotspots.append(f"{name}: {component.get('thermal_relevance')}")
    return hotspots


def placement_constraints(components: dict[str, dict[str, Any]]) -> dict[str, list[str]]:
    constraints: dict[str, list[str]] = {}
    for name in PLACEMENT_COMPONENTS:
        component = components.get(name, {})
        items = component.get("placement_constraints", [])
        constraints[name] = [str(item) for item in items]
    return constraints


def z_height_warnings(components: dict[str, dict[str, Any]], profile: str, z_stack_mm: float) -> list[str]:
    warnings: list[str] = []
    for name in RIGID_COMPONENTS:
        component = components[name]
        nominal_thickness_mm = profile_value(component, "thickness_mm", "nominal")
        if nominal_thickness_mm > RIGID_THICKNESS_WARNING_MM:
            warnings.append(
                f"{name} nominal thickness {nominal_thickness_mm:.2f} mm exceeds "
                f"{RIGID_THICKNESS_WARNING_MM:.1f} mm rigid-component screening threshold"
            )
    if z_stack_mm > TARGET_THICKNESS_MM:
        warnings.append(
            "battery_pack + vapor_chamber + display_module thickness "
            f"is {z_stack_mm:.2f} mm, exceeding {TARGET_THICKNESS_MM:.1f} mm target thickness"
        )
    return warnings


def print_mapping_of_lists(mapping: dict[str, list[str]], indent: str = "    ") -> None:
    for name, items in mapping.items():
        print(f"{indent}{name}:")
        if items:
            for item in items:
                print(f"{indent}  - {item}")
        else:
            print(f"{indent}  - no placement constraints listed")


def main() -> int:
    args = parse_args()
    components = load_components()
    profile = args.profile

    total_mass_g = sum(profile_value(c, "mass_g", profile) for c in components.values())
    total_volume_cm3 = sum(profile_value(c, "volume_cm3", profile) for c in components.values())
    total_idle_power_w = sum(profile_value(c, "idle_power_w", profile) for c in components.values())
    total_active_power_w = sum(profile_value(c, "active_power_w", profile) for c in components.values())
    pcb_area_used_mm2 = sum(profile_value(c, "pcb_area_mm2", profile) for c in components.values())
    available_pcb_area_mm2 = DEVICE_LENGTH_MM * DEVICE_WIDTH_MM * PCB_AREA_FRACTION
    pcb_utilization_percent = pcb_area_used_mm2 / available_pcb_area_mm2 * 100
    z_stack_mm = sum(
        profile_value(components[name], "thickness_mm", profile)
        for name in ("battery_pack", "vapor_chamber", "display_module")
    )
    warnings = z_height_warnings(components, profile, z_stack_mm)
    if pcb_utilization_percent > 85:
        warnings.append("PCB utilization exceeds 85%; routing, shielding, and rework margin are likely constrained")
    if total_active_power_w > 25:
        warnings.append("Total active component power exceeds 25 W placeholder handheld thermal screening level")

    print("Component packaging model")
    print("inputs:")
    print(f"  profile: {profile}")
    print(f"  component_library: {COMPONENT_LIBRARY_PATH.relative_to(REPO_ROOT)}")
    print("assumptions:")
    print("  component values are placeholder screening ranges, not vendor-certified values")
    print(f"  device_length_mm: {DEVICE_LENGTH_MM:.1f}")
    print(f"  device_width_mm: {DEVICE_WIDTH_MM:.1f}")
    print(f"  pcb_area_fraction: {PCB_AREA_FRACTION:.2f}")
    print(f"  target_thickness_mm: {TARGET_THICKNESS_MM:.1f}")
    print("  z_height_stack includes battery_pack + vapor_chamber + display_module only")
    print("formulas:")
    print("  total_component_mass_g = sum(component.mass_g[profile])")
    print("  total_component_volume_cm3 = sum(component.volume_cm3[profile])")
    print("  total_idle_power_w = sum(component.idle_power_w[profile])")
    print("  total_active_power_w = sum(component.active_power_w[profile])")
    print("  pcb_area_used_mm2 = sum(component.pcb_area_mm2[profile])")
    print("  available_pcb_area_mm2 = device_length_mm * device_width_mm * pcb_area_fraction")
    print("  pcb_utilization_percent = pcb_area_used_mm2 / available_pcb_area_mm2 * 100")
    print("  z_height_stack_mm = battery_pack + vapor_chamber + display_module thickness")
    print("outputs:")
    print(f"  profile: {profile}")
    print(f"  total_component_mass_g: {total_mass_g:.1f}")
    print(f"  total_component_volume_cm3: {total_volume_cm3:.1f}")
    print(f"  total_idle_power_w: {total_idle_power_w:.2f}")
    print(f"  total_active_power_w: {total_active_power_w:.2f}")
    print(f"  pcb_area_used_mm2: {pcb_area_used_mm2:.1f}")
    print(f"  available_pcb_area_mm2: {available_pcb_area_mm2:.1f}")
    print(f"  pcb_utilization_percent: {pcb_utilization_percent:.1f}")
    print(f"  z_height_stack_mm: {z_stack_mm:.2f}")
    print("  thermal_hotspots:")
    for hotspot in thermal_hotspots(components):
        print(f"    - {hotspot}")
    print("  placement_constraints:")
    print_mapping_of_lists(placement_constraints(components))
    print("warnings:")
    if warnings:
        for warning in warnings:
            print(f"  - {warning}")
    else:
        print("  - none for this screening profile")
    print("confidence: low")
    print("basis: placeholder component ranges in engineering/components/component_library.yaml")
    print("primary_blocker: vendor package data, ECAD placement, CAD stackups, thermal validation, and measured power")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
