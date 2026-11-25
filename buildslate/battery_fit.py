"""Reconcile public cell dimensions with Slate's complete-pack allocation."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from buildslate.io import load_yaml

PROFILE = Path("configs/devices/slate-pocket-v1r.yaml")
EVIDENCE = Path("research/evidence/battery/supplier-source-index.yaml")
ENVELOPE = Path("cad/slate-pocket-v1r/envelope-model/envelope.yaml")
CONCEPT = Path("engineering/assembly/concept-cad.yaml")
PACK_ENVELOPE = Path("research/evidence/battery/pack-envelope.yaml")
CANDIDATE_ID = "enovix_ai1_m01"
LIPOL = Path("research/evidence/battery/lipol-lp4473109.yaml")
LIPOL_PRODUCT_URL = "https://www.lipoly-battery.com/lp4473109-lihv-lipoly-battery-3-85v-high-voltage-6000mah-23-1wh-with-pcm-jst-phr-2/"
LIPOL_DRAWING_URL = "https://www.lipoly-battery.com/wp-content/uploads/2024/10/LP4473109-3.85V-6000mAh-connector.pdf"
LIPOL_DRAWING_SHA256 = (
    "4a02e68f9ada253daca18b02558b51c5c4aacca9ddef79bf2b5f3e049dc84124"
)


def audit_lipol_data(
    evidence: dict, profile: dict, envelope: dict, concept: dict
) -> dict:
    """Screen the drawing-derived LP4473109 pack against Slate's current layout."""
    candidate = evidence["candidate"]
    dimensions = candidate["pack_body_mm"]
    tolerance = candidate["drawing_tolerance_mm"]
    nominal = [float(dimensions[key]) for key in ("length", "width", "thickness")]
    maximum = [
        nominal[index] + float(tolerance[key]["plus"])
        for index, key in enumerate(("length", "width", "thickness"))
    ]
    shell = concept["additional_parts"]["battery_pack_shell_concept"]["box_mm"]
    board = envelope["placements"]["main_pcb_placeholder"]["rectangle_mm"]
    internal = envelope["device"]["internal_boundary_mm"]
    allocation = float(profile["battery"]["physical_volume_mm3"])
    sustained = float(profile["compute"]["sustained_power_w"])
    charge_target = float(profile["battery"]["charging_wired_target_w"])
    voltage = float(candidate["nominal_voltage_v"])
    charge_current = float(candidate["maximum_charge_current_a"])
    discharge_current = float(candidate["maximum_continuous_discharge_current_a"])
    pcm_trip = [float(value) for value in candidate["pcm_overcurrent_detection_a"]]
    max_charge_voltage = float(candidate["maximum_charge_voltage_v"])
    nominal_volume = math.prod(nominal)
    maximum_volume = math.prod(maximum)
    left_of_board = float(board["x"]) - float(internal["x"])
    box = [float(shell[0]), float(shell[1]), float(shell[2]), *nominal]
    errors = []
    if (
        evidence["metadata"]["status"] != "public_reference_not_selected"
        or candidate["mpn"] != "LP4473109"
        or candidate["configuration"] != "1S1P"
        or candidate["nominal_capacity_mah"] != 6000
        or not math.isclose(
            float(candidate["nominal_energy_wh"]),
            candidate["nominal_capacity_mah"] * voltage / 1000,
            abs_tol=0.01,
        )
    ):
        errors.append("Pack identity or energy conflicts with the drawing")
    if any(value <= 0 or not math.isfinite(value) for value in nominal + maximum):
        errors.append("Pack dimensions are invalid")
    if any(
        float(tolerance[key][side]) < 0
        for key in ("length", "width", "thickness")
        for side in ("minus", "plus")
    ):
        errors.append("Pack drawing tolerances are invalid")
    if (
        nominal != [110.0, 73.0, 4.4]
        or maximum != [111.0, 73.5, 4.7]
        or [float(tolerance[key]["minus"]) for key in ("length", "width", "thickness")]
        != [1.0, 0.5, 0.3]
        or not math.isclose(float(candidate["lead_tolerance_mm"]), 3.0)
    ):
        errors.append("Pack body or lead tolerance differs from the drawing")
    if (
        not candidate["protection_circuit"]
        or candidate["thermistor"]
        or candidate["connector"] != "JST PHR-2"
        or len(pcm_trip) != 2
        or pcm_trip[0] <= 0
        or pcm_trip[1] < pcm_trip[0]
        or candidate["lead_length_mm"] <= 0
        or not math.isclose(float(candidate["lead_length_mm"]), 50.0)
        or pcm_trip != [2.0, 4.5]
    ):
        errors.append("Pack protection or lead record differs from the drawing")
    if (
        charge_current <= 0
        or discharge_current <= 0
        or max_charge_voltage <= 0
        or not all(
            math.isfinite(value)
            for value in (charge_current, discharge_current, max_charge_voltage)
        )
        or not math.isclose(charge_current, 3.0)
        or not math.isclose(discharge_current, 6.0)
        or not math.isclose(float(candidate["website_listed_charge_voltage_v"]), 4.48)
        or not math.isclose(max_charge_voltage, 4.2)
        or float(candidate["website_listed_charge_voltage_v"]) <= max_charge_voltage
    ):
        errors.append("Charge-voltage source conflict or current limits changed")
    sources = candidate["source"]
    if (
        sources["product_page"] != LIPOL_PRODUCT_URL
        or sources["drawing_and_specification"] != LIPOL_DRAWING_URL
        or sources["drawing_sha256"] != LIPOL_DRAWING_SHA256
    ):
        errors.append("Public manufacturer drawing source is missing")
    if candidate["disposition"] != "rejected_current_envelope_and_electrical_limits":
        errors.append("Unqualified pack was promoted")
    return {
        "mpn": candidate["mpn"],
        "capacity_mah": candidate["nominal_capacity_mah"],
        "nominal_energy_wh": candidate["nominal_energy_wh"],
        "pack_body_mm": nominal,
        "maximum_drawing_body_mm": maximum,
        "body_box_mm": box,
        "lead_length_mm": candidate["lead_length_mm"],
        "lead_modeled_in_cad": False,
        "nominal_body_volume_mm3": round(nominal_volume, 3),
        "maximum_drawing_body_volume_mm3": round(maximum_volume, 3),
        "complete_pack_allocation_mm3": allocation,
        "nominal_body_over_allocation_mm3": round(nominal_volume - allocation, 3),
        "body_over_concept_tray_mm": [
            round(nominal[index] - float(shell[index + 3]), 3) for index in range(3)
        ],
        "left_of_board_span_mm": round(left_of_board, 3),
        "body_over_left_of_board_span_mm": round(nominal[0] - left_of_board, 3),
        "maximum_charge_voltage_v": max_charge_voltage,
        "website_listed_charge_voltage_v": candidate["website_listed_charge_voltage_v"],
        "voltage_source_conflict": True,
        "maximum_charge_current_a": charge_current,
        "maximum_charge_power_at_specified_voltage_w": round(
            charge_current * max_charge_voltage, 3
        ),
        "wired_charge_target_w": charge_target,
        "maximum_continuous_discharge_current_a": discharge_current,
        "nominal_discharge_power_w": round(discharge_current * voltage, 3),
        "pcm_overcurrent_detection_a": pcm_trip,
        "pcm_detection_below_cell_discharge_limit": pcm_trip[1] < discharge_current,
        "slate_sustained_compute_screen_w": sustained,
        "thermistor_present": candidate["thermistor"],
        "source_consistency": "pass" if not errors else "fail",
        "source_errors": errors,
        "status": "rejected_current_layout_and_power",
        "product_page": sources["product_page"],
        "drawing_source": sources["drawing_and_specification"],
        "drawing_sha256": sources["drawing_sha256"],
        "caveat": "The body envelope is drawing-derived, but its placement is assumed. Leads, connector, swelling, tolerances, and thermal protection need a released pack design. The PDF's 4.2 V charge limit is used over the product page's conflicting 4.48 V listing.",
    }


