"""Reconcile public cell dimensions with Slate's complete-pack allocation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from buildslate.io import load_yaml

PROFILE = Path("configs/devices/slate-pocket-v1r.yaml")
EVIDENCE = Path("research/evidence/battery/supplier-source-index.yaml")
ENVELOPE = Path("cad/slate-pocket-v1r/envelope-model/envelope.yaml")
CONCEPT = Path("engineering/assembly/concept-cad.yaml")
PACK_ENVELOPE = Path("research/evidence/battery/pack-envelope.yaml")
CANDIDATE_ID = "enovix_ai1_m01"


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
    return audit_data(
        *(
            load_yaml(root / path)
            for path in (PROFILE, EVIDENCE, ENVELOPE, CONCEPT, PACK_ENVELOPE)
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
