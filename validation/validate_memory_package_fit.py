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
    audit,
    audit_data,
)


def main() -> int:
    report = audit(ROOT)
    if (
        report["target_gb"] != 128
        or report["planning_sites"] != 4
        or report["public_reference_capacity_gb"] != 16
        or report["required_public_reference_packages"] != 8
        or report["additional_nominal_area_mm2"] != 1008
        or report["source_consistency"] != "pass"
        or report["integration_status"] != "blocked"
        or any(
            item["public_part_outline_fits"] or item["public_part_height_fits"]
            for item in report["site_geometry"]
        )
    ):
        raise ValueError("128 GB package geometry or capacity gap was lost")
    published = json.loads(
        (ROOT / "viewer/public/hardware-readiness.json").read_text(encoding="utf-8")
    )
    if published["memory_package_fit"] != report:
        raise ValueError("Published memory package screen is stale")
    data = [
        load_yaml(ROOT / path) for path in (PROFILE, CANDIDATES, FLOORPLAN, ASSEMBLY)
    ]
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
    print("PASS: 128 GB public memory package count and geometry screen")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
