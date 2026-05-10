#!/usr/bin/env python3
"""Perform first-pass packaging sanity checks for Slate pocket v1."""

from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError as exc:  # pragma: no cover - dependency guidance path
    raise SystemExit("PyYAML is required. Install dependencies with: pip install -r requirements.txt") from exc

REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC_PATH = REPO_ROOT / "specs" / "slate-pocket-v1.yaml"

NOMINAL_VOLTAGE = 3.85
BATTERY_ENERGY_DENSITY_WH_PER_L = 700
BATTERY_PACK_OVERHEAD = 1.20

REQUIRED_FIELDS = (
    ("dimensions", "thickness_mm"),
    ("dimensions", "display_size_in"),
    ("weight", "target_g"),
    ("battery", "capacity_mah"),
    ("memory", "capacity_gb"),
    ("storage", "capacity_tb"),
)


def load_spec(path: Path = SPEC_PATH) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as spec_file:
        data = yaml.safe_load(spec_file)
    if not isinstance(data, dict):
        raise ValueError("spec root must be a mapping/object")
    return data


def get_required_number(spec: dict[str, Any], section: str, key: str) -> float:
    if section not in spec or not isinstance(spec[section], dict):
        raise ValueError(f"{section} is required")
    if key not in spec[section]:
        raise ValueError(f"{section}.{key} is required")
    value = spec[section][key]
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError(f"{section}.{key} must be numeric")
    return float(value)


def main() -> int:
    try:
        spec = load_spec()
        values = {f"{section}.{key}": get_required_number(spec, section, key) for section, key in REQUIRED_FIELDS}
    except Exception as exc:  # noqa: BLE001 - CLI reports validation failure directly.
        print(f"FAIL: {exc}")
        return 1

    capacity_mah = values["battery.capacity_mah"]
    thickness_mm = values["dimensions.thickness_mm"]
    display_size_in = values["dimensions.display_size_in"]
    target_g = values["weight.target_g"]
    memory_gb = values["memory.capacity_gb"]
    storage_tb = values["storage.capacity_tb"]

    battery_wh = capacity_mah * NOMINAL_VOLTAGE / 1000
    minimum_battery_volume_cm3 = (
        battery_wh / BATTERY_ENERGY_DENSITY_WH_PER_L * 1000 * BATTERY_PACK_OVERHEAD
    )

    print("Slate pocket dimensional constraints")
    print(f"  battery Wh: {battery_wh:.2f} Wh")
    print(f"  estimated battery volume: {minimum_battery_volume_cm3:.2f} cm^3")
    print(f"  display size target: {display_size_in:.1f} in")
    print(f"  thickness target: {thickness_mm:.1f} mm")
    print(f"  weight target: {target_g:.0f} g")
    print("  assumptions:")
    print(f"    nominal voltage: {NOMINAL_VOLTAGE:.2f} V")
    print(f"    battery energy density: {BATTERY_ENERGY_DENSITY_WH_PER_L} Wh/L")
    print(f"    battery pack overhead: {BATTERY_PACK_OVERHEAD:.2f}x")

    warnings = []
    if thickness_mm < 9 and memory_gb >= 512:
        warnings.append("8.x mm chassis with >=512GB memory requires aggressive package and thermal validation")
    if target_g <= 250 and capacity_mah >= 6000:
        warnings.append("<=250g target with >=6000mAh battery leaves limited mass for chassis and thermal stack")
    if storage_tb >= 4 and thickness_mm < 9:
        warnings.append(">=4TB storage in <9mm chassis may conflict with package thickness and heat spreading")

    if warnings:
        print("  warnings:")
        for warning in warnings:
            print(f"    - {warning}")
    else:
        print("  warnings: none")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
