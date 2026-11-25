"""Screen the assumed USB port against the main board and public connector data."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from buildslate.cad import build_concept
from buildslate.io import load_yaml

CANDIDATE = Path("research/evidence/usb/connector-candidate.yaml")
FLOORPLAN = Path("engineering/pcb/slate-pocket-v1r-floorplan/floorplan.yaml")
PROFILE = Path("configs/devices/slate-pocket-v1r.yaml")


def _axis_gap(a: list[float], b: list[float], axis: int) -> float:
    return max(0.0, a[axis] - b[axis] - b[axis + 3], b[axis] - a[axis] - a[axis + 3])


def audit_data(model: dict, floorplan: dict, profile: dict, evidence: dict) -> dict:
    parts = {part["id"]: part for part in model["parts"]}
    port = parts["usb_c_port_concept"]
    board = parts["main_pcb_placeholder"]
    a = [float(value) for value in port["box_mm"]]
    b = [float(value) for value in board["box_mm"]]
    gaps = [_axis_gap(a, b, axis) for axis in range(3)]
    candidate = evidence["candidate"]
    errors = []
    if (
        candidate.get("status") != "active"
        or evidence["metadata"]["status"] != "public_candidate_not_selected"
    ):
        errors.append("Connector candidate status is inconsistent")
    if candidate.get("recommended_pcb_thickness_mm") != floorplan["board"][
        "outline_mm"
    ]["thickness"] or float(b[5]) != float(
        floorplan["board"]["outline_mm"]["thickness"]
    ):
        errors.append("Connector board-thickness screen differs from the CAD board")
    if (
        candidate.get("maximum_operating_voltage_v") != 20
        or candidate.get("product_page_voltage_v") != 100
        or candidate.get("voltage_disposition")
        != "use_lower_detailed_specification_until_supplier_reconciles"
    ):
        errors.append(
            "Conflicting connector voltage ratings were not resolved conservatively"
        )
    if (
        port.get("geometry_evidence_class") != "design_assumption"
        or board.get("geometry_evidence_class") != "design_assumption"
    ):
        errors.append("USB screen no longer describes assumed assembly geometry")
    if (
        candidate.get("maximum_connector_current_a") != 5
        or candidate.get("contacts") != 24
    ):
        errors.append(
            "Connector current or contact count differs from the public listing"
        )
    target_w = float(profile["battery"]["charging_wired_target_w"])
    ceiling_w = float(candidate["maximum_operating_voltage_v"]) * float(
        candidate["maximum_connector_current_a"]
    )
    return {
        "status": "blocked" if any(gap > 0 for gap in gaps) else "unverified",
        "port_part": port["id"],
        "board_part": board["id"],
        "port_box_mm": a,
        "board_box_mm": b,
        "axis_separation_mm": [round(gap, 3) for gap in gaps],
        "minimum_box_separation_mm": round(sum(gap * gap for gap in gaps) ** 0.5, 3),
        "direct_board_mount_possible_from_current_boxes": not any(
            gap > 0 for gap in gaps
        ),
        "candidate_mpn": candidate["mpn"],
        "candidate_status": evidence["metadata"]["status"],
        "candidate_pcb_thickness_mm": candidate["recommended_pcb_thickness_mm"],
        "board_thickness_mm": float(b[5]),
        "maximum_operating_voltage_v": candidate["maximum_operating_voltage_v"],
        "maximum_connector_current_a": candidate["maximum_connector_current_a"],
        "connector_voltage_current_ceiling_w": ceiling_w,
        "wired_charge_target_w": target_w,
        "target_at_connector_rating_ceiling": target_w >= ceiling_w,
        "source_consistency": "pass" if not errors else "fail",
        "source_errors": errors,
        "source": candidate["sources"]["product_page"],
        "rating_source": candidate["sources"]["detailed_specification"],
        "drawing_source": candidate["sources"]["mechanical_drawing"],
        "caveat": "Current concept boxes do not touch, so this USB port cannot mount directly to the main board as modeled. The connector is a public candidate, not a selected part; a flex, daughterboard, or changed board plus released geometry, pinout, PD design, and physical testing is required. Published ratings do not authorize charging.",
    }


def audit(root: Path) -> dict:
    return audit_data(
        build_concept(root),
        load_yaml(root / FLOORPLAN),
        load_yaml(root / PROFILE),
        load_yaml(root / CANDIDATE),
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
