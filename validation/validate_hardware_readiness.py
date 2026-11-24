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
    _evt0_prerequisites,
    build_report,
)
from buildslate.io import dump_yaml  # noqa: E402


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
    campaign = expected["evt0_campaign"]
    if campaign["gate"] == "EMPTY_CAMPAIGN" and (
        campaign["passing_required_tests"] != 0
        or len(campaign["missing_tests"]) != campaign["required_tests"]
    ):
        raise ValueError("Empty campaign must credit no physical test")
    if campaign["gate"] == "OBJECTIVE_EVIDENCE_REVIEW_READY" and (
        campaign["missing_tests"]
        or campaign["passing_required_tests"] != campaign["required_tests"]
        or campaign["coherent_evidence_group"] is None
    ):
        raise ValueError("Review-ready campaign must cover all tests on one unit")
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
    with TemporaryDirectory() as temp:
        root = Path(temp)
        spec_path = root / "validation/evt0/evt0-spec.yaml"
        registry_path = root / "engineering/evidence/evidence_registry.yaml"
        spec_path.parent.mkdir(parents=True)
        registry_path.parent.mkdir(parents=True)
        prerequisites = {
            "authorization": {"build_authorized": False, "authorized_by": None},
            "safety": {"approved_lab_procedure": False},
            "supplier_evidence": {"packages": ["battery"]},
            "phase2_integration": {"packages": ["board"]},
        }
        registry = {
            "packages": {
                "battery": {"status": "verified"},
                "board": {"status": "missing"},
            }
        }
        spec_path.write_text(
            dump_yaml({"prerequisite_gates": prerequisites}), encoding="utf-8"
        )
        registry_path.write_text(dump_yaml(registry), encoding="utf-8")
        if set(_evt0_prerequisites(root)) != {
            "authorization.build_authorized",
            "authorization.authorized_by",
            "safety.approved_lab_procedure",
            "package.board",
        }:
            raise ValueError("EVT0 prerequisite gaps were not preserved")
        prerequisites["authorization"]["build_authorized"] = True
        prerequisites["authorization"]["authorized_by"] = "fixture reviewer"
        prerequisites["safety"]["approved_lab_procedure"] = True
        registry["packages"]["board"]["status"] = "verified"
        spec_path.write_text(
            dump_yaml({"prerequisite_gates": prerequisites}), encoding="utf-8"
        )
        registry_path.write_text(dump_yaml(registry), encoding="utf-8")
        if _evt0_prerequisites(root):
            raise ValueError("Satisfied EVT0 prerequisites were not recognized")
    print(
        "PASS: hardware readiness report current; "
        f"{len(expected['requirements'])} evidence requirements checked"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
