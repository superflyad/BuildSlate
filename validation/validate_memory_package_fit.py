"""Catch 128 Gb/GB confusion and false fit of the public memory package."""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from buildslate.io import load_yaml  # noqa: E402
from buildslate.memory_package_fit import (  # noqa: E402
    ASSEMBLY,
    CANDIDATES,
    COMPACT_STUDY,
    FLOORPLAN,
    PROFILE,
    STUDY,
    audit,
    audit_data,
)


def main() -> int:
    report = audit(ROOT)
    obsolete = report["obsolete_32gb_reference"]
    compact = report["compact_16gb_reference"]
    adata = report["adata_unit_reconciliation"]
    comparison = report["x2_controller_comparison"]
    expected_controllers = {
        "X2E-96-100": (192, [64, 320]),
        "X2E-90-100": (128, [128, 384]),
        "X2P-64-100": (128, [128, 384]),
        "X2P-42-100": (128, [128, 384]),
    }
    if (
        len(comparison) != len(expected_controllers)
        or {item["part"] for item in comparison} != set(expected_controllers)
        or any(
            item["controller_bus_width_bits"] != expected_controllers[item["part"]][0]
            or [plan["package_count"] for plan in item["plans"]] != [4, 8]
            or [plan["independent_host_width_bits"] for plan in item["plans"]]
            != [256, 512]
            or [plan["excess_over_controller_bits"] for plan in item["plans"]]
            != expected_controllers[item["part"]][1]
            or any(plan["independent_host_connections_fit"] for plan in item["plans"])
            or any(plan["supplier_topology_qualified"] for plan in item["plans"])
            for item in comparison
        )
    ):
        raise ValueError("X2 controller and package route comparison is misstated")
    if (
        report["target_gb"] != 128
        or report["planning_sites"] != 4
        or report["public_reference_capacity_gb"] != 16
        or report["required_public_reference_packages"] != 8
        or report["bus_topology_screen"]["controller_bus_width_bits"] != 192
        or report["bus_topology_screen"]["independent_connection_width_bits"] != 512
        or report["bus_topology_screen"]["independent_connection_possible"]
        or not report["bus_topology_screen"][
            "shared_channel_or_other_topology_required"
        ]
        or report["additional_nominal_area_mm2"] != 1008
        or report["source_consistency"] != "pass"
        or obsolete["part_number"] != "MT62F4G64DAFL-023 WT:C"
        or obsolete["capacity_gb"] != 32
        or obsolete["density_gbit"] != 256
        or obsolete["package_mm"] != [14.0, 12.4, 0.96]
        or obsolete["public_part_status"] != "obsolete"
        or obsolete["packages_for_128gb"] != 4
        or obsolete["site_outline_fits"]
        or not obsolete["site_nominal_height_fits"]
        or obsolete["independent_bus_width_bits"] != 256
        or obsolete["independent_bus_width_fits"]
        or obsolete["status"] != "rejected_obsolete_not_x2_qualified"
        or compact["part_number"] != "MT62F2G64D8CZ-023 WT:C"
        or compact["capacity_gb"] != 16
        or compact["density_gbit"] != 128
        or compact["package_mm"] != [8.0, 12.4, 1.2]
        or compact["board_orientation_mm"] != [12.4, 8.0, 1.2]
        or compact["ball_count"] != 561
        or compact["public_part_status"] != "production_catalog_listing"
        or compact["packages_for_128gb"] != 8
        or not compact["existing_site_outline_fits"]
        or compact["additional_package_sites_required"] != 4
        or compact["nominal_height_over_existing_blocks_mm"] != 0.2
        or compact["eight_package_area_mm2"] != 793.6
        or compact["additional_area_over_four_sites_mm2"] != 233.6
        or compact["independent_bus_width_bits"] != 512
        or compact["independent_bus_width_fits"]
        or compact["placement_study"]["status"] != "outline_clear"
        or compact["placement_study"]["minimum_screened_planar_gap_mm"] != 2.0
        or compact["placement_study"]["placements"][4]["assembly_box_mm"][2] != 2.0
        or compact["placement_study"]["placements"][4]["assembly_box_mm"][0] != 100.0
        or report["integration_status"] != "blocked"
        or adata["status"] != "source_unit_conflict"
        or [part["part_number"] for part in adata["parts"]]
        != ["L5CG32D2023MCAS", "L5EG32D4023MCAS"]
        or [part["reconciled_package_capacity_gb"] for part in adata["parts"]] != [4, 8]
        or [part["four_package_capacity_gb"] for part in adata["parts"]] != [16, 32]
        or [part["packages_for_target"] for part in adata["parts"]] != [32, 16]
        or [part["independent_data_width_bits"] for part in adata["parts"]]
        != [1024, 512]
        or any(part["planning_sites_fit"] for part in adata["parts"])
        or any(
            any(part["independent_width_fits_controllers"].values())
            for part in adata["parts"]
        )
        or any(
            item["public_part_outline_fits"] or item["public_part_height_fits"]
            for item in report["site_geometry"]
        )
        or report["eight_package_study"]["status"] != "outline_clear"
        or report["eight_package_study"]["minimum_screened_planar_gap_mm"] != 1.5
        or report["eight_package_study"]["packages_per_side"]
        != {"component": 4, "reverse": 4}
        or report["eight_package_study"]["stack_issues"]
        or report["eight_package_study"]["board_z_mm"] != [3.2, 4.0]
    ):
        raise ValueError("128 GB package geometry or capacity gap was lost")
    published = json.loads(
        (ROOT / "viewer/public/hardware-readiness.json").read_text(encoding="utf-8")
    )
    if published["memory_package_fit"] != report:
        raise ValueError("Published memory package screen is stale")
    data = [
        load_yaml(ROOT / path)
        for path in (PROFILE, CANDIDATES, FLOORPLAN, ASSEMBLY, STUDY, COMPACT_STUDY)
    ]
    data.append(
        float(
            load_yaml(ROOT / data[3]["sources"]["envelope"])["placements"][
                "main_pcb_placeholder"
            ]["height_mm"]
        )
    )
    altered = copy.deepcopy(data)
    altered[1]["memory_supplier_context"]["adata_lpddr5x_32gbit"][
        "organization_megawords"
    ] = 8192
    if audit_data(*altered)["source_consistency"] != "fail":
        raise ValueError("ADATA US gigabyte label was accepted over organization")
    altered = copy.deepcopy(data)
    altered[1]["memory_supplier_context"]["adata_lpddr5x_64gbit"][
        "uk_labeled_density_gbit"
    ] = 512
    if audit_data(*altered)["source_consistency"] != "fail":
        raise ValueError("ADATA UK density disagreement was accepted")
    altered = copy.deepcopy(data)
    altered[1]["memory_supplier_context"]["micron_lpddr5x_32gb_obsolete_reference"][
        "density_gbit"
    ] = 128
    if audit_data(*altered)["source_consistency"] != "fail":
        raise ValueError("Obsolete part gigabit density was accepted as 32 GB")
    altered = copy.deepcopy(data)
    altered[1]["candidates"]["qualcomm_snapdragon_x2_elite_extreme"][
        "memory_bus_width_bits"
    ] = 128
    if audit_data(*altered)["source_consistency"] != "fail":
        raise ValueError("X2 bus width and bandwidth mismatch was accepted")
    altered = copy.deepcopy(data)
    altered[1]["candidates"]["qualcomm_snapdragon_x2_elite_90"][
        "memory_bus_width_bits"
    ] = 192
    if audit_data(*altered)["source_consistency"] != "fail":
        raise ValueError("X2E-90-100 bus width and bandwidth mismatch was accepted")
    altered = copy.deepcopy(data)
    altered[1]["candidates"]["qualcomm_snapdragon_x2_plus_6_core"][
        "memory_bandwidth_gb_s"
    ] = 228
    if audit_data(*altered)["source_consistency"] != "fail":
        raise ValueError("X2 Plus bus width and bandwidth mismatch was accepted")
    altered = copy.deepcopy(data)
    altered[1]["memory_supplier_context"]["micron_lpddr5x_16gb_public_part"][
        "capacity_gb"
    ] = 128
    if audit_data(*altered)["source_consistency"] != "fail":
        raise ValueError("Gigabit part was accepted as 128 gigabytes")
    altered = copy.deepcopy(data)
    altered[2]["placements"]["memory_a_32gb"]["evidence_class"] = "verified"
    if audit_data(*altered)["source_consistency"] != "fail":
        raise ValueError("Unqualified memory geometry was accepted as verified")
    altered = copy.deepcopy(data)
    altered[3]["parts"]["pcb"]["parts"]["memory_a_32gb"]["height_mm"] = 1.2
    if not audit_data(*altered)["site_geometry"][0]["public_part_height_fits"]:
        raise ValueError("Package height screen did not respond to assembly change")
    altered = copy.deepcopy(data)
    altered[4]["placements"]["memory_right_lower_component"]["x_mm"] = 57.0
    if audit_data(*altered)["eight_package_study"]["status"] != "outline_conflict":
        raise ValueError("Storage collision was accepted in eight-package study")
    altered = copy.deepcopy(data)
    altered[4]["placements"]["memory_left_lower_reverse"]["x_mm"] = 1.0
    if audit_data(*altered)["eight_package_study"]["status"] != "outline_conflict":
        raise ValueError("Reverse-side boundary breach was accepted")
    altered = copy.deepcopy(data)
    altered[1]["memory_supplier_context"]["micron_lpddr5x_16gb_compact_part"][
        "density_gbit"
    ] = 256
    if audit_data(*altered)["source_consistency"] != "fail":
        raise ValueError("Compact part gigabit density was accepted as 32 GB")
    altered = copy.deepcopy(data)
    altered[5]["placements"]["memory_right_lower_component"]["x_mm"] = 70.0
    if (
        audit_data(*altered)["compact_16gb_reference"]["placement_study"]["status"]
        != "outline_conflict"
    ):
        raise ValueError("Compact package board-boundary conflict was accepted")
    altered = copy.deepcopy(data)
    altered[5]["metadata"]["package_orientation"] = "unrotated"
    if (
        audit_data(*altered)["compact_16gb_reference"]["placement_study"]["status"]
        != "outline_conflict"
    ):
        raise ValueError("Incorrect compact package rotation was accepted")
    altered = copy.deepcopy(data)
    altered[6] = 1.2
    if not audit_data(*altered)["eight_package_study"]["stack_issues"]:
        raise ValueError("Board thickness disagreement was not detected")
    print("PASS: 128 GB public memory package count and geometry screen")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
