"""Export editable concept STEP and matching browser geometry from BuildSlate inputs."""

from __future__ import annotations

import argparse
import base64
import json
import math
import re
import struct
from pathlib import Path

from .assembly import build_assembly
from .battery_fit import LIPOL
from .battery_fit import audit as audit_battery
from .cad_proof import PROOF, build_proof
from .cellular_fit import CANDIDATE as CELLULAR_CANDIDATE
from .cellular_fit import audit as audit_cellular
from .cellular_fit import audit_compact as audit_compact_cellular
from .io import load_yaml
from .memory_package_fit import (
    CANDIDATES,
    COMPACT_PART,
    COMPACT_STUDY,
    PUBLIC_PART,
    STUDY,
)
from .memory_package_fit import audit as audit_memory
from .program import DEFAULT_REPO_ROOT

MANIFEST = Path("engineering/assembly/concept-cad.yaml")
STEP = Path("cad/slate-pocket-v1r/concept-cad/assembly.step")
MODEL = Path("viewer/public/concept.json")
GLTF = Path("viewer/public/concept.gltf")
MEMORY_STEP = Path("cad/slate-pocket-v1r/concept-cad/memory-8x16.step")
MEMORY_MODEL = Path("viewer/public/memory-8x16.json")
MEMORY_GLTF = Path("viewer/public/memory-8x16.gltf")
MEMORY_PROOF = Path("viewer/public/memory-8x16-proof.json")
COMPACT_MEMORY_STEP = Path("cad/slate-pocket-v1r/concept-cad/memory-8x16-compact.step")
COMPACT_MEMORY_MODEL = Path("viewer/public/memory-8x16-compact.json")
COMPACT_MEMORY_GLTF = Path("viewer/public/memory-8x16-compact.gltf")
COMPACT_MEMORY_PROOF = Path("viewer/public/memory-8x16-compact-proof.json")
PHONE_STEP = Path("cad/slate-pocket-v1r/concept-cad/phone-fit-conflict.step")
PHONE_MODEL = Path("viewer/public/phone-fit-conflict.json")
PHONE_GLTF = Path("viewer/public/phone-fit-conflict.gltf")
PHONE_PROOF = Path("viewer/public/phone-fit-conflict-proof.json")
COMPACT_PHONE_STEP = Path(
    "cad/slate-pocket-v1r/concept-cad/phone-fit-compact-outline.step"
)
COMPACT_PHONE_MODEL = Path("viewer/public/phone-fit-compact-outline.json")
COMPACT_PHONE_GLTF = Path("viewer/public/phone-fit-compact-outline.gltf")
COMPACT_PHONE_PROOF = Path("viewer/public/phone-fit-compact-outline-proof.json")
USB_STEP = Path("cad/slate-pocket-v1r/concept-cad/usb4525-outline.step")
USB_MODEL = Path("viewer/public/usb4525-outline.json")
USB_GLTF = Path("viewer/public/usb4525-outline.gltf")
USB_PROOF = Path("viewer/public/usb4525-outline-proof.json")
USB_CANDIDATE = Path("research/evidence/usb/gct-usb4525-outline.yaml")
BATTERY_STEP = Path("cad/slate-pocket-v1r/concept-cad/lp4473109-pack-outline.step")
BATTERY_MODEL = Path("viewer/public/lp4473109-pack-outline.json")
BATTERY_GLTF = Path("viewer/public/lp4473109-pack-outline.gltf")
BATTERY_PROOF = Path("viewer/public/lp4473109-pack-outline-proof.json")
FRAME_PORT_APERTURE_WIDTH_MM = 12.0
FRAME_PORT_APERTURE_HEIGHT_MM = 3.0
FRAME_PORT_APERTURE_Z_OFFSET_MM = 2.25


