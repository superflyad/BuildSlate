#!/usr/bin/env python3
"""Exercise CAD intersection proof against exact, controlled solids."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import cadquery as cq  # noqa: E402

from buildslate.cad_proof import (  # noqa: E402
    measure_intersections,
    measure_nominal_gaps,
    measure_optical_paths,
)


def part(part_id: str, x: float, use: str = "solid") -> dict:
    return {
        "id": part_id,
        "box_mm": [x, 0, 0, 2, 2, 2],
        "active": True,
        "geometry_use": use,
    }


def main() -> int:
    parts = [
        part("a", 0),
        part("b", 1),
        part("touching", 3),
        part("near", 5.25),
        part("reserve", 0.5, "reservation"),
    ]
    shapes = {
        item["id"]: cq.Workplane("XY")
        .box(2, 2, 2, centered=False)
        .translate((item["box_mm"][0], 0, 0))
        .val()
        for item in parts
    }
    results = measure_intersections(parts, shapes)
    by_pair = {(item["first"], item["second"]): item for item in results}
    if (
        by_pair[("a", "b")]["kind"] != "interference"
        or by_pair[("a", "b")]["volume_mm3"] != 4
    ):
        raise ValueError("exact solid overlap was not detected")
    if ("b", "touching") in by_pair:
        raise ValueError("face contact was incorrectly treated as interference")
    if by_pair[("a", "reserve")]["kind"] != "reservation_conflict":
        raise ValueError("reservation overlap was not classified")
    gaps = measure_nominal_gaps(parts, shapes, results)
    by_gap = {(item["first"], item["second"]): item for item in gaps}
    if (
        ("a", "b") in by_gap
        or by_gap[("b", "touching")]["kind"] != "contact"
        or by_gap[("touching", "near")]["distance_mm"] != 0.25
        or any("reserve" in pair for pair in by_gap)
    ):
        raise ValueError("Exact nominal contact and small-gap screen failed")
    optical_parts = [
        {
            "id": "rear_cover",
            "box_mm": [0, 0, 0, 4, 4, 0.5],
            "geometry_use": "solid",
            "aperture_center_mm": [2, 2],
            "aperture_radius_mm": 1.0,
        },
        {
            "id": "rear_camera_placeholder",
            "box_mm": [0.5, 0.5, 1, 3, 3, 1],
            "lens_face": "rear",
            "lens_radius_mm": 1.2,
        },
        {
            "id": "display_stack",
            "box_mm": [0, 0, 3, 4, 4, 0.5],
            "geometry_use": "solid",
            "optical_aperture_center_mm": [2, 2],
            "optical_aperture_radius_mm": 0.6,
        },
        {
            "id": "touch_digitizer_concept",
            "box_mm": [0, 0, 2.75, 4, 4, 0.1],
            "geometry_use": "solid",
            "optical_aperture_center_mm": [2, 2],
            "optical_aperture_radius_mm": 0.6,
        },
        {
            "id": "front_camera_concept",
            "box_mm": [1, 1, 1, 2, 2, 1.5],
            "lens_face": "front",
            "lens_radius_mm": 0.5,
        },
    ]

    def cover(radius: float):
        opening = (
            cq.Workplane("XY")
            .center(2, 2)
            .circle(radius)
            .extrude(1)
            .translate((0, 0, -0.25))
        )
        return cq.Workplane("XY").box(4, 4, 0.5, centered=False).cut(opening).val()

    optical_shapes = {
        "rear_cover": cover(1.0),
        "display_stack": cq.Workplane("XY")
        .box(4, 4, 0.5, centered=False)
        .translate((0, 0, 3))
        .val(),
        "touch_digitizer_concept": cq.Workplane("XY")
        .box(4, 4, 0.1, centered=False)
        .translate((0, 0, 2.75))
        .val(),
    }
    paths = measure_optical_paths(optical_parts, optical_shapes)
    if (
        paths[0]["aperture_radial_margin_mm"] != -0.2
        or paths[0]["status"] != "model_path_conflict"
        or paths[1]["pupil_prism_overlap_percent"] != 100
        or paths[2]["pupil_prism_overlap_percent"] != 100
    ):
        raise ValueError("Narrow rear aperture or opaque front path escaped proof")
    optical_parts[0]["aperture_radius_mm"] = 1.3
    optical_shapes["rear_cover"] = cover(1.3)
    opening = cq.Workplane("XY").center(2, 2).circle(0.6).extrude(4)
    for part_id in ("display_stack", "touch_digitizer_concept"):
        optical_shapes[part_id] = optical_shapes[part_id].cut(opening.val())
    clear_paths = measure_optical_paths(optical_parts, optical_shapes)
    if any(item["status"] != "nominal_prism_clear" for item in clear_paths):
        raise ValueError("Clear camera openings were reported as blocked")
    if [item["aperture_radial_margin_mm"] for item in clear_paths] != [0.1, 0.1, 0.1]:
        raise ValueError("Camera aperture margins do not match concept geometry")
    print("PASS: exact overlap, nominal gap, reservation, and optical-path screens")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
