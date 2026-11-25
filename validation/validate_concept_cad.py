"""Check the committed concept contract against its engineering inputs."""

from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from buildslate.cad import (  # noqa: E402
    BATTERY_GLTF,
    BATTERY_MODEL,
    BATTERY_PROOF,
    BATTERY_STEP,
    COMPACT_MEMORY_GLTF,
    COMPACT_MEMORY_MODEL,
    COMPACT_MEMORY_PROOF,
    COMPACT_MEMORY_STEP,
    GLTF,
    MEMORY_GLTF,
    MEMORY_MODEL,
    MEMORY_PROOF,
    MEMORY_STEP,
    MODEL,
    PHONE_GLTF,
    PHONE_MODEL,
    PHONE_PROOF,
    PHONE_STEP,
    STEP,
    USB_CANDIDATE,
    USB_GLTF,
    USB_MODEL,
    USB_PROOF,
    USB_STEP,
    build_battery_pack_variant,
    build_concept,
    build_compact_memory_variant,
    build_memory_variant,
    build_phone_conflict_variant,
    build_usb_connector_variant,
)
from buildslate.cad_proof import PROOF  # noqa: E402
from buildslate.battery_fit import audit as audit_battery  # noqa: E402
from buildslate.cellular_fit import audit as audit_cellular  # noqa: E402
from buildslate.io import load_yaml  # noqa: E402
from buildslate.memory_package_fit import audit as audit_memory  # noqa: E402


def _check_model(
    expected: dict, model_path: Path, gltf_path: Path, step_path: Path, proof_path: Path
) -> dict:
    committed = json.loads((ROOT / model_path).read_text(encoding="utf-8"))
    if committed != expected:
        raise ValueError(
            "concept JSON is stale; regenerate with Python 3.12 CAD environment"
        )
    geometry = json.loads((ROOT / gltf_path).read_text(encoding="utf-8"))
    ids = {part["id"] for part in expected["parts"]}
    node_ids = {node["extras"]["part_id"] for node in geometry["nodes"]}
    if node_ids != ids or len(geometry["meshes"]) != len(ids):
        raise ValueError("concept glTF part identities drifted")
    step = (ROOT / step_path).read_text(encoding="utf-8")
    if step.count("MANIFOLD_SOLID_BREP") != len(ids):
        raise ValueError("concept STEP solid count drifted")
    proof = json.loads((ROOT / proof_path).read_text(encoding="utf-8"))
    expected_hash = hashlib.sha256(
        (json.dumps(expected, indent=2) + "\n").encode("utf-8")
    ).hexdigest()
    if proof["model_sha256"] != expected_hash:
        raise ValueError("CAD proof does not match the current concept model")
    part_reports = proof["parts"]
    if {item["id"] for item in part_reports} != ids:
        raise ValueError("CAD proof omits a concept part")
    roles = proof["roles"]
    if {role["id"] for role in roles} != {
        item["id"] for item in expected["component_coverage"]
    } or any(not role["part_ids"] or set(role["part_ids"]) - ids for role in roles):
        raise ValueError("CAD proof omits a component role or links an unknown part")
    role_by_id = {role["id"]: role for role in roles}
    library = load_yaml(ROOT / expected["sources"]["component_library"])["components"]
    for coverage in expected["component_coverage"]:
        role = role_by_id[coverage["id"]]
        if (
            role["part_ids"] != coverage["concept_part_ids"]
            or role["missing_evidence"] != library[coverage["id"]]["unknowns"]
        ):
            raise ValueError(f"CAD role proof is stale: {coverage['id']}")
    if not all(all(item["checks"].values()) for item in part_reports):
        raise ValueError("CAD proof contains a failed integrity check")
    summary = proof["summary"]
    if (
        summary["parts_checked"] != len(ids)
        or summary["roles_covered"] != len(expected["component_coverage"])
        or summary["roles_checked"] != len(roles)
        or not summary["step_roundtrip_passed"]
        or summary["interferences"]
        != sum(item["kind"] == "interference" for item in proof["intersections"])
        or summary["reservation_conflicts"]
        != sum(
            item["kind"] == "reservation_conflict" for item in proof["intersections"]
        )
        or summary["nominal_contacts"]
        != sum(item["kind"] == "contact" for item in proof["nominal_gaps"])
        or summary["small_nominal_gaps"]
        != sum(item["kind"] == "small_gap" for item in proof["nominal_gaps"])
        or summary["optical_model_conflicts"]
        != sum(
            item["status"] == "model_path_conflict" for item in proof["optical_paths"]
        )
        or summary["keepout_conflicts"] != len(proof["keepout_conflicts"])
        or summary["stack_failures"]
        != sum(item["status"] == "fail" for item in proof["zones"])
    ):
        raise ValueError("CAD proof summary does not match its findings")
    for finding in proof["nominal_gaps"]:
        first, second = finding["first"], finding["second"]
        if (
            first not in ids
            or second not in ids
            or finding["distance_mm"] < 0
            or finding["distance_mm"] > proof["thresholds"]["nominal_gap_screen_mm"]
            or second
            not in next(item for item in part_reports if item["id"] == first)[
                "nominal_gap_ids"
            ]
        ):
            raise ValueError("CAD nominal gap finding is inconsistent")
    optical = proof["optical_paths"]
    if {(item["camera_id"], item["blocking_part_id"]) for item in optical} != {
        ("rear_camera_placeholder", "rear_cover"),
        ("front_camera_concept", "display_stack"),
        ("front_camera_concept", "touch_digitizer_concept"),
    } or len(optical) != 3:
        raise ValueError("CAD proof omits a camera optical path")
    by_part = {part["id"]: part for part in expected["parts"]}
    for path in optical:
        camera = by_part[path["camera_id"]]
        blocker = by_part[path["blocking_part_id"]]
        box = camera["box_mm"]
        aperture_center = blocker.get(
            "aperture_center_mm", blocker.get("optical_aperture_center_mm")
        )
        aperture_radius = blocker.get(
            "aperture_radius_mm", blocker.get("optical_aperture_radius_mm")
        )
        expected_margin = round(
            aperture_radius
            - math.hypot(
                box[0] + box[3] / 2 - aperture_center[0],
                box[1] + box[4] / 2 - aperture_center[1],
            )
            - camera["lens_radius_mm"],
            3,
        )
        if (
            path["face"] != camera["lens_face"]
            or path["lens_radius_mm"] != camera["lens_radius_mm"]
            or path["axis_xy_mm"] != [box[0] + box[3] / 2, box[1] + box[4] / 2]
            or path["status"] not in {"model_path_conflict", "nominal_prism_clear"}
            or not 0 <= path["pupil_prism_overlap_percent"] <= 100
            or path["aperture_radial_margin_mm"] != expected_margin
            or (path["status"] == "nominal_prism_clear")
            != (
                path["solid_overlap_mm3"]
                <= proof["thresholds"]["optical_prism_overlap_mm3"]
            )
            or blocker["id"]
            not in next(item for item in part_reports if item["id"] == camera["id"])[
                "optical_path_ids"
            ]
        ):
            raise ValueError("CAD optical path finding is inconsistent")
    unverified = sum(part["evidence_class"] != "verified" for part in expected["parts"])
    if (
        proof["status"] != "review_required"
        or summary["unverified_parts"] != unverified
    ):
        raise ValueError("concept proof must preserve the evidence boundary")
    return proof


