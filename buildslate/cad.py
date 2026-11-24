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
from .io import load_yaml
from .program import DEFAULT_REPO_ROOT

MANIFEST = Path("engineering/assembly/concept-cad.yaml")
STEP = Path("cad/slate-pocket-v1r/concept-cad/assembly.step")
MODEL = Path("viewer/public/concept.json")
GLTF = Path("viewer/public/concept.gltf")


def build_concept(repo_root: Path) -> dict:
    source = build_assembly(repo_root)
    manifest = load_yaml(repo_root / MANIFEST)
    if manifest.get("schema_version") != 1:
        raise ValueError("unsupported concept CAD schema")
    source_ids = {part["id"] for part in source["parts"]}
    if set(manifest["source_overrides"]) - source_ids:
        raise ValueError("unknown source part in concept override")
    parts = []
    for original in source["parts"]:
        part = {**original, "shape": "box"}
        part.update(manifest["source_overrides"].get(part["id"], {}))
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
        }
        for key in ("radius_mm", "band_mm"):
            if key in spec:
                part[key] = float(spec[key])
        parts.append(part)
    if len({part["id"] for part in parts}) != len(parts):
        raise ValueError("duplicate concept part ID")
    extent = source["extent_mm"]
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


def _shape(cq, part: dict):
    x, y, z, length, width, height = part["box_mm"]
    kind = part["shape"]
    body = cq.Workplane("XY").box(length, width, height, centered=False)
    if kind in {"rounded_box", "speaker"}:
        radius = min(float(part.get("radius_mm", 1.0)), length / 3, width / 3)
        body = body.edges("|Z").fillet(radius)
    elif kind == "camera_module":
        body = cq.Workplane("XY").box(length, width, height * 0.65, centered=False)
        lens = (
            cq.Workplane("XY")
            .center(length / 2, width / 2)
            .circle(min(length, width) * 0.32)
            .extrude(height * 0.35)
            .translate((0, 0, height * 0.65))
        )
        body = body.union(lens)
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
            .box(12, width + 2, 3, centered=False)
            .translate((length / 2 - 6, -1, 2.25))
        )
        body = body.cut(void)
    elif kind != "box":
        raise ValueError(f"unknown CAD shape: {kind}")
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


def generate(repo_root: Path = DEFAULT_REPO_ROOT) -> tuple[int, Path]:
    try:
        import cadquery as cq
    except ImportError as error:
        raise RuntimeError("Install requirements-cad.txt with Python 3.12") from error
    root = repo_root.resolve()
    model = build_concept(root)
    cad = cq.Assembly(name=model["device"])
    solids = []
    for part in model["parts"]:
        solid = _shape(cq, part)
        if len(solid.solids().vals()) != 1:
            raise ValueError(f"concept part is not one solid: {part['id']}")
        cad.add(solid, name=part["id"])
        solids.append((part, solid))
    step_path = root / STEP
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
    if len(cq.importers.importStep(str(step_path)).solids().vals()) != len(solids):
        raise ValueError("STEP solid count drift")
    (root / MODEL).write_text(
        json.dumps(model, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    (root / GLTF).write_text(
        json.dumps(_gltf(solids), separators=(",", ":")) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return len(solids), step_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=DEFAULT_REPO_ROOT)
    args = parser.parse_args()
    count, path = generate(args.repo_root)
    print(f"Exported {count} editable concept solids to {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
