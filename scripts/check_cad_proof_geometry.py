#!/usr/bin/env python3
"""Exercise CAD intersection proof against exact, controlled solids."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import cadquery as cq  # noqa: E402

from buildslate.cad_proof import measure_intersections  # noqa: E402


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
    print("PASS: exact overlap, face contact, and reservation classification")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
