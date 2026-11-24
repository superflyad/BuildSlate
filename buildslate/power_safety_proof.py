"""Audit a selected power design against its released parts and load budget.

The arithmetic and byte bindings are reproducible. Supplier ratings and safe
behavior still require engineering review and physical tests.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path

from buildslate.io import load_yaml
from buildslate.part_selection import RELEASE as SELECTED_BOM

RELEASE = Path("engineering/hardware/released/power/power-safety.json")
ELECTRICAL_BOM = Path("engineering/hardware/released/board.bom.csv")
BOARD = Path("engineering/hardware/released/board.kicad_pcb")
PROFILE = Path("configs/devices/slate-pocket-v1r.yaml")
LOADS = (
    "compute_platform",
    "memory_128gb",
    "storage_1tb",
    "display",
    "radios",
    "cameras",
    "system_io_and_controls",
)
POWER_COMPONENTS = ("charger", "pmic", "protection", "usb_pd")
FAULTS = (
    "battery_overvoltage",
    "battery_undervoltage",
    "battery_overcurrent",
    "battery_overtemperature",
    "charger_overcurrent",
    "usb_input_overvoltage",
)
BATTERY_RATINGS = (
    "min_voltage_v",
    "max_voltage_v",
    "max_charge_current_a",
    "max_continuous_discharge_a",
    "max_peak_discharge_a",
    "charge_temperature_min_c",
    "charge_temperature_max_c",
    "maximum_operating_temperature_c",
    "maximum_validated_charge_w",
)
LIMIT_FIELDS = (
    "operating_min_v",
    "normal_charge_termination_v",
    "charge_current_limit_a",
    "continuous_discharge_limit_a",
    "peak_discharge_limit_a",
    "charge_temperature_min_c",
    "charge_temperature_max_c",
    "battery_overvoltage_trip_v",
    "battery_undervoltage_trip_v",
    "battery_overtemperature_trip_c",
    "wired_input_cap_w",
    "charge_path_efficiency",
    "idle_system_w",
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _text(value: object) -> bool:
    return (
        isinstance(value, str)
        and bool(value.strip())
        and value.strip().lower()
        not in {
            "unknown",
            "placeholder",
            "tbd",
        }
    )


def _number(value: object) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _fail(errors: list[str]) -> dict:
    return {"status": "fail", "errors": errors}


def _electrical_parts(path: Path) -> dict[str, str]:
    with path.open("r", encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        if not reader.fieldnames or not {"ref", "manufacturer", "mpn"}.issubset(
            reader.fieldnames
        ):
            raise ValueError("Electrical BOM needs ref, manufacturer, and mpn")
        parts: dict[str, str] = {}
        for row in reader:
            ref = (row["ref"] or "").strip()
            mpn = (row["mpn"] or "").strip()
            if not ref or ref in parts or not mpn:
                raise ValueError("Electrical BOM has blank or duplicate part identity")
            parts[ref] = mpn
        if not parts:
            raise ValueError("Electrical BOM has no parts")
        return parts


def audit(root: Path) -> dict:
    """Require internally consistent limits, rail capacity, and source identity."""
    path = root / RELEASE
    if not path.is_file():
        return {"status": "missing", "errors": ["No released power safety design"]}
    upstream = {
        "selected_bom_sha256": root / SELECTED_BOM,
        "electrical_bom_sha256": root / ELECTRICAL_BOM,
        "routed_pcb_sha256": root / BOARD,
    }
    missing = [name for name, source in upstream.items() if not source.is_file()]
    if missing:
        return _fail([f"Missing power design source: {name}" for name in missing])
    try:
        release = json.loads(path.read_text(encoding="utf-8"))
        selected = json.loads((root / SELECTED_BOM).read_text(encoding="utf-8"))
        electrical = _electrical_parts(root / ELECTRICAL_BOM)
        profile = load_yaml(root / PROFILE)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as error:
        return _fail([f"Power design input cannot be read: {error}"])
    if not isinstance(release, dict) or not isinstance(selected, dict):
        return _fail(["Power release and selected BOM must be objects"])
    errors: list[str] = []
    if (
        release.get("schema_version") != 1
        or release.get("device") != "slate-pocket-v1r"
    ):
        errors.append("Unknown power release schema or device")
    for field in ("revision", "reviewed_by"):
        if not _text(release.get(field)):
            errors.append(f"Missing power release {field}")
    for field, source in upstream.items():
        if release.get(field) != _sha(source):
            errors.append(f"Power release is not bound to {field}")
    selected_parts = selected.get("parts")
    battery = (
        selected_parts.get("battery_pack") if isinstance(selected_parts, dict) else None
    )
    if not isinstance(battery, dict) or not isinstance(
        battery.get("capabilities"), dict
    ):
        return _fail(errors + ["Selected BOM has no battery pack ratings"])
    ratings = battery["capabilities"]
    if any(not _number(ratings.get(field)) for field in BATTERY_RATINGS):
        return _fail(errors + ["Selected battery pack ratings are incomplete"])
    if not (
        0 < ratings["min_voltage_v"] < ratings["max_voltage_v"]
        and ratings["max_charge_current_a"] > 0
        and 0 < ratings["max_continuous_discharge_a"] <= ratings["max_peak_discharge_a"]
        and ratings["maximum_validated_charge_w"] > 0
        and ratings["charge_temperature_min_c"]
        < ratings["charge_temperature_max_c"]
        <= ratings["maximum_operating_temperature_c"]
    ):
        errors.append("Selected battery pack ratings are inconsistent")
    if battery.get("mpn") != release.get("battery_mpn") or not _text(
        release.get("battery_mpn")
    ):
        errors.append("Power design battery MPN differs from selected BOM")
    components = release.get("power_components")
    if not isinstance(components, dict) or set(components) != set(POWER_COMPONENTS):
        errors.append("Power component inventory is incomplete")
        components = {}
    refs: set[str] = set()
    for role in POWER_COMPONENTS:
        item = components.get(role)
        if (
            not isinstance(item, dict)
            or not _text(item.get("ref"))
            or not _text(item.get("mpn"))
        ):
            errors.append(f"Missing selected electrical part for {role}")
            continue
        if item["ref"] in refs or electrical.get(item["ref"]) != item["mpn"]:
            errors.append(f"Power component {role} differs from electrical BOM")
        refs.add(item["ref"])
    limits = release.get("limits")
    if not isinstance(limits, dict) or any(
        not _number(limits.get(field)) for field in LIMIT_FIELDS
    ):
        return _fail(errors + ["Power operating or fault limits are incomplete"])
    if (
        limits.get("wireless_enabled") is not False
        or limits.get("full_power_charge_ai_overlap") is not False
    ):
        errors.append("EVT0 wireless or full-power charge/AI overlap is enabled")
    if not (
        ratings["min_voltage_v"]
        <= limits["battery_undervoltage_trip_v"]
        <= limits["operating_min_v"]
        < limits["normal_charge_termination_v"]
        <= limits["battery_overvoltage_trip_v"]
        <= ratings["max_voltage_v"]
    ):
        errors.append("Battery voltage operating and protection thresholds conflict")
    if not (
        ratings["charge_temperature_min_c"]
        <= limits["charge_temperature_min_c"]
        < limits["charge_temperature_max_c"]
        <= ratings["charge_temperature_max_c"]
        <= limits["battery_overtemperature_trip_c"]
        <= ratings["maximum_operating_temperature_c"]
    ):
        errors.append(
            "Battery temperature operating and protection thresholds conflict"
        )
    if not (
        0 < limits["charge_current_limit_a"] <= ratings["max_charge_current_a"]
        and limits["charge_current_limit_a"] * limits["normal_charge_termination_v"]
        <= ratings["maximum_validated_charge_w"]
    ):
        errors.append("Charge current or power exceeds selected battery rating")
    if not (
        0
        < limits["continuous_discharge_limit_a"]
        <= ratings["max_continuous_discharge_a"]
        <= ratings["max_peak_discharge_a"]
        and limits["continuous_discharge_limit_a"]
        <= limits["peak_discharge_limit_a"]
        <= ratings["max_peak_discharge_a"]
    ):
        errors.append("Discharge limits exceed selected battery rating")
    evt0_cap = profile["integration_configuration"]["wired_charge_evt0_input_cap_w"]
    if not (
        0 < limits["wired_input_cap_w"] <= evt0_cap
        and 0 < limits["charge_path_efficiency"] <= 1
        and limits["idle_system_w"] >= 0
    ):
        errors.append("Charge path limits or efficiency are invalid")
    else:
        required_input_w = (
            limits["charge_current_limit_a"]
            * limits["normal_charge_termination_v"]
            / limits["charge_path_efficiency"]
            + limits["idle_system_w"]
        )
        if required_input_w > limits["wired_input_cap_w"]:
            errors.append("Charge path exceeds the EVT0 wired-input cap")
    loads = release.get("loads")
    if not isinstance(loads, list):
        loads = []
    load_by_id: dict[str, dict] = {}
    for load in loads:
        if not isinstance(load, dict) or not _text(load.get("id")):
            errors.append("Power load has no identity")
            continue
        identifier = load["id"]
        if identifier in load_by_id:
            errors.append(f"Duplicate power load: {identifier}")
            continue
        if (
            not _number(load.get("continuous_w"))
            or not _number(load.get("peak_w"))
            or load["continuous_w"] < 0
            or load["peak_w"] < load["continuous_w"]
        ):
            errors.append(f"Power load has invalid watts: {identifier}")
            continue
        load_by_id[identifier] = load
    if set(load_by_id) != set(LOADS):
        errors.append("Power loads do not cover the EVT0 subsystem inventory")
    compute = load_by_id.get("compute_platform")
    if compute and (
        compute["continuous_w"] < profile["compute"]["sustained_power_w"]
        or compute["peak_w"] < profile["compute"]["peak_power_w"]
    ):
        errors.append("Compute power load is below the approved profile")
    rails = release.get("rails")
    if not isinstance(rails, list) or not rails:
        rails = []
        errors.append("Power release has no output rails")
    rail_by_id: dict[str, dict] = {}
    assigned: list[str] = []
    continuous_battery_w = 0.0
    peak_battery_w = 0.0
    for rail in rails:
        if not isinstance(rail, dict) or not _text(rail.get("id")):
            errors.append("Power rail has no identity")
            continue
        identifier = rail["id"]
        if identifier in rail_by_id:
            errors.append(f"Duplicate power rail: {identifier}")
            continue
        rail_by_id[identifier] = rail
        ids = rail.get("load_ids")
        if not isinstance(ids, list) or not ids or any(not _text(item) for item in ids):
            errors.append(f"Power rail {identifier} has no valid load list")
            continue
        assigned.extend(ids)
        fields = ("voltage_v", "efficiency", "continuous_current_a", "peak_current_a")
        if any(not _number(rail.get(field)) for field in fields) or any(
            item not in load_by_id for item in ids
        ):
            errors.append(f"Power rail {identifier} has invalid ratings or loads")
            continue
        voltage = rail["voltage_v"]
        efficiency = rail["efficiency"]
        if (
            voltage <= 0
            or not 0 < efficiency <= 1
            or rail["continuous_current_a"] <= 0
            or rail["peak_current_a"] < rail["continuous_current_a"]
        ):
            errors.append(f"Power rail {identifier} has invalid limits")
            continue
        continuous = sum(load_by_id[item]["continuous_w"] for item in ids)
        peak = sum(load_by_id[item]["peak_w"] for item in ids)
        if (
            continuous > voltage * rail["continuous_current_a"]
            or peak > voltage * rail["peak_current_a"]
        ):
            errors.append(f"Power rail {identifier} cannot supply declared loads")
        continuous_battery_w += continuous / efficiency
        peak_battery_w += peak / efficiency
    if sorted(assigned) != sorted(LOADS):
        errors.append("Every EVT0 load must be assigned to exactly one power rail")
    sequence = release.get("rail_sequence")
    if (
        not isinstance(sequence, list)
        or len(sequence) != len(rail_by_id)
        or any(not _text(item) for item in sequence)
        or set(sequence) != set(rail_by_id)
    ):
        errors.append("Power rail sequence is incomplete or duplicated")
    else:
        position = {identifier: index for index, identifier in enumerate(sequence)}
        for identifier, rail in rail_by_id.items():
            parents = rail.get("depends_on")
            if not isinstance(parents, list) or any(
                not _text(parent) for parent in parents
            ):
                errors.append(
                    f"Power rail {identifier} has invalid startup dependencies"
                )
            elif len(parents) != len(set(parents)) or any(
                parent not in position or position[parent] >= position[identifier]
                for parent in parents
            ):
                errors.append(
                    f"Power rail {identifier} has invalid startup dependencies"
                )
    continuous_battery_a = (
        continuous_battery_w / limits["operating_min_v"]
        if limits["operating_min_v"] > 0
        else math.inf
    )
    peak_battery_a = (
        peak_battery_w / limits["operating_min_v"]
        if limits["operating_min_v"] > 0
        else math.inf
    )
    if (
        continuous_battery_a > limits["continuous_discharge_limit_a"]
        or peak_battery_a > limits["peak_discharge_limit_a"]
    ):
        errors.append("Battery current budget exceeds released discharge limits")
    faults = release.get("fault_controls")
    if (
        not isinstance(faults, dict)
        or set(faults) != set(FAULTS)
        or any(
            not isinstance(faults.get(identifier), dict)
            or not _text(faults[identifier].get("hardware_action"))
            or faults[identifier].get("hardware_ref") not in refs
            or not _text(faults[identifier].get("firmware_action"))
            for identifier in FAULTS
        )
    ):
        errors.append(
            "Power fault controls lack selected hardware and firmware actions"
        )
    return {
        "status": "pass" if not errors else "fail",
        "source": RELEASE.as_posix(),
        "revision": release.get("revision"),
        "reviewed_by": release.get("reviewed_by"),
        "selected_bom_sha256": release.get("selected_bom_sha256"),
        "electrical_bom_sha256": release.get("electrical_bom_sha256"),
        "routed_pcb_sha256": release.get("routed_pcb_sha256"),
        "loads_checked": len(load_by_id),
        "rails_checked": len(rail_by_id),
        "continuous_battery_current_a": round(continuous_battery_a, 3),
        "peak_battery_current_a": round(peak_battery_a, 3),
        "errors": errors,
        "caveat": "Internal consistency does not verify supplier ratings, safe protection thresholds, circuit implementation, or physical behavior.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    result = audit(args.repo_root)
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