def build_concept(repo_root: Path) -> dict:
    source = build_assembly(repo_root)
    manifest = load_yaml(repo_root / MANIFEST)
    if manifest.get("schema_version") != 1:
        raise ValueError("unsupported concept CAD schema")
    source_ids = {part["id"] for part in source["parts"]}
    if set(manifest["source_overrides"]) - source_ids:
        raise ValueError("unknown source part in concept override")
    envelope = load_yaml(repo_root / source["sources"]["envelope"])
    placement_layers = {
        part_id: spec["layer"] for part_id, spec in envelope["placements"].items()
    }
    parts = []
    for original in source["parts"]:
        part = {**original, "shape": "box"}
        part["geometry_use"] = "solid"
        part["screen_layer"] = placement_layers.get(part["id"])
        if part["source"].startswith(source["sources"]["pcb"] + "#"):
            part["screen_layer"] = "component_planform"
        override = manifest["source_overrides"].get(part["id"])
        if override:
            part.update(override)
            if "height_mm" in override:
                part["box_mm"] = [*part["box_mm"][:5], float(override["height_mm"])]
            part["geometry_source"] = (
                f"{MANIFEST.as_posix()}#source_overrides.{part['id']}"
            )
            part["geometry_evidence_class"] = "design_assumption"
        else:
            part["geometry_source"] = part["source"]
            part["geometry_evidence_class"] = part["evidence_class"]
        parts.append(part)
    for part_id, spec in manifest["additional_parts"].items():
        if part_id in source_ids:
            raise ValueError(f"duplicate concept part: {part_id}")
        part = {
            "id": part_id,
            "label": spec["label"],
            "group": spec["group"],
            "box_mm": [float(value) for value in spec["box_mm"]],
            "evidence_class": "design_assumption",
            "source": spec["basis"],
            "notes": spec["assumption"],
            "active": True,
            "shape": spec["shape"],
            "roles": spec["roles"],
            "geometry_source": f"{MANIFEST.as_posix()}#additional_parts.{part_id}",
            "geometry_evidence_class": "design_assumption",
            "geometry_use": spec.get("geometry_use", "solid"),
            "screen_layer": spec.get("screen_layer"),
            "allowed_keepouts": spec.get("allowed_keepouts", []),
        }
        for key in (
            "radius_mm",
            "band_mm",
            "wall_mm",
            "lens_radius_mm",
            "optical_aperture_radius_mm",
        ):
            if key in spec:
                part[key] = float(spec[key])
        if "lens_face" in spec:
            part["lens_face"] = spec["lens_face"]
        if "optical_aperture_center_mm" in spec:
            part["optical_aperture_center_mm"] = [
                float(value) for value in spec["optical_aperture_center_mm"]
            ]
        parts.append(part)
    if len({part["id"] for part in parts}) != len(parts):
        raise ValueError("duplicate concept part ID")
    extent = source["extent_mm"]
    keepouts = load_yaml(repo_root / source["sources"]["keepouts"])["keepouts"]
    screen_layers = {
        layer for keepout in keepouts.values() for layer in keepout["applies_to_layers"]
    }
    for part in parts:
        box = part["box_mm"]
        if (
            len(box) != 6
            or min(box[:3]) < 0
            or min(box[3:]) <= 0
            or any(
                box[i] + box[i + 3] > limit + 1e-6
                for i, limit in enumerate(
                    (extent["length"], extent["width"], extent["thickness"])
                )
            )
        ):
            raise ValueError(f"concept part outside device: {part['id']}")
        if part["geometry_use"] not in {"solid", "reservation"}:
            raise ValueError(f"unknown geometry use: {part['id']}")
        if (
            part.get("screen_layer") is not None
            and part["screen_layer"] not in screen_layers
        ):
            raise ValueError(f"unknown keepout screen layer: {part['id']}")
        if set(part.get("allowed_keepouts", [])) - set(keepouts):
            raise ValueError(f"unknown keepout allowance: {part['id']}")
        if part["shape"] == "camera_module" and (
            part.get("lens_face") not in {"front", "rear"}
            or not 0 < part.get("lens_radius_mm", 0) <= min(box[3], box[4]) / 2
        ):
            raise ValueError(f"invalid camera pupil assumption: {part['id']}")
        if "optical_aperture_radius_mm" in part:
            center = part.get("optical_aperture_center_mm")
            radius = part["optical_aperture_radius_mm"]
            if (
                not isinstance(center, list)
                or len(center) != 2
                or radius <= 0
                or not box[0] + radius < center[0] < box[0] + box[3] - radius
                or not box[1] + radius < center[1] < box[1] + box[4] - radius
            ):
                raise ValueError(f"invalid optical aperture assumption: {part['id']}")
    roles = {item["id"] for item in source["component_coverage"]}
    if {role for part in parts for role in part.get("roles", [])} - roles:
        raise ValueError("unknown concept component role")
    coverage = []
    for item in source["component_coverage"]:
        ids = list(item["part_ids"])
        ids.extend(part["id"] for part in parts if item["id"] in part.get("roles", []))
        if not ids:
            raise ValueError(f"unrepresented component role: {item['id']}")
        coverage.append({**item, "concept_part_ids": ids})
    return {
        **source,
        "status": manifest["status"],
        "description": manifest["description"],
        "parts": parts,
        "component_coverage": coverage,
        "caveat": "Editable concept CAD. Assumed placements and packages are not supplier CAD or verified fit.",
    }


