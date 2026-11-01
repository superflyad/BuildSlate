"""Load authoritative BuildSlate sources into one traceable program graph."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from .io import dump_yaml, load_yaml
from .model import ProgramEntity, ProgramRelation, ProgramSnapshot

DEFAULT_REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = Path("engineering/program/program_model.yaml")
REQUIRED_SOURCES = {
    "profile",
    "evidence",
    "assumptions",
    "risks",
    "blockers",
    "suppliers",
    "components",
    "tests",
    "defects",
    "configuration_authority",
    "provenance",
    "dependencies",
}


class ProgramRepository:
    """Read-only integration layer over BuildSlate's authoritative registries."""

    def __init__(self, repo_root: Path | None = None, manifest_path: Path | None = None) -> None:
        self.repo_root = (repo_root or DEFAULT_REPO_ROOT).resolve()
        candidate = manifest_path or DEFAULT_MANIFEST
        self.manifest_path = candidate if candidate.is_absolute() else self.repo_root / candidate
        self.manifest = load_yaml(self.manifest_path)

    def _repo_path(self, value: str) -> Path:
        path = (self.repo_root / value).resolve()
        try:
            path.relative_to(self.repo_root)
        except ValueError as exc:
            raise ValueError(f"program path escapes repository root: {value}") from exc
        return path

    def validate_manifest(self) -> None:
        """Validate manifest structure and referenced source paths."""
        metadata = self.manifest.get("metadata")
        if not isinstance(metadata, dict):
            raise ValueError("program manifest metadata must be a mapping")
        if metadata.get("schema_version") != 1:
            raise ValueError("program manifest schema_version must be 1")
        for field in ("program_id", "title", "authority"):
            if not isinstance(metadata.get(field), str) or not metadata[field].strip():
                raise ValueError(f"program manifest metadata.{field} must be a non-empty string")

        sources = self.manifest.get("sources")
        if not isinstance(sources, dict):
            raise ValueError("program manifest sources must be a mapping")
        missing_sources = REQUIRED_SOURCES - set(sources)
        unknown_sources = set(sources) - REQUIRED_SOURCES
        if missing_sources or unknown_sources:
            details = []
            if missing_sources:
                details.append(f"missing: {', '.join(sorted(missing_sources))}")
            if unknown_sources:
                details.append(f"unknown: {', '.join(sorted(unknown_sources))}")
            raise ValueError(f"program manifest source set mismatch ({'; '.join(details)})")
        for source_id, source in sources.items():
            if not isinstance(source, dict):
                raise ValueError(f"sources.{source_id} must be a mapping")
            for field in ("entity_kind", "path"):
                if not isinstance(source.get(field), str) or not source[field].strip():
                    raise ValueError(f"sources.{source_id}.{field} must be a non-empty string")
            load_yaml(self._repo_path(source["path"]))

        gates = self.manifest.get("gate_sources")
        if not isinstance(gates, dict) or not gates:
            raise ValueError("program manifest gate_sources must be a non-empty mapping")
        for gate_id, gate in gates.items():
            if not isinstance(gate, dict):
                raise ValueError(f"gate_sources.{gate_id} must be a mapping")
            path = gate.get("path")
            marker = gate.get("marker")
            if not isinstance(path, str) or not path or not isinstance(marker, str) or not marker:
                raise ValueError(f"gate_sources.{gate_id} requires non-empty path and marker")
            report = self._repo_path(path)
            if not report.exists():
                raise ValueError(f"gate source missing: {path}")
            if not any(marker in line for line in report.read_text(encoding="utf-8").splitlines()):
                raise ValueError(f"gate source {path} does not contain marker {marker}")

        outputs = self.manifest.get("outputs")
        if not isinstance(outputs, dict) or not isinstance(outputs.get("program_snapshot"), str):
            raise ValueError("program manifest outputs.program_snapshot must be a path")
        self._repo_path(outputs["program_snapshot"])
        caveat = self.manifest.get("caveat")
        if not isinstance(caveat, str) or "not" not in caveat.lower():
            raise ValueError("program manifest must contain a non-validation caveat")

    def _source(self, source_id: str) -> tuple[str, dict[str, Any]]:
        source = self.manifest["sources"][source_id]
        return source["path"], load_yaml(self._repo_path(source["path"]))

    @staticmethod
    def _entity(entity_id: str, kind: str, title: str, status: str, source: str, **attributes: Any) -> ProgramEntity:
        return ProgramEntity(entity_id, kind, title, status, source, attributes)

    def build_snapshot(self) -> ProgramSnapshot:
        """Build and validate a deterministic unified graph."""
        self.validate_manifest()
        entities: list[ProgramEntity] = []
        relations: list[ProgramRelation] = []

        profile_path, profile = self._source("profile")
        baseline = profile["decision_baseline"]
        for outcome in baseline["stable_product_outcomes"]:
            entities.append(self._entity(f"outcome:{outcome}", "requirement", outcome.replace("_", " "), "locked", profile_path, requirement_class="must_have_outcome"))
        for requirement_id, rule in baseline["locked_trade_rules"].items():
            entities.append(self._entity(f"requirement:{requirement_id}", "requirement", requirement_id.replace("_", " "), "locked", profile_path, requirement_class="trade_rule", rule=rule))
        for safety_id, value in baseline["safety_boundaries"].items():
            entities.append(self._entity(f"safety:{safety_id}", "requirement", safety_id.replace("_", " "), "locked", profile_path, requirement_class="safety_boundary", value=value))
        config_id = f"configuration:{profile['identity']['profile_id']}"
        entities.append(self._entity(config_id, "configuration", profile["identity"]["name"], profile["integration_configuration"]["status"], profile_path, operational=profile["integration_configuration"], geometry=profile["geometry"]))
        for requirement_id in baseline["locked_trade_rules"]:
            relations.append(ProgramRelation(config_id, "implements", f"requirement:{requirement_id}"))

        evidence_path, evidence_data = self._source("evidence")
        for package_id, package in evidence_data["packages"].items():
            evidence_id = f"evidence:{package_id}"
            entities.append(self._entity(evidence_id, "evidence_package", package["title"], package["status"], evidence_path, phase=package["phase"], priority=package["priority"], owner=package["owner"], acceptance_criteria=package["acceptance_criteria"], notes=package["notes"]))
            for dependency in package["depends_on"]:
                relations.append(ProgramRelation(evidence_id, "depends_on", f"evidence:{dependency}"))
            for risk_id in package["linked_risks"]:
                relations.append(ProgramRelation(evidence_id, "linked_to", f"risk:{risk_id}"))
            for artifact_path in package["expected_artifacts"]:
                artifact_id = f"artifact:{artifact_path}"
                artifact_exists = self._repo_path(artifact_path).exists()
                entities.append(self._entity(artifact_id, "artifact", artifact_path, "present" if artifact_exists else "missing", evidence_path, expected_by=package_id))
                relations.append(ProgramRelation(evidence_id, "expects", artifact_id))

        assumption_path, assumption_data = self._source("assumptions")
        for assumption_id, assumption in assumption_data["assumptions"].items():
            entities.append(self._entity(f"assumption:{assumption_id}", "assumption", assumption_id.replace("_", " "), assumption["maturity"], assumption_path, value=assumption["value"], unit=assumption["unit"], confidence=assumption["confidence"], profile_scope=assumption["profile_scope"], evidence_required=assumption["evidence_required"]))

        risk_path, risk_data = self._source("risks")
        for risk_id, risk in risk_data["risks"].items():
            entities.append(self._entity(f"risk:{risk_id}", "risk", risk["title"], risk["status"], risk_path, subsystem=risk["subsystem"], likelihood=risk["likelihood"], impact=risk["impact"], maturity=risk["maturity"], mitigation=risk["mitigation"], evidence_required=risk["evidence_required"]))
            for assumption_id in risk["related_assumptions"]:
                relations.append(ProgramRelation(f"risk:{risk_id}", "depends_on", f"assumption:{assumption_id}"))

        blocker_path, blocker_data = self._source("blockers")
        for blocker_id, blocker in blocker_data["blockers"].items():
            entities.append(self._entity(f"blocker:{blocker_id}", "blocker", blocker_id.replace("_", " "), "external", blocker_path, category=blocker["category"], missing_evidence=blocker["missing_evidence"], exact_request=blocker["exact_request"], acceptance_criteria=blocker["acceptance_criteria"], fallback=blocker["fallback"], authorization_required=blocker["authorization_required"]))
            for package_id in blocker["affects"]:
                relations.append(ProgramRelation(f"blocker:{blocker_id}", "blocks", f"evidence:{package_id}"))

        supplier_path, supplier_data = self._source("suppliers")
        supplier_packages: dict[str, set[str]] = {}
        for packet in supplier_data["packets"].values():
            package_id = packet["linked_evidence_package"]
            for supplier in packet["target_suppliers"] + packet["alternates"]:
                supplier_packages.setdefault(supplier, set()).add(package_id)
        for supplier, packages in supplier_packages.items():
            supplier_id = f"supplier:{supplier}"
            entities.append(self._entity(supplier_id, "supplier", supplier.replace("_", " "), "candidate_not_contacted", supplier_path, evidence_packages=sorted(packages)))
            for package_id in sorted(packages):
                relations.append(ProgramRelation(supplier_id, "candidate_for", f"evidence:{package_id}"))

        component_path, component_data = self._source("components")
        for role_id, role in component_data["roles"].items():
            component_id = f"component_role:{role_id}"
            entities.append(self._entity(component_id, "component_role", role_id.replace("_", " "), role["status"], component_path, quantity_per_unit=role["quantity_per_unit"], required_evidence=role.get("required_evidence", [])))
            relations.append(ProgramRelation(component_id, "planned_for", config_id))

        test_path, test_data = self._source("tests")
        for test in test_data["sequence"]:
            test_id = f"test:{test['id']}"
            entities.append(self._entity(test_id, "test", test["test"].replace("_", " "), test["state"], test_path, workload=test["workload"], purpose=test["purpose"]))
            relations.append(ProgramRelation(test_id, "verifies", "evidence:evt0_prototype_evidence"))

        defect_path, defect_data = self._source("defects")
        for defect_id, description in defect_data["codes"].items():
            entity_id = f"defect:{defect_id}"
            entities.append(self._entity(entity_id, "defect_code", defect_id, defect_data["metadata"]["status"], defect_path, description=description))
            relations.append(ProgramRelation(entity_id, "classified_by", "evidence:manufacturing_review_package"))

        authority_path, authority_data = self._source("configuration_authority")
        provenance_references: dict[str, ProgramEntity] = {}
        for decision_id, decision in authority_data["entries"].items():
            entity_id = f"decision:{decision_id}"
            entities.append(
                self._entity(
                    entity_id,
                    "decision",
                    decision_id.replace("_", " "),
                    decision["state"],
                    authority_path,
                    value=decision["value"],
                    unit=decision.get("unit"),
                    model_use=decision["model_use"],
                    notes=decision.get("notes"),
                )
            )
            relations.append(ProgramRelation(config_id, "governed_by", entity_id))
            for source_reference in decision["sources"]:
                source_file = source_reference.split("#", 1)[0]
                reference_id = f"provenance_ref:{source_reference}"
                provenance_references[reference_id] = self._entity(
                    reference_id,
                    "provenance",
                    source_reference,
                    "traceable_reference",
                    source_file,
                    reference=source_reference,
                )
                relations.append(ProgramRelation(entity_id, "sourced_from", reference_id))
            external = decision.get("external_blocker")
            if external and f"blocker:{external}" in {entity.entity_id for entity in entities}:
                relations.append(ProgramRelation(entity_id, "blocked_by", f"blocker:{external}"))
        change_root = self._repo_path("engineering/program/configuration-decisions")
        for receipt_path in sorted(change_root.glob("*.yaml")) if change_root.exists() else ():
            receipt = load_yaml(receipt_path)
            decision = receipt["decision"]
            relative_receipt = receipt_path.relative_to(self.repo_root).as_posix()
            change_id = f"configuration_change:{decision['decision_id']}"
            entities.append(
                self._entity(
                    change_id,
                    "configuration_change",
                    decision["decision_id"].replace("_", " "),
                    receipt["application"]["status"],
                    relative_receipt,
                    authority=decision["authority"],
                    prior_values=receipt["application"]["prior_values"],
                    new_value=decision["new_value"],
                    approval=decision["approval"],
                    supplier_raw_sha256=receipt["application"]["supplier_raw_sha256"],
                )
            )
            relations.append(ProgramRelation(change_id, "applies_to", f"decision:{decision['authority']}"))
            supplier_receipt = decision["evidence"]["supplier_receipt"]
            reference_id = f"provenance_ref:{supplier_receipt}"
            provenance_references.setdefault(
                reference_id,
                self._entity(
                    reference_id,
                    "provenance",
                    supplier_receipt,
                    "supplier_receipt",
                    supplier_receipt,
                    reference=supplier_receipt,
                ),
            )
            relations.append(ProgramRelation(change_id, "supported_by", reference_id))
        entities.extend(provenance_references.values())

        provenance_path, provenance_data = self._source("provenance")
        for entry in provenance_data["entries"]:
            provenance_id = f"provenance:{entry['id']}"
            entities.append(
                self._entity(
                    provenance_id,
                    "provenance",
                    entry["name"],
                    entry["category"],
                    provenance_path,
                    value_or_range=entry["value_or_range"],
                    units=entry["units"],
                    confidence=entry["confidence"],
                    used_by=entry["used_by"],
                    future_validation=entry["future_validation"],
                    source_notes=entry["source_notes"],
                )
            )

        dependency_path, dependency_data = self._source("dependencies")
        for node_id, node in dependency_data["nodes"].items():
            workflow_id = f"workflow:{node_id}"
            entities.append(
                self._entity(
                    workflow_id,
                    "workflow",
                    node_id.replace("_", " "),
                    "tracked_generator",
                    dependency_path,
                    command=node["command"],
                    inputs=node["inputs"],
                    outputs=node["outputs"],
                )
            )
            for dependency in node["depends_on"]:
                relations.append(ProgramRelation(workflow_id, "depends_on", f"workflow:{dependency}"))
            for output in node["outputs"]:
                output_id = f"generated_output:{output}"
                entities.append(
                    self._entity(
                        output_id,
                        "generated_output",
                        output,
                        "present" if self._repo_path(output).is_file() else "missing",
                        dependency_path,
                        generator=node_id,
                    )
                )
                relations.append(ProgramRelation(workflow_id, "produces", output_id))

        for gate_id, gate in self.manifest["gate_sources"].items():
            report_path = self._repo_path(gate["path"])
            values = [line.split(gate["marker"], 1)[1].strip() for line in report_path.read_text(encoding="utf-8").splitlines() if gate["marker"] in line]
            decision = values[-1]
            entities.append(self._entity(f"gate:{gate_id}", "gate", gate_id.replace("_", " "), decision, gate["path"], marker=gate["marker"]))

        entity_by_id: dict[str, ProgramEntity] = {}
        for entity in entities:
            existing = entity_by_id.get(entity.entity_id)
            if existing and existing != entity:
                raise ValueError(f"conflicting entity definitions: {entity.entity_id}")
            entity_by_id[entity.entity_id] = entity
        relation_set = set(relations)
        for relation in relation_set:
            if relation.source_id not in entity_by_id:
                raise ValueError(f"relation source does not exist: {relation.source_id}")
            if relation.target_id not in entity_by_id:
                raise ValueError(f"relation target does not exist: {relation.target_id}")

        ordered_entities = tuple(sorted(entity_by_id.values(), key=lambda item: (item.kind, item.entity_id)))
        ordered_relations = tuple(sorted(relation_set, key=lambda item: (item.source_id, item.relationship, item.target_id)))
        kind_counts = Counter(entity.kind for entity in ordered_entities)
        evidence_counts = Counter(entity.status for entity in ordered_entities if entity.kind == "evidence_package")
        summary = {
            "entity_count": len(ordered_entities),
            "relation_count": len(ordered_relations),
            "entity_kind_counts": dict(sorted(kind_counts.items())),
            "evidence_status_counts": dict(sorted(evidence_counts.items())),
        }
        metadata = self.manifest["metadata"]
        return ProgramSnapshot(metadata["schema_version"], metadata["program_id"], metadata["title"], ordered_entities, ordered_relations, summary, self.manifest["caveat"])

    def generate_snapshot(self, output_path: Path | None = None) -> Path:
        """Write the deterministic program snapshot and return its path."""
        destination = output_path or self._repo_path(self.manifest["outputs"]["program_snapshot"])
        if not destination.is_absolute():
            destination = self.repo_root / destination
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(dump_yaml(self.build_snapshot().to_dict()), encoding="utf-8")
        return destination

    def blockers(self) -> tuple[ProgramEntity, ...]:
        """Return blocker entities from the current snapshot."""
        return tuple(entity for entity in self.build_snapshot().entities if entity.kind == "blocker")


def flatten_scalars(value: Any, prefix: str = "") -> dict[str, Any]:
    """Flatten configuration scalars for deterministic comparison."""
    output: dict[str, Any] = {}
    if isinstance(value, dict):
        for key in sorted(value):
            path = f"{prefix}.{key}" if prefix else str(key)
            output.update(flatten_scalars(value[key], path))
    elif isinstance(value, list):
        output[prefix] = value
    else:
        output[prefix] = value
    return output


def compare_yaml(left: Path, right: Path) -> list[dict[str, Any]]:
    """Compare scalar configuration values from two YAML mappings."""
    left_values = flatten_scalars(load_yaml(left))
    right_values = flatten_scalars(load_yaml(right))
    differences = []
    for key in sorted(set(left_values) | set(right_values)):
        left_value = left_values.get(key, "<missing>")
        right_value = right_values.get(key, "<missing>")
        if left_value != right_value:
            differences.append({"path": key, "left": left_value, "right": right_value})
    return differences
