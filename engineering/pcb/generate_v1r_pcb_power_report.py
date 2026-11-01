#!/usr/bin/env python3
"""Generate the provisional Slate Pocket v1R PCB and power architecture screen."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
FLOORPLAN_PATH = REPO_ROOT / "engineering" / "pcb" / "slate-pocket-v1r-floorplan" / "floorplan.yaml"
POWER_TREE_PATH = REPO_ROOT / "engineering" / "pcb" / "power-tree.yaml"
REPORT_PATH = REPO_ROOT / "reports" / "slate-pocket-v1r-pcb-power-architecture.txt"


@dataclass(frozen=True)
class Rectangle:
    x: float
    y: float
    length: float
    width: float

    @property
    def right(self) -> float:
        return self.x + self.length

    @property
    def top(self) -> float:
        return self.y + self.width

    @property
    def area(self) -> float:
        return self.length * self.width

    def contains(self, other: "Rectangle") -> bool:
        return self.x <= other.x and self.y <= other.y and self.right >= other.right and self.top >= other.top

    def overlaps(self, other: "Rectangle") -> bool:
        return self.x < other.right and self.right > other.x and self.y < other.top and self.top > other.y


def _load(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as input_file:
        data = yaml.safe_load(input_file)
    if not isinstance(data, dict):
        raise ValueError(f"{path.relative_to(REPO_ROOT)} must contain a mapping")
    return data


def _rect(data: dict[str, Any]) -> Rectangle:
    return Rectangle(float(data["x"]), float(data["y"]), float(data["length"]), float(data["width"]))


def _scenario_power(scenario: dict[str, Any], loads: dict[str, Any]) -> float:
    column = scenario["load_column"]
    return sum(float(loads[load_id][column]) for load_id in scenario["included_loads"])


def build_report() -> str:
    floorplan = _load(FLOORPLAN_PATH)
    power_tree = _load(POWER_TREE_PATH)

    boundary = _rect(floorplan["board"]["component_side_boundary_mm"])
    placements = floorplan["placements"]
    rectangles = {item_id: _rect(item["rectangle_mm"]) for item_id, item in placements.items()}
    outside = [item_id for item_id, rectangle in rectangles.items() if not boundary.contains(rectangle)]
    overlaps: list[tuple[str, str]] = []
    placement_ids = list(placements)
    for index, first_id in enumerate(placement_ids):
        for second_id in placement_ids[index + 1 :]:
            if rectangles[first_id].overlaps(rectangles[second_id]):
                overlaps.append((first_id, second_id))

    occupied_area = sum(rectangle.area for rectangle in rectangles.values())
    occupancy_percent = occupied_area / boundary.area * 100.0
    memory_sites = [item_id for item_id, item in placements.items() if item["function"] == "lpddr5x_32gb_planning_site"]

    constraints = power_tree["source_constraints"]
    nominal_voltage = float(constraints["battery_nominal_voltage_v"])
    system_efficiency = float(constraints["system_conversion_efficiency"])
    scenario_results: list[tuple[str, float, float]] = []
    for scenario_id, scenario in power_tree["scenarios"].items():
        load_power = _scenario_power(scenario, power_tree["loads"])
        battery_current = load_power / (nominal_voltage * system_efficiency)
        scenario_results.append((scenario_id, load_power, battery_current))

    charge_voltage = float(constraints["battery_charge_voltage_screen_v"])
    wired_pack_power = float(constraints["wired_input_target_w"]) * float(constraints["wired_path_efficiency"])
    wireless_pack_power = float(constraints["wireless_input_target_w"]) * float(constraints["wireless_path_efficiency"])
    wired_charge_current = wired_pack_power / charge_voltage
    wireless_charge_current = wireless_pack_power / charge_voltage

    compute_rail = power_tree["rail_hypotheses"]["compute_core"]
    rail_voltage = float(compute_rail["nominal_voltage_v"])
    rail_peak_power = float(compute_rail["peak_power_w"])
    rail_peak_current = rail_peak_power / rail_voltage
    maximum_droop_v = rail_voltage * float(compute_rail["maximum_droop_percent"]) / 100.0
    target_impedance_mohm = maximum_droop_v / rail_peak_current * 1000.0

    lines = [
        "Slate Pocket v1R Provisional PCB and Power Architecture",
        "=========================================================",
        "",
        "Architecture basis:",
        f"  modeled memory tier: {floorplan['metadata']['modeled_memory_tier_gb']} GB",
        f"  memory planning sites: {len(memory_sites)} x 32 GB",
        "  512 GB topology modeled: no",
        f"  board outline: {floorplan['board']['outline_mm']['length']:.1f} x {floorplan['board']['outline_mm']['width']:.1f} x {floorplan['board']['outline_mm']['thickness']:.1f} mm",
        f"  assumed layer count: {floorplan['layer_stack']['assumed_total_layers']}",
        "",
        "Floorplan screen:",
        f"  planning blocks: {len(placements)}",
        f"  component-side occupancy before passives/routing: {occupancy_percent:.1f}%",
        f"  containment failures: {len(outside)}",
        f"  placement overlaps: {len(overlaps)}",
    ]
    for item_id in outside:
        lines.append(f"  - outside component boundary: {item_id}")
    for first_id, second_id in overlaps:
        lines.append(f"  - overlap: {first_id} with {second_id}")

    lines.extend(["", "System-load screen:"])
    for scenario_id, load_power, battery_current in scenario_results:
        lines.extend(
            [
                f"  - {scenario_id}",
                f"    internal load: {load_power:.1f} W",
                f"    battery current at {nominal_voltage:.2f} V and {system_efficiency:.0%} efficiency: {battery_current:.1f} A",
            ]
        )

    lines.extend(
        [
            "",
            "Charging boundary screen:",
            f"  100 W wired target estimated pack charge current at {charge_voltage:.2f} V: {wired_charge_current:.1f} A",
            f"  50 W wireless target estimated pack charge current at {charge_voltage:.2f} V: {wireless_charge_current:.1f} A",
            "  full-power wired plus sustained AI: PROHIBITED_UNTIL_VALIDATED",
            "  wireless charging plus sustained AI: PROHIBITED_UNTIL_VALIDATED",
            f"  EVT0 wired input cap before supplier derating: {power_tree['charging_policy']['evt0_wired_input_cap_w']} W",
            "  EVT0 wireless charging: DISABLED",
            "",
            "Compute-rail hypothesis:",
            f"  peak rail current at {rail_voltage:.2f} V: {rail_peak_current:.1f} A",
            f"  first-order target impedance for {compute_rail['maximum_droop_percent']:.1f}% droop: {target_impedance_mohm:.2f} mOhm",
            "  status: placeholder until platform rail map and load-step profile exist",
            "",
            "Routing and release gaps:",
            "  - No released package ball map, schematic, pin map, preliminary netlist, or escape study.",
            "  - No supplier stackup, impedance rules, via qualification, SI/PI analysis, or routed-board review.",
            "  - No selected PMIC, charger, protection path, battery pack, connector, cable, or charge curve.",
            "  - No verified loss map, safe charge/load overlap envelope, or thermal correlation.",
            "  - The 2 TB fallback requires an additional qualified storage path; 4 TB is not supported by the reviewed packages.",
            "",
            "PROVISIONAL_PCB_POWER_DECISION: BLOCKED_ON_PLATFORM_REFERENCE_DESIGN_AND_BATTERY_CHARGE_LIMITS",
            "",
            "Caveat:",
            "  This report exposes architecture pressure; it does not prove routing closure, electrical feasibility, signal integrity, power integrity, charge safety, thermal performance, manufacturability, or component availability.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    try:
        report = build_report()
    except (KeyError, TypeError, ValueError) as exc:
        print(f"FAIL: {exc}")
        return 1
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(report, encoding="utf-8")
    print(f"Wrote {REPORT_PATH.relative_to(REPO_ROOT)}")
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
