"""Check evidence needed to hand off and validate a physical v1R build.

This is an evidence-control check, not an electrical or safety certification.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from buildslate.battery_fit import audit as audit_battery_fit
from buildslate.build_procedure_proof import (
    ASSEMBLY_RELEASE as ASSEMBLY_PROCEDURE_RELEASE,
)
from buildslate.build_procedure_proof import BENCH_RELEASE as BENCH_SAFETY_RELEASE
from buildslate.build_procedure_proof import audit_assembly, audit_bench
from buildslate.cellular_fit import audit as audit_cellular_fit
from buildslate.cellular_fit import audit_compact as audit_compact_cellular_fit
from buildslate.display_fit import audit as audit_display_fit
from buildslate.erc_proof import audit as audit_erc
from buildslate.evt0 import EVT0CampaignRepository
from buildslate.firmware_proof import RELEASE as FIRMWARE_RELEASE
from buildslate.firmware_proof import audit as audit_firmware
from buildslate.interconnect_proof import RELEASE as INTERCONNECT_RELEASE
from buildslate.interconnect_proof import audit as audit_interconnect
from buildslate.io import load_yaml
from buildslate.mechanical_proof import ASSEMBLY as MECHANICAL_ASSEMBLY
from buildslate.mechanical_proof import MANIFEST as MECHANICAL_MANIFEST
from buildslate.mechanical_proof import REPORT as MECHANICAL_REPORT
from buildslate.mechanical_proof import REQUIRED_ROLES as MECHANICAL_ROLES
from buildslate.memory_package_fit import audit as audit_memory_package_fit
from buildslate.netlist_proof import audit as audit_netlist
from buildslate.part_selection import RELEASE as SELECTED_BOM_RELEASE
from buildslate.part_selection import audit as audit_part_selection
from buildslate.pcb_proof import audit as audit_pcb
from buildslate.phone_proof import audit as audit_phone
from buildslate.platform_fit import audit as audit_platform_fit
from buildslate.platform_reference_proof import RELEASE as PLATFORM_REFERENCE_RELEASE
from buildslate.platform_reference_proof import audit as audit_platform_reference
from buildslate.power_safety_proof import RELEASE as POWER_RELEASE
from buildslate.power_safety_proof import audit as audit_power_safety
from buildslate.rf_proof import RELEASE as RF_RELEASE
from buildslate.rf_proof import audit as audit_rf
from buildslate.storage_fit import audit as audit_storage_fit
from buildslate.thermal_proof import RELEASE as THERMAL_RELEASE
from buildslate.thermal_proof import audit as audit_thermal
from buildslate.usb_fit import audit as audit_usb_fit

MANIFEST = Path("engineering/hardware/readiness.yaml")
STRATEGY = Path("validation/evt0/bom-strategy.yaml")
REPORT = Path("viewer/public/hardware-readiness.json")
EVT0_SPEC = Path("validation/evt0/evt0-spec.yaml")
EVIDENCE_REGISTRY = Path("engineering/evidence/evidence_registry.yaml")
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
PHONE_DESIGN_ROOT = Path("engineering/hardware/released")


def _evidence_result(
    root: Path,
    requirement: dict,
    record: object,
    selection_proof: dict | None = None,
    related_records: dict | None = None,
) -> dict:
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
        allowed = (
            root
            / (
                PHONE_DESIGN_ROOT
                if requirement.get("id") in {"cellular_design", "telephony_software"}
                else ROOTS[stage]
            )
        ).resolve()
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
        if not reasons and requirement.get("id") == "selected_bom":
            if target != (root / SELECTED_BOM_RELEASE).resolve():
                reasons.append("Selected BOM must name the controlled release JSON")
            elif selection_proof is None or selection_proof["status"] != "pass":
                reasons.append("Selected part set or interface proof is incomplete")
            elif (
                selection_proof.get("revision") != record["revision"]
                or selection_proof.get("reviewed_by") != record["reviewed_by"]
            ):
                reasons.append(
                    "Selected BOM review identity or revision differs from evidence record"
                )
            else:
                proof = selection_proof
        if not reasons and requirement.get("id") == "platform_reference":
            if target != (root / PLATFORM_REFERENCE_RELEASE).resolve():
                reasons.append(
                    "Platform reference must name the controlled release JSON"
                )
            else:
                proof = audit_platform_reference(root)
                if proof["status"] != "pass":
                    reasons.extend(proof["errors"])
                elif (
                    proof["revision"] != record["revision"]
                    or proof["reviewed_by"] != record["reviewed_by"]
                ):
                    reasons.append("Platform review identity or revision differs")
                selected = (related_records or {}).get("selected_bom")
                if (
                    not isinstance(selected, dict)
                    or selected.get("disposition") != "approved"
                    or selected.get("sha256") != proof["selected_bom_sha256"]
                    or selection_proof is None
                    or selection_proof.get("status") != "pass"
                    or selection_proof.get("sha256") != proof["selected_bom_sha256"]
                ):
                    reasons.append(
                        "Platform reference is not bound to approved part selection"
                    )
                electrical = (related_records or {}).get("schematic_netlist")
                if (
                    not isinstance(electrical, dict)
                    or electrical.get("disposition") != "approved"
                    or electrical.get("bom_sha256") != proof["electrical_bom_sha256"]
                ):
                    reasons.append(
                        "Platform reference is not bound to approved electrical BOM"
                    )
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
        if not reasons and requirement.get("id") == "erc_report":
            if not target.name.endswith(".erc.json"):
                reasons.append("ERC evidence must be a KiCad JSON report")
            else:
                schematic = target.with_name(
                    target.name.removesuffix(".erc.json") + ".kicad_sch"
                )
                project = schematic.with_suffix(".kicad_pro")
                upstream = (related_records or {}).get("schematic_source")
                if (
                    not isinstance(upstream, dict)
                    or upstream.get("disposition") != "approved"
                    or not isinstance(upstream.get("path"), str)
                    or (root / upstream["path"]).resolve() != schematic
                    or upstream.get("sha256") != record.get("schematic_sha256")
                    or not schematic.is_file()
                    or record.get("schematic_sha256")
                    != hashlib.sha256(schematic.read_bytes()).hexdigest()
                    or not project.is_file()
                    or record.get("project_sha256")
                    != hashlib.sha256(project.read_bytes()).hexdigest()
                ):
                    reasons.append(
                        "ERC is not bound to approved schematic and project bytes"
                    )
                else:
                    proof = audit_erc(schematic, target)
                    if proof["status"] != "pass":
                        reasons.extend(proof["errors"])
        if not reasons and requirement.get("id") == "routed_pcb":
            if target.suffix.lower() != ".kicad_pcb":
                reasons.append("Routed PCB must be an editable KiCad board")
            else:
                schematic = target.with_suffix(".kicad_sch")
                netlist = target.with_suffix(".xml")
                project = target.with_suffix(".kicad_pro")
                related = related_records or {}
                for identifier, path, hash_field in (
                    ("schematic_source", schematic, "schematic_sha256"),
                    ("schematic_netlist", netlist, "netlist_sha256"),
                ):
                    upstream = related.get(identifier)
                    if (
                        not isinstance(upstream, dict)
                        or upstream.get("disposition") != "approved"
                        or not isinstance(upstream.get("path"), str)
                        or (root / upstream["path"]).resolve() != path
                        or not path.is_file()
                        or upstream.get("sha256") != record.get(hash_field)
                        or record.get(hash_field)
                        != hashlib.sha256(path.read_bytes()).hexdigest()
                    ):
                        reasons.append(
                            f"PCB is not bound to approved {identifier} bytes"
                        )
                erc_record = related.get("erc_report")
                if (
                    not project.is_file()
                    or record.get("project_sha256")
                    != hashlib.sha256(project.read_bytes()).hexdigest()
                    or not isinstance(erc_record, dict)
                    or erc_record.get("disposition") != "approved"
                    or erc_record.get("project_sha256") != record.get("project_sha256")
                    or erc_record.get("schematic_sha256")
                    != record.get("schematic_sha256")
                ):
                    reasons.append(
                        "PCB project settings differ from approved ERC settings"
                    )
                if not reasons:
                    proof = audit_pcb(target, schematic, netlist)
                    if proof["status"] != "pass":
                        reasons.extend(proof["errors"])
        if not reasons and requirement.get("id") == "power_safety":
            if target != (root / POWER_RELEASE).resolve():
                reasons.append("Power release must name the controlled power JSON")
            else:
                proof = audit_power_safety(root)
                if proof["status"] != "pass":
                    reasons.extend(proof["errors"])
                elif (
                    proof["revision"] != record["revision"]
                    or proof["reviewed_by"] != record["reviewed_by"]
                ):
                    reasons.append("Power review identity or revision differs")
                related = related_records or {}
                for identifier, digest in (
                    ("selected_bom", proof["selected_bom_sha256"]),
                    ("schematic_netlist", proof["electrical_bom_sha256"]),
                    ("routed_pcb", proof["routed_pcb_sha256"]),
                ):
                    upstream = related.get(identifier)
                    field = (
                        "bom_sha256" if identifier == "schematic_netlist" else "sha256"
                    )
                    if (
                        not isinstance(upstream, dict)
                        or upstream.get("disposition") != "approved"
                        or upstream.get(field) != digest
                    ):
                        reasons.append(
                            f"Power release is not bound to approved {identifier}"
                        )
                if (
                    selection_proof is None
                    or selection_proof.get("status") != "pass"
                    or selection_proof.get("sha256") != proof["selected_bom_sha256"]
                ):
                    reasons.append("Power selected BOM has no passing part proof")
        if not reasons and requirement.get("id") == "thermal_release":
            if target != (root / THERMAL_RELEASE).resolve():
                reasons.append("Thermal release must name the controlled thermal JSON")
            else:
                proof = audit_thermal(root)
                if proof["status"] != "pass":
                    reasons.extend(proof["errors"])
                elif (
                    proof["revision"] != record["revision"]
                    or proof["reviewed_by"] != record["reviewed_by"]
                ):
                    reasons.append("Thermal review identity or revision differs")
                related = related_records or {}
                for identifier, hash_field, proof_field in (
                    ("selected_bom", "sha256", "selected_bom_sha256"),
                    ("routed_pcb", "sha256", "routed_pcb_sha256"),
                    ("mechanical_release", "sha256", "mechanical_assembly_sha256"),
                    (
                        "mechanical_release",
                        "manifest_sha256",
                        "mechanical_manifest_sha256",
                    ),
                    ("power_safety", "sha256", "power_safety_sha256"),
                ):
                    upstream = related.get(identifier)
                    if (
                        not isinstance(upstream, dict)
                        or upstream.get("disposition") != "approved"
                        or upstream.get(hash_field) != proof[proof_field]
                    ):
                        reasons.append(
                            f"Thermal release is not bound to approved {identifier}"
                        )
                if (
                    selection_proof is None
                    or selection_proof.get("status") != "pass"
                    or selection_proof.get("sha256") != proof["selected_bom_sha256"]
                ):
                    reasons.append("Thermal selected BOM has no passing part proof")
        if not reasons and requirement.get("id") == "rf_release":
            if target != (root / RF_RELEASE).resolve():
                reasons.append("RF release must name the controlled RF JSON")
            else:
                proof = audit_rf(root)
                if proof["status"] != "pass":
                    reasons.extend(proof["errors"])
                elif (
                    proof["revision"] != record["revision"]
                    or proof["reviewed_by"] != record["reviewed_by"]
                ):
                    reasons.append("RF review identity or revision differs")
                related = related_records or {}
                for identifier, hash_field, proof_field in (
                    ("selected_bom", "sha256", "selected_bom_sha256"),
                    ("routed_pcb", "sha256", "routed_pcb_sha256"),
                    ("schematic_netlist", "sha256", "netlist_sha256"),
                    ("schematic_netlist", "bom_sha256", "electrical_bom_sha256"),
                    ("mechanical_release", "sha256", "mechanical_assembly_sha256"),
                    (
                        "mechanical_release",
                        "manifest_sha256",
                        "mechanical_manifest_sha256",
                    ),
                    ("firmware_boot", "sha256", "firmware_bundle_sha256"),
                ):
                    upstream = related.get(identifier)
                    if (
                        not isinstance(upstream, dict)
                        or upstream.get("disposition") != "approved"
                        or upstream.get(hash_field) != proof[proof_field]
                    ):
                        reasons.append(
                            f"RF release is not bound to approved {identifier}"
                        )
                if (
                    selection_proof is None
                    or selection_proof.get("status") != "pass"
                    or selection_proof.get("sha256") != proof["selected_bom_sha256"]
                ):
                    reasons.append("RF selected BOM has no passing part proof")
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
        if not reasons and requirement.get("id") == "interconnect":
            if target != (root / INTERCONNECT_RELEASE).resolve():
                reasons.append("Interconnect must name the controlled release JSON")
            else:
                proof = audit_interconnect(root)
                if proof["status"] != "pass":
                    reasons.extend(proof["errors"])
                elif (
                    proof["revision"] != record["revision"]
                    or proof["reviewed_by"] != record["reviewed_by"]
                ):
                    reasons.append("Interconnect review identity or revision differs")
                related = related_records or {}
                for identifier, hash_field, proof_field in (
                    ("selected_bom", "sha256", "selected_bom_sha256"),
                    ("schematic_netlist", "sha256", "netlist_sha256"),
                    ("schematic_netlist", "bom_sha256", "electrical_bom_sha256"),
                    ("routed_pcb", "sha256", "routed_pcb_sha256"),
                    ("mechanical_release", "sha256", "mechanical_assembly_sha256"),
                ):
                    upstream = related.get(identifier)
                    if (
                        not isinstance(upstream, dict)
                        or upstream.get("disposition") != "approved"
                        or upstream.get(hash_field) != proof[proof_field]
                    ):
                        reasons.append(
                            f"Interconnect is not bound to approved {identifier}"
                        )
                if (
                    selection_proof is None
                    or selection_proof.get("status") != "pass"
                    or selection_proof.get("sha256") != proof["selected_bom_sha256"]
                ):
                    reasons.append(
                        "Interconnect selected BOM has no passing part proof"
                    )
        if not reasons and requirement.get("id") == "firmware_boot":
            if target != (root / FIRMWARE_RELEASE).resolve():
                reasons.append("Firmware release must name the controlled bundle JSON")
            else:
                proof = audit_firmware(target)
                if proof["status"] != "pass":
                    reasons.extend(proof["errors"])
                elif (
                    proof["revision"] != record["revision"]
                    or proof["reviewed_by"] != record["reviewed_by"]
                ):
                    reasons.append("Firmware review identity or revision differs")
                related = related_records or {}
                selected = related.get("selected_bom")
                board = related.get("routed_pcb")
                for identifier, upstream, expected_hash in (
                    ("selected_bom", selected, proof["selected_bom_sha256"]),
                    ("routed_pcb", board, proof["routed_pcb_sha256"]),
                ):
                    if (
                        not isinstance(upstream, dict)
                        or upstream.get("disposition") != "approved"
                        or upstream.get("sha256") != expected_hash
                    ):
                        reasons.append(
                            f"Firmware is not bound to approved {identifier}"
                        )
                if (
                    selection_proof is None
                    or selection_proof.get("status") != "pass"
                    or selection_proof.get("sha256") != proof["selected_bom_sha256"]
                ):
                    reasons.append("Firmware selected BOM has no passing part proof")
                if isinstance(board, dict) and proof["board_revision"] != board.get(
                    "revision"
                ):
                    reasons.append("Firmware board revision differs from routed PCB")
        if not reasons and requirement.get("id") in {
            "assembly_release",
            "bench_safety",
        }:
            is_assembly = requirement["id"] == "assembly_release"
            expected = (
                ASSEMBLY_PROCEDURE_RELEASE if is_assembly else BENCH_SAFETY_RELEASE
            )
            if target != (root / expected).resolve():
                reasons.append("Procedure must name its controlled release JSON")
            else:
                proof = audit_assembly(root) if is_assembly else audit_bench(root)
                if proof["status"] != "pass":
                    reasons.extend(proof["errors"])
                elif (
                    proof["revision"] != record["revision"]
                    or proof["reviewed_by"] != record["reviewed_by"]
                ):
                    reasons.append("Procedure review identity or revision differs")
                sources = (
                    ("selected_bom", "selected_bom_sha256"),
                    ("routed_pcb", "routed_pcb_sha256"),
                    ("power_safety", "power_safety_sha256"),
                    ("firmware_boot", "firmware_bundle_sha256"),
                ) + (
                    (
                        ("mechanical_release", "mechanical_assembly_sha256"),
                        ("interconnect", "interconnect_sha256"),
                        ("thermal_release", "thermal_release_sha256"),
                        ("bench_safety", "bench_safety_sha256"),
                    )
                    if is_assembly
                    else ()
                )
                for identifier, field in sources:
                    upstream = (related_records or {}).get(identifier)
                    if (
                        not isinstance(upstream, dict)
                        or upstream.get("disposition") != "approved"
                        or upstream.get("sha256") != proof.get(field)
                    ):
                        reasons.append(
                            f"Procedure is not bound to approved {identifier}"
                        )
                if (
                    selection_proof is None
                    or selection_proof.get("status") != "pass"
                    or selection_proof.get("sha256") != proof.get("selected_bom_sha256")
                ):
                    reasons.append("Procedure selected BOM has no passing part proof")
        if not reasons and requirement.get("id") == "phone_validation":
            if target.suffix.lower() != ".json":
                reasons.append("Phone validation must be a controlled JSON bundle")
            else:
                proof = audit_phone(target, root)
                if proof["status"] != "pass":
                    reasons.extend(proof["errors"])
                related = related_records or {}
                for identifier, field in (
                    ("selected_bom", "selected_bom_sha256"),
                    ("cellular_design", "cellular_design_sha256"),
                    ("telephony_software", "telephony_software_sha256"),
                ):
                    upstream = related.get(identifier)
                    if (
                        not isinstance(upstream, dict)
                        or upstream.get("disposition") != "approved"
                        or upstream.get("sha256") != proof[field]
                    ):
                        reasons.append(
                            f"Phone test bundle is not bound to approved {identifier}"
                        )
    result = {
        "status": "accepted" if not reasons else "rejected",
        "reasons": reasons,
    }
    if proof is not None:
        result["technical_proof"] = proof
    return result


def _evt0_prerequisites(root: Path) -> list[str]:
    """Preserve source authorization, safety, and supplier gates in hardware status."""
    spec = load_yaml(root / EVT0_SPEC)
    registry = load_yaml(root / EVIDENCE_REGISTRY)
    prerequisites = spec["prerequisite_gates"]
    missing = []
    for field, value in prerequisites["authorization"].items():
        if field.endswith("_authorized") and value is not True:
            missing.append(f"authorization.{field}")
    if (
        not isinstance(prerequisites["authorization"].get("authorized_by"), str)
        or not prerequisites["authorization"]["authorized_by"].strip()
    ):
        missing.append("authorization.authorized_by")
    for field, value in prerequisites["safety"].items():
        if value is not True:
            missing.append(f"safety.{field}")
    for group in ("supplier_evidence", "phase2_integration"):
        for package in prerequisites[group]["packages"]:
            if registry["packages"][package]["status"] != "verified":
                missing.append(f"package.{package}")
    return missing


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
    selection = audit_part_selection(root, strategy)
    platform_reference = audit_platform_reference(root)
    platform_fit = audit_platform_fit(root)
    storage_fit = audit_storage_fit(root)
    battery_fit = audit_battery_fit(root)
    usb_fit = audit_usb_fit(root)
    display_fit = audit_display_fit(root)
    memory_package_fit = audit_memory_package_fit(root)
    firmware_bundle = audit_firmware(root / FIRMWARE_RELEASE)
    power_safety = audit_power_safety(root)
    thermal_release = audit_thermal(root)
    rf_release = audit_rf(root)
    interconnect_release = audit_interconnect(root)
    assembly_procedure = audit_assembly(root)
    bench_safety = audit_bench(root)
    selected_roles = []
    for role in manifest["selected_roles"]:
        item = strategy["roles"].get(role)
        if item is None:
            raise ValueError(f"Unknown sourcing role: {role}")
        proof_role = next(entry for entry in selection["roles"] if entry["id"] == role)
        selected_roles.append(
            {
                "id": role,
                "status": item["status"],
                "selected": proof_role["selected"],
                "reasons": proof_role["reasons"],
                "mpn": proof_role.get("mpn"),
            }
        )
    entries = [
        {
            "id": item["id"],
            "stage": item["stage"],
            "title": item["title"],
            **_evidence_result(root, item, records.get(item["id"]), selection, records),
        }
        for item in requirements
    ]
    evt0_spec = load_yaml(root / EVT0_SPEC)
    evidence_registry = load_yaml(root / EVIDENCE_REGISTRY)
    supplier_gaps = [
        package
        for package in evt0_spec["prerequisite_gates"]["supplier_evidence"]["packages"]
        if evidence_registry["packages"][package]["status"] != "verified"
    ]
    design = (
        selection["status"] == "pass"
        and display_fit["status"] == "pass"
        and not supplier_gaps
        and all(item["selected"] for item in selected_roles)
        and all(
            entry["status"] == "accepted"
            for entry in entries
            if entry["stage"] == "design_release"
        )
    )
    campaign_repository = EVT0CampaignRepository(root)
    campaign = campaign_repository.build_campaign_report()
    prerequisite_gaps = _evt0_prerequisites(root)
    evt0 = (
        design
        and all(
            entry["status"] == "accepted"
            for entry in entries
            if entry["stage"] == "functional_evt0"
        )
        and campaign["EVT0_CAMPAIGN_GATE"] == "OBJECTIVE_EVIDENCE_REVIEW_READY"
        and not prerequisite_gaps
    )
    cellular = strategy["roles"]["cellular"]
    cellular_proof = next(
        (entry for entry in selection["roles"] if entry["id"] == "cellular"), None
    )
    cellular_selected = bool(cellular_proof and cellular_proof["selected"])
    phone_test = next(
        (
            entry.get("technical_proof")
            for entry in entries
            if entry["id"] == "phone_validation" and entry["status"] == "accepted"
        ),
        None,
    )
    phone = (
        evt0
        and cellular_selected
        and phone_test is not None
        and phone_test["identity"] == campaign["coherent_evidence_group"]
        and phone_test["cellular_mpn"] == cellular_proof["mpn"]
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
        "evt0_campaign": {
            "gate": campaign["EVT0_CAMPAIGN_GATE"],
            "incoming_inspection_limits": campaign_repository.objective_measurements[
                "B00"
            ]["physical_maximum_columns"],
            "required_tests": campaign["summary"]["required_test_count"],
            "passing_required_tests": campaign["summary"][
                "passing_required_test_count"
            ],
            "missing_tests": campaign["missing_or_nonpassing_required_tests"],
            "coherent_evidence_group": campaign["coherent_evidence_group"],
            "prerequisite_gaps": prerequisite_gaps,
        },
        "phone_function": "evidence_ready_for_review" if phone else "blocked",
        "part_selection": {
            "status": selection["status"],
            "source": selection["source"],
            "errors": selection["errors"],
            "supplier_packages_unverified": supplier_gaps,
        },
        "platform_reference": platform_reference,
        "platform_fit": platform_fit,
        "storage_fit": storage_fit,
        "battery_fit": battery_fit,
        "usb_fit": usb_fit,
        "cellular_reference_fit": audit_cellular_fit(root),
        "cellular_compact_memory_fit": audit_compact_cellular_fit(root),
        "display_fit": display_fit,
        "memory_package_fit": memory_package_fit,
        "firmware_bundle": firmware_bundle,
        "power_safety": power_safety,
        "thermal_release": thermal_release,
        "rf_release": rf_release,
        "interconnect_release": interconnect_release,
        "assembly_procedure": assembly_procedure,
        "bench_safety": bench_safety,
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
        (root / REPORT).write_text(serialized, encoding="utf-8", newline="\n")
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
