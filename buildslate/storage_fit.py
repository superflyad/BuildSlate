"""Check one public UFS package against the provisional board and power inputs.

This is a package outline and voltage screen. It cannot qualify the part or host.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from buildslate.io import load_yaml

CANDIDATES = Path("research/evidence/display-storage/candidate-comparison.yaml")
FLOORPLAN = Path("engineering/pcb/slate-pocket-v1r-floorplan/floorplan.yaml")
POWER_TREE = Path("engineering/pcb/power-tree.yaml")
ASSEMBLY = Path("engineering/assembly/assembly.yaml")
STORAGE_ID = "storage_ufs_1tb_reference"
MIN_OUTLINE_CLEARANCE_MM = 0.5


def _edges(rectangle: dict) -> tuple[float, float, float, float]:
    x, y = float(rectangle["x"]), float(rectangle["y"])
    return x, y, x + float(rectangle["length"]), y + float(rectangle["width"])


def _separation(first: tuple, second: tuple) -> float:
    fx1, fy1, fx2, fy2 = first
    sx1, sy1, sx2, sy2 = second
    x_gap = max(sx1 - fx2, fx1 - sx2, 0.0)
    y_gap = max(sy1 - fy2, fy1 - sy2, 0.0)
    if (
        x_gap == 0
        and y_gap == 0
        and fx1 < sx2
        and fx2 > sx1
        and fy1 < sy2
        and fy2 > sy1
    ):
        return -1.0
    return (
        max(x_gap, y_gap) if x_gap == 0 or y_gap == 0 else (x_gap**2 + y_gap**2) ** 0.5
    )


def audit_data(candidates: dict, floorplan: dict, power: dict, assembly: dict) -> dict:
    site = floorplan["placements"][STORAGE_ID]
    candidate_id = site["candidate_id"]
    candidate = candidates["storage_candidates"][candidate_id]
    package = candidate["package_mm"]
    rectangle = site["rectangle_mm"]
    assembly_height = assembly["parts"]["pcb"]["parts"][STORAGE_ID]["height_mm"]
    geometry_issues = []
    electrical_issues = []
    if any(
        abs(float(a) - float(b)) > 0.001
        for a, b in zip(
            (rectangle["length"], rectangle["width"], assembly_height),
            package,
            strict=True,
        )
    ):
        geometry_issues.append(
            "Board and assembly package dimensions differ from the manufacturer outline"
        )
    if site["source"] != f"{CANDIDATES.as_posix()}#{candidate_id}":
        geometry_issues.append(
            "Board placement is not linked to the screened candidate"
        )
    boundary = _edges(floorplan["board"]["component_side_boundary_mm"])
    placed = _edges(rectangle)
    edge_clearance = min(
        placed[0] - boundary[0],
        placed[1] - boundary[1],
        boundary[2] - placed[2],
        boundary[3] - placed[3],
    )
    if edge_clearance < MIN_OUTLINE_CLEARANCE_MM - 1e-6:
        geometry_issues.append(
            "Storage package has less than 0.5 mm nominal board-boundary clearance"
        )
    neighbor_clearances = {
        identifier: _separation(placed, _edges(item["rectangle_mm"]))
        for identifier, item in floorplan["placements"].items()
        if identifier != STORAGE_ID
    }
    closest = min(neighbor_clearances, key=neighbor_clearances.get)
    neighbor_clearance = neighbor_clearances[closest]
    if neighbor_clearance < MIN_OUTLINE_CLEARANCE_MM - 1e-6:
        geometry_issues.append(
            f"Storage package has less than 0.5 mm nominal clearance to {closest}"
        )
    rails = []
    for supply, bounds in candidate["supply_voltage_v"].items():
        rail_id = f"storage_{supply}"
        rail = power["rail_hypotheses"].get(rail_id, {})
        voltage = rail.get("nominal_voltage_v")
        status = "undefined"
        if voltage is not None:
            status = (
                "in_range"
                if bounds[0] <= float(voltage) <= bounds[1]
                else "out_of_range"
            )
            if status == "out_of_range":
                electrical_issues.append(
                    f"{rail_id} nominal voltage is outside manufacturer range"
                )
        rails.append(
            {
                "id": rail_id,
                "required_voltage_v": bounds,
                "modeled_nominal_voltage_v": voltage,
                "status": status,
            }
        )
    return {
        "candidate": candidate_id,
        "manufacturer_part_number": candidate["part_number"],
        "capacity_tb": candidate["capacity_tb"],
        "interface": candidate["interface"],
        "package_mm": package,
        "ball_count": candidate["ball_count"],
        "outline_fit": "pass" if not geometry_issues else "fail",
        "board_boundary_clearance_mm": round(edge_clearance, 3),
        "nearest_component": closest,
        "component_clearance_mm": round(neighbor_clearance, 3),
        "rails": rails,
        "screen_errors": geometry_issues + electrical_issues,
        "integration_status": "blocked",
        "missing_design_evidence": [
            "Selected platform UFS host support and boot compatibility",
            "Controlled 153-ball pin map, land pattern, and assembly keepouts",
            "Regulator selection, power sequence, decoupling, and PDN measurements",
            "Sourcing, lifecycle, and controlled supplier acceptance",
            "Routed signal-integrity review and physical read/write test",
        ],
        "source": candidate["product_brief"]["url"],
        "caveat": "A public package outline and supply range are candidate inputs, not a selected storage design or a functional device.",
    }


def audit(root: Path) -> dict:
    return audit_data(
        *(
            load_yaml(root / path)
            for path in (CANDIDATES, FLOORPLAN, POWER_TREE, ASSEMBLY)
        )
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo-root", type=Path, default=Path(__file__).resolve().parents[1]
    )
    args = parser.parse_args()
    print(json.dumps(audit(args.repo_root), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
