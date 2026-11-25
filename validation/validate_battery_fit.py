"""Keep the public battery geometry and charge interpretation source bound."""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from buildslate.battery_fit import (  # noqa: E402
    CONCEPT,
    ENVELOPE,
    EVIDENCE,
    LIPOL,
    PACK_ENVELOPE,
    PROFILE,
    audit,
    audit_data,
    audit_lipol_data,
)
from buildslate.io import load_yaml  # noqa: E402


def main() -> int:
    report = audit(ROOT)
    lipol = report["lipol_pack_screen"]
    if (
        report["product"] != "AI1-M01"
        or report["cell_over_allocation_mm3"] != 221.248
        or report["concept_pack_over_allocation_mm3"] != 6001.4
        or report["public_charge_limit"] != "not_published_for_this_cell"
        or report["supplier_path_status"] != "smartphone_field_testing_paused"
        or report["source_consistency"] != "pass"
        or report["integration_status"] != "blocked"
        or lipol["mpn"] != "LP4473109"
        or lipol["capacity_mah"] != 6000
        or lipol["pack_body_mm"] != [110.0, 73.0, 4.4]
        or lipol["maximum_drawing_body_mm"] != [111.0, 73.5, 4.7]
        or lipol["nominal_body_over_allocation_mm3"] != 6508.0
        or lipol["body_over_left_of_board_span_mm"] != 21.0
        or lipol["maximum_charge_power_at_specified_voltage_w"] != 12.6
        or lipol["nominal_discharge_power_w"] != 23.1
        or lipol["pcm_overcurrent_detection_a"] != [2.0, 4.5]
        or not lipol["pcm_detection_below_cell_discharge_limit"]
        or lipol["thermistor_present"]
        or lipol["source_consistency"] != "pass"
        or lipol["status"] != "rejected_current_layout_and_power"
    ):
        raise ValueError("Current battery source or pack contradiction was lost")
    published = json.loads(
        (ROOT / "viewer/public/hardware-readiness.json").read_text(encoding="utf-8")
    )
    if published["battery_fit"] != report:
        raise ValueError("Published battery fit screen is stale")
    data = [
        load_yaml(ROOT / path)
        for path in (PROFILE, EVIDENCE, ENVELOPE, CONCEPT, PACK_ENVELOPE)
    ]
    altered = copy.deepcopy(data)
    altered[2]["placements"]["battery_reference"]["height_mm"] = 5.0
    if audit_data(*altered)["source_consistency"] != "fail":
        raise ValueError("Incorrect CAD cell dimensions passed")
    altered = copy.deepcopy(data)
    altered[1]["candidates"]["enovix_ai1_m01"]["charge_rate"] = "up_to_2c"
    if audit_data(*altered)["source_consistency"] != "fail":
        raise ValueError("Discharge limit was accepted as a charge rating")
    altered = copy.deepcopy(data)
    altered[1]["screening_conclusion"]["preferred_supplier_conversation"] = (
        "enovix_custom_ai1"
    )
    if audit_data(*altered)["source_consistency"] != "fail":
        raise ValueError("Paused supplier route remained preferred")
    altered = copy.deepcopy(data)
    altered[0]["battery"]["physical_volume_mm3"] = 30000
    if audit_data(*altered)["source_consistency"] != "fail":
        raise ValueError("Conflicting pack allocations passed")
    altered = copy.deepcopy(data)
    altered[4]["charge_pressure"]["public_candidate_charge_limits"][
        "enovix_ai1_m01"
    ] = "2c"
    if audit_data(*altered)["source_consistency"] != "fail":
        raise ValueError("Pack study accepted a discharge limit as charge evidence")
    inputs = [load_yaml(ROOT / path) for path in (LIPOL, PROFILE, ENVELOPE, CONCEPT)]
    altered_lipol = copy.deepcopy(inputs)
    altered_lipol[0]["candidate"]["maximum_charge_voltage_v"] = 4.48
    if audit_lipol_data(*altered_lipol)["source_consistency"] != "fail":
        raise ValueError("Conflicting product-page charge limit overrode the drawing")
    altered_lipol = copy.deepcopy(inputs)
    altered_lipol[0]["candidate"]["nominal_capacity_mah"] = 5000
    if audit_lipol_data(*altered_lipol)["source_consistency"] != "fail":
        raise ValueError("Non-6 Ah pack was accepted as the drawing candidate")
    altered_lipol = copy.deepcopy(inputs)
    altered_lipol[0]["candidate"]["pack_body_mm"]["length"] = 100.0
    if audit_lipol_data(*altered_lipol)["source_consistency"] != "fail":
        raise ValueError("Unpublished pack dimensions were accepted")
    altered_lipol = copy.deepcopy(inputs)
    altered_lipol[0]["candidate"]["maximum_charge_current_a"] = 100.0
    if audit_lipol_data(*altered_lipol)["source_consistency"] != "fail":
        raise ValueError("Unpublished charging current was accepted")
    print("PASS: battery cell, pack allocation, and charge interpretation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
