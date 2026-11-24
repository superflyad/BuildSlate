"""Keep the public hardware gate current and fail closed on planning inputs."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from buildslate.hardware_readiness import (  # noqa: E402
    REPORT,
    _evidence_result,
    build_report,
)


def main() -> int:
    expected = build_report(ROOT)
    committed = json.loads((ROOT / REPORT).read_text(encoding="utf-8"))
    if committed != expected:
        raise ValueError("Hardware readiness report is stale; regenerate with --write")
    if (
        expected["functional_evt0"] != "blocked"
        and expected["design_release"] == "blocked"
    ):
        raise ValueError("Functional EVT0 cannot precede design release")
    if (
        expected["phone_function"] != "blocked"
        and expected["functional_evt0"] == "blocked"
    ):
        raise ValueError("Phone function cannot precede functional EVT0")
    requirement = {"stage": "design_release"}
    with TemporaryDirectory() as temp:
        root = Path(temp)
        controlled = root / "engineering/hardware/released"
        controlled.mkdir(parents=True)
        artifact = controlled / "reviewed.pdf"
        artifact.write_bytes(b"fixture artifact")
        import hashlib

        record = {
            "path": "engineering/hardware/released/reviewed.pdf",
            "sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(),
            "revision": "A",
            "reviewed_by": "fixture reviewer",
            "disposition": "approved",
        }
        if _evidence_result(root, requirement, record)["status"] != "accepted":
            raise ValueError("Valid controlled fixture was rejected")
        for mutation in (
            {"sha256": "0" * 64},
            {"disposition": "draft"},
            {"path": "engineering/hardware/readiness.yaml"},
            {"path": "engineering/hardware/released/missing.pdf"},
            {"reviewed_by": None},
        ):
            invalid = {**record, **mutation}
            if _evidence_result(root, requirement, invalid)["status"] == "accepted":
                raise ValueError(f"Invalid evidence was accepted: {mutation}")
    print(
        "PASS: hardware readiness report current; "
        f"{len(expected['requirements'])} evidence requirements checked"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
