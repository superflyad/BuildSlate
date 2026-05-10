#!/usr/bin/env python3
"""Compare a candidate chassis material for mass and simplified heat spreading."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
MATERIAL_CONSTANTS_PATH = REPO_ROOT / "engineering" / "constants" / "materials.yaml"

BLOCKERS = {
    "aluminum_alloy": "RF antenna breaks/windows and measured chassis contact resistance",
    "magnesium_alloy": "corrosion protection, manufacturing fire controls, and RF antenna isolation",
    "titanium_alloy": "low thermal conductivity, RF antenna isolation, machining cost, and mass penalty versus aluminum/magnesium",
    "stainless_steel": "high density and modest thermal spreading for large chassis volume",
    "copper": "very high density; best reserved for local heat hardware rather than full chassis shells",
    "graphite_sheet": "not a standalone structural chassis material and highly anisotropic",
    "ceramic": "brittle impact behavior, grade variation, mass, and limited heat spreading for zirconia-like grades",
    "glass": "poor heat spreading plus edge-impact and bonding reliability",
    "pcb_assembly": "not a chassis material; properties depend on stackup and component population",
    "battery_pack": "not a chassis material; safety, swelling, and directional thermal behavior dominate",
}


def load_materials() -> dict[str, Any]:
    with MATERIAL_CONSTANTS_PATH.open("r", encoding="utf-8") as constants_file:
        data = yaml.safe_load(constants_file)
    if not isinstance(data, dict) or not isinstance(data.get("materials"), dict):
        raise ValueError("materials constants must contain a top-level 'materials' mapping")
    return data["materials"]


def positive_float(value: str) -> float:
    parsed = float(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("value must be greater than zero")
    return parsed


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--material", required=True, help="Material key from engineering/constants/materials.yaml")
    parser.add_argument("--chassis-volume-cm3", type=positive_float, default=20.0)
    parser.add_argument("--heat-path-length-mm", type=positive_float, default=80.0)
    parser.add_argument("--cross-section-area-mm2", type=positive_float, default=150.0)
    parser.add_argument("--delta-temp-c", type=positive_float, default=10.0)
    return parser.parse_args()


def range_values(entry: dict[str, Any], key: str) -> tuple[float, float, float]:
    values = entry[key]
    return float(values["min"]), float(values["typical"]), float(values["max"])


def fmt_range(values: tuple[float, float, float], unit: str) -> str:
    return f"min {values[0]:.2g}, typical {values[1]:.2g}, max {values[2]:.2g} {unit}"


def main() -> int:
    args = parse_args()
    materials = load_materials()
    if args.material not in materials:
        available = ", ".join(sorted(materials))
        raise SystemExit(f"Unknown material '{args.material}'. Available materials: {available}")

    material = materials[args.material]
    density = range_values(material, "density_g_cm3")
    conductivity = range_values(material, "thermal_conductivity_w_mk")

    volume_cm3 = args.chassis_volume_cm3
    area_m2 = args.cross_section_area_mm2 * 1e-6
    length_m = args.heat_path_length_mm * 1e-3
    delta_t = args.delta_temp_c

    mass_range_g = tuple(d * volume_cm3 for d in density)
    heat_range_w = tuple(k * area_m2 * delta_t / length_m for k in conductivity)

    print("Material comparison model")
    print("inputs:")
    print(f"  material: {args.material}")
    print(f"  chassis_volume_cm3: {volume_cm3:.1f}")
    print(f"  heat_path_length_mm: {args.heat_path_length_mm:.1f}")
    print(f"  cross_section_area_mm2: {args.cross_section_area_mm2:.1f}")
    print(f"  delta_temp_c: {delta_t:.1f}")
    print("assumptions:")
    print("  constants_source: engineering/constants/materials.yaml")
    print("  material properties are conservative screening ranges, not vendor-certified values")
    print("  chassis mass is estimated as density * chassis_volume")
    print("  heat conduction is one-dimensional and ignores contact resistance, anisotropy, heat spreading geometry, and skin limits")
    print("formulas:")
    print("  chassis_mass_g = density_g_cm3 * chassis_volume_cm3")
    print("  Q = k * A * deltaT / L")
    print("  A_m2 = cross_section_area_mm2 * 1e-6")
    print("  L_m = heat_path_length_mm * 1e-3")
    print("outputs:")
    print(f"  material: {args.material}")
    print(f"  density_range: {fmt_range(density, 'g/cm^3')}")
    print(f"  thermal_conductivity_range: {fmt_range(conductivity, 'W/mK')}")
    print(f"  estimated_chassis_mass_range_g: {fmt_range(mass_range_g, 'g')}")
    print(f"  simplified_heat_conduction_range_w: {fmt_range(heat_range_w, 'W')}")
    print("confidence: low")
    print("basis: first-order screening from conservative material property ranges")
    print(f"primary blocker: {BLOCKERS.get(args.material, 'vendor material grade, geometry, RF, manufacturing, and measured thermal interfaces')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