def build_usb_connector_variant(repo_root: Path) -> dict:
    """Place a drawing-derived connector envelope in the existing frame opening."""
    model = build_concept(repo_root)
    evidence = load_yaml(repo_root / USB_CANDIDATE)
    candidate = evidence["candidate"]
    if (
        evidence["metadata"]["status"] != "public_candidate_not_selected"
        or candidate["mpn"] != "USB4525-03-A"
    ):
        raise ValueError("USB connector study no longer matches the public candidate")
    frame = next(part for part in model["parts"] if part["id"] == "frame_bottom")
    port = next(part for part in model["parts"] if part["id"] == "usb_c_port_concept")
    frame_box = frame["box_mm"]
    old_port_box = port["box_mm"]
    center_x = frame_box[0] + frame_box[3] / 2
    center_z = (
        frame_box[2]
        + FRAME_PORT_APERTURE_Z_OFFSET_MM
        + FRAME_PORT_APERTURE_HEIGHT_MM / 2
    )
    span = float(candidate["overall_mounting_span_mm"])
    depth = float(candidate["body_depth_mm"])
    profile = float(candidate["maximum_profile_mm"])
    port["box_mm"] = [
        round(center_x - span / 2, 3),
        old_port_box[1],
        round(center_z - profile / 2, 3),
        span,
        depth,
        profile,
    ]
    port["label"] = f"GCT {candidate['mpn']} mounting envelope"
    port["source"] = f"{USB_CANDIDATE.as_posix()}#candidate"
    port["geometry_source"] = f"{USB_CANDIDATE.as_posix()}#candidate"
    port["geometry_evidence_class"] = "design_assumption"
    port["notes"] = (
        "Drawing-derived overall mounting span, body depth and maximum profile "
        "centered in the assumed frame aperture. Rectangular volume is a "
        "conservative envelope, not the supplier STEP, footprint, or released placement."
    )
    model["status"] = "usb_connector_outline_conflict_study"
    model["description"] = (
        "GCT USB4525-03-A public drawing envelope centered in the current chassis "
        "opening, with all other baseline concept parts unchanged."
    )
    model["caveat"] = (
        "Editable envelope study only. The mounting span includes shell stakes, so "
        "the box can overstate actual material overlap. Supplier STEP, full footprint, "
        "board attachment, enclosure seal, and physical clearance remain unverified."
    )
    return model


def build_battery_pack_variant(repo_root: Path) -> dict:
    """Place a drawing-derived 6 Ah pack body against the present assembly."""
    model = build_concept(repo_root)
    screen = audit_battery(repo_root)["lipol_pack_screen"]
    if (
        screen["source_consistency"] != "pass"
        or screen["status"] != "rejected_current_layout_and_power"
        or screen["mpn"] != "LP4473109"
    ):
        raise ValueError("battery pack study no longer matches the public drawing")
    pack = next(part for part in model["parts"] if part["id"] == "battery_reference")
    pack["box_mm"] = screen["body_box_mm"]
    pack["label"] = "LiPol LP4473109 pack body envelope"
    pack["source"] = f"{LIPOL.as_posix()}#candidate"
    pack["geometry_source"] = f"{LIPOL.as_posix()}#candidate.pack_body_mm"
    pack["geometry_evidence_class"] = "design_assumption"
    pack["shape"] = "box"
    pack["notes"] = (
        "Drawing-derived pack body at the current tray origin. This is an assumed "
        "placement; the 50 mm lead, connector, tolerance, and swelling are not modeled."
    )
    model["status"] = "battery_pack_outline_conflict_study"
    model["description"] = (
        "Public LP4473109 6 Ah pack body against the current board, tray, camera, "
        "and audio geometry. The pack is not selected."
    )
    model["caveat"] = (
        "Editable body envelope only, not detailed supplier CAD or a released pack. "
        "The drawing's 50 mm lead and connector are not routed; physical, electrical, "
        "and thermal integration remain blocked."
    )
    return model


