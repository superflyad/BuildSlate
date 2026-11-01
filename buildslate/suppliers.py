"""Controlled supplier-response validation, preservation, and review queues."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from .io import dump_yaml, load_yaml


MISSING = object()
DEFAULT_MANIFEST = "engineering/program/supplier_ingestion.yaml"


def _value_at(document: dict[str, Any], dotted_path: str) -> Any:
    value: Any = document
    for segment in dotted_path.split("."):
        if not isinstance(value, dict) or segment not in value:
            return MISSING
        value = value[segment]
    return value


def _answered(value: Any) -> bool:
    if value is MISSING or value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict, tuple, set)):
        return bool(value)
    return True


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_name(name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", name).strip("-.")
    return cleaned or "response.yaml"


@dataclass(frozen=True)
class ResponseReview:
    domain: str
    linked_evidence_package: str
    schema_errors: tuple[str, ...]
    completeness_percent: float
    missing_fields: tuple[str, ...]
    provenance_issues: tuple[str, ...]
    contradictions: tuple[dict[str, Any], ...]
    disposition: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "domain": self.domain,
            "linked_evidence_package": self.linked_evidence_package,
            "disposition": self.disposition,
            "completeness_percent": self.completeness_percent,
            "schema_errors": list(self.schema_errors),
            "missing_fields": list(self.missing_fields),
            "provenance_issues": list(self.provenance_issues),
            "contradictions": list(self.contradictions),
            "evidence_effect": "none; engineering review is required before any authoritative state change",
        }


class SupplierResponseRepository:
    """Apply the repository's supplier-ingestion contract without promoting evidence."""

    def __init__(self, repo_root: Path, manifest_path: str = DEFAULT_MANIFEST) -> None:
        self.repo_root = repo_root.resolve()
        self.manifest_path = self._repo_path(manifest_path)
        self.manifest = load_yaml(self.manifest_path)
        self._validate_manifest()

    def _repo_path(self, value: str | Path) -> Path:
        path = Path(value)
        candidate = path.resolve() if path.is_absolute() else (self.repo_root / path).resolve()
        try:
            candidate.relative_to(self.repo_root)
        except ValueError as exc:
            raise ValueError(f"path escapes repository: {value}") from exc
        return candidate

    def _validate_manifest(self) -> None:
        metadata = self.manifest.get("metadata")
        storage = self.manifest.get("storage")
        domains = self.manifest.get("domains")
        policy = self.manifest.get("review_policy")
        if not isinstance(metadata, dict) or metadata.get("schema_version") != 1:
            raise ValueError("supplier ingestion manifest requires metadata.schema_version 1")
        if not isinstance(storage, dict):
            raise ValueError("supplier ingestion manifest requires storage")
        for key in ("raw_root", "receipt_root", "review_report"):
            if not isinstance(storage.get(key), str) or not storage[key]:
                raise ValueError(f"supplier ingestion storage.{key} must be a path")
            self._repo_path(storage[key])
        if not isinstance(domains, dict) or not domains:
            raise ValueError("supplier ingestion manifest requires domains")
        if not isinstance(policy, dict):
            raise ValueError("supplier ingestion manifest requires review_policy")
        for domain, entry in domains.items():
            if not isinstance(entry, dict) or not isinstance(entry.get("schema"), str):
                raise ValueError(f"supplier ingestion domain {domain} requires a schema")
            schema = self._load_schema(domain)
            if schema.get("domain") != domain:
                raise ValueError(f"supplier schema domain mismatch for {domain}")

    @property
    def domains(self) -> tuple[str, ...]:
        return tuple(sorted(self.manifest["domains"]))

    def _load_schema(self, domain: str) -> dict[str, Any]:
        if domain not in self.manifest.get("domains", {}):
            raise ValueError(f"unknown supplier response domain: {domain}")
        entry = self.manifest["domains"][domain]
        schema = load_yaml(self._repo_path(entry["schema"]))
        required_keys = (
            "schema_version",
            "domain",
            "required_sections",
            "required_fields",
            "source_documents_path",
            "attestation_paths",
            "contradiction_rules",
        )
        for key in required_keys:
            if key not in schema:
                raise ValueError(f"supplier schema {domain} is missing {key}")
        if schema["schema_version"] != 1:
            raise ValueError(f"supplier schema {domain} has unsupported schema_version")
        for rule in schema["contradiction_rules"]:
            required = {"id", "field", "operator", "expected", "requirement_class", "fallback", "basis"}
            if not isinstance(rule, dict) or not required.issubset(rule):
                raise ValueError(f"supplier schema {domain} has an incomplete contradiction rule")
            basis = rule["basis"]
            if not isinstance(basis, str) or "#" not in basis:
                raise ValueError(f"supplier schema {domain} rule {rule['id']} requires a file#field basis")
            basis_file, basis_field = basis.split("#", 1)
            authoritative_value = _value_at(load_yaml(self._repo_path(basis_file)), basis_field)
            if authoritative_value is MISSING:
                raise ValueError(f"supplier schema {domain} rule {rule['id']} basis field is missing")
            if authoritative_value != rule["expected"]:
                raise ValueError(
                    f"supplier schema {domain} rule {rule['id']} expected value is stale: "
                    f"{rule['expected']!r} != {authoritative_value!r}"
                )
            effect = rule.get("configuration_effect")
            if effect is not None:
                if not isinstance(effect, dict) or not {"authority", "value_policy"}.issubset(effect):
                    raise ValueError(f"supplier schema {domain} rule {rule['id']} has an incomplete configuration effect")
                if effect["value_policy"] not in {"supplier_value", "fixed_value"}:
                    raise ValueError(f"supplier schema {domain} rule {rule['id']} has an unsupported value policy")
                if effect["value_policy"] == "fixed_value" and "value" not in effect:
                    raise ValueError(f"supplier schema {domain} rule {rule['id']} fixed-value effect requires value")
                for bound in ("minimum", "maximum"):
                    if bound in effect and not isinstance(effect[bound], (int, float)):
                        raise ValueError(f"supplier schema {domain} rule {rule['id']} {bound} must be numeric")
        return schema

    def validate_response(self, response_path: Path, domain: str) -> ResponseReview:
        schema = self._load_schema(domain)
        document = load_yaml(response_path)
        schema_errors: list[str] = []

        for section in schema["required_sections"]:
            if not isinstance(document.get(section), dict) and not (
                section == "comments" and isinstance(document.get(section), list)
            ):
                schema_errors.append(f"required section {section} is missing or has the wrong type")

        for path in schema["required_fields"]:
            if _value_at(document, path) is MISSING:
                schema_errors.append(f"required field is absent: {path}")

        for path, expected in schema.get("constants", {}).items():
            actual = _value_at(document, path)
            if actual is MISSING:
                schema_errors.append(f"constant field is absent: {path}")
            elif actual != expected:
                schema_errors.append(f"{path} must be {expected!r}, got {actual!r}")

        missing_fields = tuple(
            path for path in schema["required_fields"] if not _answered(_value_at(document, path))
        )
        total = len(schema["required_fields"])
        completeness = round(100.0 * (total - len(missing_fields)) / total, 1) if total else 100.0

        provenance_issues: list[str] = []
        source_documents = _value_at(document, schema["source_documents_path"])
        if not isinstance(source_documents, list) or not source_documents:
            provenance_issues.append(f"no source documents at {schema['source_documents_path']}")
        for path in schema["attestation_paths"]:
            if _value_at(document, path) is not True:
                provenance_issues.append(f"positive supplier attestation required at {path}")

        contradictions: list[dict[str, Any]] = []
        for rule in schema["contradiction_rules"]:
            actual = _value_at(document, rule["field"])
            if not _answered(actual):
                continue
            expected = rule["expected"]
            tolerance = rule.get("tolerance", 0)
            try:
                if rule["operator"] == "at_least":
                    contradicted = actual < expected
                elif rule["operator"] == "at_most":
                    contradicted = actual > expected
                elif rule["operator"] == "equal":
                    contradicted = abs(actual - expected) > tolerance if all(
                        isinstance(value, (int, float)) for value in (actual, expected)
                    ) else actual != expected
                else:
                    schema_errors.append(f"unsupported contradiction operator: {rule['operator']}")
                    continue
            except TypeError:
                schema_errors.append(f"{rule['field']} has an incompatible value for {rule['operator']}")
                continue
            if contradicted:
                contradictions.append(
                    {
                        "rule_id": rule["id"],
                        "field": rule["field"],
                        "actual": actual,
                        "operator": rule["operator"],
                        "expected": expected,
                        "requirement_class": rule["requirement_class"],
                        "basis": rule.get("basis"),
                        "approved_fallback_or_action": rule["fallback"],
                    }
                )

        threshold = float(self.manifest["review_policy"]["ready_requires_completeness_percent"])
        if schema_errors:
            disposition = "REJECTED_SCHEMA"
        elif provenance_issues:
            disposition = "NEEDS_PROVENANCE_REVIEW"
        elif contradictions:
            disposition = "CONTRADICTION_REVIEW_REQUIRED"
        elif completeness < threshold:
            disposition = "INCOMPLETE_RESPONSE"
        else:
            disposition = "READY_FOR_ENGINEERING_REVIEW"

        return ResponseReview(
            domain=domain,
            linked_evidence_package=self.manifest["domains"][domain]["linked_evidence_package"],
            schema_errors=tuple(schema_errors),
            completeness_percent=completeness,
            missing_fields=missing_fields,
            provenance_issues=tuple(provenance_issues),
            contradictions=tuple(contradictions),
            disposition=disposition,
        )

    def ingest(self, response_path: Path, domain: str, received_at: str, received_by: str) -> tuple[Path, ResponseReview]:
        source = response_path.resolve()
        if source.suffix.lower() not in {".yaml", ".yml"}:
            raise ValueError("supplier response must be a YAML file")
        if not source.is_file():
            raise ValueError(f"supplier response does not exist: {source}")
        if not received_by.strip():
            raise ValueError("received_by must not be empty")
        try:
            datetime.fromisoformat(received_at.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("received_at must be an ISO-8601 timestamp") from exc

        review = self.validate_response(source, domain)
        if review.schema_errors and self.manifest["review_policy"]["schema_errors_reject_ingestion"]:
            raise ValueError("response rejected by schema: " + "; ".join(review.schema_errors))

        digest = _sha256(source)
        raw_root = self._repo_path(self.manifest["storage"]["raw_root"])
        receipt_root = self._repo_path(self.manifest["storage"]["receipt_root"])
        raw_path = raw_root / domain / f"{digest[:12]}-{_safe_name(source.name)}"
        receipt_path = receipt_root / f"{digest}.yaml"
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        receipt_root.mkdir(parents=True, exist_ok=True)

        source_bytes = source.read_bytes()
        if raw_path.exists() and raw_path.read_bytes() != source_bytes:
            raise ValueError(f"raw response collision at {raw_path}")
        if not raw_path.exists():
            raw_path.write_bytes(source_bytes)

        receipt = {
            "receipt_version": 1,
            "domain": domain,
            "sha256": digest,
            "raw_path": raw_path.relative_to(self.repo_root).as_posix(),
            "original_filename": source.name,
            "received_at": received_at,
            "received_by": received_by,
            "review": review.to_dict(),
            "authority_boundary": "ingested_not_verified_not_selected",
        }
        serialized = dump_yaml(receipt)
        if receipt_path.exists() and receipt_path.read_text(encoding="utf-8") != serialized:
            raise ValueError(f"receipt already exists with different provenance: {receipt_path}")
        receipt_path.write_text(serialized, encoding="utf-8")
        return receipt_path, review

    def build_review_queue(self) -> dict[str, Any]:
        receipt_root = self._repo_path(self.manifest["storage"]["receipt_root"])
        items: list[dict[str, Any]] = []
        receipt_paths = sorted(receipt_root.glob("*.yaml")) if receipt_root.exists() else []
        for receipt_path in receipt_paths:
            receipt = load_yaml(receipt_path)
            item: dict[str, Any] = {
                "receipt": receipt_path.relative_to(self.repo_root).as_posix(),
                "domain": receipt.get("domain"),
                "sha256": receipt.get("sha256"),
                "raw_path": receipt.get("raw_path"),
            }
            integrity_errors: list[str] = []
            try:
                raw_path = self._repo_path(receipt["raw_path"])
                if not raw_path.is_file():
                    integrity_errors.append("raw response is missing")
                elif _sha256(raw_path) != receipt.get("sha256"):
                    integrity_errors.append("raw response hash does not match receipt")
                elif receipt.get("domain") not in self.domains:
                    integrity_errors.append("receipt domain is unknown")
                else:
                    item["review"] = self.validate_response(raw_path, receipt["domain"]).to_dict()
            except (KeyError, TypeError, ValueError) as exc:
                integrity_errors.append(str(exc))
            item["integrity_errors"] = integrity_errors
            if integrity_errors:
                item["disposition"] = "REJECTED_INTEGRITY"
            else:
                item["disposition"] = item["review"]["disposition"]
            items.append(item)

        disposition_counts: dict[str, int] = {}
        for item in items:
            disposition_counts[item["disposition"]] = disposition_counts.get(item["disposition"], 0) + 1
        if not items:
            gate = "EMPTY_INBOX"
        elif any(item["disposition"].startswith("REJECTED") for item in items):
            gate = "BLOCKED_BY_INVALID_RESPONSE"
        elif all(item["disposition"] == "READY_FOR_ENGINEERING_REVIEW" for item in items):
            gate = "ENGINEERING_REVIEW_READY"
        else:
            gate = "REVIEW_QUEUE_OPEN"

        return {
            "SUPPLIER_RESPONSE_GATE": gate,
            "baseline_profile": self.manifest["metadata"]["baseline_profile"],
            "summary": {"receipt_count": len(items), "disposition_counts": dict(sorted(disposition_counts.items()))},
            "items": items,
            "next_actions": [
                "Ingest only authorized supplier-authored YAML responses with explicit receipt metadata.",
                "Resolve schema, provenance, completeness, and contradiction findings before configuration review.",
                "Use the configuration resolver for any authoritative selection or approved fallback change.",
            ],
            "caveat": "Ingestion and review do not verify supplier claims, select components, or promote evidence status.",
        }

    def generate_review_queue(self) -> Path:
        destination = self._repo_path(self.manifest["storage"]["review_report"])
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(dump_yaml(self.build_review_queue()), encoding="utf-8")
        return destination

