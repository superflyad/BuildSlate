"""Evidence-aware configuration authority and downstream binding checks."""

from __future__ import annotations

import hashlib
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from .io import dump_yaml, load_yaml
from .regeneration import RegenerationEngine
from .suppliers import SupplierResponseRepository


MISSING = object()
VALID_STATES = {
    "locked_target",
    "operational_fallback",
    "selected_component",
    "rejected_option",
    "unresolved_decision",
    "modeled_reference",
}
MODEL_CONSUMPTION = {"model_input", "disabled_input"}


def value_at(document: dict[str, Any], dotted_path: str) -> Any:
    value: Any = document
    for segment in dotted_path.split("."):
        if not isinstance(value, dict) or segment not in value:
            return MISSING
        value = value[segment]
    return value


def set_value(document: dict[str, Any], dotted_path: str, value: Any) -> Any:
    """Replace an existing dotted-path value and return its prior value."""
    segments = dotted_path.split(".")
    parent: Any = document
    for segment in segments[:-1]:
        if not isinstance(parent, dict) or segment not in parent:
            raise ValueError(f"configuration target field is missing: {dotted_path}")
        parent = parent[segment]
    leaf = segments[-1]
    if not isinstance(parent, dict) or leaf not in parent:
        raise ValueError(f"configuration target field is missing: {dotted_path}")
    prior = parent[leaf]
    parent[leaf] = value
    return prior