def build_memory_variant(repo_root: Path) -> dict:
    """Replace planning DRAM solids with eight unqualified reference outlines."""
    model = build_concept(repo_root)
    report = audit_memory(repo_root)
    study = report["eight_package_study"]
    if study["placement_conflicts"] or study["package_count"] != 8:
        raise ValueError(
            "eight-package reference outline has unresolved planar conflicts"
        )
    floorplan = load_yaml(repo_root / model["sources"]["pcb"])
    planning_ids = {
        part_id
        for part_id, placement in floorplan["placements"].items()
        if placement["function"] == "lpddr5x_32gb_planning_site"
    }
    if len(planning_ids) != 4:
        raise ValueError("unexpected baseline memory planning sites")
    model["parts"] = [part for part in model["parts"] if part["id"] not in planning_ids]
    supplier = load_yaml(repo_root / CANDIDATES)["memory_supplier_context"][PUBLIC_PART]
    supplier_source = f"{CANDIDATES.as_posix()}#memory_supplier_context.{PUBLIC_PART}"
    for item in study["placements"]:
        part_id = item["id"]
        model["parts"].append(
            {
                "id": part_id,
                "label": f"16 GB memory · {part_id.removeprefix('memory_').replace('_', ' ')}",
                "group": "memory",
                "box_mm": item["assembly_box_mm"],
                "evidence_class": "design_assumption",
                "source": supplier_source,
                "active": True,
                "notes": (
                    f"{supplier['part_number']} public package outline; {item['side']} "
                    "placement and X2 support are unqualified."
                ),
                "shape": "chip",
                "geometry_use": "solid",
                "screen_layer": "component_planform"
                if item["side"] == "component"
                else None,
                "roles": ["memory_packages"],
                "geometry_source": f"{STUDY.as_posix()}#placements.{part_id}",
                "geometry_evidence_class": "design_assumption",
            }
        )
    model["component_coverage"] = [
        {
            **item,
            "concept_part_ids": [
                part["id"]
                for part in model["parts"]
                if "memory_packages" in part.get("roles", [])
            ],
        }
        if item["id"] == "memory_packages"
        else item
        for item in model["component_coverage"]
    ]
    if len({part["id"] for part in model["parts"]}) != len(model["parts"]):
        raise ValueError("duplicate part ID in memory variant")
    model["status"] = "eight_package_reference_unqualified"
    model["description"] = (
        "Two-sided eight-package reference alternative. Public package outlines "
        "replace the four 32 GB planning sites; all other concept parts remain."
    )
    model["caveat"] = (
        "Editable outline study only. The 0.8 mm PCB stack remains an unreviewed "
        "fabrication assumption; memory topology, routing, thermal path, and "
        "physical function are unproven."
    )
    return model


def build_compact_memory_variant(repo_root: Path) -> dict:
    """Place the exact compact 16 GB package outlines in the full concept."""
    model = build_memory_variant(repo_root)
    screen = audit_memory(repo_root)["compact_16gb_reference"]
    study = screen["placement_study"]
    if study["status"] != "outline_clear" or study["package_count"] != 8:
        raise ValueError("compact eight-package outline has planar conflicts")
    supplier = load_yaml(repo_root / CANDIDATES)["memory_supplier_context"][
        COMPACT_PART
    ]
    source = f"{CANDIDATES.as_posix()}#memory_supplier_context.{COMPACT_PART}"
    placements = {item["id"]: item for item in study["placements"]}
    replaced = 0
    for part in model["parts"]:
        if part["id"] not in placements:
            continue
        item = placements[part["id"]]
        part["box_mm"] = item["assembly_box_mm"]
        part["source"] = source
        part["geometry_source"] = f"{COMPACT_STUDY.as_posix()}#placements.{part['id']}"
        part["notes"] = (
            f"{supplier['part_number']} public package outline; {item['side']} "
            "placement and X2 support are unqualified."
        )
        replaced += 1
    if replaced != 8:
        raise ValueError("compact memory variant did not replace eight packages")
    model["status"] = "eight_package_compact_reference_unqualified"
    model["description"] = (
        "Two-sided compact eight-package reference alternative. Published Micron "
        "outlines replace the four 32 GB planning sites in the full concept."
    )
    model["caveat"] = (
        "Editable nominal outline study only. The 1.2 mm package exceeds the "
        "original 1.0 mm memory block height. Land patterns, X2 topology, routing, "
        "thermal path, procurement, and physical function are unproven."
    )
    return model


