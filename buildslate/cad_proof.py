"""Measure concept CAD integrity and expose unresolved packaging conflicts.

These checks prove properties of the committed concept geometry. They do not
qualify supplier parts, tolerances, electronics, RF, thermal behavior, or a build.
"""

from __future__ import annotations

import hashlib
import json
from itertools import combinations
from pathlib import Path
from typing import Any

from .io import load_yaml

PROOF = Path("viewer/public/proof.json")
DECLARED_BOUNDS_TOLERANCE_MM = 0.01
MESH_BOUNDS_MAX_TOLERANCE_MM = 0.25
INTERFERENCE_THRESHOLD_MM3 = 0.01


def _source_exists(root: Path, reference: str) -> bool:
    path, separator, anchor = reference.partition("#")
    target = (root / path).resolve()
    if not target.is_relative_to(root.resolve()) or not target.is_file():
        return False
    if not separator:
        return True
    if target.suffix not in {".yaml", ".yml"}:
        return False
    node: Any = load_yaml(target)
    for key in anchor.split("."):
        if isinstance(node, dict) and key in node:
            node = node[key]
        elif isinstance(node, list):
            match = next(
                (
                    item
                    for item in node
                    if isinstance(item, dict) and item.get("id") == key
                ),
                None,
            )
            if match is None:
                return False
            node = match
        else:
            return False
    return True


def _declared_bounds(part: dict) -> list[float]:
    x, y, z, length, width, height = part["box_mm"]
    return [x, y, z, x + length, y + width, z + height]


def _near_bounds(actual: list[float], expected: list[float], tolerance: float) -> bool:
    return all(abs(a - b) <= tolerance for a, b in zip(actual, expected, strict=True))


def _mesh_bounds_match(mesh: list[float], brep: list[float]) -> bool:
    for axis in range(3):
        extent = brep[axis + 3] - brep[axis]
        tolerance = min(MESH_BOUNDS_MAX_TOLERANCE_MM, max(0.005, extent * 0.05))
        if (
            abs(mesh[axis] - brep[axis]) > tolerance
            or abs(mesh[axis + 3] - brep[axis + 3]) > tolerance
        ):
            return False
    return True


def _boxes_overlap(a: list[float], b: list[float]) -> bool:
    return all(min(a[i + 3], b[i + 3]) - max(a[i], b[i]) > 0.001 for i in range(3))


def _rectangle_overlap_area(box: list[float], rect: dict) -> float:
    x, y, _, length, width, _ = box
    dx = min(x + length, rect["x"] + rect["length"]) - max(x, rect["x"])
    dy = min(y + width, rect["y"] + rect["width"]) - max(y, rect["y"])
    return max(0.0, dx) * max(0.0, dy)


def measure_intersections(parts: list[dict], shapes: dict[str, Any]) -> list[dict]:
    """Use a box broad phase and exact BREP Boolean volume for each candidate."""
    intersections = []
    for first, second in combinations(parts, 2):
        if not _boxes_overlap(_declared_bounds(first), _declared_bounds(second)):
            continue
        volume = shapes[first["id"]].intersect(shapes[second["id"]]).Volume()
        if volume <= INTERFERENCE_THRESHOLD_MM3:
            continue
        reservation = (
            not first["active"]
            or not second["active"]
            or first["geometry_use"] == "reservation"
            or second["geometry_use"] == "reservation"
        )
        intersections.append(
            {
                "first": first["id"],
                "second": second["id"],
                "volume_mm3": round(volume, 3),
                "kind": "reservation_conflict" if reservation else "interference",
            }
        )
    return intersections


def _zone_screen(root: Path, model: dict) -> list[dict]:
    stackups = load_yaml(root / model["sources"]["stackups"])
    budget = float(stackups["metadata"]["device_thickness_mm"])
    rules = stackups["decision_rules"]

    def layers(zone_id: str) -> list[dict]:
        zone = stackups["zones"][zone_id]
        if "inherits" in zone:
            return layers(zone["inherits"]) + zone.get("additional_layers", [])
        return zone["layers"]

    results = []
    for zone_id in stackups["zones"]:
        total = sum(float(layer["thickness_mm"]) for layer in layers(zone_id))
        margin = budget - total
        if margin >= float(rules["pass_margin_mm"]):
            status = "pass"
        elif margin >= float(rules["warning_margin_mm"]):
            status = "warning"
        else:
            status = "fail"
        results.append(
            {
                "id": zone_id,
                "status": status,
                "total_mm": round(total, 3),
                "margin_mm": round(margin, 3),
                "basis": model["sources"]["stackups"],
            }
        )
    return results


