"""Check evidence needed to hand off and validate a physical v1R build.

This is an evidence-control check, not an electrical or safety certification.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from buildslate.io import load_yaml
from buildslate.mechanical_proof import ASSEMBLY as MECHANICAL_ASSEMBLY
from buildslate.mechanical_proof import MANIFEST as MECHANICAL_MANIFEST
from buildslate.mechanical_proof import REPORT as MECHANICAL_REPORT
from buildslate.mechanical_proof import REQUIRED_ROLES as MECHANICAL_ROLES
from buildslate.netlist_proof import audit as audit_netlist

MANIFEST = Path("engineering/hardware/readiness.yaml")
STRATEGY = Path("validation/evt0/bom-strategy.yaml")
REPORT = Path("viewer/public/hardware-readiness.json")
STAGES = ("design_release", "functional_evt0", "phone_function")
REQUIRED = {
    "design_release": (
        "selected_bom",
        "platform_reference",
        "power_safety",
        "schematic_source",
        "schematic_netlist",
        "erc_report",
        "routed_pcb",
        "interconnect",
        "mechanical_release",
        "thermal_release",
        "rf_release",
        "firmware_boot",
        "assembly_release",
        "bench_safety",
    ),
    "functional_evt0": (
        "power_on",
        "charge_discharge",
        "interfaces",
        "thermal_measurements",
        "rf_measurements",
        "mechanical_measurements",
        "evt0_review",
    ),
    "phone_function": ("cellular_design", "telephony_software", "phone_validation"),
}
SELECTED_ROLES = (
    "compute_platform",
    "memory",
    "storage",
    "battery_pack",
    "display_module",
)
ROOTS = {
    "design_release": Path("engineering/hardware/released"),
    "functional_evt0": Path("validation/evt0/test-results"),
    "phone_function": Path("validation/phone/test-results"),
}


def _evidence_result(root: Path, requirement: dict, record: object) -> dict:
    """Require a reviewed, revisioned artifact under the stage's controlled root."""
    reasons: list[str] = []
    if not isinstance(record, dict):
        return {"status": "missing", "reasons": ["No evidence record"]}
    stage = requirement["stage"]
    if record.get("disposition") != "approved":
        reasons.append("Engineering review has not approved this revision")
    for field in ("path", "sha256", "revision", "reviewed_by"):
        if not isinstance(record.get(field), str) or not record[field].strip():
            reasons.append(f"Missing {field}")
    proof: dict | None = None
    if "Missing path" not in reasons:
        relative = Path(record["path"])
        allowed = (root / ROOTS[stage]).resolve()
        target = (root / relative).resolve()
        if not target.is_relative_to(allowed) or target == allowed:
            reasons.append("Artifact is outside the controlled evidence directory")
        elif not target.is_file():
            reasons.append("Artifact file does not exist")
        elif target.suffix.lower() in {".md", ".yaml", ".yml"}:
            reasons.append("Plans and status files are not release evidence")
        elif (
            requirement.get("id") == "schematic_source"
            and target.suffix.lower() != ".kicad_sch"
        ):
            reasons.append("Schematic source must be an editable KiCad schematic")
        elif "Missing sha256" not in reasons:
            digest = hashlib.sha256(target.read_bytes()).hexdigest()
            if digest != record["sha256"]:
                reasons.append("Artifact hash does not match")
        if not reasons and requirement.get("id") == "schematic_netlist":
            if target.suffix.lower() != ".xml":
                reasons.append("Schematic netlist must be a KiCad XML export")
            else:
                contract = target.with_suffix(".contract.yaml")
                bom = target.with_suffix(".bom.csv")
                for key, path in (("contract_sha256", contract), ("bom_sha256", bom)):
                    if not path.is_file():
                        reasons.append(f"Missing electrical bundle file: {path.name}")
                    elif hashlib.sha256(path.read_bytes()).hexdigest() != record.get(
                        key
                    ):
                        reasons.append(f"Missing or mismatched {key}")
                if not reasons:
                    try:
                        proof = audit_netlist(target, contract, bom)
                    except (ValueError, OSError) as error:
                        reasons.append(f"Electrical proof could not run: {error}")
                    else:
                        if proof["status"] != "pass":
                            reasons.extend(proof["errors"])
        if not reasons and requirement.get("id") == "mechanical_release":
            if target != (root / MECHANICAL_ASSEMBLY).resolve():
                reasons.append(
                    "Mechanical release must name the controlled assembly STEP"
                )
            else:
                manifest_path = root / MECHANICAL_MANIFEST
                proof_path = root / MECHANICAL_REPORT
                if not manifest_path.is_file() or not proof_path.is_file():
                    reasons.append("Mechanical manifest or CAD proof is missing")
                else:
                    proof = json.loads(proof_path.read_text(encoding="utf-8"))
                    if (
                        proof.get("status") != "pass"
                        or proof.get("assembly_sha256") != record["sha256"]
                        or proof.get("manifest_sha256") != record.get("manifest_sha256")
                        or proof.get("manifest_sha256")
                        != hashlib.sha256(manifest_path.read_bytes()).hexdigest()
                        or not set(MECHANICAL_ROLES).issubset(
                            proof.get("roles_covered", [])
                        )
                    ):
                        reasons.append("Released mechanical proof is missing or stale")
    result = {
        "status": "accepted" if not reasons else "rejected",
        "reasons": reasons,
    }
    if proof is not None:
        result["technical_proof"] = proof
    return result


