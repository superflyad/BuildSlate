#!/usr/bin/env python3
"""Zone-based local z-height stackup screening model."""

from __future__ import annotations

import argparse
from collections import OrderedDict

from common import positive_float, print_section

ZONES: dict[str, OrderedDict[str, float]] = {
    "display_general_zone": OrderedDict(
        [
            ("cover_glass", 0.6),
            ("display_module", 1.2),
            ("adhesive", 0.2),
            ("midframe_allowance", 0.7),
            ("rear_housing", 0.8),
        ]
    ),
    "battery_zone": OrderedDict(
        [
            ("cover_glass", 0.6),
            ("display_module", 1.2),
            ("adhesive", 0.2),
            ("battery_pack", 4.5),
            ("swelling_allowance", 0.4),
            ("rear_housing", 0.8),
        ]
    ),
    "soc_memory_zone": OrderedDict(
        [
            ("cover_glass", 0.6),
            ("display_module", 1.2),
            ("adhesive", 0.2),
            ("vapor_chamber", 0.8),
            ("pcb", 0.8),
            ("package_height", 1.5),
            ("rear_housing", 0.8),
            ("thermal_interface_allowance", 0.2),
        ]
    ),
    "storage_zone": OrderedDict(
        [
            ("cover_glass", 0.6),
            ("display_module", 1.2),
            ("adhesive", 0.2),
            ("pcb", 0.8),
            ("storage_package", 1.5),
            ("graphite_spreader", 0.1),
            ("rear_housing", 0.8),
        ]
    ),
    "camera_zone": OrderedDict(
        [
            ("cover_glass", 0.6),
            ("display_module", 1.2),
            ("adhesive", 0.2),
            ("camera_module_depth", 5.0),
            ("prism_path_allowance", 1.0),
            ("rear_housing", 0.8),
        ]
    ),
    "wireless_charging_zone": OrderedDict(
        [
            ("cover_glass", 0.6),
            ("display_module", 1.2),
            ("adhesive", 0.2),
            ("battery_pack", 4.5),
            ("coil", 0.6),
            ("ferrite_or_shield", 0.3),
            ("rear_housing", 0.8),
        ]
    ),
    "antenna_edge_zone": OrderedDict(
        [
            ("cover_glass", 0.6),
            ("display_module", 1.2),
            ("adhesive", 0.2),
            ("antenna_clearance", 1.0),
            ("structural_frame", 1.0),
            ("rear_housing", 0.8),
        ]
    ),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target-thickness-mm", type=positive_float, default=8.8)
    parser.add_argument("--zone", choices=sorted(ZONES), help="Analyze one zone instead of all zones")
    parser.add_argument("--profile", choices=("nominal",), default="nominal")
    return parser.parse_args()


def warning_rows(warnings: list[str]) -> list[str]:
    if not warnings:
        return ["none"]
    return [f"- {warning}" for warning in warnings]


def analyze_zone(zone_name: str, layers: OrderedDict[str, float], target_thickness_mm: float) -> dict[str, object]:
    total_thickness_mm = sum(layers.values())
    margin_mm = target_thickness_mm - total_thickness_mm
    warnings = []
    if margin_mm < 0:
        warnings.append("zone exceeds target thickness")
    if zone_name == "camera_zone" and margin_mm < 0:
        warnings.append("camera zone exceeds target")
    if zone_name == "battery_zone" and 0 <= margin_mm < 0.5:
        warnings.append("battery zone margin is below 0.5 mm")
    if zone_name == "soc_memory_zone" and 0 <= margin_mm < 0.5:
        warnings.append("soc_memory zone margin is below 0.5 mm")
    if zone_name == "wireless_charging_zone" and margin_mm < 0.8:
        warnings.append("wireless charging zone overlaps battery zone with limited clearance")
    return {
        "zone_name": zone_name,
        "layers": layers,
        "total_thickness_mm": total_thickness_mm,
        "margin_mm": margin_mm,
        "passed": margin_mm >= 0,
        "warnings": warnings,
    }


def print_zone_result(result: dict[str, object], target_thickness_mm: float) -> None:
    zone_name = str(result["zone_name"])
    layers = result["layers"]
    assert isinstance(layers, OrderedDict)
    total_thickness_mm = float(result["total_thickness_mm"])
    margin_mm = float(result["margin_mm"])
    passed = bool(result["passed"])
    warnings = result["warnings"]
    assert isinstance(warnings, list)

    print(f"zone name: {zone_name}")
    print_section("layer list", [f"{name}: {thickness:.2f} mm" for name, thickness in layers.items()])
    print_section(
        "outputs",
        [
            f"total_thickness_mm: {total_thickness_mm:.2f}",
            f"target_thickness_mm: {target_thickness_mm:.2f}",
            f"margin_vs_target_mm: {margin_mm:.2f}",
            f"pass: {passed}",
        ],
    )
    print_section("warnings", warning_rows(warnings))


def main() -> int:
    args = parse_args()
    selected_zones = {args.zone: ZONES[args.zone]} if args.zone else ZONES
    results = [analyze_zone(name, layers, args.target_thickness_mm) for name, layers in selected_zones.items()]
    worst_zone = min(results, key=lambda item: float(item["margin_mm"]))
    primary_blocker = (
        f"{worst_zone['zone_name']} has negative z-height margin"
        if float(worst_zone["margin_mm"]) < 0
        else f"{worst_zone['zone_name']} has the tightest z-height margin"
    )

    print("Zone stackup model")
    print_section(
        "inputs",
        [
            f"target_thickness_mm: {args.target_thickness_mm:.2f}",
            f"zone: {args.zone or 'all'}",
            f"profile: {args.profile}",
        ],
    )
    print_section(
        "assumptions",
        [
            "phone thickness is checked as separate local zones rather than one global stack",
            "layer values are nominal first-pass z-height placeholders",
            "profile is nominal only; conservative and aggressive profiles are intentionally not added yet",
            "local overlap, cutouts, fasteners, tolerances, cable bends, and CAD keepouts are not modeled",
        ],
    )
    print_section(
        "formulas",
        [
            "total_thickness_mm = sum(zone_layer_thicknesses_mm)",
            "margin_vs_target_mm = target_thickness_mm - total_thickness_mm",
            "pass = margin_vs_target_mm >= 0",
        ],
    )

    for index, result in enumerate(results):
        if index:
            print("")
        print_zone_result(result, args.target_thickness_mm)

    print("")
    print_section(
        "worst zone summary",
        [
            f"zone_name: {worst_zone['zone_name']}",
            f"total_thickness_mm: {float(worst_zone['total_thickness_mm']):.2f}",
            f"margin_vs_target_mm: {float(worst_zone['margin_mm']):.2f}",
            f"pass: {bool(worst_zone['passed'])}",
        ],
    )
    all_warnings = [warning for result in results for warning in result["warnings"]]
    print_section("warnings", warning_rows(all_warnings))
    print("confidence: medium for arithmetic; low to medium for layer placeholders before CAD and supplier stackups")
    print("basis: modeled estimate using nominal local z-height stacks")
    print(f"primary blocker: {primary_blocker}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
