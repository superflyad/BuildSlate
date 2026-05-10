#!/usr/bin/env python3
"""Estimate mixed-material chassis mass, RF exposure, and first-order heat conduction."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
MATERIAL_CONSTANTS_PATH = REPO_ROOT / "engineering" / "constants" / "materials.yaml"

PRESETS: dict[str, dict[str, float]] = {
    "aluminum_heat_frame_glass_windows": {
        "aluminum_volume_cm3": 14.0,
        "magnesium_volume_cm3": 0.0,
        "glass_volume_cm3": 6.0,
        "ceramic_volume_cm3": 0.0,
        "polymer_volume_cm3": 0.0,
        "graphite_volume_cm3": 1.5,
        "copper_volume_cm3": 1.0,
    },
    "magnesium_heat_frame_glass_windows": {
        "aluminum_volume_cm3": 0.0,
        "magnesium_volume_cm3": 14.0,
        "glass_volume_cm3": 6.0,
        "ceramic_volume_cm3": 0.0,
        "polymer_volume_cm3": 0.0,
        "graphite_volume_cm3": 1.5,
        "copper_volume_cm3": 1.0,
    },
    "hybrid_aluminum_magnesium_frame": {
        "aluminum_volume_cm3": 8.0,
        "magnesium_volume_cm3": 6.0,
        "glass_volume_cm3": 5.0,
        "ceramic_volume_cm3": 0.0,
        "polymer_volume_cm3": 1.0,
        "graphite_volume_cm3": 1.5,
        "copper_volume_cm3": 1.0,
    },
    "copper_vapor_graphite_spreader_stack": {
        "aluminum_volume_cm3": 6.0,
        "magnesium_volume_cm3": 4.0,
        "glass_volume_cm3": 4.0,
        "ceramic_volume_cm3": 0.0,
        "polymer_volume_cm3": 1.0,
        "graphite_volume_cm3": 3.0,
        "copper_volume_cm3": 2.0,
    },
}

MATERIAL_ALIASES = {
    "aluminum": ("aluminum_alloy", "aluminum"),
    "magnesium": ("magnesium_alloy", "magnesium"),
    "glass": ("glass",),
    "ceramic": ("ceramic",),
    "polymer": ("polymer", "plastic", "polycarbonate"),
    "graphite": ("graphite_sheet", "graphite"),
    "copper": ("copper",),
}

RF_FRIENDLY_MATERIALS = {"glass", "ceramic", "polymer"}
METAL_MATERIALS = {"aluminum", "magnesium", "copper"}
THERMAL_PATH_MATERIALS = {"aluminum", "magnesium", "graphite", "copper"}


@dataclass(frozen=True)
class MaterialProperty:
    constants_key: str
    density_g_cm3: float
    thermal_conductivity_w_mk: float


def load_materials() -> dict[str, Any]:
    with MATERIAL_CONSTANTS_PATH.open("r", encoding="utf-8") as constants_file:
        data = yaml.safe_load(constants_file)
    if not isinstance(data, dict) or not isinstance(data.get("materials"), dict):
        raise ValueError("materials constants must contain a top-level 'materials' mapping")
    return data["materials"]


def typical(entry: dict[str, Any], key: str) -> float:
    values = entry.get(key)
    if isinstance(values, dict) and "typical" in values:
        return float(values["typical"])
    raise ValueError(f"material entry is missing {key}.typical")


def resolve_material(materials: dict[str, Any], logical_name: str) -> MaterialProperty:
    for candidate_key in MATERIAL_ALIASES[logical_name]:
        if candidate_key in materials:
            entry = materials[candidate_key]
            return MaterialProperty(
                constants_key=candidate_key,
                density_g_cm3=typical(entry, "density_g_cm3"),
                thermal_conductivity_w_mk=typical(entry, "thermal_conductivity_w_mk"),
            )
    aliases = ", ".join(MATERIAL_ALIASES[logical_name])
    raise KeyError(f"No material constants found for {logical_name}; tried aliases: {aliases}")


def nonnegative_float(value: str) -> float:
    parsed = float(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("value must be zero or greater")
    return parsed


def positive_float(value: str) -> float:
    parsed = float(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("value must be greater than zero")
    return parsed


def add_volume_argument(parser: argparse.ArgumentParser, material: str) -> None:
    parser.add_argument(f"--{material}-volume-cm3", type=nonnegative_float, default=None)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preset", choices=sorted(PRESETS), help="Composite architecture preset")
    for material in ("aluminum", "magnesium", "glass", "ceramic", "polymer", "graphite", "copper"):
        add_volume_argument(parser, material)
    parser.add_argument("--heat-path-length-mm", type=positive_float, default=80.0)
    parser.add_argument("--heat-cross-section-area-mm2", type=positive_float, default=150.0)
    parser.add_argument("--delta-temp-c", type=positive_float, default=10.0)
    return parser.parse_args()


def selected_volumes(args: argparse.Namespace) -> dict[str, float]:
    preset_values = PRESETS.get(args.preset, {}) if args.preset else {}
    volumes = {}
    for material in MATERIAL_ALIASES:
        arg_name = f"{material}_volume_cm3"
        override = getattr(args, arg_name)
        volumes[material] = float(override if override is not None else preset_values.get(arg_name, 0.0))
    return volumes


def percent(part: float, whole: float) -> float:
    return (part / whole) * 100.0 if whole else 0.0


def fmt(value: float) -> str:
    return f"{value:.2f}"


def print_mapping(name: str, values: dict[str, float], unit: str = "") -> None:
    print(f"  {name}:")
    for key, value in values.items():
        suffix = f" {unit}" if unit else ""
        print(f"    {key}: {fmt(value)}{suffix}")


def risk_notes(
    rf_friendly_percent: float,
    metal_percent: float,
    total_mass_g: float,
    weighted_k: float,
    copper_volume_cm3: float,
) -> list[str]:
    notes = [
        "WARNING: weighted thermal conductivity is a crude screening approximation and does not represent true anisotropic heat spreading"
    ]
    if rf_friendly_percent < 20.0:
        notes.append("WARNING: antenna/RF design may be constrained because RF-friendly volume is below 20%")
    if metal_percent > 75.0:
        notes.append("WARNING: RF windows and antenna isolation become critical because metal volume exceeds 75%")
    if total_mass_g > 75.0:
        notes.append("WARNING: chassis/thermal stack mass is high for a 250g target")
    if weighted_k < 50.0:
        notes.append("WARNING: passive heat spreading may be weak because weighted thermal conductivity is below 50 W/mK")
    if copper_volume_cm3 > 2.0:
        notes.append("WARNING: copper improves heat transfer but quickly increases mass")
    return notes


def main() -> int:
    args = parse_args()
    constants = load_materials()
    properties = {name: resolve_material(constants, name) for name in MATERIAL_ALIASES}
    volumes_cm3 = selected_volumes(args)
    total_volume_cm3 = sum(volumes_cm3.values())
    if total_volume_cm3 <= 0:
        raise SystemExit("Total material volume must be greater than zero. Use --preset or pass material volume arguments.")

    mass_by_material_g = {
        material: volumes_cm3[material] * properties[material].density_g_cm3 for material in volumes_cm3
    }
    total_mass_g = sum(mass_by_material_g.values())
    volume_fractions = {material: volume / total_volume_cm3 for material, volume in volumes_cm3.items()}
    weighted_k = sum(
        properties[material].thermal_conductivity_w_mk * fraction for material, fraction in volume_fractions.items()
    )
    area_m2 = args.heat_cross_section_area_mm2 * 1e-6
    length_m = args.heat_path_length_mm * 1e-3
    simplified_conduction_w = weighted_k * area_m2 * args.delta_temp_c / length_m

    rf_volume = sum(volume for material, volume in volumes_cm3.items() if material in RF_FRIENDLY_MATERIALS)
    metal_volume = sum(volume for material, volume in volumes_cm3.items() if material in METAL_MATERIALS)
    thermal_path_volume = sum(volume for material, volume in volumes_cm3.items() if material in THERMAL_PATH_MATERIALS)
    rf_friendly_percent = percent(rf_volume, total_volume_cm3)
    metal_percent = percent(metal_volume, total_volume_cm3)
    thermal_path_percent = percent(thermal_path_volume, total_volume_cm3)

    print("Composite chassis model")
    print("inputs:")
    print(f"  preset: {args.preset or 'custom'}")
    print(f"  heat_path_length_mm: {fmt(args.heat_path_length_mm)}")
    print(f"  heat_cross_section_area_mm2: {fmt(args.heat_cross_section_area_mm2)}")
    print(f"  delta_temp_c: {fmt(args.delta_temp_c)}")
    print_mapping("material_volumes_cm3", volumes_cm3)
    print("assumptions:")
    print("  constants_source: engineering/constants/materials.yaml")
    print("  typical density and thermal conductivity values are used before min/max ranges")
    print("  graphite conductivity uses the graphite_sheet in-plane screening value when available")
    print("  magnesium is counted as a thermal-path material with lower confidence than aluminum/copper/graphite")
    print("  RF-friendly volume counts glass, ceramic, and polymer only")
    print("  vapor-chamber behavior is approximated as copper/graphite material volume, not modeled as two-phase flow")
    print("formulas:")
    print("  mass_g = volume_cm3 * density_g_cm3")
    print("  total_mass_g = sum(material_mass_g)")
    print("  volume_fraction = material_volume_cm3 / total_volume_cm3")
    print("  k_weighted = sum(k_material * volume_fraction)")
    print("  Q = k * A * deltaT / L")
    print("  A_m2 = heat_cross_section_area_mm2 * 1e-6")
    print("  L_m = heat_path_length_mm * 1e-3")
    print("  rf_friendly_percent = RF_friendly_volume / total_volume * 100")
    print("  metal_percent = metal_volume / total_volume * 100")
    print("  thermal_path_percent = thermal_path_volume / total_volume * 100")
    print("outputs:")
    print_mapping("material_volumes_cm3", volumes_cm3)
    print_mapping("mass_by_material_g", mass_by_material_g, "g")
    print(f"  total_volume_cm3: {fmt(total_volume_cm3)}")
    print(f"  total_mass_g: {fmt(total_mass_g)}")
    print_mapping("volume_fractions", volume_fractions)
    print(f"  weighted_thermal_conductivity_w_mk: {fmt(weighted_k)}")
    print(f"  simplified_conduction_w: {fmt(simplified_conduction_w)}")
    print(f"  rf_friendly_percent: {fmt(rf_friendly_percent)}")
    print(f"  metal_percent: {fmt(metal_percent)}")
    print(f"  thermal_path_percent: {fmt(thermal_path_percent)}")
    print("  resolved_material_constants:")
    for material, property_set in properties.items():
        print(f"    {material}: {property_set.constants_key}")
    print("risk_notes:")
    for note in risk_notes(rf_friendly_percent, metal_percent, total_mass_g, weighted_k, volumes_cm3["copper"]):
        print(f"  - {note}")
    print("confidence: low")
    print("basis: first-order screening from typical material constants, simple volume fractions, and one-dimensional conduction")
    print("primary_blocker: real feasibility requires CAD geometry, thermal contacts, anisotropic spreading, antenna layout, manufacturing process data, and CFD/FEA validation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