class ConfigurationResolver:
    def __init__(self, repo_root: Path, registry_path: str = "engineering/program/configuration_registry.yaml") -> None:
        self.repo_root = repo_root.resolve()
        self.registry_path = self._repo_path(registry_path)
        self.registry = load_yaml(self.registry_path)
        self.profile_path = self._repo_path("configs/devices/slate-pocket-v1r.yaml")
        self.profile = load_yaml(self.profile_path)
        self._validate_registry()

    def _repo_path(self, value: str | Path) -> Path:
        path = Path(value)
        candidate = path.resolve() if path.is_absolute() else (self.repo_root / path).resolve()
        try:
            candidate.relative_to(self.repo_root)
        except ValueError as exc:
            raise ValueError(f"path escapes repository: {value}") from exc
        return candidate

    def _source_value(self, source: str) -> Any:
        if "#" not in source:
            raise ValueError(f"configuration source must use file#field syntax: {source}")
        source_file, source_field = source.split("#", 1)
        value = value_at(load_yaml(self._repo_path(source_file)), source_field)
        if value is MISSING:
            raise ValueError(f"configuration source field is missing: {source}")
        return value

    def _validate_registry(self) -> None:
        metadata = self.registry.get("metadata")
        entries = self.registry.get("entries")
        bindings = self.registry.get("bindings")
        propagations = self.registry.get("propagations")
        if not isinstance(metadata, dict) or metadata.get("schema_version") != 1:
            raise ValueError("configuration registry requires metadata.schema_version 1")
        if not isinstance(entries, dict) or not entries:
            raise ValueError("configuration registry requires entries")
        if not isinstance(bindings, list) or not bindings:
            raise ValueError("configuration registry requires bindings")
        if not isinstance(propagations, list):
            raise ValueError("configuration registry requires propagations")
        for entry_id, entry in entries.items():
            if not isinstance(entry, dict) or entry.get("state") not in VALID_STATES:
                raise ValueError(f"configuration entry {entry_id} has invalid state")
            if "value" not in entry or not isinstance(entry.get("sources"), list) or not entry["sources"]:
                raise ValueError(f"configuration entry {entry_id} requires value and sources")
            source_values = [self._source_value(source) for source in entry["sources"]]
            if entry["state"] not in {"rejected_option"} and entry["value"] not in source_values:
                raise ValueError(f"configuration entry {entry_id} value is not present in its authoritative sources")
            if entry["state"] == "selected_component":
                if entry["value"] is None or not entry.get("selection_receipt") or not entry.get("selection_value_path"):
                    raise ValueError(
                        f"selected component {entry_id} requires value, selection_receipt, and selection_value_path"
                    )
                receipt = load_yaml(self._repo_path(entry["selection_receipt"]))
                if receipt.get("review", {}).get("disposition") != "READY_FOR_ENGINEERING_REVIEW":
                    raise ValueError(f"selected component {entry_id} receipt is not ready for engineering review")
                raw_path = self._repo_path(receipt.get("raw_path", ""))
                if not raw_path.is_file() or hashlib.sha256(raw_path.read_bytes()).hexdigest() != receipt.get("sha256"):
                    raise ValueError(f"selected component {entry_id} receipt integrity check failed")
                selected_value = value_at(load_yaml(raw_path), entry["selection_value_path"])
                if selected_value is MISSING or selected_value != entry["value"]:
                    raise ValueError(f"selected component {entry_id} value does not match its raw response")
            if entry["state"] == "unresolved_decision" and entry.get("model_use") not in {"prohibited", "status_only"}:
                raise ValueError(f"unresolved entry {entry_id} cannot be an allowed model input")
            if entry["state"] == "rejected_option" and not entry.get("notes"):
                raise ValueError(f"rejected option {entry_id} requires notes")
        seen_paths: set[str] = set()
        for binding in bindings:
            if not isinstance(binding, dict) or not {"profile_path", "authority", "consumption"}.issubset(binding):
                raise ValueError("configuration binding requires profile_path, authority, and consumption")
            if binding["authority"] not in entries:
                raise ValueError(f"configuration binding references unknown authority: {binding['authority']}")
            if binding["profile_path"] in seen_paths:
                raise ValueError(f"duplicate configuration binding: {binding['profile_path']}")
            seen_paths.add(binding["profile_path"])
        seen_targets: set[str] = set()
        for propagation in propagations:
            if not isinstance(propagation, dict) or not {"target", "authority", "consumption"}.issubset(propagation):
                raise ValueError("configuration propagation requires target, authority, and consumption")
            if propagation["authority"] not in entries:
                raise ValueError(f"configuration propagation references unknown authority: {propagation['authority']}")
            if not isinstance(propagation["target"], str) or "#" not in propagation["target"]:
                raise ValueError("configuration propagation target must use file#field syntax")
            if propagation["target"] in seen_targets:
                raise ValueError(f"duplicate configuration propagation: {propagation['target']}")
            seen_targets.add(propagation["target"])

    def resolve(self) -> dict[str, Any]:
        entries = self.registry["entries"]
        resolved: list[dict[str, Any]] = []
        violations: list[dict[str, Any]] = []
        for binding in self.registry["bindings"]:
            entry = entries[binding["authority"]]
            actual = value_at(self.profile, binding["profile_path"])
            expected = entry["value"]
            item = {
                "profile_path": binding["profile_path"],
                "authority": binding["authority"],
                "state": entry["state"],
                "value": None if actual is MISSING else actual,
                "unit": entry.get("unit"),
                "consumption": binding["consumption"],
                "model_use": entry["model_use"],
                "sources": list(entry["sources"]),
            }
            if actual is MISSING or actual != expected:
                violations.append(
                    {
                        "profile_path": binding["profile_path"],
                        "issue": "missing" if actual is MISSING else "authority_mismatch",
                        "actual": None if actual is MISSING else actual,
                        "expected": expected,
                        "authority": binding["authority"],
                    }
                )
            if binding["consumption"] in MODEL_CONSUMPTION and entry["model_use"] in {"prohibited", "status_only"}:
                violations.append(
                    {
                        "profile_path": binding["profile_path"],
                        "issue": "unsupported_value_entered_model",
                        "state": entry["state"],
                        "authority": binding["authority"],
                    }
                )
            resolved.append(item)

        resolved_propagations: list[dict[str, Any]] = []
        for propagation in self.registry["propagations"]:
            entry = entries[propagation["authority"]]
            actual = self._source_value(propagation["target"])
            item = {
                "target": propagation["target"],
                "authority": propagation["authority"],
                "state": entry["state"],
                "value": actual,
                "unit": entry.get("unit"),
                "consumption": propagation["consumption"],
            }
            if actual != entry["value"]:
                violations.append(
                    {
                        "target": propagation["target"],
                        "issue": "propagation_mismatch",
                        "actual": actual,
                        "expected": entry["value"],
                        "authority": propagation["authority"],
                    }
                )
            resolved_propagations.append(item)

        counts: dict[str, int] = {}
        unresolved: list[dict[str, Any]] = []
        for entry_id, entry in entries.items():
            counts[entry["state"]] = counts.get(entry["state"], 0) + 1
            if entry["state"] == "unresolved_decision":
                unresolved.append(
                    {
                        "authority": entry_id,
                        "current_value": entry["value"],
                        "external_blocker": entry.get("external_blocker"),
                        "model_use": entry["model_use"],
                    }
                )
        if violations:
            gate = "BLOCKED_UNSUPPORTED_CONFIGURATION"
        elif unresolved:
            gate = "CONTROLLED_WITH_UNRESOLVED_EXTERNAL_DECISIONS"
        else:
            gate = "CONTROLLED_CONFIGURATION"
        return {
            "CONFIGURATION_GATE": gate,
            "profile": self.registry["metadata"]["profile"],
            "classification_counts": dict(sorted(counts.items())),
            "resolved_bindings": resolved,
            "resolved_propagations": resolved_propagations,
            "violations": violations,
            "unresolved_decisions": unresolved,
            "caveat": "Resolved values remain targets, fallbacks, references, or dispositions as classified; no supplier component is selected or verified.",
        }

    def generate(self) -> Path:
        destination = self._repo_path(self.registry["outputs"]["resolution_report"])
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(dump_yaml(self.resolve()), encoding="utf-8")
        return destination


