#!/usr/bin/env python3
"""Validate configuration authority and dependency-aware regeneration."""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from buildslate.configuration import ConfigurationChangeController, ConfigurationResolver
from buildslate.io import dump_yaml, load_yaml
from buildslate.regeneration import RegenerationEngine, deterministic_file_digest
from buildslate.suppliers import SupplierResponseRepository


def passed(message: str) -> None:
    print(f"PASS: {message}")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)
    passed(message)


def require_raises(action, expected: str, message: str) -> None:
    try:
        action()
    except ValueError as exc:
        require(expected in str(exc), message)
    else:
        raise AssertionError(message)


def main() -> int:
    artifacts = (
        "engineering/program/configuration_registry.yaml",
        "engineering/program/regeneration.yaml",
        "engineering/program/configuration-change.schema.yaml",
        "reports/program/configuration-resolution.yaml",
        "reports/program/regeneration-state.yaml",
    )
    for artifact in artifacts:
        require((REPO_ROOT / artifact).is_file(), f"configuration automation artifact exists: {artifact}")

    with tempfile.TemporaryDirectory() as temp_directory:
        line_endings = Path(temp_directory) / "line-endings.yaml"
        line_endings.write_bytes(b"alpha: 1\nbeta: 2\n")
        lf_digest = deterministic_file_digest(line_endings)
        line_endings.write_bytes(b"alpha: 1\r\nbeta: 2\r\n")
        crlf_digest = deterministic_file_digest(line_endings)
        line_endings.write_bytes(b"alpha: 1\r\nbeta: 2\nbeta2: 3\r")
        mixed_digest = deterministic_file_digest(line_endings)
        canonical_mixed = Path(temp_directory) / "canonical-mixed.yaml"
        canonical_mixed.write_bytes(b"alpha: 1\nbeta: 2\nbeta2: 3\n")
        require(lf_digest == crlf_digest, "regeneration text hashes are stable across LF and CRLF checkouts")
        require(mixed_digest == deterministic_file_digest(canonical_mixed), "regeneration text hashes canonicalize mixed line endings")
        binary = Path(temp_directory) / "evidence.bin"
        binary.write_bytes(b"raw\r\nbytes")
        binary_digest = deterministic_file_digest(binary)
        binary.write_bytes(b"raw\nbytes")
        require(binary_digest != deterministic_file_digest(binary), "regeneration binary hashes preserve exact evidence bytes")

    resolver = ConfigurationResolver(REPO_ROOT)
    resolution = resolver.resolve()
    require(resolution["violations"] == [], "protected v1R profile has no configuration authority violations")
    require(resolution["CONFIGURATION_GATE"] == "CONTROLLED_WITH_UNRESOLVED_EXTERNAL_DECISIONS", "configuration gate preserves unresolved external decisions")
    require(resolution["classification_counts"]["operational_fallback"] == 4, "operational fallbacks are classified separately")
    require(resolution["classification_counts"]["rejected_option"] == 3, "rejected options remain traceable")
    require(resolution["classification_counts"].get("selected_component", 0) == 0, "no component selection is invented")
    require(load_yaml(REPO_ROOT / "reports/program/configuration-resolution.yaml") == resolution, "configuration resolution report is deterministic and current")
    require(len(resolution["resolved_propagations"]) == 4, "cross-domain configuration propagation targets are authoritative")

    with tempfile.TemporaryDirectory() as temp_directory:
        temporary_root = Path(temp_directory)
        for source in (
            "engineering/program/configuration_registry.yaml",
            "configs/devices/slate-pocket-v1r.yaml",
            "engineering/assumptions/assumption_registry.yaml",
            "engineering/pcb/slate-pocket-v1r-floorplan/floorplan.yaml",
            "engineering/pcb/power-tree.yaml",
            "validation/evt0/evt0-spec.yaml",
        ):
            destination = temporary_root / source
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(REPO_ROOT / source, destination)
        profile_path = temporary_root / "configs/devices/slate-pocket-v1r.yaml"
        profile = load_yaml(profile_path)
        profile["memory"]["capacity_gb"] = 256
        profile_path.write_text(yaml.safe_dump(profile, sort_keys=False), encoding="utf-8")
        mutated = ConfigurationResolver(temporary_root).resolve()
        require(mutated["CONFIGURATION_GATE"] == "BLOCKED_UNSUPPORTED_CONFIGURATION", "authority mismatch blocks configuration")
        require(any(item["profile_path"] == "memory.capacity_gb" for item in mutated["violations"]), "unsupported downstream memory value is identified exactly")

    with tempfile.TemporaryDirectory() as temp_directory:
        temporary_root = Path(temp_directory) / "synthetic-repository"
        shutil.copytree(
            REPO_ROOT,
            temporary_root,
            ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"),
        )
        response_path = Path(temp_directory) / "synthetic-battery-response.yaml"
        response = {
            "request": {"packet": "slate-pocket-v1r-battery"},
            "supplier": {
                "legal_name": "SYNTHETIC TEST SUPPLIER - NOT REAL",
                "response_date": "2026-01-01",
                "confidentiality": "synthetic_test_only",
            },
            "proposal": {"option_id": "SYNTHETIC-OPTION", "source_documents": ["synthetic-test-datasheet"]},
            "electrical": {"energy_wh_min": 23.1},
            "mechanical": {
                "complete_pack_mm": {"length": 1, "width": 1, "thickness": 1},
                "complete_pack_volume_mm3": 28824,
                "mass_g": 1,
            },
            "charge_discharge": {"maximum_validated_charge_w": 20},
            "thermal_safety": {"protection_requirements": ["synthetic"]},
            "reliability_supply": {"sample_availability": "synthetic"},
            "supplier_attestation": {
                "values_are_supplier_provided": True,
                "authorized_for_public_disclosure": True,
            },
        }
        response_path.write_text(dump_yaml(response), encoding="utf-8")
        supplier_repository = SupplierResponseRepository(temporary_root)
        receipt_path, review = supplier_repository.ingest(
            response_path,
            "battery",
            "2026-01-01T00:00:00Z",
            "SYNTHETIC TEST OPERATOR",
        )
        require(review.disposition == "CONTRADICTION_REVIEW_REQUIRED", "synthetic supplier limit enters contradiction review")
        receipt_relative = f"research/supplier-responses/receipts/{receipt_path.name}"
        decision_path = Path(temp_directory) / "synthetic-fallback-decision.yaml"
        decision = {
            "schema_version": 1,
            "decision_id": "synthetic_charge_cap_20w",
            "authority": "evt0_wired_charge_cap",
            "expected_current_value": 30,
            "new_value": 20,
            "evidence": {
                "supplier_receipt": receipt_relative,
                "contradiction_rule_id": "battery_evt0_charge_cap",
            },
            "approval": {
                "disposition": "approved",
                "approved_by": "SYNTHETIC TEST APPROVER",
                "approved_at": "2026-01-01T01:00:00Z",
                "rationale": "Synthetic fixture exercises controlled fallback propagation only.",
            },
        }
        decision_path.write_text(dump_yaml(decision), encoding="utf-8")
        controller = ConfigurationChangeController(temporary_root)

        bad_decision = {**decision, "new_value": 19, "decision_id": "synthetic_bad_value"}
        bad_path = Path(temp_directory) / "synthetic-bad-decision.yaml"
        bad_path.write_text(dump_yaml(bad_decision), encoding="utf-8")
        require_raises(
            lambda: controller.validate_decision(bad_path),
            "must equal the executable fallback value",
            "fallback value cannot diverge from supplier evidence",
        )
        unapproved = {**decision, "decision_id": "synthetic_unapproved", "approval": {**decision["approval"], "disposition": "pending"}}
        unapproved_path = Path(temp_directory) / "synthetic-unapproved-decision.yaml"
        unapproved_path.write_text(dump_yaml(unapproved), encoding="utf-8")
        require_raises(
            lambda: controller.validate_decision(unapproved_path),
            "requires approval.disposition=approved",
            "unapproved fallback cannot change authority",
        )

        raw_path = temporary_root / load_yaml(receipt_path)["raw_path"]
        original_raw = raw_path.read_bytes()
        raw_path.write_bytes(original_raw + b"\n# tampered")
        require_raises(
            lambda: controller.validate_decision(decision_path),
            "integrity failed",
            "tampered supplier evidence blocks fallback application",
        )
        raw_path.write_bytes(original_raw)

        plan = controller.validate_decision(decision_path)
        require(plan["status"] == "VALIDATED_NOT_APPLIED" and len(plan["targets"]) == 3, "approved fallback plan identifies every writable target")
        result = controller.apply(decision_path, regenerate=False)
        require(result["status"] == "APPLIED", "approved synthetic fallback applies transactionally")
        updated_profile = load_yaml(temporary_root / "configs/devices/slate-pocket-v1r.yaml")
        updated_power = load_yaml(temporary_root / "engineering/pcb/power-tree.yaml")
        require(updated_profile["battery"]["charging_wired_w"] == 20, "fallback updates the subsystem model input")
        require(updated_profile["integration_configuration"]["wired_charge_evt0_input_cap_w"] == 20, "fallback updates the operational integration value")
        require(updated_power["charging_policy"]["evt0_wired_input_cap_w"] == 20, "fallback propagates into the ECAD power contract")
        require(updated_profile["battery"]["charging_wired_target_w"] == 100, "fallback preserves the locked charging target")
        require(ConfigurationResolver(temporary_root).resolve()["violations"] == [], "fallback leaves no configuration propagation mismatch")
        application = load_yaml(temporary_root / plan["destination"])
        require(application["application"]["supplier_raw_sha256"] == plan["supplier_raw_sha256"], "fallback receipt preserves supplier provenance")
        require(application["application"]["prior_values"], "fallback receipt preserves prior values")
        queue = SupplierResponseRepository(temporary_root).build_review_queue()
        require(queue["items"][0]["disposition"] == "READY_FOR_ENGINEERING_REVIEW", "applied fallback resolves the active contradiction without verifying the claim")
        changed_impact = RegenerationEngine(temporary_root).impacted_nodes(result["changed_paths"])
        require("supplier_review" in changed_impact and "dashboard" in changed_impact, "fallback paths identify every downstream regeneration branch")
        require_raises(
            lambda: ConfigurationChangeController(temporary_root).validate_decision(decision_path),
            "already exists",
            "applied fallback decision cannot be replayed",
        )

    engine = RegenerationEngine(REPO_ROOT)
    require(engine.build_state()["state_version"] == 2, "regeneration state records the portable hash policy version")
    require(engine.stale_nodes() == (), "all generated nodes match committed input and output hashes")
    profile_impact = engine.impacted_nodes(["configs/devices/slate-pocket-v1r.yaml"])
    require("configuration_resolution" in profile_impact and "program_snapshot" in profile_impact, "profile change propagates through configuration and program snapshot")
    supplier_impact = engine.impacted_nodes(["research/supplier-responses/receipts/example.yaml"])
    unaffected = set(engine.nodes) - set(supplier_impact)
    require(unaffected == {"migration_audit"}, "supplier receipt change propagates across every dependent engineering node")
    require(engine.impacted_nodes(["docs/unrelated-note.md"]) == (), "untracked path does not trigger unrelated generators")
    require(engine.load_state() == engine.build_state(), "regeneration state is deterministic and current")

    original_dependencies = list(engine.nodes["supplier_review"]["depends_on"])
    engine.nodes["supplier_review"]["depends_on"] = ["program_snapshot"]
    try:
        engine.topological_order()
    except ValueError as exc:
        require("cycle" in str(exc), "regeneration dependency cycles are rejected")
    else:
        raise AssertionError("regeneration cycle was not rejected")
    finally:
        engine.nodes["supplier_review"]["depends_on"] = original_dependencies

    with tempfile.TemporaryDirectory() as temp_directory:
        first = Path(temp_directory) / "first.txt"
        second = Path(temp_directory) / "second.txt"
        command = [sys.executable, "engineering/run_device_profile.py", "--profile", "configs/devices/slate-pocket-v1r.yaml"]
        first_run = subprocess.run(command + ["--output", str(first)], cwd=REPO_ROOT, capture_output=True, text=True, check=False)
        second_run = subprocess.run(command + ["--output", str(second)], cwd=REPO_ROOT, capture_output=True, text=True, check=False)
        require(first_run.returncode == 0 and second_run.returncode == 0, "device profile generator runs twice")
        require(first.read_bytes() == second.read_bytes(), "device profile output is byte-for-byte deterministic")

    cli = subprocess.run(
        [sys.executable, "-m", "buildslate", "impact", "--changed", "configs/devices/slate-pocket-v1r.yaml", "--format", "json"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    require(cli.returncode == 0 and '"configuration_resolution"' in cli.stdout, "CLI exposes dependency impact")
    fallback_help = subprocess.run(
        [sys.executable, "-m", "buildslate", "configuration", "fallback", "--help"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    require(fallback_help.returncode == 0 and "apply" in fallback_help.stdout and "validate" in fallback_help.stdout, "CLI exposes controlled fallback validation and application")
    passed("configuration authority and regeneration validation")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AssertionError, OSError, ValueError, KeyError, TypeError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)