def build_proof(
    root: Path,
    model: dict,
    solids: list[tuple[dict, Any]],
    gltf: dict,
    imported_solids: list[Any],
    exact_bounds: dict[str, list[float]],
) -> dict:
    """Return a deterministic proof report derived from BREP, mesh and sources."""
    if len(solids) != len(model["parts"]):
        raise ValueError("CAD solid count does not match concept parts")
    model_text = json.dumps(model, indent=2) + "\n"
    model_sha256 = hashlib.sha256(model_text.encode("utf-8")).hexdigest()
    mesh_nodes = {node["extras"]["part_id"]: node for node in gltf["nodes"]}
    if set(mesh_nodes) != {part["id"] for part in model["parts"]}:
        raise ValueError("mesh identities do not match concept parts")
    volume_expected = sum(shape.val().Volume() for _, shape in solids)
    volume_imported = sum(shape.Volume() for shape in imported_solids)
    step_roundtrip = len(imported_solids) == len(solids) and abs(
        volume_imported - volume_expected
    ) <= max(0.01, volume_expected * 1e-7)
    if not step_roundtrip:
        raise ValueError("STEP round-trip changed solid count or aggregate volume")
    part_reports = []
    by_id = {}
    shape_by_id = {}
    for part, workplane in solids:
        part_id = part["id"]
        shape = workplane.val()
        shape_by_id[part_id] = shape
        actual = exact_bounds[part_id]
        node = mesh_nodes[part_id]
        primitive = gltf["meshes"][node["mesh"]]["primitives"][0]
        mesh_bounds = gltf["accessors"][primitive["attributes"]["POSITION"]]
        mesh_box = mesh_bounds["min"] + mesh_bounds["max"]
        checks = {
            "valid_solid": bool(shape.isValid())
            and len(workplane.solids().vals()) == 1,
            "positive_volume": shape.Volume() > 0,
            "declared_bounds": _near_bounds(
                actual, _declared_bounds(part), DECLARED_BOUNDS_TOLERANCE_MM
            ),
            "mesh_matches_brep": _mesh_bounds_match(mesh_box, actual),
            "source_anchor": _source_exists(root, part["source"]),
            "geometry_anchor": _source_exists(root, part["geometry_source"]),
        }
        if not all(checks.values()):
            raise ValueError(f"CAD integrity failed for {part_id}: {checks}")
        report = {
            "id": part_id,
            "checks": checks,
            "volume_mm3": round(shape.Volume(), 3),
            "surface_area_mm2": round(shape.Area(), 3),
            "faces": len(shape.Faces()),
            "edges": len(shape.Edges()),
            "interference_ids": [],
            "reservation_conflict_ids": [],
            "keepout_ids": [],
        }
        part_reports.append(report)
        by_id[part_id] = report
    intersections = measure_intersections(model["parts"], shape_by_id)
    for item in intersections:
        key = (
            "reservation_conflict_ids"
            if item["kind"] == "reservation_conflict"
            else "interference_ids"
        )
        by_id[item["first"]][key].append(item["second"])
        by_id[item["second"]][key].append(item["first"])
    keepout_conflicts = []
    keepout_specs = load_yaml(root / model["sources"]["keepouts"])["keepouts"]
    for part in model["parts"]:
        layer = part.get("screen_layer")
        if not part["active"] or part["geometry_use"] == "reservation" or not layer:
            continue
        for keepout in model["keepouts"]:
            spec = keepout_specs[keepout["id"]]
            if (
                layer not in spec["applies_to_layers"]
                or part["id"] in spec.get("allowed_placements", [])
                or keepout["id"] in part.get("allowed_keepouts", [])
            ):
                continue
            area = _rectangle_overlap_area(part["box_mm"], keepout["rectangle_mm"])
            if area <= 0:
                continue
            keepout_conflicts.append(
                {
                    "part_id": part["id"],
                    "keepout_id": keepout["id"],
                    "category": keepout["category"],
                    "overlap_area_mm2": round(area, 3),
                }
            )
            by_id[part["id"]]["keepout_ids"].append(keepout["id"])
    zones = _zone_screen(root, model)
    physical = [item for item in intersections if item["kind"] == "interference"]
    reserves = [
        item for item in intersections if item["kind"] == "reservation_conflict"
    ]
    unverified = sum(part["evidence_class"] != "verified" for part in model["parts"])
    library = load_yaml(root / model["sources"]["component_library"])["components"]
    role_reports = []
    for coverage in model["component_coverage"]:
        part_ids = coverage["concept_part_ids"]
        if not part_ids or any(part_id not in by_id for part_id in part_ids):
            raise ValueError(
                f"component role has no checked CAD solid: {coverage['id']}"
            )
        role_reports.append(
            {
                "id": coverage["id"],
                "part_ids": part_ids,
                "geometry_integrity_passed": all(
                    all(by_id[part_id]["checks"].values()) for part_id in part_ids
                ),
                "interference_count": sum(
                    len(by_id[part_id]["interference_ids"]) for part_id in part_ids
                ),
                "keepout_count": sum(
                    len(by_id[part_id]["keepout_ids"]) for part_id in part_ids
                ),
                "source_representation": coverage["representation"],
                "evidence_status": "unverified",
                "missing_evidence": library[coverage["id"]]["unknowns"],
            }
        )
    return {
        "schema_version": 1,
        "device": model["device"],
        "model_sha256": model_sha256,
        "status": "review_required",
        "method": "CadQuery BREP validity, exact Boolean intersections, STEP round-trip, glTF bounds, anchored sources, planform keepouts, and local stack sums.",
        "thresholds": {
            "declared_bounds_tolerance_mm": DECLARED_BOUNDS_TOLERANCE_MM,
            "mesh_bounds_max_tolerance_mm": MESH_BOUNDS_MAX_TOLERANCE_MM,
            "interference_volume_mm3": INTERFERENCE_THRESHOLD_MM3,
        },
        "summary": {
            "parts_checked": len(part_reports),
            "roles_covered": len(model["component_coverage"]),
            "roles_checked": len(role_reports),
            "integrity_passed": all(
                all(item["checks"].values()) for item in part_reports
            ),
            "step_roundtrip_passed": step_roundtrip,
            "interferences": len(physical),
            "reservation_conflicts": len(reserves),
            "keepout_conflicts": len(keepout_conflicts),
            "stack_failures": sum(item["status"] == "fail" for item in zones),
            "unverified_parts": unverified,
        },
        "parts": part_reports,
        "roles": role_reports,
        "intersections": intersections,
        "keepout_conflicts": keepout_conflicts,
        "zones": zones,
        "caveat": "Integrity checks establish that the concept artifacts agree. Interferences and keepout overlaps are unresolved design work. No fit, tolerance, performance, or release approval is implied.",
    }
