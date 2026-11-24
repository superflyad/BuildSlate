"""Catch storage package, clearance, and supply regressions in the viewer screen."""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from buildslate.io import load_yaml  # noqa: E402
from buildslate.storage_fit import (  # noqa: E402
    ASSEMBLY,
    CANDIDATES,
    FLOORPLAN,
    POWER_TREE,
    STORAGE_ID,
    audit,
    audit_data,
)


def main() -> int:
    report = audit(ROOT)
    if (
        report["manufacturer_part_number"] != "THGJFRT3E88BATW"
        or report["package_mm"] != [9.0, 13.0, 0.85]
        or report["outline_fit"] != "pass"
        or report["integration_status"] != "blocked"
        or report["board_boundary_clearance_mm"] != 0.5
        or report["component_clearance_mm"] != 0.5
        or [rail["status"] for rail in report["rails"]] != ["undefined", "undefined"]
    ):
        raise ValueError(
            "Published storage candidate screen differs from the source design"
        )
    published = json.loads(
        (ROOT / "viewer/public/hardware-readiness.json").read_text(encoding="utf-8")
    )
    if published["storage_fit"] != report:
        raise ValueError("Public storage screen is stale")
    data = [
        load_yaml(ROOT / path) for path in (CANDIDATES, FLOORPLAN, POWER_TREE, ASSEMBLY)
    ]
    altered = copy.deepcopy(data)
    altered[1]["placements"][STORAGE_ID]["rectangle_mm"]["length"] = 7.5
    if audit_data(*altered)["outline_fit"] != "fail":
        raise ValueError("Wrong package outline passed")
    altered = copy.deepcopy(data)
    altered[1]["placements"][STORAGE_ID]["rectangle_mm"]["x"] = 67.0
    if audit_data(*altered)["outline_fit"] != "fail":
        raise ValueError("Zero board-edge clearance passed")
    altered = copy.deepcopy(data)
    altered[2]["rail_hypotheses"]["storage_vcc"]["nominal_voltage_v"] = 3.3
    if audit_data(*altered)["rails"][0]["status"] != "out_of_range":
        raise ValueError("Out-of-range storage supply passed")
    print("PASS: 1 TB UFS package, clearance, and supply screen")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
