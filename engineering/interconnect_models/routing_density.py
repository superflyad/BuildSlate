#!/usr/bin/env python3
"""First-pass PCB routing density and high-speed interconnect pressure screen."""
from __future__ import annotations

import argparse
from common import positive_float, positive_int, print_section


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pcb-area-mm2", type=positive_float, default=6000.0)
    parser.add_argument("--soc-package-area-mm2", type=positive_float, default=324.0)
    parser.add_argument("--memory-package-count", type=positive_int, default=16)
    parser.add_argument("--high-speed-links", type=positive_int, default=128)
    parser.add_argument("--pcb-layer-count", type=positive_int, default=12)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    assumed_memory_package_area_mm2 = 80.0
    memory_area_mm2 = args.memory_package_count * assumed_memory_package_area_mm2
    package_area_mm2 = args.soc_package_area_mm2 + memory_area_mm2
    area_utilization_pct = package_area_mm2 / args.pcb_area_mm2 * 100.0
    high_speed_links_per_layer = args.high_speed_links / args.pcb_layer_count
    routing_density_proxy = args.high_speed_links / args.pcb_area_mm2 * 1000.0
    interconnect_pressure = routing_density_proxy * (12.0 / args.pcb_layer_count) * (1.0 + area_utilization_pct / 100.0)

    warnings: list[str] = []
    if args.memory_package_count > 12 or memory_area_mm2 > args.pcb_area_mm2 * 0.15:
        warnings.append("memory package crowding is likely around the SoC keepout and escape-routing region")
    if routing_density_proxy > 18.0 or high_speed_links_per_layer > 10.0:
        warnings.append("excessive high-speed density may increase crosstalk, length-matching, and via-stub risk")
    if args.pcb_layer_count < 14 and (args.high_speed_links >= 128 or interconnect_pressure > 25.0):
        warnings.append("likely layer-count escalation beyond the nominal PCB stackup")

    print("PCB routing density screening model")
    print_section("assumptions", [
        "memory package area uses an 80 mm2 placeholder per package for crowding pressure only",
        "high-speed links are counted as abstract lanes/interfaces, not exact differential pairs or byte lanes",
        "routing density proxy is normalized per 1000 mm2 of PCB area",
        "vias, impedance rules, blind/buried via choices, keepouts, antennas, and flex routing are not modeled",
    ])
    print_section("formulas", [
        "memory_area_mm2 = memory_package_count * 80 mm2",
        "area_utilization_percent = (SoC_package_area + memory_area) / PCB_area * 100",
        "high_speed_links_per_layer = high_speed_links / PCB_layer_count",
        "routing_density_proxy = high_speed_links / PCB_area_mm2 * 1000",
        "interconnect_pressure = routing_density_proxy * (12 / layer_count) * (1 + area_utilization_percent / 100)",
    ])
    print_section("outputs", [
        f"pcb_area_mm2: {args.pcb_area_mm2:.0f}",
        f"soc_package_area_mm2: {args.soc_package_area_mm2:.0f}",
        f"memory_package_count: {args.memory_package_count}",
        f"estimated_memory_package_area_mm2: {memory_area_mm2:.0f}",
        f"package_area_utilization_percent: {area_utilization_pct:.0f}",
        f"high_speed_links: {args.high_speed_links}",
        f"pcb_layer_count: {args.pcb_layer_count}",
        f"high_speed_links_per_layer: {high_speed_links_per_layer:.1f}",
        f"routing_density_proxy_per_1000mm2: {routing_density_proxy:.1f}",
        f"interconnect_pressure_score: {interconnect_pressure:.1f}",
    ])
    print_section("warnings", warnings)
    print("confidence: low; intended only for routing-pressure triage before board floorplanning")
    print("basis: package count, link count, board area, and layer-count screening heuristics")
    print("primary blocker: memory escape routing and high-speed signal-integrity margin in limited board area")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
