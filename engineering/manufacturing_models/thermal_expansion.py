#!/usr/bin/env python3
"""First-pass thermal expansion mismatch screen for bonded material pairs."""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
MATERIALS_PATH = REPO_ROOT / "engineering" / "constants" / "materials.yaml"

MATERIAL_ALIASES = {
    "aluminum": "aluminum_alloy",
    "magnesium": "magnesium_alloy",
    "copper": "copper",
    "graphite": "graphite_sheet",
    "ceramic": "ceramic",
    "glass": "glass",
    "pcb": "pcb_assembly",
}

PAIRS = [
    ("aluminum", "glass"),
    ("magnesium", "glass"),
    ("aluminum", "ceramic"),
    ("copper", "graphite"),
    ("pcb", "aluminum"),
]


def positive_float(value: str) -> float:
    parsed = float(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("value must be positive")
    return parsed


def print_section(title: str, rows: list[str]) -> None:
    print(f"{title}:")
    for row in rows:
        print(f"  - {row}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--delta-temp-c", type=positive_float, default=35.0)
    parser.add_argument("--bond-length-mm", type=positive_float, default=120.0)
    return parser.parse_args()


def load_cte_values() -> dict[str, float]:
    data = yaml.safe_load(MATERIALS_PATH.read_text(encoding="utf-8"))
    materials = data["materials"]
    values: dict[str, float] = {}
    for alias, material_key in MATERIAL_ALIASES.items():
        cte: Any = materials[material_key]["cte_per_c"]
        values[alias] = float(cte["typical"])
    return values


def expansion_mm(length_mm: float, cte_per_c: float, delta_temp_c: float) -> float:
    return length_mm * cte_per_c * delta_temp_c


def main() -> int:
    args = parse_args()
    cte_values = load_cte_values()
    rows: list[str] = []
    warnings: list[str] = []

    for material_a, material_b in PAIRS:
        expansion_a = expansion_mm(args.bond_length_mm, cte_values[material_a], args.delta_temp_c)
        expansion_b = expansion_mm(args.bond_length_mm, cte_values[material_b], args.delta_temp_c)
        mismatch = abs(expansion_a - expansion_b)
        rows.append(
            f"{material_a}/{material_b}: expansion_a_mm={expansion_a:.3f}, "
            f"expansion_b_mm={expansion_b:.3f}, mismatch_mm={mismatch:.3f}"
        )
        if mismatch >= 0.05:
            warnings.append(f"high mismatch for {material_a}/{material_b}; bonded interface stress risk")
        if mismatch >= 0.03:
            warnings.append(f"thermal cycling fatigue risk for {material_a}/{material_b} over long bonded surfaces")

    print("Thermal expansion mismatch screening model")
    print_section("inputs", [
        f"delta_temp_c: {args.delta_temp_c:.0f}",
        f"bond_length_mm: {args.bond_length_mm:.0f}",
    ])
    print_section("assumptions", [
        "CTE values use typical screening constants from engineering/constants/materials.yaml",
        "bonded interfaces are treated as straight free-expansion lengths before constraint effects",
        "adhesive compliance, part geometry, creep, and local features are not modeled",
    ])
    print_section("formulas", ["expansion_mm = length_mm * cte_per_c * delta_temp_c", "mismatch_mm = abs(expansion_a_mm - expansion_b_mm)"])
    print_section("outputs", rows)
    print_section("warnings", warnings or ["none"])
    print("confidence: low; use FEA and measured materials for bonded-stack reliability decisions")
    print("basis: first-pass CTE mismatch screen")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