def build_phone_conflict_variant(repo_root: Path) -> dict:
    """Show the rejected board extension, modem, and existing mechanical parts."""
    model = build_memory_variant(repo_root)
    screen = audit_cellular(repo_root)
    extension = screen["reverse_board_extension"]
    if (
        screen["status"] != "outline_blocked"
        or extension["status"] != "mechanical_relayout_required"
        or not extension["board_inside_current_internal_xy"]
        or not extension["board_3d_conflicts"]
        or not extension["module_3d_conflicts"]
    ):
        raise ValueError("phone collision study no longer matches the screened layout")
    board = next(
        part for part in model["parts"] if part["id"] == "main_pcb_placeholder"
    )
    board["box_mm"] = extension["board_global_box_mm"]
    board["geometry_source"] = "docs/engineering/cellular_module_fit.md"
    board["geometry_evidence_class"] = "design_assumption"
    board["notes"] = (
        "Hypothetical board extension; intersects the current camera and speaker envelopes."
    )
    model["parts"].append(
        {
            "id": "cellular_reference_module",
            "label": "Quectel RG255C-GL reference outline",
            "group": "radio",
            "box_mm": extension["module_global_box_mm"],
            "evidence_class": "design_assumption",
            "source": f"{CELLULAR_CANDIDATE.as_posix()}#reference_module",
            "active": True,
            "notes": "Public package dimensions; this placement intersects the current camera envelope. Voice support, X2 integration, and suitability are unverified.",
            "shape": "chip",
            "geometry_use": "solid",
            "screen_layer": None,
            "roles": [],
            "geometry_source": "docs/engineering/cellular_module_fit.md",
            "geometry_evidence_class": "design_assumption",
        }
    )
    model["status"] = "phone_integration_collision_study"
    model["description"] = (
        "Rejected board extension with a public modem outline against the current "
        "eight-package memory, camera, and speaker geometry."
    )
    model["caveat"] = (
        "Deliberate intersections show why this nominal board extension is not a "
        "buildable phone layout. The modem is unselected; all electronics, RF, "
        "mechanical tolerances, and physical function remain unproven."
    )
    return model


def build_compact_phone_variant(repo_root: Path) -> dict:
    """Place the 5G reference beside shifted compact memory on the existing board."""
    model = build_compact_memory_variant(repo_root)
    screen = audit_compact_cellular(repo_root)
    placement = screen["reverse_board_extension"]
    if (
        screen["status"] != "outline_possible_unqualified"
        or placement["status"] != "outline_possible_unqualified"
        or placement["increase_from_current_board_mm"] != 0
        or placement["board_3d_conflicts"]
        or placement["module_3d_conflicts"]
        or not placement["module_above_rear_cover"]
    ):
        raise ValueError("compact phone outline no longer fits the current board")
    model["parts"].append(
        {
            "id": "cellular_reference_module",
            "label": "Quectel RG255C-GL reference outline",
            "group": "radio",
            "box_mm": placement["module_global_box_mm"],
            "evidence_class": "design_assumption",
            "source": f"{CELLULAR_CANDIDATE.as_posix()}#reference_module",
            "active": True,
            "notes": (
                "Public package dimensions at a nominal reverse-side placement. "
                "Voice support, X2 integration, RF and power design, and handheld "
                "suitability are unverified."
            ),
            "shape": "chip",
            "geometry_use": "solid",
            "screen_layer": None,
            "roles": [],
            "geometry_source": "docs/engineering/cellular_module_fit.md",
            "geometry_evidence_class": "design_assumption",
        }
    )
    model["status"] = "compact_phone_outline_unqualified"
    model["description"] = (
        "Compact eight-package memory and 5G reference outlines on the current "
        "board inside the full concept assembly."
    )
    model["caveat"] = (
        "Nominal outline geometry only. The 128 GB memory topology and modem "
        "attachment are unqualified; land patterns, routing, RF feeds, power, "
        "tolerance, thermal behavior, and working phone function are unproven."
    )
    return model


