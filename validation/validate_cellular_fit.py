"""Check that the public 5G reference cannot be mistaken for a phone design."""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from buildslate.cellular_fit import (  # noqa: E402
    ASSEMBLY,
    CANDIDATE,
    ENVELOPE,
    FLOORPLAN,
    MEMORY_CANDIDATES,
    MEMORY_STUDY,
    audit,
    audit_data,
)
from buildslate.io import load_yaml  # noqa: E402


def main() -> int:
    report = audit(ROOT)
    extension = report["reverse_board_extension"]
    if (
        report["status"] != "outline_blocked"
        or report["candidate"] != "RG255C-GL"
        or report["candidate_role"] != "public_reference_not_selected"
        or report["package_mm"] != [29.0, 32.0, 2.4]
        or report["board_outline_mm"] != [78.0, 55.0, 0.8]
        or report["voice"] != "optional_VoNR_and_VoLTE"
        or report["source_errors"]
        or any(side["outline_fits"] for side in report["sides"].values())
        or extension["minimum_whole_mm_board_width"] != 78.0
        or extension["increase_from_current_board_mm"] != 23.0
        or extension["module_orientation"] != "32x29"
        or extension["module_local_origin_mm"] != [2.0, 47.0]
        or not extension["board_inside_current_internal_xy"]
        or extension["board_3d_conflicts"]
        != ["rear_camera_placeholder", "speaker_a_placeholder"]
        or extension["module_3d_conflicts"] != ["rear_camera_placeholder"]
        or not extension["module_above_rear_cover"]
        or extension["module_bottom_to_rear_cover_mm"] != 0.25
        or extension["status"] != "mechanical_relayout_required"
    ):
        raise ValueError("Current 5G reference board conflict was lost")
    published = json.loads(
        (ROOT / "viewer/public/hardware-readiness.json").read_text(encoding="utf-8")
    )
    if published["cellular_reference_fit"] != report:
        raise ValueError("Public 5G reference fit report is stale")
    inputs = [
        load_yaml(ROOT / path)
        for path in (
            CANDIDATE,
            MEMORY_CANDIDATES,
            FLOORPLAN,
            MEMORY_STUDY,
            ENVELOPE,
            ASSEMBLY,
        )
    ]
    wider = copy.deepcopy(inputs)
    wider[2]["board"]["outline_mm"]["length"] = 114.0
    wider[2]["board"]["outline_mm"]["width"] = 74.0
    wider[2]["board"]["component_side_boundary_mm"]["length"] = 110.0
    wider[2]["board"]["component_side_boundary_mm"]["width"] = 70.0
    wider[4]["placements"]["main_pcb_placeholder"]["rectangle_mm"]["length"] = 114.0
    wider[4]["placements"]["main_pcb_placeholder"]["rectangle_mm"]["width"] = 74.0
    recovered = audit_data(*wider)
    if (
        recovered["status"] != "outline_possible_unqualified"
        or not recovered["sides"]["reverse"]["outline_fits"]
    ):
        raise ValueError(
            "Synthetic board enlargement did not recover nominal outline fit"
        )
    bad_source = copy.deepcopy(inputs)
    bad_source[3]["metadata"]["reference_part"] = "unknown"
    if audit_data(*bad_source)["status"] != "source_conflict":
        raise ValueError("Mismatched memory package source was accepted")
    bad_source = copy.deepcopy(inputs)
    bad_source[4]["placements"]["main_pcb_placeholder"]["rectangle_mm"]["width"] = 70.0
    if audit_data(*bad_source)["status"] != "source_conflict":
        raise ValueError("Mismatched mechanical board width was accepted")
    relocated = copy.deepcopy(inputs)
    for name in ("rear_camera_placeholder", "speaker_a_placeholder"):
        relocated[4]["placements"][name]["rectangle_mm"]["x"] = 5.0
    recovered = audit_data(*relocated)["reverse_board_extension"]
    if (
        recovered["status"] != "outline_possible_unqualified"
        or recovered["board_3d_conflicts"]
        or recovered["module_3d_conflicts"]
    ):
        raise ValueError("Synthetic relocation did not clear the 3D box conflicts")
    too_tall = copy.deepcopy(relocated)
    too_tall[0]["reference_module"]["package_mm"][2] = 3.0
    if audit_data(*too_tall)["reverse_board_extension"]["module_above_rear_cover"]:
        raise ValueError("Tall reverse-side module penetrated the rear cover")
    print("PASS: public 5G module outline conflict and recovery screen")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
