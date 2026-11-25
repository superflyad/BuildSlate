"""Screen a public 5G voice-module outline against the current 128 GB board plan."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from buildslate.io import load_yaml

CANDIDATE = Path("research/evidence/cellular/candidate-comparison.yaml")
MEMORY_CANDIDATES = Path("research/evidence/compute/platform-comparison.yaml")
FLOORPLAN = Path("engineering/pcb/slate-pocket-v1r-floorplan/floorplan.yaml")
MEMORY_STUDY = Path("engineering/pcb/slate-pocket-v1r-floorplan/memory-8x16-study.yaml")
COMPACT_MEMORY_STUDY = Path(
    "engineering/pcb/slate-pocket-v1r-floorplan/memory-8x16-compact-study.yaml"
)
ENVELOPE = Path("cad/slate-pocket-v1r/envelope-model/envelope.yaml")
ASSEMBLY = Path("engineering/assembly/assembly.yaml")
CONCEPT = Path("engineering/assembly/concept-cad.yaml")
MEMORY_ID = "micron_lpddr5x_16gb_public_part"
COMPACT_MEMORY_ID = "micron_lpddr5x_16gb_compact_part"


def _intersects_with_clearance(a: tuple, b: tuple, clearance: float) -> bool:
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    return (
        ax < bx + bw + clearance
        and ax + aw + clearance > bx
        and ay < by + bh + clearance
        and ay + ah + clearance > by
    )


def _valid_origins(boundary: tuple, obstacles: list[tuple], size: tuple, gap: float):
    """Test every axis-aligned origin after sliding left/down to a boundary."""
    x0, y0, length, width = boundary
    module_length, module_width = size
    xs = sorted({x0, *(x + w + gap for x, y, w, h in obstacles)})
    ys = sorted({y0, *(y + h + gap for x, y, w, h in obstacles)})
    for x in xs:
        for y in ys:
            placed = (x, y, module_length, module_width)
            if x + module_length > x0 + length or y + module_width > y0 + width:
                continue
            if not any(
                _intersects_with_clearance(placed, item, gap) for item in obstacles
            ):
                yield (x, y)


def _overlaps_3d(a: tuple, b: tuple) -> bool:
    return all(a[i] < b[i] + b[i + 3] and a[i] + a[i + 3] > b[i] for i in range(3))


def _reverse_board_extension(
    floorplan: dict,
    envelope: dict,
    assembly: dict,
    concept: dict,
    obstacles: list[tuple],
    package: list[float],
    gap: float,
) -> dict:
    """Find the first whole-mm board-width extension that holds the module outline."""
    outer = floorplan["board"]["outline_mm"]
    inner = floorplan["board"]["component_side_boundary_mm"]
    origin = floorplan["board"]["origin_in_mechanical_model_mm"]
    outer_length, outer_width, thickness = (
        float(outer[key]) for key in ("length", "width", "thickness")
    )
    inset_top = outer_width - float(inner["y"]) - float(inner["width"])
    max_obstacle_top = max(y + h for x, y, w, h in obstacles)
    search_end = math.ceil(max_obstacle_top + gap + max(package[:2]) + inset_top)
    found = None
    for candidate_width in range(math.ceil(outer_width), search_end + 1):
        boundary = (
            float(inner["x"]),
            float(inner["y"]),
            float(inner["length"]),
            candidate_width - float(inner["y"]) - inset_top,
        )
        for orientation, size in (
            (f"{package[0]:g}x{package[1]:g}", tuple(package[:2])),
            (f"{package[1]:g}x{package[0]:g}", tuple(reversed(package[:2]))),
        ):
            first = next(_valid_origins(boundary, obstacles, size, gap), None)
            if first is not None:
                found = (float(candidate_width), orientation, first, size)
                break
        if found is not None:
            break
    if found is None:
        return {"status": "outline_blocked", "minimum_whole_mm_board_width": None}
    board_width, orientation, local_origin, size = found
    board_bottom = float(
        assembly["parts"]["mechanical"]["main_pcb_placeholder"]["z_mm"]
    )
    board_box = (
        float(origin["x"]),
        float(origin["y"]),
        board_bottom,
        outer_length,
        board_width,
        thickness,
    )
    module_box = (
        board_box[0] + local_origin[0],
        board_box[1] + local_origin[1],
        board_bottom - package[2],
        size[0],
        size[1],
        package[2],
    )
    mechanical = envelope["placements"]
    conflicts = {"board": [], "module": []}
    for name, item in mechanical.items():
        if name == "main_pcb_placeholder" or item["layer"] != "component_planform":
            continue
        rect = item["rectangle_mm"]
        part_box = (
            float(rect["x"]),
            float(rect["y"]),
            float(assembly["parts"]["mechanical"][name]["z_mm"]),
            float(rect["length"]),
            float(rect["width"]),
            float(item["height_mm"]),
        )
        if _overlaps_3d(board_box, part_box):
            conflicts["board"].append(name)
        if _overlaps_3d(module_box, part_box):
            conflicts["module"].append(name)
    for name, item in concept["additional_parts"].items():
        if item.get("geometry_use", "solid") != "solid":
            continue
        part_box = tuple(float(value) for value in item["box_mm"])
        if _overlaps_3d(board_box, part_box):
            conflicts["board"].append(name)
        if _overlaps_3d(module_box, part_box):
            conflicts["module"].append(name)
    internal = envelope["device"]["internal_boundary_mm"]
    inside = (
        board_box[0] >= float(internal["x"])
        and board_box[1] >= float(internal["y"])
        and board_box[0] + board_box[3]
        <= float(internal["x"]) + float(internal["length"])
        and board_box[1] + board_box[4]
        <= float(internal["y"]) + float(internal["width"])
    )
    rear_cover_top = float(assembly["parts"]["enclosure"]["rear_cover"]["box_mm"][5])
    above_rear_cover = module_box[2] >= rear_cover_top
    return {
        "status": "mechanical_relayout_required"
        if any(conflicts.values()) or not inside or not above_rear_cover
        else "outline_possible_unqualified",
        "search_resolution_mm": 1,
        "minimum_whole_mm_board_width": board_width,
        "increase_from_current_board_mm": board_width - outer_width,
        "module_orientation": orientation,
        "module_local_origin_mm": list(local_origin),
        "module_global_box_mm": [round(value, 3) for value in module_box],
        "board_global_box_mm": list(board_box),
        "board_inside_current_internal_xy": inside,
        "board_3d_conflicts": conflicts["board"],
        "module_3d_conflicts": conflicts["module"],
        "module_above_rear_cover": above_rear_cover,
        "module_bottom_to_rear_cover_mm": round(module_box[2] - rear_cover_top, 3),
        "caveat": "Whole-mm board-width search and nominal boxes only; this is not a qualified modem site, board, or phone design.",
    }


def audit_data(
    candidate: dict,
    memory_candidates: dict,
    floorplan: dict,
    study: dict,
    envelope: dict,
    assembly: dict,
    concept: dict,
    memory_id: str = MEMORY_ID,
    memory_study_source: Path = MEMORY_STUDY,
) -> dict:
    """Report whether the module outline fits each side at a nominal 1 mm gap."""
    module = candidate["reference_module"]
    package = [float(value) for value in module["package_mm"]]
    gap = float(candidate["screen"]["assumed_nominal_package_clearance_mm"])
    if min(*package, gap) < 0 or any(value == 0 for value in package):
        raise ValueError("Module dimensions must be positive and clearance nonnegative")
    memory = memory_candidates["memory_supplier_context"][memory_id]
    memory_length, memory_width = (float(value) for value in memory["package_mm"][:2])
    orientation = study["metadata"].get("package_orientation", "unrotated")
    if orientation == "rotated_90":
        memory_length, memory_width = memory_width, memory_length
    boundary_data = floorplan["board"]["component_side_boundary_mm"]
    boundary = tuple(float(boundary_data[key]) for key in ("x", "y", "length", "width"))
    memory_obstacles: dict[str, list[tuple]] = {"component": [], "reverse": []}
    errors = []
    if study["metadata"]["reference_part"] != memory_id:
        errors.append("Memory study does not use the screened public package")
    if orientation not in {"unrotated", "rotated_90"}:
        errors.append("Memory study has an unsupported package orientation")
    expected_orientation = (
        "rotated_90" if memory_id == COMPACT_MEMORY_ID else "unrotated"
    )
    if orientation != expected_orientation:
        errors.append("Memory package orientation differs from its screened study")
    if floorplan["metadata"]["modeled_memory_tier_gb"] != 128:
        errors.append("Board plan is not the 128 GB study")
    if concept.get("schema_version") != 1:
        errors.append("Concept CAD manifest schema is unsupported")
    board = floorplan["board"]
    mechanical_board = envelope["placements"]["main_pcb_placeholder"]
    rect = mechanical_board["rectangle_mm"]
    if (
        any(
            not math.isclose(
                float(board["outline_mm"][key]), float(rect[key]), abs_tol=1e-6
            )
            for key in ("length", "width")
        )
        or any(
            not math.isclose(
                float(board["origin_in_mechanical_model_mm"][key]),
                float(rect[key]),
                abs_tol=1e-6,
            )
            for key in ("x", "y")
        )
        or not math.isclose(
            float(board["outline_mm"]["thickness"]),
            float(mechanical_board["height_mm"]),
            abs_tol=1e-6,
        )
    ):
        errors.append("Board floorplan and mechanical placement disagree")
    if not math.isclose(
        float(assembly["parts"]["mechanical"]["main_pcb_placeholder"]["z_mm"])
        + float(board["outline_mm"]["thickness"]),
        float(assembly["parts"]["pcb"]["z_mm"]),
        abs_tol=1e-6,
    ):
        errors.append("PCB top and bottom elevations disagree")
    for name, item in study["placements"].items():
        side = item["side"]
        if side not in memory_obstacles:
            errors.append(f"{name}: unknown board side")
            continue
        memory_obstacles[side].append(
            (
                float(item["x_mm"]),
                float(item["y_mm"]),
                memory_length,
                memory_width,
            )
        )
    if {side: len(items) for side, items in memory_obstacles.items()} != {
        "component": 4,
        "reverse": 4,
    }:
        errors.append("Memory study must have four reference packages per side")
    component_obstacles = list(memory_obstacles["component"])
    component_obstacles.extend(
        tuple(float(rect[key]) for key in ("x", "y", "length", "width"))
        for item in floorplan["placements"].values()
        if item["function"] != "lpddr5x_32gb_planning_site"
        for rect in (item["rectangle_mm"],)
    )
    sides = {}
    for side, obstacles in (
        ("component", component_obstacles),
        ("reverse", memory_obstacles["reverse"]),
    ):
        orientations = {}
        for name, size in (
            (f"{package[0]:g}x{package[1]:g}", tuple(package[:2])),
            (f"{package[1]:g}x{package[0]:g}", tuple(reversed(package[:2]))),
        ):
            origins = list(_valid_origins(boundary, obstacles, size, gap))
            orientations[name] = {
                "outline_fits": bool(origins),
                "first_nominal_origin_mm": list(origins[0]) if origins else None,
            }
        sides[side] = {
            "memory_packages": len(memory_obstacles[side]),
            "other_planning_rectangles": len(obstacles) - len(memory_obstacles[side]),
            "orientations": orientations,
            "outline_fits": any(item["outline_fits"] for item in orientations.values()),
        }
    fits = any(item["outline_fits"] for item in sides.values())
    extension = _reverse_board_extension(
        floorplan,
        envelope,
        assembly,
        concept,
        memory_obstacles["reverse"],
        package,
        gap,
    )
    if errors:
        status = "source_conflict"
    else:
        status = "outline_possible_unqualified" if fits else "outline_blocked"
    return {
        "status": status,
        "candidate": module["variant"],
        "candidate_role": "public_reference_not_selected",
        "memory_reference_part": memory["part_number"],
        "memory_study_source": memory_study_source.as_posix(),
        "memory_package_orientation": orientation,
        "technology": module["technology"],
        "package_mm": package,
        "board_outline_mm": [
            float(floorplan["board"]["outline_mm"][key])
            for key in ("length", "width", "thickness")
        ],
        "usable_board_boundary_mm": list(boundary),
        "assumed_nominal_package_clearance_mm": gap,
        "sides": sides,
        "reverse_board_extension": extension,
        "voice": module["voice"],
        "supplier_design_documents": module["supplier_design_documents"],
        "source_errors": errors,
        "required_before_selection": candidate["screen"]["required_before_selection"],
        "source": module["source"]["url"],
        "caveat": (
            "This only tests axis-aligned module outlines against planning rectangles. "
            "It does not check land patterns, routes, power transients, two antenna "
            "feeds, SIM, audio, 3D fit, thermal behavior, carrier support, or approval."
        ),
    }


def audit(root: Path) -> dict:
    return audit_data(
        *(
            load_yaml(root / path)
            for path in (
                CANDIDATE,
                MEMORY_CANDIDATES,
                FLOORPLAN,
                MEMORY_STUDY,
                ENVELOPE,
                ASSEMBLY,
                CONCEPT,
            )
        )
    )


def audit_compact(root: Path) -> dict:
    """Screen the compact 16 GB package arrangement against the same modem."""
    return audit_data(
        *(
            load_yaml(root / path)
            for path in (
                CANDIDATE,
                MEMORY_CANDIDATES,
                FLOORPLAN,
                COMPACT_MEMORY_STUDY,
                ENVELOPE,
                ASSEMBLY,
                CONCEPT,
            )
        ),
        memory_id=COMPACT_MEMORY_ID,
        memory_study_source=COMPACT_MEMORY_STUDY,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo-root", type=Path, default=Path(__file__).resolve().parents[1]
    )
    parser.add_argument(
        "--compact",
        action="store_true",
        help="Screen the shifted compact 16 GB memory placement",
    )
    args = parser.parse_args()
    result = audit_compact(args.repo_root) if args.compact else audit(args.repo_root)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