def _shape(cq, part: dict):
    x, y, z, length, width, height = part["box_mm"]
    kind = part["shape"]
    body = cq.Workplane("XY").box(length, width, height, centered=False)
    if kind in {"rounded_box", "speaker", "rear_panel", "pcb"}:
        radius = min(float(part.get("radius_mm", 1.0)), length / 3, width / 3)
        body = body.edges("|Z").fillet(radius)
    if kind == "rear_panel":
        center_x, center_y = part["aperture_center_mm"]
        aperture = (
            cq.Workplane("XY")
            .center(center_x - x, center_y - y)
            .circle(float(part["aperture_radius_mm"]))
            .extrude(height + 2)
            .translate((0, 0, -1))
        )
        body = body.cut(aperture)
    elif kind == "pcb":
        for hole_x in (4, length - 4):
            for hole_y in (4, width - 4):
                drill = (
                    cq.Workplane("XY")
                    .center(hole_x, hole_y)
                    .circle(0.9)
                    .extrude(height + 2)
                    .translate((0, 0, -1))
                )
                body = body.cut(drill)
    elif kind == "speaker":
        slot_width = min(0.8, length / 12)
        for slot_x in (length * 0.3, length * 0.5, length * 0.7):
            slot = (
                cq.Workplane("XY")
                .box(slot_width, width * 0.55, height * 0.4, centered=False)
                .translate((slot_x - slot_width / 2, width * 0.225, height * 0.6))
            )
            body = body.cut(slot)
    elif kind == "chip":
        inset = min(0.6, length * 0.12, width * 0.12)
        recess_depth = min(0.08, height * 0.12)
        recess = (
            cq.Workplane("XY")
            .box(
                length - 2 * inset,
                width - 2 * inset,
                recess_depth + 0.1,
                centered=False,
            )
            .translate((inset, inset, height - recess_depth))
        )
        body = body.cut(recess)
    elif kind == "battery_tray":
        wall = float(part["wall_mm"])
        floor = min(0.3, height * 0.1)
        cavity = (
            cq.Workplane("XY")
            .box(length - 2 * wall, width - 2 * wall, height + 1, centered=False)
            .translate((wall, wall, floor))
        )
        body = body.cut(cavity)
    elif kind == "camera_module":
        rear = part.get("lens_face") == "rear"
        base_z = height * 0.35 if rear else 0
        lens_z = 0 if rear else height * 0.65
        body = (
            cq.Workplane("XY")
            .box(length, width, height * 0.65, centered=False)
            .translate((0, 0, base_z))
        )
        lens_radius = float(part["lens_radius_mm"])
        lens = (
            cq.Workplane("XY")
            .center(length / 2, width / 2)
            .circle(lens_radius)
            .extrude(height * 0.35)
            .translate((0, 0, lens_z))
        )
        body = body.union(lens)
        well_z = 0 if rear else height * 0.9
        optical_well = (
            cq.Workplane("XY")
            .center(length / 2, width / 2)
            .circle(lens_radius * 0.42)
            .extrude(height * 0.1)
            .translate((0, 0, well_z))
        )
        body = body.cut(optical_well)
    elif kind == "cylinder":
        body = (
            cq.Workplane("XY")
            .center(length / 2, width / 2)
            .circle(min(length, width) / 2)
            .extrude(height)
        )
    elif kind in {"coil", "gasket", "port"}:
        band = float(part.get("band_mm", max(0.5, min(length, width) * 0.18)))
        if kind == "port":
            void = (
                cq.Workplane("XY")
                .box(length * 0.75, width + 2, height * 0.55, centered=False)
                .translate((length * 0.125, -1, height * 0.225))
            )
        else:
            void = (
                cq.Workplane("XY")
                .box(length - 2 * band, width - 2 * band, height + 2, centered=False)
                .translate((band, band, -1))
            )
        body = body.cut(void)
    elif kind == "ported_frame":
        void = (
            cq.Workplane("XY")
            .box(
                FRAME_PORT_APERTURE_WIDTH_MM,
                width + 2,
                FRAME_PORT_APERTURE_HEIGHT_MM,
                centered=False,
            )
            .translate(
                (
                    length / 2 - FRAME_PORT_APERTURE_WIDTH_MM / 2,
                    -1,
                    FRAME_PORT_APERTURE_Z_OFFSET_MM,
                )
            )
        )
        body = body.cut(void)
    elif kind not in {"box", "rounded_box"}:
        raise ValueError(f"unknown CAD shape: {kind}")
    if "optical_aperture_radius_mm" in part:
        center_x, center_y = part["optical_aperture_center_mm"]
        aperture = (
            cq.Workplane("XY")
            .center(center_x - x, center_y - y)
            .circle(part["optical_aperture_radius_mm"])
            .extrude(height + 2)
            .translate((0, 0, -1))
        )
        body = body.cut(aperture)
    return body.translate((x, y, z))


