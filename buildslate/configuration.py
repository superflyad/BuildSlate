"""Evidence-aware configuration authority and downstream binding checks."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from .io import dump_yaml, load_yaml


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
        if not isinstance(metadata, dict) or metadata.get("schema_version") != 1:
            raise ValueError("configuration registry requires metadata.schema_version 1")
        if not isinstance(entries, dict) or not entries:
            raise ValueError("configuration registry requires entries")
        if not isinstance(bindings, list) or not bindings:
            raise ValueError("configuration registry requires bindings")
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
            "violations": violations,
            "unresolved_decisions": unresolved,
            "caveat": "Resolved values remain targets, fallbacks, references, or dispositions as classified; no supplier component is selected or verified.",
        }

    def generate(self) -> Path:
        destination = self._repo_path(self.registry["outputs"]["resolution_report"])
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(dump_yaml(self.resolve()), encoding="utf-8")
        return destination