class ConfigurationChangeController:
    """Validate and atomically apply an approved supplier-backed fallback."""

    DECISION_ID = re.compile(r"^[a-z0-9][a-z0-9_-]{2,63}$")

    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root.resolve()
        self.resolver = ConfigurationResolver(self.repo_root)
        self.suppliers = SupplierResponseRepository(self.repo_root)

    def _repo_path(self, value: str | Path) -> Path:
        path = Path(value)
        candidate = path.resolve() if path.is_absolute() else (self.repo_root / path).resolve()
        try:
            candidate.relative_to(self.repo_root)
        except ValueError as exc:
            raise ValueError(f"path escapes repository: {value}") from exc
        return candidate

    @staticmethod
    def _parse_timestamp(value: Any) -> None:
        if not isinstance(value, str):
            raise ValueError("approval.approved_at must be an ISO-8601 timestamp")
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("approval.approved_at must be an ISO-8601 timestamp") from exc
        if parsed.tzinfo is None:
            raise ValueError("approval.approved_at must include a timezone")

    def _receipt_item(self, relative_path: str) -> dict[str, Any]:
        wanted = self._repo_path(relative_path)
        queue = self.suppliers.build_review_queue()
        for item in queue["items"]:
            if self._repo_path(item["receipt"]) == wanted:
                if item["integrity_errors"]:
                    raise ValueError("supplier receipt integrity failed: " + "; ".join(item["integrity_errors"]))
                return item
        raise ValueError(f"supplier receipt is not in the controlled store: {relative_path}")

    def validate_decision(self, decision_path: Path) -> dict[str, Any]:
        source = decision_path.resolve()
        decision = load_yaml(source)
        required = {"schema_version", "decision_id", "authority", "expected_current_value", "new_value", "evidence", "approval"}
        missing = required - set(decision)
        if missing:
            raise ValueError(f"configuration fallback decision is missing fields: {sorted(missing)}")
        extra = set(decision) - required
        if extra:
            raise ValueError(f"configuration fallback decision has unsupported fields: {sorted(extra)}")
        if decision["schema_version"] != 1:
            raise ValueError("configuration fallback decision requires schema_version 1")
        decision_id = decision["decision_id"]
        if not isinstance(decision_id, str) or not self.DECISION_ID.fullmatch(decision_id):
            raise ValueError("decision_id must be 3-64 lowercase letters, digits, underscores, or hyphens")
        destination = self._repo_path(f"engineering/program/configuration-decisions/{decision_id}.yaml")
        if destination.exists():
            raise ValueError(f"configuration fallback decision already exists: {decision_id}")

        authority = decision["authority"]
        entry = self.resolver.registry["entries"].get(authority)
        if not isinstance(entry, dict):
            raise ValueError(f"unknown configuration authority: {authority}")
        if entry["state"] != "operational_fallback":
            raise ValueError(f"fallback workflow cannot change {entry['state']} authority: {authority}")
        if decision["expected_current_value"] != entry["value"]:
            raise ValueError("expected_current_value does not match the authoritative registry")

        approval = decision["approval"]
        if not isinstance(approval, dict) or approval.get("disposition") != "approved":
            raise ValueError("fallback requires approval.disposition=approved")
        if set(approval) != {"disposition", "approved_by", "approved_at", "rationale"}:
            raise ValueError("approval fields do not match the fallback decision schema")
        for field in ("approved_by", "rationale"):
            if not isinstance(approval.get(field), str) or not approval[field].strip():
                raise ValueError(f"approval.{field} must be a non-empty string")
        self._parse_timestamp(approval.get("approved_at"))

        evidence = decision["evidence"]
        if not isinstance(evidence, dict) or not {"supplier_receipt", "contradiction_rule_id"}.issubset(evidence):
            raise ValueError("evidence requires supplier_receipt and contradiction_rule_id")
        if set(evidence) != {"supplier_receipt", "contradiction_rule_id"}:
            raise ValueError("evidence fields do not match the fallback decision schema")
        item = self._receipt_item(evidence["supplier_receipt"])
        if item["disposition"] != "CONTRADICTION_REVIEW_REQUIRED":
            raise ValueError("supplier receipt is not in contradiction review")
        contradiction = next(
            (value for value in item["review"]["contradictions"] if value["rule_id"] == evidence["contradiction_rule_id"]),
            None,
        )
        if contradiction is None:
            raise ValueError("approved contradiction rule is not active in the supplier receipt")
        schema = self.suppliers._load_schema(item["domain"])
        rule = next(value for value in schema["contradiction_rules"] if value["id"] == evidence["contradiction_rule_id"])
        effect = rule.get("configuration_effect")
        if not isinstance(effect, dict):
            raise ValueError("contradiction has no machine-executable configuration effect")
        if effect.get("authority") != authority:
            raise ValueError("decision authority does not match the contradiction configuration effect")
        policy = effect.get("value_policy")
        if policy == "supplier_value":
            expected_new = contradiction["actual"]
        elif policy == "fixed_value":
            expected_new = effect.get("value")
        else:
            raise ValueError(f"unsupported fallback value policy: {policy}")
        if decision["new_value"] != expected_new:
            raise ValueError(f"new_value must equal the executable fallback value {expected_new!r}")
        if isinstance(expected_new, bool) or not isinstance(expected_new, type(entry["value"])):
            raise ValueError("executable fallback value type does not match the current authority")
        if "minimum" in effect and expected_new < effect["minimum"]:
            raise ValueError("executable fallback value is below the policy minimum")
        if "maximum" in effect and expected_new > effect["maximum"]:
            raise ValueError("executable fallback value is above the policy maximum")

        targets: list[str] = []
        for binding in self.resolver.registry["bindings"]:
            if binding["authority"] == authority:
                targets.append(f"configs/devices/slate-pocket-v1r.yaml#{binding['profile_path']}")
        for propagation in self.resolver.registry["propagations"]:
            if propagation["authority"] == authority:
                targets.append(propagation["target"])
        if not targets:
            raise ValueError(f"configuration authority has no writable targets: {authority}")
        return {
            "decision_id": decision_id,
            "authority": authority,
            "current_value": entry["value"],
            "new_value": decision["new_value"],
            "supplier_receipt": item["receipt"],
            "supplier_raw_sha256": item["sha256"],
            "contradiction_rule_id": contradiction["rule_id"],
            "contradiction_schema": self.suppliers.manifest["domains"][item["domain"]]["schema"],
            "approved_fallback_or_action": contradiction["approved_fallback_or_action"],
            "targets": targets,
            "decision_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
            "destination": destination.relative_to(self.repo_root).as_posix(),
            "status": "VALIDATED_NOT_APPLIED",
            "caveat": "Approval applies only the declared operational fallback; it does not verify supplier claims or select a component.",
        }

    def apply(self, decision_path: Path, regenerate: bool = True) -> dict[str, Any]:
        plan = self.validate_decision(decision_path)
        decision = load_yaml(decision_path.resolve())
        registry = load_yaml(self.resolver.registry_path)
        documents: dict[Path, dict[str, Any]] = {self.resolver.registry_path: registry}
        prior_values: dict[str, Any] = {}
        for target in plan["targets"]:
            file_name, field = target.split("#", 1)
            path = self._repo_path(file_name)
            document = documents.setdefault(path, load_yaml(path))
            prior_values[target] = set_value(document, field, plan["new_value"])
        registry["entries"][plan["authority"]]["value"] = plan["new_value"]
        destination = self._repo_path(plan["destination"])
        registry["entries"][plan["authority"]]["sources"] = list(
            dict.fromkeys(
                [
                    *registry["entries"][plan["authority"]]["sources"],
                    f"{plan['destination']}#decision.new_value",
                ]
            )
        )
        schema_path = self._repo_path(plan["contradiction_schema"])
        schema_document = documents.setdefault(schema_path, load_yaml(schema_path))
        schema_rule = next(
            value for value in schema_document["contradiction_rules"] if value["id"] == plan["contradiction_rule_id"]
        )
        prior_values[f"{plan['contradiction_schema']}#rule:{plan['contradiction_rule_id']}.expected"] = schema_rule["expected"]
        schema_rule["expected"] = plan["new_value"]
        changed_paths = sorted(
            {path.relative_to(self.repo_root).as_posix() for path in documents} | {plan["destination"]}
        )
        engine = RegenerationEngine(self.repo_root) if regenerate else None
        impacted = engine.impacted_nodes(changed_paths) if engine else ()
        protected_paths = set(documents) | {destination}
        if engine:
            protected_paths.add(engine._repo_path(engine.manifest["state_file"]))
            for node_id in impacted:
                protected_paths.update(engine._repo_path(value) for value in engine.nodes[node_id]["outputs"])
        snapshots = {path: path.read_bytes() if path.exists() else None for path in protected_paths}
        application = {
            "receipt_version": 1,
            "decision": decision,
            "application": {
                "status": "APPLIED",
                "decision_sha256": plan["decision_sha256"],
                "supplier_raw_sha256": plan["supplier_raw_sha256"],
                "prior_values": prior_values,
                "new_value": plan["new_value"],
                "changed_paths": changed_paths,
                "regenerated_nodes": list(impacted),
            },
            "authority_boundary": "approved_operational_fallback_not_supplier_verification_or_component_selection",
        }
        try:
            for path, document in documents.items():
                path.write_text(dump_yaml(document), encoding="utf-8")
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(dump_yaml(application), encoding="utf-8")
            resolution = ConfigurationResolver(self.repo_root).resolve()
            if resolution["violations"]:
                raise ValueError(f"fallback produced configuration violations: {resolution['violations']}")
            if engine:
                engine.regenerate(impacted)
                remaining_stale = engine.stale_nodes()
                if remaining_stale:
                    raise ValueError(f"fallback regeneration left stale nodes: {list(remaining_stale)}")
        except Exception:
            for path, content in snapshots.items():
                if content is None:
                    if path.exists() and path.is_file():
                        path.unlink()
                else:
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(content)
            raise
        return {**plan, "status": "APPLIED", "changed_paths": changed_paths, "regenerated_nodes": list(impacted)}

