#!/usr/bin/env python3
"""Screen common chassis materials without declaring a universal winner."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
MATERIAL_CONSTANTS_PATH = REPO_ROOT / "engineering" / "constants" / "materials.yaml"
CANDIDATES = [
    "aluminum_alloy",
    "magnesium_alloy",
    "titanium_alloy",
    "stainless_steel",
    "ceramic",
    "glass",
]
RF_RISK = {
    "magnesium_alloy": 3,
    "aluminum_alloy": 3,
    "titanium_alloy": 3,
    "stainless_steel": 3,
    "ceramic": 1,
    "glass": 1,
}
MFG_RISK = {
    "aluminum_alloy": 1,
    "glass": 2,
    "magnesium_alloy": 3,
    "titanium_alloy": 3,
    "stainless_steel": 2,
    "ceramic": 3,
}
NOTES = {
    "aluminum_alloy": "Low mass among structural metals and strong heat spreading, but RF-hostile without antenna breaks/windows.",
    "magnesium_alloy": "Very light, but lower stiffness plus corrosion, coating, and process safety concerns need review.",
    "titanium_alloy": "Strong and premium, but heavier than aluminum/magnesium and not a good passive heat spreader.",
    "stainless_steel": "Strong and durable, but heavy and thermally modest for large phone-class shells.",
    "ceramic": "RF-friendly and premium, but grade-dependent mass, brittleness, cost, and heat-spreading limits matter.",
    "glass": "RF and wireless charging friendly, but poor heat spreading and impact/bonding reliability need validation.",
}


def load_materials() -> dict[str, Any]:
    with MATERIAL_CONSTANTS_PATH.open("r", encoding="utf-8") as constants_file:
        data = yaml.safe_load(constants_file)
    if not isinstance(data, dict) or not isinstance(data.get("materials"), dict):
        raise ValueError("materials constants must contain a top-level 'materials' mapping")
    return data["materials"]


def typical(entry: dict[str, Any], key: str) -> float:
    return float(entry[key]["typical"])


def risk_label(value: int) -> str:
    return {1: "low", 2: "medium", 3: "high"}[value]


def main() -> int:
    materials = load_materials()
    rows = []
    for name in CANDIDATES:
        entry = materials[name]
        density = typical(entry, "density_g_cm3")
        conductivity = typical(entry, "thermal_conductivity_w_mk")
        rf = RF_RISK[name]
        mfg = MFG_RISK[name]
        # Balanced screen: lower density, higher conductivity, lower RF risk, and lower manufacturing risk.
        # This is a sorting aid only and must not be treated as a single material recommendation.
        score = density - (conductivity / 100.0) + rf + mfg
        rows.append((score, name, density, conductivity, rf, mfg))

    rows.sort(key=lambda row: row[0])

    print("Material screening table")
    print("inputs:")
    print(f"  candidates: {', '.join(CANDIDATES)}")
    print("assumptions:")
    print("  constants_source: engineering/constants/materials.yaml")
    print("  ranking is a coarse screen by lower mass, higher thermal conductivity, RF risk, and manufacturability risk")
    print("  no universal winner is implied; final selection depends on antenna layout, thermal architecture, durability target, cosmetics, cost, and supply chain")
    print("formulas:")
    print("  mass_proxy = typical density_g_cm3")
    print("  thermal_proxy = typical thermal_conductivity_w_mk")
    print("  screen_score = density - thermal_conductivity/100 + rf_risk + manufacturability_risk")
    print("  lower screen_score prints earlier as a tradeoff aid, not a recommendation")
    print("outputs:")
    print("  rank | material | density_typ_g_cm3 | k_typ_w_mk | rf_risk | manufacturability_risk | screen_score")
    for idx, (score, name, density, conductivity, rf, mfg) in enumerate(rows, start=1):
        print(
            f"  {idx:>4} | {name:<16} | {density:>17.2f} | {conductivity:>10.1f} | "
            f"{risk_label(rf):<7} | {risk_label(mfg):<22} | {score:>12.2f}"
        )
    print("tradeoff_notes:")
    for _, name, *_ in rows:
        print(f"  - {name}: {NOTES[name]}")
    print("confidence: low")
    print("basis: first-order screening from conservative property ranges and qualitative RF/manufacturing risk labels")
    print("primary blocker: material choice cannot be finalized without antenna design, CAD stackup, measured thermal contacts, drop targets, cosmetic requirements, and vendor process data")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
