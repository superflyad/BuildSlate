#!/usr/bin/env python3
"""Exercise the released CAD gate with synthetic STEP geometry and faults."""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

import cadquery as cq
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from buildslate.mechanical_proof import (  # noqa: E402
    ASSEMBLY,
    MANIFEST,
    REQUIRED_ROLES,
    audit,
)


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _fixture(root: Path) -> tuple[Path, dict]:
    directory = root / ASSEMBLY.parent
    parts_dir = directory / "parts"
    parts_dir.mkdir(parents=True)
    parts = []
    bodies = []
    for part_id, role, x in (("board", "main_pcb", 1.0), ("pack", "battery_pack", 5.0)):
        source = parts_dir / f"{part_id}.step"
        drawing = parts_dir / f"{part_id}.pdf"
        shape = cq.Workplane("XY").box(2, 2, 2, centered=False).val()
        cq.exporters.export(shape, str(source))
        drawing.write_bytes(f"synthetic drawing for {part_id}".encode("utf-8"))
        bodies.append(shape.translate(cq.Vector(x, 1, 1)))
        parts.append(
            {
                "id": part_id,
                "roles": [role],
                "manufacturer": "fixture vendor",
                "part_number": f"fixture-{part_id}",
                "revision": "A",
                "source_frame": "fixture box origin",
                "geometry_license": "fixture generated geometry",
                "distribution_scope": "public",
                "step": source.relative_to(root).as_posix(),
                "step_sha256": _hash(source),
                "drawing": drawing.relative_to(root).as_posix(),
                "drawing_sha256": _hash(drawing),
                "dimensions_mm": [2, 2, 2],
                "translation_mm": [x, 1, 1],
                "rotation_deg": [0, 0, 0],
                "radial_uncertainty_mm": 0.1,
            }
        )
    cq.exporters.export(cq.Compound.makeCompound(bodies), str(root / ASSEMBLY))
    manifest = {
        "schema_version": 1,
        "device": "slate-pocket-v1r",
        "units": "mm",
        "assembly_frame": "lower_left_rear_xyz_mm",
        "envelope_mm": [20, 10, 5],
        "minimum_clearance_mm": 0.1,
        "maximum_contact_gap_mm": 0.1,
        "contact_pairs": [],
        "parts": parts,
    }
    (root / MANIFEST).write_text(
        yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8"
    )
    return root / MANIFEST, manifest


def main() -> int:
    with TemporaryDirectory() as temp:
        root = Path(temp)
        if audit(root)["status"] != "missing":
            raise ValueError("Missing release geometry passed")
        manifest_path, manifest = _fixture(root)
        result = audit(
            root,
            required_roles=("main_pcb", "battery_pack"),
            expected_envelope=(20, 10, 5),
        )
        if result["status"] != "pass" or result["part_count"] != 2:
            raise ValueError(f"Valid STEP assembly did not pass: {result['findings']}")
        manifest["envelope_mm"][0] = 21
        manifest_path.write_text(
            yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8"
        )
        try:
            audit(
                root,
                required_roles=("main_pcb", "battery_pack"),
                expected_envelope=(20, 10, 5),
            )
        except ValueError as error:
            if "active v1R profile" not in str(error):
                raise
        else:
            raise ValueError("Unapproved device envelope change passed")
        manifest["envelope_mm"][0] = 20
        manifest["parts"][0]["roles"] = ["enclosure_structure"]
        manifest_path.write_text(
            yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8"
        )
        result = audit(
            root,
            required_roles=("enclosure_structure", "battery_pack"),
            expected_envelope=(20, 10, 5),
        )
        if not any("outer planform" in item for item in result["findings"]):
            raise ValueError("Incomplete enclosure geometry passed")
        manifest["parts"][0]["roles"] = ["main_pcb"]
        try:
            audit(root, expected_envelope=(20, 10, 5))
        except ValueError as error:
            if "too few distinct solids" not in str(error):
                raise
        else:
            raise ValueError("Incomplete mechanical part count passed")
        manifest["parts"][1]["translation_mm"][0] = 3.1
        manifest_path.write_text(
            yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8"
        )
        result = audit(
            root,
            required_roles=("main_pcb", "battery_pack"),
            expected_envelope=(20, 10, 5),
        )
        if not any("tolerance clearance" in item for item in result["findings"]):
            raise ValueError("Tolerance closure was missed")
        manifest["parts"][1]["translation_mm"][0] = 2.5
        manifest_path.write_text(
            yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8"
        )
        result = audit(
            root,
            required_roles=("main_pcb", "battery_pack"),
            expected_envelope=(20, 10, 5),
        )
        if not any("penetration" in item for item in result["findings"]):
            raise ValueError("Exact solid penetration was missed")
        manifest["parts"][1]["step_sha256"] = "0" * 64
        manifest_path.write_text(
            yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8"
        )
        try:
            audit(
                root,
                required_roles=("main_pcb", "battery_pack"),
                expected_envelope=(20, 10, 5),
            )
        except ValueError as error:
            if "hash mismatch" not in str(error):
                raise
        else:
            raise ValueError("Modified supplier STEP passed")
        if len(REQUIRED_ROLES) < 20:
            raise ValueError("Mechanical release role requirement was reduced")
    print("PASS: release STEP identity, assembly placement, clearance, and overlap")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