def main() -> int:
    baseline = build_concept(ROOT)
    primary_proof = _check_model(baseline, MODEL, GLTF, STEP, PROOF)
    variant = build_memory_variant(ROOT)
    reference_proof = _check_model(
        variant, MEMORY_MODEL, MEMORY_GLTF, MEMORY_STEP, MEMORY_PROOF
    )
    baseline_memory = {
        part["id"] for part in baseline["parts"] if part["group"] == "memory"
    }
    variant_memory = [part for part in variant["parts"] if part["group"] == "memory"]
    if (
        len(baseline_memory) != 4
        or len(variant_memory) != 8
        or baseline_memory & {part["id"] for part in variant_memory}
        or len(variant["parts"]) != len(baseline["parts"]) + 4
        or reference_proof["summary"]["interferences"] != 0
        or reference_proof.get("memory_study")
        != audit_memory(ROOT)["eight_package_study"]
    ):
        raise ValueError(
            "eight-package CAD variant does not replace the planning solids cleanly"
        )
    compact = build_compact_memory_variant(ROOT)
    compact_proof = _check_model(
        compact,
        COMPACT_MEMORY_MODEL,
        COMPACT_MEMORY_GLTF,
        COMPACT_MEMORY_STEP,
        COMPACT_MEMORY_PROOF,
    )
    compact_parts = [part for part in compact["parts"] if part["group"] == "memory"]
    if (
        len(compact_parts) != 8
        or len(compact["parts"]) != len(variant["parts"])
        or compact_proof["summary"]["interferences"] != 0
        or compact_proof.get("memory_study")
        != audit_memory(ROOT)["compact_16gb_reference"]["placement_study"]
    ):
        raise ValueError("compact memory CAD variant drifted from package study")
    phone = build_phone_conflict_variant(ROOT)
    phone_proof = _check_model(phone, PHONE_MODEL, PHONE_GLTF, PHONE_STEP, PHONE_PROOF)
    extension = audit_cellular(ROOT)["reverse_board_extension"]
    phone_by_id = {part["id"]: part for part in phone["parts"]}
    intersections = {
        frozenset((item["first"], item["second"]))
        for item in phone_proof["intersections"]
        if item["kind"] == "interference"
    }
    expected_intersections = {
        frozenset(pair)
        for pair in (
            ("main_pcb_placeholder", "rear_camera_placeholder"),
            ("main_pcb_placeholder", "speaker_a_placeholder"),
            ("main_pcb_placeholder", "haptics_concept"),
            ("cellular_reference_module", "rear_camera_placeholder"),
        )
    }
    if (
        len(phone["parts"]) != len(variant["parts"]) + 1
        or phone_by_id["main_pcb_placeholder"]["box_mm"]
        != extension["board_global_box_mm"]
        or phone_by_id["cellular_reference_module"]["box_mm"]
        != extension["module_global_box_mm"]
        or phone_proof.get("phone_extension") != extension
        or intersections != expected_intersections
        or phone_proof["summary"]["interferences"] != 4
    ):
        raise ValueError("phone collision CAD does not prove the rejected layout")
    usb = build_usb_connector_variant(ROOT)
    usb_proof = _check_model(usb, USB_MODEL, USB_GLTF, USB_STEP, USB_PROOF)
    candidate = load_yaml(ROOT / USB_CANDIDATE)["candidate"]
    usb_port = next(part for part in usb["parts"] if part["id"] == "usb_c_port_concept")
    usb_interferences = [
        item for item in usb_proof["intersections"] if item["kind"] == "interference"
    ]
    usb_rf_conflicts = [
        item
        for item in usb_proof["keepout_conflicts"]
        if item["part_id"] == "usb_c_port_concept"
        and item["keepout_id"] == "bottom_rf_edge"
    ]
    if (
        len(usb["parts"]) != len(baseline["parts"])
        or usb_port["box_mm"] != [84.48, 0.0, 2.72, 11.04, 7.9, 3.16]
        or usb_proof["usb_candidate"]["mpn"] != candidate["mpn"]
        or usb_proof["usb_candidate"]["drawing_sha256"]
        != candidate["sources"]["distributor_drawing_sha256"]
        or len(usb_interferences) != 1
        or frozenset((usb_interferences[0]["first"], usb_interferences[0]["second"]))
        != frozenset(("frame_bottom", "usb_c_port_concept"))
        or len(usb_rf_conflicts) != 1
        or usb_rf_conflicts[0]["overlap_area_mm2"] != 54.096
    ):
        raise ValueError("USB candidate envelope CAD proof drifted")
    battery = build_battery_pack_variant(ROOT)
    battery_proof = _check_model(
        battery, BATTERY_MODEL, BATTERY_GLTF, BATTERY_STEP, BATTERY_PROOF
    )
    pack = next(part for part in battery["parts"] if part["id"] == "battery_reference")
    battery_collisions = {
        item["second"]
        for item in battery_proof["intersections"]
        if item["first"] == "battery_reference" and item["kind"] == "interference"
    }
    if (
        len(battery["parts"]) != len(baseline["parts"])
        or pack["box_mm"] != [9.0, 11.0, 1.2, 110.0, 73.0, 4.4]
        or battery_proof["battery_pack_candidate"]
        != audit_battery(ROOT)["lipol_pack_screen"]
        or battery_proof["summary"]["interferences"] != 10
        or not {
            "main_pcb_placeholder",
            "rear_camera_placeholder",
            "speaker_b_placeholder",
            "battery_pack_shell_concept",
        }.issubset(battery_collisions)
    ):
        raise ValueError("6 Ah pack drawing envelope CAD proof drifted")
    print(
        f"PASS: {primary_proof['summary']['parts_checked']} baseline and "
        f"{reference_proof['summary']['parts_checked']} memory and "
        f"{compact_proof['summary']['parts_checked']} compact memory and "
        f"{phone_proof['summary']['parts_checked']} phone and "
        f"{usb_proof['summary']['parts_checked']} USB and "
        f"{battery_proof['summary']['parts_checked']} battery study CAD solids"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
