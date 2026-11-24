"""Check the committed concept contract against its engineering inputs."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from buildslate.cad import GLTF, MODEL, STEP, build_concept  # noqa: E402


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
    print(f"PASS: {len(ids)} concept solids represent all component roles")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
