#!/usr/bin/env python3
"""Generate the provisional Slate Pocket v1R CAD envelope and local stackup screen."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
MODEL_ROOT = REPO_ROOT / "cad" / "slate-pocket-v1r" / "envelope-model"
ENVELOPE_PATH = MODEL_ROOT / "envelope.yaml"
KEEPOUT_PATH = MODEL_ROOT / "keepouts.yaml"
STACKUP_PATH = MODEL_ROOT / "zone-stackups.yaml"
REPORT_PATH = REPO_ROOT / "reports" / "slate-pocket-v1r-cad-budget.txt"


@dataclass(frozen=True)
class Rectangle:
    x: float
    y: float
    length: float
    width: float

    @property
    def right(self) -> float:
        return self.x + self.length

    @property
    def top(self) -> float:
        return self.y + self.width

    @property
    def area(self) -> float:
        return self.length * self.width

    def contains(self, other: "Rectangle") -> bool:
        return self.x <= other.x and self.y <= other.y and self.right >= other.right and self.top >= other.top

    def overlaps(self, other: "Rectangle") -> bool:
        return self.x < other.right and self.right > other.x and self.y < other.top and self.top > other.y


def _load(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as input_file:
        data = yaml.safe_load(input_file)
    if not isinstance(data, dict):
        raise ValueError(f"{path.relative_to(REPO_ROOT)} must contain a mapping")
    return data


def _rect(data: dict[str, Any]) -> Rectangle:
    return Rectangle(float(data["x"]), float(data["y"]), float(data["length"]), float(data["width"]))


def _zone_layers(zone_id: str, zones: dict[str, Any]) -> list[dict[str, Any]]:
    zone = zones[zone_id]
    if "inherits" in zone:
        return _zone_layers(zone["inherits"], zones) + list(zone.get("additional_layers", []))
    return list(zone["layers"])


def build_report() -> str:
    envelope = _load(ENVELOPE_PATH)
    keepouts = _load(KEEPOUT_PATH)
    stackups = _load(STACKUP_PATH)

    boundary = _rect(envelope["device"]["internal_boundary_mm"])
    placements = envelope["placements"]
    placement_rects = {item_id: _rect(item["rectangle_mm"]) for item_id, item in placements.items()}
    containment_failures = [item_id for item_id, rect in placement_rects.items() if not boundary.contains(rect)]

    same_layer_overlaps: list[tuple[str, str, str]] = []
    placement_ids = list(placements)
    for index, first_id in enumerate(placement_ids):
        for second_id in placement_ids[index + 1 :]:
            first = placements[first_id]
            second = placements[second_id]
            if first["layer"] == second["layer"] and placement_rects[first_id].overlaps(placement_rects[second_id]):
                same_layer_overlaps.append((first["layer"], first_id, second_id))

    keepout_conflicts: list[tuple[str, str, str]] = []
    for keepout_id, keepout in keepouts["keepouts"].items():
        allowed = set(keepout.get("allowed_placements", []))
        keepout_rect = _rect(keepout["rectangle_mm"])
        for placement_id, placement in placements.items():
            if placement_id in allowed or placement["layer"] not in keepout["applies_to_layers"]:
                continue
            if placement_rects[placement_id].overlaps(keepout_rect):
                keepout_conflicts.append((keepout_id, keepout["category"], placement_id))

    component_layer_area = sum(
        placement_rects[item_id].area
        for item_id, placement in placements.items()
        if placement["layer"] == "component_planform"
    )
    component_area_percent = component_layer_area / boundary.area * 100.0

    budget = float(stackups["metadata"]["device_thickness_mm"])
    pass_margin = float(stackups["decision_rules"]["pass_margin_mm"])
    warning_margin = float(stackups["decision_rules"]["warning_margin_mm"])
    zone_results: list[tuple[str, float, float, str, list[str]]] = []
    for zone_id in stackups["zones"]:
        layers = _zone_layers(zone_id, stackups["zones"])
        total = sum(float(layer["thickness_mm"]) for layer in layers)
        margin = budget - total
        if margin >= pass_margin:
            status = "PASS"
        elif margin >= warning_margin:
            status = "WARNING"
        else:
            status = "FAIL"
        weak_layers = [layer["id"] for layer in layers if layer["evidence_class"] not in {"public_supplier", "measured", "validated"}]
        zone_results.append((zone_id, total, margin, status, weak_layers))

    lines = [
        "Slate Pocket v1R Provisional CAD Budget",
        "========================================",
        "",
        "Scope:",
        "  purpose: prepare a supplier-replaceable blocking model and expose local conflicts",
        f"  device envelope: {envelope['device']['external_mm']['length']:.1f} x {envelope['device']['external_mm']['width']:.1f} x {envelope['device']['external_mm']['thickness']:.1f} mm",
        f"  internal planform boundary: {boundary.length:.1f} x {boundary.width:.1f} mm",
        "  model status: provisional_pre_supplier_cad",
        "",
        "Planform screen:",
        f"  reference placements: {len(placements)}",
        f"  component-layer area consumption: {component_area_percent:.1f}%",
        f"  containment failures: {len(containment_failures)}",
        f"  same-layer overlaps: {len(same_layer_overlaps)}",
        f"  keepout conflicts: {len(keepout_conflicts)}",
    ]
    for item_id in containment_failures:
        lines.append(f"  - containment failure: {item_id}")
    for layer, first_id, second_id in same_layer_overlaps:
        lines.append(f"  - overlap on {layer}: {first_id} with {second_id}")
    for keepout_id, category, placement_id in keepout_conflicts:
        lines.append(f"  - {category} keepout conflict: {placement_id} intersects {keepout_id}")

    lines.extend(["", "Local z-height screen:"])
    for zone_id, total, margin, status, weak_layers in zone_results:
        lines.extend(
            [
                f"  - {zone_id}: {status}",
                f"    total: {total:.2f} mm",
                f"    margin: {margin:.2f} mm",
                f"    non-verified layers: {', '.join(weak_layers)}",
            ]
        )

    lines.extend(
        [
            "",
            "Interpretation:",
            "  - Local-zone sums replace the prior global additive assumption, but most dimensions remain estimates or placeholders.",
            "  - The public battery cell is a geometry reference, not a complete pack or selected component.",
            "  - Wireless charging is screened as a separate overlay because it competes directly with battery-zone z-height.",
            "  - Keepout conflicts are design work, not validation failures; they must be resolved with RF, acoustic, connector, and supplier inputs.",
            "",
            "Required replacements before evidence-backed CAD:",
            "  - Supplier battery cell and complete-pack drawing with swelling and tolerances.",
            "  - SoC, memory, storage, PMIC, display, camera, charging, and thermal module drawings.",
            "  - ECAD placement, connector/flex routing, shields, test points, fasteners, seals, and service access.",
            "  - Approved RF, acoustic, camera, and industrial-design keepouts.",
            "  - Zone section drawings, tolerance analysis, interference review, and mass rollup.",
            "",
            "PROVISIONAL_CAD_DECISION: BLOCKED_ON_SUPPLIER_GEOMETRY_AND_KEEP_OUT_RESOLUTION",
            "",
            "Caveat:",
            "  This report prepares integration work; it does not prove fit, tolerance margin, structural performance, manufacturability, RF performance, thermal performance, or component availability.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    try:
        report = build_report()
    except (KeyError, TypeError, ValueError) as exc:
        print(f"FAIL: {exc}")
        return 1
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(report, encoding="utf-8")
    print(f"Wrote {REPORT_PATH.relative_to(REPO_ROOT)}")
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
