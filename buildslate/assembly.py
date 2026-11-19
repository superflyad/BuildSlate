"""Generate a traceable provisional assembly and a glTF geometry view."""

from __future__ import annotations

import base64
import json
import struct
from pathlib import Path
from typing import Any

from .io import load_yaml
from .program import DEFAULT_REPO_ROOT

MANIFEST = Path("engineering/assembly/assembly.yaml")
OUTPUT = Path("viewer/public/assembly.json")
GEOMETRY = Path("viewer/public/assembly.gltf")


def _rect_box(rect: dict[str, Any], z: float, height: float) -> list[float]:
    return [
        float(rect["x"]),
        float(rect["y"]),
        float(z),
        float(rect["length"]),
        float(rect["width"]),
        float(height),
    ]


def _part(
    part_id: str,
    label: str,
    group: str,
    box: list[float],
    evidence: str,
    source: str,
    active: bool = True,
    notes: str = "",
) -> dict[str, Any]:
    if (
        len(box) != 6
        or any(value < 0 for value in box[:3])
        or any(value <= 0 for value in box[3:])
    ):
        raise ValueError(f"invalid box for {part_id}: {box}")
    return {
        "id": part_id,
        "label": label,
        "group": group,
        "box_mm": box,
        "evidence_class": evidence,
        "source": source,
        "active": active,
        "notes": notes,
    }


def build_assembly(repo_root: Path = DEFAULT_REPO_ROOT) -> dict[str, Any]:
    root = repo_root.resolve()
    manifest = load_yaml(root / MANIFEST)
    if manifest.get("schema_version") != 1:
        raise ValueError("unsupported assembly schema version")
    sources = {
        key: load_yaml(root / value) for key, value in manifest["sources"].items()
    }
    envelope, pcb = sources["envelope"], sources["pcb"]
    extent = envelope["device"]["external_mm"]
    parts: list[dict[str, Any]] = []
    for part_id, spec in manifest["parts"]["enclosure"].items():
        parts.append(
            _part(
                part_id,
                spec["label"],
                spec["group"],
                [float(v) for v in spec["box_mm"]],
                spec["evidence_class"],
                spec["source"],
            )
        )
    for part_id, spec in manifest["parts"]["mechanical"].items():
        original = envelope["placements"][part_id]
        parts.append(
            _part(
                part_id,
                spec["label"],
                spec["group"],
                _rect_box(
                    original["rectangle_mm"], spec["z_mm"], original["height_mm"]
                ),
                original["evidence_class"],
                f"{manifest['sources']['envelope']}#placements.{part_id}",
                spec.get("active", True),
                original.get("status", ""),
            )
        )
    board = pcb["board"]
    origin = board["origin_in_mechanical_model_mm"]
    pcb_spec = manifest["parts"]["pcb"]
    for part_id, spec in pcb_spec["parts"].items():
        original = pcb["placements"][part_id]
        rect = original["rectangle_mm"]
        translated = {
            "x": origin["x"] + rect["x"],
            "y": origin["y"] + rect["y"],
            "length": rect["length"],
            "width": rect["width"],
        }
        parts.append(
            _part(
                part_id,
                spec["label"],
                spec["group"],
                _rect_box(
                    translated,
                    pcb_spec["z_mm"],
                    spec.get("height_mm", pcb_spec["default_height_mm"]),
                ),
                original["evidence_class"],
                f"{manifest['sources']['pcb']}#placements.{part_id}",
                spec.get("active", True),
                original.get("function", ""),
            )
        )
    ids = [part["id"] for part in parts]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate assembly part ID")
    for part in parts:
        x, y, z, length, width, height = part["box_mm"]
        if (
            x + length > extent["length"] + 1e-6
            or y + width > extent["width"] + 1e-6
            or z + height > extent["thickness"] + 1e-6
        ):
            raise ValueError(f"assembly part outside envelope: {part['id']}")
    representations = manifest["component_representations"]
    library = sources["component_library"]["components"]
    if set(representations) - set(library):
        raise ValueError(
            "assembly representation references unknown library components"
        )
    coverage = []
    for component_id, component in library.items():
        representation = representations.get(
            component_id, {"kind": "unplaced", "part_ids": []}
        )
        if representation["kind"] not in {"box", "aggregate", "deferred", "unplaced"}:
            raise ValueError(f"invalid component representation: {component_id}")
        if set(representation["part_ids"]) - set(ids):
            raise ValueError(
                f"component representation references unknown part: {component_id}"
            )
        coverage.append(
            {
                "id": component_id,
                "function": component["function"],
                "representation": representation["kind"],
                "part_ids": representation["part_ids"],
                "source": f"{manifest['sources']['component_library']}#components.{component_id}",
            }
        )
    keepouts = [
        {
            "id": key,
            "category": value["category"],
            "rectangle_mm": value["rectangle_mm"],
            "evidence_class": value["evidence_class"],
            "source": f"{manifest['sources']['keepouts']}#keepouts.{key}",
        }
        for key, value in sources["keepouts"]["keepouts"].items()
    ]
    dashboard = sources["dashboard"]
    return {
        "schema_version": 1,
        "device": manifest["device"],
        "status": manifest["status"],
        "coordinate_system": manifest["coordinate_system"],
        "extent_mm": extent,
        "parts": parts,
        "keepouts": keepouts,
        "zones": sources["stackups"]["zones"],
        "component_coverage": coverage,
        "program_summary": sources["program"]["summary"],
        "gates": dashboard["gates"],
        "summary": dashboard["summary"],
        "blockers": dashboard["externally_blocked"],
        "sources": manifest["sources"],
        "caveat": "Planning geometry only. Boxes do not represent released CAD, selected parts, validated fit, or measured performance.",
    }


