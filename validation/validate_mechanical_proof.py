"""Check the committed released-CAD proof identity without requiring CadQuery."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from buildslate.mechanical_proof import (  # noqa: E402
    ASSEMBLY,
    MANIFEST,
    REPORT,
    REQUIRED_ROLES,
)


def main() -> int:
    report = json.loads((ROOT / REPORT).read_text(encoding="utf-8"))
    if report.get("schema_version") != 1 or report.get("device") != "slate-pocket-v1r":
        raise ValueError("Unknown released mechanical proof report")
    assembly, manifest = ROOT / ASSEMBLY, ROOT / MANIFEST
    if not assembly.is_file() or not manifest.is_file():
        if report["status"] != "missing" or report["part_count"] != 0:
            raise ValueError("Mechanical proof claims release without source geometry")
        print("PASS: released mechanical CAD absent and status blocked")
        return 0
    if (
        report["assembly_sha256"] != hashlib.sha256(assembly.read_bytes()).hexdigest()
        or report["manifest_sha256"]
        != hashlib.sha256(manifest.read_bytes()).hexdigest()
        or report["status"] not in {"pass", "fail"}
        or not set(REQUIRED_ROLES).issubset(report["roles_covered"])
    ):
        raise ValueError("Mechanical CAD proof is stale or incomplete")
    print(f"PASS: mechanical CAD proof current; status={report['status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
