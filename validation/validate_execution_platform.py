#!/usr/bin/env python3
"""Validate the unified BuildSlate program graph and CLI foundation."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = REPO_ROOT / "engineering" / "program" / "program_model.yaml"
SCHEMA_PATH = REPO_ROOT / "engineering" / "program" / "program_model.schema.yaml"
SNAPSHOT_PATH = REPO_ROOT / "reports" / "program" / "buildslate-program-snapshot.yaml"

sys.path.insert(0, str(REPO_ROOT))

from buildslate.program import ProgramRepository  # noqa: E402


def _run_cli(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "buildslate", *arguments],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def main() -> int:
    failures: list[str] = []
    for path in (MANIFEST_PATH, SCHEMA_PATH):
        if path.exists():
            print(f"PASS: execution-platform artifact exists: {path.relative_to(REPO_ROOT)}")
        else:
            failures.append(f"execution-platform artifact missing: {path.relative_to(REPO_ROOT)}")

    try:
        repository = ProgramRepository(REPO_ROOT)
        first = repository.build_snapshot()
        second = repository.build_snapshot()
        if first.to_dict() != second.to_dict():
            failures.append("program snapshot is not deterministic")
        expected_kinds = {
            "requirement",
            "configuration",
            "evidence_package",
            "artifact",
            "assumption",
            "risk",
            "blocker",
            "supplier",
            "component_role",
            "test",
            "defect_code",
            "gate",
            "decision",
            "provenance",
            "workflow",
            "generated_output",
        }
        actual_kinds = {entity.kind for entity in first.entities}
        missing_kinds = expected_kinds - actual_kinds
        if missing_kinds:
            failures.append(f"program graph missing entity kinds: {', '.join(sorted(missing_kinds))}")
        evidence_statuses = first.summary["evidence_status_counts"]
        if evidence_statuses != {"available": 3, "planned": 6, "verified": 1}:
            failures.append(f"program graph changed evidence status truth: {evidence_statuses}")
        entity_ids = {entity.entity_id for entity in first.entities}
        if len(entity_ids) != len(first.entities):
            failures.append("program graph contains duplicate entity ids")
        for relation in first.relations:
            if relation.source_id not in entity_ids or relation.target_id not in entity_ids:
                failures.append(f"program graph contains dangling relation: {relation}")
                break
        relation_keys = {(item.source_id, item.relationship, item.target_id) for item in first.relations}
        required_relations = {
            ("configuration:slate-pocket-v1r", "governed_by", "decision:memory_operational"),
            ("decision:memory_operational", "sourced_from", "provenance_ref:configs/devices/slate-pocket-v1r.yaml#integration_configuration.memory_gb"),
            ("decision:compute_platform_selection", "blocked_by", "blocker:platform_reference_design"),
            ("workflow:dashboard", "depends_on", "workflow:program_snapshot"),
            ("workflow:program_snapshot", "produces", "generated_output:reports/program/buildslate-program-snapshot.yaml"),
        }
        missing_relations = required_relations - relation_keys
        if missing_relations:
            failures.append(f"program graph missing authority/dependency relations: {sorted(missing_relations)}")
        if not failures:
            print(f"PASS: deterministic program graph has {len(first.entities)} entities and {len(first.relations)} relations")
            print("PASS: graph covers requirements, evidence, artifacts, assumptions, risks, blockers, suppliers, configuration decisions, provenance, workflows, components, tests, defects, and gates")
    except (KeyError, TypeError, ValueError) as exc:
        failures.append(str(exc))

    if not failures:
        generated = repository.generate_snapshot()
        if generated == SNAPSHOT_PATH and SNAPSHOT_PATH.exists():
            on_disk = yaml.safe_load(SNAPSHOT_PATH.read_text(encoding="utf-8"))
            if on_disk != first.to_dict():
                failures.append("generated program snapshot differs from in-memory graph")
            else:
                print("PASS: generated program snapshot matches the authoritative graph")
        else:
            failures.append("program snapshot was not generated at the declared path")

    cli_cases = (
        (("validate",), "PASS: program manifest and graph"),
        (("status", "--format", "json"), '"program_id": "slate-pocket-v1r"'),
        (("blockers", "--id", "supplier_responses", "--format", "json"), '"entity_id": "blocker:supplier_responses"'),
        (("compare", "--left", "configs/devices/slate-pocket-v1.yaml", "--right", "configs/devices/slate-pocket-v1r.yaml", "--format", "json"), '"difference_count"'),
    )
    for arguments, marker in cli_cases:
        result = _run_cli(*arguments)
        if result.returncode != 0 or marker not in result.stdout:
            failures.append(f"CLI {' '.join(arguments)} failed: {result.stderr.strip() or result.stdout.strip()}")
        else:
            print(f"PASS: CLI {' '.join(arguments)}")
    status_result = _run_cli("status", "--format", "json")
    if status_result.returncode == 0:
        try:
            status_payload = json.loads(status_result.stdout)
            if status_payload["summary"]["evidence_status_counts"] != {"available": 3, "planned": 6, "verified": 1}:
                failures.append("structured CLI status changed evidence classification")
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            failures.append(f"structured CLI status is invalid JSON: {exc}")

    unknown_result = _run_cli("blockers", "--id", "does_not_exist")
    if unknown_result.returncode != 2 or "unknown blocker" not in unknown_result.stderr:
        failures.append("CLI does not reject an unknown blocker with exit code 2")
    else:
        print("PASS: CLI rejects unknown blocker input")

    with tempfile.TemporaryDirectory() as temporary_directory:
        bad_manifest_path = Path(temporary_directory) / "bad.yaml"
        bad_manifest_path.write_text("metadata:\n  schema_version: 1\n  program_id: broken\n  title: Broken\n  authority: test\nsources: {}\n", encoding="utf-8")
        try:
            ProgramRepository(REPO_ROOT, bad_manifest_path).validate_manifest()
        except ValueError as exc:
            if "source set mismatch" in str(exc):
                print("PASS: malformed program manifest is rejected")
            else:
                failures.append(f"malformed manifest failed for the wrong reason: {exc}")
        else:
            failures.append("malformed program manifest was accepted")

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1
    print("PASS: BuildSlate execution platform foundation validation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