def audit_data(
    profile: dict, evidence: dict, envelope: dict, concept: dict, pack: dict
) -> dict:
    candidate = evidence["candidates"][CANDIDATE_ID]
    platform = evidence["candidates"]["enovix_ai1_platform"]
    supplier_update = platform["latest_supplier_update"]
    cell = candidate["dimensions_mm"]
    dimensions = [float(cell[key]) for key in ("length", "width", "thickness")]
    cell_volume = dimensions[0] * dimensions[1] * dimensions[2]
    placement = envelope["placements"]["battery_reference"]
    placed = placement["rectangle_mm"]
    placed_dimensions = [placed["length"], placed["width"], placement["height_mm"]]
    shell = concept["additional_parts"]["battery_pack_shell_concept"]["box_mm"]
    shell_volume = float(shell[3]) * float(shell[4]) * float(shell[5])
    allocation = float(profile["battery"]["physical_volume_mm3"])
    target = evidence["slate_target"]
    errors = []
    if any(
        abs(float(a) - b) > 0.001
        for a, b in zip(placed_dimensions, dimensions, strict=True)
    ):
        errors.append(
            "CAD cell reference dimensions differ from the manufacturer listing"
        )
    if placement["source"] != f"{EVIDENCE.as_posix()}#{CANDIDATE_ID}":
        errors.append("CAD cell reference is not linked to the candidate source")
    if abs(float(candidate["calculated_cell_volume_mm3"]) - cell_volume) > 1:
        errors.append("Recorded cell volume differs from published dimensions")
    if float(target["complete_pack_volume_mm3"]) != allocation:
        errors.append("Battery allocation differs between profile and candidate review")
    if candidate.get("charge_rate") is not None:
        errors.append("Discharge category is still recorded as a charge rating")
    if candidate.get("max_charge_rate") != "unknown_public_source_does_not_state":
        errors.append("Public candidate charge rating must remain unknown")
    if (
        supplier_update.get("status") != "smartphone_field_testing_paused"
        or platform.get("public_status") != supplier_update["status"]
        or not str(supplier_update.get("source", "")).startswith(
            "https://ir.enovix.com/"
        )
        or evidence["screening_conclusion"].get("preferred_supplier_conversation")
        is not None
    ):
        errors.append("Battery sourcing disposition contradicts latest supplier update")
    if (
        candidate["target_fit"].get("wired_100w_charge")
        != "unverified_public_charge_limit_absent"
    ):
        errors.append(
            "Charging disposition must reflect the missing public charge limit"
        )
    equivalent_c = float(profile["battery"]["charging_wired_target_w"]) / (
        float(profile["battery"]["capacity_mah"])
        / 1000
        * float(profile["battery"]["nominal_voltage_v"])
    )
    if (
        pack["charge_pressure"]["public_candidate_charge_limits"][CANDIDATE_ID]
        != "unknown"
    ):
        errors.append("Pack study promotes an unpublished candidate charge limit")
    if (
        abs(
            float(
                pack["charge_pressure"]["wired_target_power_to_nominal_energy_per_hour"]
            )
            - equivalent_c
        )
        > 0.01
    ):
        errors.append("Pack charge-pressure ratio differs from the profile")
    return {
        "candidate": CANDIDATE_ID,
        "product": candidate["product"],
        "cell_dimensions_mm": dimensions,
        "cell_box_volume_mm3": round(cell_volume, 3),
        "concept_pack_envelope_mm3": round(shell_volume, 3),
        "complete_pack_allocation_mm3": allocation,
        "cell_over_allocation_mm3": round(cell_volume - allocation, 3),
        "concept_pack_over_allocation_mm3": round(shell_volume - allocation, 3),
        "public_charge_limit": "not_published_for_this_cell",
        "public_discharge_category": candidate["max_continuous_discharge_band"],
        "supplier_path_status": supplier_update["status"],
        "supplier_path_finding": supplier_update["finding"],
        "supplier_path_source": supplier_update["source"],
        "wired_target_equivalent_c_at_nominal_energy": round(equivalent_c, 2),
        "source_consistency": "pass" if not errors else "fail",
        "source_errors": errors,
        "integration_status": "blocked",
        "missing_design_evidence": [
            "Custom cell and complete-pack drawing within the allocation",
            "Tab, protection, connector, insulation, and swelling allowances",
            "Supplier charge curve and maximum current across voltage and temperature",
            "Battery protection design, safety review, and measured charge validation",
        ],
        "source": candidate["source"]["url"],
        "caveat": "The published cell box and concept pack envelope both exceed the current complete-pack allocation. A custom design or approved allocation change is required; no cell or charge rate is selected.",
    }


def audit(root: Path) -> dict:
    report = audit_data(
        *(
            load_yaml(root / path)
            for path in (PROFILE, EVIDENCE, ENVELOPE, CONCEPT, PACK_ENVELOPE)
        )
    )
    report["lipol_pack_screen"] = audit_lipol_data(
        load_yaml(root / LIPOL),
        load_yaml(root / PROFILE),
        load_yaml(root / ENVELOPE),
        load_yaml(root / CONCEPT),
    )
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
