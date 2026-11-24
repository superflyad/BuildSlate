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
    FLOORPLAN,
    PROFILE,
    STUDY,
    audit,
    audit_data,
)


def main() -> int:
    report = audit(ROOT)
    obsolete = report["obsolete_32gb_reference"]
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
        or report["integration_status"] != "blocked"
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
        for path in (PROFILE, CANDIDATES, FLOORPLAN, ASSEMBLY, STUDY)
    ]
    data.append(
        float(
            load_yaml(ROOT / data[3]["sources"]["envelope"])["placements"][
                "main_pcb_placeholder"
            ]["height_mm"]
        )
    )
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
    altered[5] = 1.2
    if not audit_data(*altered)["eight_package_study"]["stack_issues"]:
        raise ValueError("Board thickness disagreement was not detected")
    print("PASS: 128 GB public memory package count and geometry screen")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
