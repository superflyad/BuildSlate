"""Screen a public 5G voice-module outline against the current 128 GB board plan."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from buildslate.io import load_yaml

CANDIDATE = Path("research/evidence/cellular/candidate-comparison.yaml")
MEMORY_CANDIDATES = Path("research/evidence/compute/platform-comparison.yaml")
FLOORPLAN = Path("engineering/pcb/slate-pocket-v1r-floorplan/floorplan.yaml")
MEMORY_STUDY = Path("engineering/pcb/slate-pocket-v1r-floorplan/memory-8x16-study.yaml")
MEMORY_ID = "micron_lpddr5x_16gb_public_part"


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


def audit_data(
    candidate: dict, memory_candidates: dict, floorplan: dict, study: dict
) -> dict:
    """Report whether the module outline fits each side at a nominal 1 mm gap."""
    module = candidate["reference_module"]
    package = [float(value) for value in module["package_mm"]]
    gap = float(candidate["screen"]["assumed_nominal_package_clearance_mm"])
    if min(*package, gap) < 0 or any(value == 0 for value in package):
        raise ValueError("Module dimensions must be positive and clearance nonnegative")
    memory = memory_candidates["memory_supplier_context"][MEMORY_ID]
    memory_length, memory_width = (float(value) for value in memory["package_mm"][:2])
    boundary_data = floorplan["board"]["component_side_boundary_mm"]
    boundary = tuple(float(boundary_data[key]) for key in ("x", "y", "length", "width"))
    memory_obstacles: dict[str, list[tuple]] = {"component": [], "reverse": []}
    errors = []
    if study["metadata"]["reference_part"] != MEMORY_ID:
        errors.append("Memory study does not use the screened public package")
    if floorplan["metadata"]["modeled_memory_tier_gb"] != 128:
        errors.append("Board plan is not the 128 GB study")
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
            ("29x32", tuple(package[:2])),
            ("32x29", tuple(reversed(package[:2]))),
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
    if errors:
        status = "source_conflict"
    else:
        status = "outline_possible_unqualified" if fits else "outline_blocked"
    return {
        "status": status,
        "candidate": module["variant"],
        "candidate_role": "public_reference_not_selected",
        "technology": module["technology"],
        "package_mm": package,
        "board_outline_mm": [
            float(floorplan["board"]["outline_mm"][key])
            for key in ("length", "width", "thickness")
        ],
        "usable_board_boundary_mm": list(boundary),
        "assumed_nominal_package_clearance_mm": gap,
        "sides": sides,
        "voice": module["voice"],
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
            for path in (CANDIDATE, MEMORY_CANDIDATES, FLOORPLAN, MEMORY_STUDY)
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