def _gltf(solids: list[tuple[dict, object]]) -> dict:
    binary = bytearray()
    views, accessors, meshes, nodes = [], [], [], []
    for part, solid in solids:
        vertices, triangles = solid.val().tessellate(0.2, 0.3)
        coords = [(v.x, v.y, v.z) for v in vertices]
        if not coords or not triangles:
            raise ValueError(f"empty tessellation: {part['id']}")
        positions = []
        normals = []
        for triangle in triangles:
            a, b, c = (coords[index] for index in triangle)
            ab = [b[i] - a[i] for i in range(3)]
            ac = [c[i] - a[i] for i in range(3)]
            normal = (
                ab[1] * ac[2] - ab[2] * ac[1],
                ab[2] * ac[0] - ab[0] * ac[2],
                ab[0] * ac[1] - ab[1] * ac[0],
            )
            magnitude = math.sqrt(sum(value * value for value in normal))
            if magnitude == 0:
                raise ValueError(f"degenerate CAD triangle: {part['id']}")
            normal = tuple(value / magnitude for value in normal)
            positions.extend((a, b, c))
            normals.extend((normal, normal, normal))
        offset = len(binary)
        for coordinate in positions:
            binary.extend(struct.pack("<3f", *coordinate))
        views.append(
            {
                "buffer": 0,
                "byteOffset": offset,
                "byteLength": len(positions) * 12,
                "target": 34962,
            }
        )
        position = len(accessors)
        accessors.append(
            {
                "bufferView": len(views) - 1,
                "componentType": 5126,
                "count": len(positions),
                "type": "VEC3",
                "min": [min(v[i] for v in coords) for i in range(3)],
                "max": [max(v[i] for v in coords) for i in range(3)],
            }
        )
        offset = len(binary)
        for normal in normals:
            binary.extend(struct.pack("<3f", *normal))
        views.append(
            {
                "buffer": 0,
                "byteOffset": offset,
                "byteLength": len(normals) * 12,
                "target": 34962,
            }
        )
        normal = len(accessors)
        accessors.append(
            {
                "bufferView": len(views) - 1,
                "componentType": 5126,
                "count": len(normals),
                "type": "VEC3",
            }
        )
        meshes.append(
            {
                "primitives": [
                    {
                        "attributes": {"POSITION": position, "NORMAL": normal},
                        "material": 0,
                    }
                ]
            }
        )
        nodes.append(
            {
                "name": part["id"],
                "mesh": len(meshes) - 1,
                "extras": {"part_id": part["id"]},
            }
        )
    return {
        "asset": {
            "version": "2.0",
            "generator": "BuildSlate CadQuery concept exporter",
        },
        "scene": 0,
        "scenes": [{"nodes": list(range(len(nodes)))}],
        "nodes": nodes,
        "meshes": meshes,
        "buffers": [
            {
                "uri": "data:application/octet-stream;base64,"
                + base64.b64encode(binary).decode("ascii"),
                "byteLength": len(binary),
            }
        ],
        "bufferViews": views,
        "accessors": accessors,
        "materials": [
            {
                "doubleSided": True,
                "pbrMetallicRoughness": {
                    "baseColorFactor": [0.7, 0.75, 0.82, 1],
                    "roughnessFactor": 0.65,
                },
            }
        ],
    }


