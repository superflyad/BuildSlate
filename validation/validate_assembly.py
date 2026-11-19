#!/usr/bin/env python3
"""Check assembly coverage, provenance, and generated geometry."""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from buildslate.assembly import GEOMETRY, OUTPUT, build_assembly, build_gltf, generate  # noqa: E402


def main() -> int:
    assembly = build_assembly(REPO_ROOT)
    parts = assembly["parts"]
    ids = {part["id"] for part in parts}
    assert len(parts) >= 25 and len(ids) == len(parts), "expected stable unique parts"
    assert len(assembly["component_coverage"]) >= 20, "component library coverage is incomplete"
    assert any(item["representation"] == "unplaced" for item in assembly["component_coverage"]), "missing geometry must remain visible"
    assert assembly["summary"]["external_blockers"] > 0, "external evidence boundary was lost"
    for part in parts:
        source = REPO_ROOT / part["source"].split("#", 1)[0]
        assert source.is_file(), f"part source missing: {part['id']}"
        assert part["evidence_class"] != "verified", f"provisional geometry cannot be verified: {part['id']}"
    for item in assembly["component_coverage"]:
        assert set(item["part_ids"]) <= ids, f"coverage refers to unknown part: {item['id']}"
    gltf = build_gltf(assembly)
    assert gltf["asset"]["version"] == "2.0"
    assert len(gltf["nodes"]) == len(parts)
    assert {node["extras"]["part_id"] for node in gltf["nodes"]} == ids
    for node, part in zip(gltf["nodes"], parts):
        assert node["scale"] == part["box_mm"][3:], f"geometry dimension drift: {part['id']}"
    generate(REPO_ROOT, check=True)
    assert json.loads((REPO_ROOT / OUTPUT).read_text(encoding="utf-8")) == assembly
    assert json.loads((REPO_ROOT / GEOMETRY).read_text(encoding="utf-8")) == gltf
    print(f"PASS: {len(parts)} traceable provisional boxes, {len(assembly['component_coverage'])} component roles, current JSON and glTF")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AssertionError, OSError, ValueError, KeyError, TypeError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