def build_gltf(assembly: dict[str, Any]) -> dict[str, Any]:
    # Unit cube shared by every part. Nodes carry the physical dimensions and stable IDs.
    positions = [
        (-0.5, -0.5, -0.5),
        (0.5, -0.5, -0.5),
        (0.5, 0.5, -0.5),
        (-0.5, 0.5, -0.5),
        (-0.5, -0.5, 0.5),
        (0.5, -0.5, 0.5),
        (0.5, 0.5, 0.5),
        (-0.5, 0.5, 0.5),
    ]
    indices = [
        0,
        2,
        1,
        0,
        3,
        2,
        4,
        5,
        6,
        4,
        6,
        7,
        0,
        1,
        5,
        0,
        5,
        4,
        1,
        2,
        6,
        1,
        6,
        5,
        2,
        3,
        7,
        2,
        7,
        6,
        3,
        0,
        4,
        3,
        4,
        7,
    ]
    binary = b"".join(struct.pack("<3f", *p) for p in positions) + b"".join(
        struct.pack("<H", i) for i in indices
    )
    nodes = []
    for part in assembly["parts"]:
        x, y, z, length, width, height = part["box_mm"]
        nodes.append(
            {
                "name": part["id"],
                "mesh": 0,
                "translation": [x + length / 2, y + width / 2, z + height / 2],
                "scale": [length, width, height],
                "extras": {"part_id": part["id"]},
            }
        )
    return {
        "asset": {"version": "2.0", "generator": "BuildSlate assembly exporter"},
        "scene": 0,
        "scenes": [{"nodes": list(range(len(nodes)))}],
        "nodes": nodes,
        "buffers": [
            {
                "uri": "data:application/octet-stream;base64,"
                + base64.b64encode(binary).decode("ascii"),
                "byteLength": len(binary),
            }
        ],
        "bufferViews": [
            {"buffer": 0, "byteOffset": 0, "byteLength": 96, "target": 34962},
            {"buffer": 0, "byteOffset": 96, "byteLength": 72, "target": 34963},
        ],
        "accessors": [
            {
                "bufferView": 0,
                "componentType": 5126,
                "count": 8,
                "type": "VEC3",
                "min": [-0.5, -0.5, -0.5],
                "max": [0.5, 0.5, 0.5],
            },
            {
                "bufferView": 1,
                "componentType": 5123,
                "count": 36,
                "type": "SCALAR",
                "min": [0],
                "max": [7],
            },
        ],
        "meshes": [
            {
                "primitives": [
                    {"attributes": {"POSITION": 0}, "indices": 1, "material": 0}
                ]
            }
        ],
        "materials": [
            {
                "pbrMetallicRoughness": {
                    "baseColorFactor": [0.7, 0.75, 0.82, 1],
                    "metallicFactor": 0.1,
                    "roughnessFactor": 0.65,
                },
                "doubleSided": True,
            }
        ],
    }


def generate(
    repo_root: Path = DEFAULT_REPO_ROOT, check: bool = False
) -> tuple[Path, Path]:
    root = repo_root.resolve()
    assembly = build_assembly(root)
    output = root / OUTPUT
    geometry = root / GEOMETRY
    contents = [
        (output, json.dumps(assembly, indent=2, ensure_ascii=False) + "\n"),
        (
            geometry,
            json.dumps(build_gltf(assembly), separators=(",", ":"), ensure_ascii=False)
            + "\n",
        ),
    ]
    for path, content in contents:
        if check:
            if not path.exists() or path.read_text(encoding="utf-8") != content:
                raise ValueError(
                    f"generated assembly is stale: {path.relative_to(root)}"
                )
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8", newline="\n")
    return output, geometry


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    output, geometry = generate(check=args.check)
    print(
        f"{'Checked' if args.check else 'Wrote'} {output.relative_to(DEFAULT_REPO_ROOT)} and {geometry.relative_to(DEFAULT_REPO_ROOT)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
