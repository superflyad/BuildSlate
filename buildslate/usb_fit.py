"""Screen the assumed USB port against the main board and public connector data."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from buildslate.cad import (
    FRAME_PORT_APERTURE_HEIGHT_MM,
    FRAME_PORT_APERTURE_WIDTH_MM,
    FRAME_PORT_APERTURE_Z_OFFSET_MM,
    USB_CANDIDATE,
    build_concept,
    build_usb_connector_variant,
)
from buildslate.io import load_yaml

CANDIDATE = Path("research/evidence/usb/connector-candidate.yaml")
FLOORPLAN = Path("engineering/pcb/slate-pocket-v1r-floorplan/floorplan.yaml")
PROFILE = Path("configs/devices/slate-pocket-v1r.yaml")


def _axis_gap(a: list[float], b: list[float], axis: int) -> float:
    return max(0.0, a[axis] - b[axis] - b[axis + 3], b[axis] - a[axis] - a[axis + 3])


def _box_overlap(a: list[float], b: list[float]) -> list[float]:
    lower = [max(a[axis], b[axis]) for axis in range(3)]
    upper = [min(a[axis] + a[axis + 3], b[axis] + b[axis + 3]) for axis in range(3)]
    return [round(max(0.0, upper[axis] - lower[axis]), 3) for axis in range(3)]


def audit_data(model: dict, floorplan: dict, profile: dict, evidence: dict) -> dict:
    parts = {part["id"]: part for part in model["parts"]}
    port = parts["usb_c_port_concept"]
    board = parts["main_pcb_placeholder"]
    pack = parts["battery_pack_shell_concept"]
    frame = parts["frame_bottom"]
    a = [float(value) for value in port["box_mm"]]
    b = [float(value) for value in board["box_mm"]]
    battery_box = [float(value) for value in pack["box_mm"]]
    frame_box = [float(value) for value in frame["box_mm"]]
    gaps = [_axis_gap(a, b, axis) for axis in range(3)]
    # The only nominal port-to-board path at the PCB height is their x overlap.
    overlap_x = max(0.0, min(a[0] + a[3], b[0] + b[3]) - max(a[0], b[0]))
    corridor = [
        max(a[0], b[0]),
        a[1] + a[4],
        b[2],
        overlap_x,
        gaps[1],
        b[5],
    ]
    full_width_carrier = [a[0], a[1] + a[4], b[2], a[3], gaps[1], b[5]]
    pack_overlap = _box_overlap(full_width_carrier, battery_box)
    corridor_blockers = [
        part["id"]
        for part in model["parts"]
        if part["id"] not in {port["id"], board["id"]}
        and part["active"]
        and part["geometry_use"] == "solid"
        and all(_box_overlap(corridor, part["box_mm"]))
    ]
    # The ported-frame primitive cuts a central aperture through the rail.
    aperture_x = frame_box[0] + (frame_box[3] - FRAME_PORT_APERTURE_WIDTH_MM) / 2.0
    shifted_port_x = b[0]
    shifted_outside_aperture = max(
        0.0,
        shifted_port_x + a[3] - (aperture_x + FRAME_PORT_APERTURE_WIDTH_MM),
    )
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
    if frame.get("shape") != "ported_frame" or aperture_x != a[0]:
        errors.append("Assumed port and the modeled chassis aperture diverged")
    if not corridor[3] or corridor[4] < 0 or corridor[5] <= 0:
        errors.append("Port-to-board corridor is degenerate")
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
        "current_clear_corridor_box_mm": corridor,
        "current_clear_corridor_width_mm": round(overlap_x, 3),
        "current_corridor_envelope_blockers": corridor_blockers,
        "full_port_width_carrier_box_mm": full_width_carrier,
        "full_width_carrier_battery_envelope_overlap_mm": pack_overlap,
        "shifted_port_x_mm_for_full_width_corridor": shifted_port_x,
        "shifted_port_frame_aperture_overrun_mm": round(shifted_outside_aperture, 3),
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
        "caveat": "The 4 mm clear corridor is only an AABB routing screen, not a connector footprint or manufacturable flex. A full-width carrier crosses the assumed battery pack envelope. Moving the port to the PCB edge misses the modeled frame aperture. Connector mounting, flex bend and traces, pack clearance, retention, enclosure seal, PD design, and physical testing remain unresolved. Published ratings do not authorize charging.",
    }


def audit(root: Path) -> dict:
    report = audit_data(
        build_concept(root),
        load_yaml(root / FLOORPLAN),
        load_yaml(root / PROFILE),
        load_yaml(root / CANDIDATE),
    )
    variant = build_usb_connector_variant(root)
    parts = {part["id"]: part for part in variant["parts"]}
    port = parts["usb_c_port_concept"]["box_mm"]
    board = parts["main_pcb_placeholder"]["box_mm"]
    frame = parts["frame_bottom"]["box_mm"]
    battery = parts["battery_pack_shell_concept"]["box_mm"]
    candidate = load_yaml(root / USB_CANDIDATE)["candidate"]
    aperture_bottom = frame[2] + FRAME_PORT_APERTURE_Z_OFFSET_MM
    aperture_top = aperture_bottom + FRAME_PORT_APERTURE_HEIGHT_MM
    candidate_carrier = [
        port[0],
        port[1] + port[4],
        board[2],
        port[3],
        _axis_gap(port, board, 1),
        board[5],
    ]
    report["gct_candidate_outline"] = {
        "status": "envelope_conflict_unqualified",
        "mpn": candidate["mpn"],
        "interface": candidate["interface"],
        "drawing_revision": candidate["drawing_revision"],
        "drawing_sha256": candidate["sources"]["distributor_drawing_sha256"],
        "box_mm": port,
        "frame_aperture_width_mm": FRAME_PORT_APERTURE_WIDTH_MM,
        "frame_aperture_height_mm": FRAME_PORT_APERTURE_HEIGHT_MM,
        "frame_aperture_vertical_overrun_mm": [
            round(max(0.0, aperture_bottom - port[2]), 3),
            round(max(0.0, port[2] + port[5] - aperture_top), 3),
        ],
        "board_gap_y_mm": round(_axis_gap(port, board, 1), 3),
        "board_overlap_x_mm": round(_box_overlap(port, board)[0], 3),
        "full_width_carrier_battery_envelope_overlap_mm": _box_overlap(
            candidate_carrier, battery
        ),
        "drawing_mating_cycles_used": candidate["conservative_mating_cycles"],
        "product_page_mating_cycles": candidate["current_page_mating_cycles"],
        "rated_voltage_v": candidate["voltage_rating_v"],
        "rated_current_a": candidate["current_rating_a"],
        "source": candidate["sources"]["product_page"],
        "drawing_source": candidate["sources"]["manufacturer_drawing"],
        "caveat": "Centered rectangular drawing envelope only. The mounting span includes stakes and can overstate frame interference. The 0.8 mm connector offset does not qualify the 0.8 mm board. USB 3.2 Gen 2 is not USB4. No footprint, supplier STEP, PD design, or physical fit is released.",
    }
    return report


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