def build_report(root: Path) -> dict:
    """Return a deterministic, fail-closed readiness report."""
    manifest = load_yaml(root / MANIFEST)
    strategy = load_yaml(root / STRATEGY)
    if manifest["schema_version"] != 1 or manifest["device"] != "slate-pocket-v1r":
        raise ValueError("Unknown hardware readiness manifest")
    requirements = manifest["requirements"]
    ids = [item["id"] for item in requirements]
    if len(ids) != len(set(ids)) or any(
        item["stage"] not in STAGES for item in requirements
    ):
        raise ValueError("Duplicate requirement or unknown readiness stage")
    for stage, required in REQUIRED.items():
        actual = {item["id"] for item in requirements if item["stage"] == stage}
        if actual != set(required):
            raise ValueError(f"Readiness requirements are incomplete: {stage}")
    if tuple(manifest["selected_roles"]) != SELECTED_ROLES:
        raise ValueError("Critical part selection roles are incomplete")
    records = manifest["evidence"]
    if set(records) - set(ids):
        raise ValueError("Evidence record does not match a requirement")
    selected_roles = []
    for role in manifest["selected_roles"]:
        item = strategy["roles"].get(role)
        if item is None:
            raise ValueError(f"Unknown sourcing role: {role}")
        candidate = item.get("selected_candidate")
        selected_roles.append(
            {
                "id": role,
                "status": item["status"],
                "selected": item["status"] == "selected"
                and isinstance(candidate, str)
                and bool(candidate.strip()),
            }
        )
    entries = [
        {
            "id": item["id"],
            "stage": item["stage"],
            "title": item["title"],
            **_evidence_result(root, item, records.get(item["id"])),
        }
        for item in requirements
    ]
    design = (
        all(item["selected"] for item in selected_roles)
        and strategy["metadata"]["selected_parts"] >= len(SELECTED_ROLES)
        and all(
            entry["status"] == "accepted"
            for entry in entries
            if entry["stage"] == "design_release"
        )
    )
    evt0 = design and all(
        entry["status"] == "accepted"
        for entry in entries
        if entry["stage"] == "functional_evt0"
    )
    cellular = strategy["roles"]["cellular"]
    cellular_selected = (
        cellular["status"] == "selected"
        and isinstance(cellular.get("selected_candidate"), str)
        and bool(cellular["selected_candidate"].strip())
    )
    phone = (
        evt0
        and cellular_selected
        and all(
            entry["status"] == "accepted"
            for entry in entries
            if entry["stage"] == "phone_function"
        )
    )
    return {
        "schema_version": 1,
        "device": manifest["device"],
        "design_release": "ready_for_review" if design else "blocked",
        "functional_evt0": "evidence_ready_for_review" if evt0 else "blocked",
        "phone_function": "evidence_ready_for_review" if phone else "blocked",
        "selected_roles": selected_roles,
        "cellular": {"status": cellular["status"], "selected": cellular_selected},
        "requirements": entries,
        "caveat": (
            "Accepted files and recorded review are necessary evidence, not proof "
            "of correctness. A functional device requires an actual built unit and "
            "measured results; no concept model can establish that outcome."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="Update viewer report")
    parser.add_argument(
        "--require-design-release", action="store_true", help="Fail if blocked"
    )
    parser.add_argument(
        "--require-functional-evt0", action="store_true", help="Fail if blocked"
    )
    parser.add_argument(
        "--require-phone-function", action="store_true", help="Fail if blocked"
    )
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    report = build_report(root)
    serialized = json.dumps(report, indent=2) + "\n"
    if args.write:
        (root / REPORT).write_text(serialized, encoding="utf-8")
    else:
        print(serialized, end="")
    if args.require_design_release and report["design_release"] == "blocked":
        return 1
    if args.require_functional_evt0 and report["functional_evt0"] == "blocked":
        return 1
    if args.require_phone_function and report["phone_function"] == "blocked":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