def _export(
    cq,
    root: Path,
    model: dict,
    step: Path,
    output: Path,
    gltf: Path,
    proof_output: Path,
) -> None:
    cad = cq.Assembly(name=model["device"])
    solids = []
    for part in model["parts"]:
        solid = _shape(cq, part)
        if len(solid.solids().vals()) != 1:
            raise ValueError(f"concept part is not one solid: {part['id']}")
        cad.add(solid, name=part["id"])
        solids.append((part, solid))
    exact_bounds = {}
    for part, solid in solids:
        box = solid.val().BoundingBox()
        exact_bounds[part["id"]] = [
            box.xmin,
            box.ymin,
            box.zmin,
            box.xmax,
            box.ymax,
            box.zmax,
        ]
    step_path = root / step
    step_path.parent.mkdir(parents=True, exist_ok=True)
    cad.export(str(step_path))
    step_text, count = re.subn(
        r"(FILE_NAME\('Open CASCADE Shape Model',')[^']+(')",
        r"\g<1>1970-01-01T00:00:00\2",
        step_path.read_text(encoding="utf-8"),
    )
    if count != 1:
        raise ValueError("STEP header format changed")
    step_path.write_text(step_text, encoding="utf-8", newline="\n")
    imported_solids = cq.importers.importStep(str(step_path)).solids().vals()
    geometry = _gltf(solids)
    proof = build_proof(root, model, solids, geometry, imported_solids, exact_bounds)
    if model["status"] in {
        "eight_package_reference_unqualified",
        "phone_integration_collision_study",
    }:
        proof["memory_study"] = audit_memory(root)["eight_package_study"]
    if model["status"] == "eight_package_compact_reference_unqualified":
        proof["memory_study"] = audit_memory(root)["compact_16gb_reference"][
            "placement_study"
        ]
    if model["status"] == "compact_phone_outline_unqualified":
        proof["memory_study"] = audit_memory(root)["compact_16gb_reference"][
            "placement_study"
        ]
        proof["phone_outline_study"] = audit_compact_cellular(root)
    if model["status"] == "phone_integration_collision_study":
        proof["phone_extension"] = audit_cellular(root)["reverse_board_extension"]
    if model["status"] == "usb_connector_outline_conflict_study":
        candidate = load_yaml(root / USB_CANDIDATE)["candidate"]
        proof["usb_candidate"] = {
            "mpn": candidate["mpn"],
            "drawing_revision": candidate["drawing_revision"],
            "source": candidate["sources"]["manufacturer_drawing"],
            "drawing_sha256": candidate["sources"]["distributor_drawing_sha256"],
            "caveat": "Bounding envelope, not supplier STEP or released footprint.",
        }
    if model["status"] == "battery_pack_outline_conflict_study":
        proof["battery_pack_candidate"] = audit_battery(root)["lipol_pack_screen"]
    (root / output).write_text(
        json.dumps(model, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    (root / gltf).write_text(
        json.dumps(geometry, separators=(",", ":")) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    (root / proof_output).write_text(
        json.dumps(proof, indent=2) + "\n", encoding="utf-8", newline="\n"
    )


def generate(repo_root: Path = DEFAULT_REPO_ROOT) -> tuple[int, Path]:
    try:
        import cadquery as cq
    except ImportError as error:
        raise RuntimeError("Install requirements-cad.txt with Python 3.12") from error
    root = repo_root.resolve()
    model = build_concept(root)
    _export(cq, root, model, STEP, MODEL, GLTF, PROOF)
    variant = build_memory_variant(root)
    _export(cq, root, variant, MEMORY_STEP, MEMORY_MODEL, MEMORY_GLTF, MEMORY_PROOF)
    compact = build_compact_memory_variant(root)
    _export(
        cq,
        root,
        compact,
        COMPACT_MEMORY_STEP,
        COMPACT_MEMORY_MODEL,
        COMPACT_MEMORY_GLTF,
        COMPACT_MEMORY_PROOF,
    )
    phone = build_phone_conflict_variant(root)
    _export(cq, root, phone, PHONE_STEP, PHONE_MODEL, PHONE_GLTF, PHONE_PROOF)
    usb = build_usb_connector_variant(root)
    _export(cq, root, usb, USB_STEP, USB_MODEL, USB_GLTF, USB_PROOF)
    battery = build_battery_pack_variant(root)
    _export(cq, root, battery, BATTERY_STEP, BATTERY_MODEL, BATTERY_GLTF, BATTERY_PROOF)
    compact_phone = build_compact_phone_variant(root)
    _export(
        cq,
        root,
        compact_phone,
        COMPACT_PHONE_STEP,
        COMPACT_PHONE_MODEL,
        COMPACT_PHONE_GLTF,
        COMPACT_PHONE_PROOF,
    )
    return len(model["parts"]), root / STEP


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=DEFAULT_REPO_ROOT)
    args = parser.parse_args()
    count, path = generate(args.repo_root)
    print(f"Exported {count} baseline solids to {path}")
    print(f"Exported eight-package reference STEP to {args.repo_root / MEMORY_STEP}")
    print(
        f"Exported compact eight-package STEP to {args.repo_root / COMPACT_MEMORY_STEP}"
    )
    print(f"Exported phone collision study STEP to {args.repo_root / PHONE_STEP}")
    print(f"Exported USB connector outline STEP to {args.repo_root / USB_STEP}")
    print(f"Exported battery pack outline STEP to {args.repo_root / BATTERY_STEP}")
    print(
        f"Exported compact phone outline STEP to {args.repo_root / COMPACT_PHONE_STEP}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
