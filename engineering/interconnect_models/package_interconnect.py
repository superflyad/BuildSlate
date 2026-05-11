#!/usr/bin/env python3
"""First-pass package adjacency and short-path pressure screen."""
from __future__ import annotations

import argparse
from common import positive_float, positive_int, print_section


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--soc-memory-distance-mm", type=positive_float, default=8.0)
    parser.add_argument("--memory-package-count", type=positive_int, default=16)
    parser.add_argument("--storage-distance-mm", type=positive_float, default=25.0)
    parser.add_argument("--target-memory-bandwidth-gbps", type=positive_float, default=2048.0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    bandwidth_tbps = args.target_memory_bandwidth_gbps / 1000.0
    short_path_pressure_score = bandwidth_tbps * args.soc_memory_distance_mm * (args.memory_package_count / 8.0)
    package_clustering_density = args.memory_package_count / max(args.soc_memory_distance_mm, 1.0)
    storage_path_pressure_score = args.storage_distance_mm / args.soc_memory_distance_mm

    warnings: list[str] = []
    if args.soc_memory_distance_mm > 10.0:
        warnings.append("memory distance is growing beyond a short-path target for very high bandwidth")
    if args.memory_package_count > 12:
        warnings.append("routing complexity increases rapidly with memory package count and escape-routing fanout")
    if short_path_pressure_score > 35.0:
        warnings.append("short-path pressure score is high; package adjacency likely dominates floorplanning")

    print("Package interconnect screening model")
    print_section("assumptions", [
        "high-bandwidth systems prefer short routing between the SoC/NPU and memory packages",
        "routing complexity increases rapidly with package count because escape routing, length matching, and keepouts multiply",
        "distance values are package-to-package floorplan placeholders, not measured trace lengths",
        "signal integrity, skew budgets, channel loss, connector/flex effects, and package pin maps are not modeled",
    ])
    print_section("formulas", [
        "bandwidth_Tbps = target_memory_bandwidth_Gbps / 1000",
        "short_path_pressure_score = bandwidth_Tbps * SoC_memory_distance_mm * (memory_package_count / 8)",
        "package_clustering_density = memory_package_count / SoC_memory_distance_mm",
        "storage_path_pressure_score = storage_distance_mm / SoC_memory_distance_mm",
    ])
    print_section("outputs", [
        f"soc_memory_distance_mm: {args.soc_memory_distance_mm:.1f}",
        f"memory_package_count: {args.memory_package_count}",
        f"storage_distance_mm: {args.storage_distance_mm:.1f}",
        f"target_memory_bandwidth_gbps: {args.target_memory_bandwidth_gbps:.0f}",
        f"short_path_pressure_score: {short_path_pressure_score:.1f}",
        f"package_clustering_density_packages_per_mm: {package_clustering_density:.2f}",
        f"storage_path_pressure_score: {storage_path_pressure_score:.1f}",
    ])
    print_section("warnings", warnings)
    print("confidence: low; package maps and board floorplan are required for real interconnect feasibility")
    print("basis: first-order adjacency pressure from bandwidth, distance, and memory package count")
    print("primary blocker: keeping high-bandwidth memory physically close enough while leaving room for routing escape")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
