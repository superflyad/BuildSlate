"""Check the committed concept contract against its engineering inputs."""

from __future__ import annotations

import json
import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from buildslate.cad import GLTF, MODEL, STEP, build_concept  # noqa: E402
from buildslate.cad_proof import PROOF  # noqa: E402
from buildslate.io import load_yaml  # noqa: E402


def main() -> int:
    expected = build_concept(ROOT)
    committed = json.loads((ROOT / MODEL).read_text(encoding="utf-8"))
    if committed != expected:
        raise ValueError(
            "concept JSON is stale; regenerate with Python 3.12 CAD environment"
        )
    geometry = json.loads((ROOT / GLTF).read_text(encoding="utf-8"))
    ids = {part["id"] for part in expected["parts"]}
    node_ids = {node["extras"]["part_id"] for node in geometry["nodes"]}
    if node_ids != ids or len(geometry["meshes"]) != len(ids):
        raise ValueError("concept glTF part identities drifted")
    step = (ROOT / STEP).read_text(encoding="utf-8")
    if step.count("MANIFOLD_SOLID_BREP") != len(ids):
        raise ValueError("concept STEP solid count drifted")
    proof = json.loads((ROOT / PROOF).read_text(encoding="utf-8"))
    expected_hash = hashlib.sha256(
        (json.dumps(expected, indent=2) + "\n").encode("utf-8")
    ).hexdigest()
    if proof["model_sha256"] != expected_hash:
        raise ValueError("CAD proof does not match the current concept model")
    part_reports = proof["parts"]
    if {item["id"] for item in part_reports} != ids:
        raise ValueError("CAD proof omits a concept part")
    roles = proof["roles"]
    if {role["id"] for role in roles} != {
        item["id"] for item in expected["component_coverage"]
    } or any(not role["part_ids"] or set(role["part_ids"]) - ids for role in roles):
        raise ValueError("CAD proof omits a component role or links an unknown part")
    role_by_id = {role["id"]: role for role in roles}
    library = load_yaml(ROOT / expected["sources"]["component_library"])["components"]
    for coverage in expected["component_coverage"]:
        role = role_by_id[coverage["id"]]
        if (
            role["part_ids"] != coverage["concept_part_ids"]
            or role["missing_evidence"] != library[coverage["id"]]["unknowns"]
        ):
            raise ValueError(f"CAD role proof is stale: {coverage['id']}")
    if not all(all(item["checks"].values()) for item in part_reports):
        raise ValueError("CAD proof contains a failed integrity check")
    summary = proof["summary"]
    if (
        summary["parts_checked"] != len(ids)
        or summary["roles_covered"] != len(expected["component_coverage"])
        or summary["roles_checked"] != len(roles)
        or not summary["step_roundtrip_passed"]
        or summary["interferences"]
        != sum(item["kind"] == "interference" for item in proof["intersections"])
        or summary["reservation_conflicts"]
        != sum(
            item["kind"] == "reservation_conflict" for item in proof["intersections"]
        )
        or summary["keepout_conflicts"] != len(proof["keepout_conflicts"])
        or summary["stack_failures"]
        != sum(item["status"] == "fail" for item in proof["zones"])
    ):
        raise ValueError("CAD proof summary does not match its findings")
    unverified = sum(part["evidence_class"] != "verified" for part in expected["parts"])
    if (
        proof["status"] != "review_required"
        or summary["unverified_parts"] != unverified
    ):
        raise ValueError("concept proof must preserve the evidence boundary")
    print(f"PASS: {len(ids)} concept solids and {len(part_reports)} part proof records")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
