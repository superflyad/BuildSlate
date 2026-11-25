"""Check the public USB candidate and concept routing-envelope conflicts."""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from buildslate.cad import build_concept  # noqa: E402
from buildslate.io import load_yaml  # noqa: E402
from buildslate.usb_fit import (  # noqa: E402
    CANDIDATE,
    FLOORPLAN,
    PROFILE,
    audit,
    audit_data,
)


def main() -> int:
    report = audit(ROOT)
    if (
        report["status"] != "blocked"
        or report["minimum_box_separation_mm"] != 6.0
        or report["direct_board_mount_possible_from_current_boxes"]
        or report["candidate_mpn"] != "12402075E512A"
        or report["current_clear_corridor_width_mm"] != 4.0
        or report["current_corridor_envelope_blockers"]
        or report["full_width_carrier_battery_envelope_overlap_mm"] != [7.0, 1.0, 0.8]
        or report["shifted_port_frame_aperture_overrun_mm"] != 8.0
        or report["target_at_connector_rating_ceiling"] is not True
        or report["source_consistency"] != "pass"
    ):
        raise ValueError("Current USB assembly gap or source limits were lost")
    published = json.loads(
        (ROOT / "viewer/public/hardware-readiness.json").read_text(encoding="utf-8")
    )
    if published["usb_fit"] != report:
        raise ValueError("Published USB fit screen is stale")
    inputs = (
        build_concept(ROOT),
        load_yaml(ROOT / FLOORPLAN),
        load_yaml(ROOT / PROFILE),
        load_yaml(ROOT / CANDIDATE),
    )
    changed = copy.deepcopy(inputs)
    port = next(
        part for part in changed[0]["parts"] if part["id"] == "usb_c_port_concept"
    )
    port["box_mm"][1] = 6
    if audit_data(*changed)["minimum_box_separation_mm"] != 0:
        raise ValueError("Port gap did not respond to a moved concept port")
    changed = copy.deepcopy(inputs)
    pack = next(
        part
        for part in changed[0]["parts"]
        if part["id"] == "battery_pack_shell_concept"
    )
    pack["box_mm"][0] += 2
    if (
        "battery_pack_shell_concept"
        not in audit_data(*changed)["current_corridor_envelope_blockers"]
    ):
        raise ValueError("Corridor screen missed a moved battery-pack envelope")
    changed = copy.deepcopy(inputs)
    frame = next(part for part in changed[0]["parts"] if part["id"] == "frame_bottom")
    frame["box_mm"][0] += 2
    if audit_data(*changed)["source_consistency"] != "fail":
        raise ValueError("Frame-aperture drift passed the source screen")
    changed = copy.deepcopy(inputs)
    changed[3]["candidate"]["maximum_operating_voltage_v"] = 100
    if audit_data(*changed)["source_consistency"] != "fail":
        raise ValueError("Product-page voltage displaced the lower operating limit")
    changed = copy.deepcopy(inputs)
    changed[1]["board"]["outline_mm"]["thickness"] = 1.0
    if audit_data(*changed)["source_consistency"] != "fail":
        raise ValueError("Wrong PCB thickness passed the connector screen")
    print("PASS: USB concept gap and public connector ratings")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
