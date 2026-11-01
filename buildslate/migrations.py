"""Legacy artifact authority, compatibility, and migration audit."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .io import dump_yaml, load_yaml


class MigrationRegistry:
    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root.resolve()
        self.path = self.repo_root / "engineering/program/migration_registry.yaml"
        self.registry = load_yaml(self.path)

    def audit(self) -> dict[str, Any]:
        errors: list[str] = []
        artifacts = self.registry.get("artifacts", {})
        roles = set(self.registry.get("allowed_roles", []))
        states = set(self.registry.get("allowed_states", []))
        authoritative_domains: dict[str, list[str]] = {}
        items: list[dict[str, Any]] = []
        if self.registry.get("metadata", {}).get("schema_version") != 1:
            errors.append("migration registry schema_version must be 1")
        for artifact_id, entry in artifacts.items():
            path = self.repo_root / entry.get("path", "")
            replacement_text = entry.get("replacement")
            replacement = self.repo_root / replacement_text if replacement_text else None
            item_errors: list[str] = []
            if entry.get("role") not in roles:
                item_errors.append("invalid role")
            if entry.get("migration_state") not in states:
                item_errors.append("invalid migration_state")
            if not path.exists():
                item_errors.append("artifact path is missing")
            if replacement is not None and not replacement.exists():
                item_errors.append("replacement path is missing")
            if entry.get("role") == "authoritative_input":
                domain = entry.get("authority_domain")
                if not domain or domain == "none":
                    item_errors.append("authoritative input requires an authority_domain")
                else:
                    authoritative_domains.setdefault(domain, []).append(artifact_id)
            if entry.get("role") == "legacy_intake" and not entry.get("migration_command"):
                item_errors.append("legacy intake requires a migration_command")
            errors.extend(f"{artifact_id}: {error}" for error in item_errors)
            items.append(
                {
                    "id": artifact_id,
                    "path": entry.get("path"),
                    "role": entry.get("role"),
                    "authority_domain": entry.get("authority_domain"),
                    "replacement": replacement_text,
                    "migration_state": entry.get("migration_state"),
                    "preservation": entry.get("preservation"),
                    "migration_command": entry.get("migration_command"),
                    "errors": item_errors,
                }
            )
        duplicate_authority = {domain: ids for domain, ids in authoritative_domains.items() if len(ids) > 1}
        for domain, ids in duplicate_authority.items():
            errors.append(f"duplicated authority for {domain}: {', '.join(ids)}")
        return {
            "MIGRATION_GATE": "MIGRATION_MAP_VALID" if not errors else "BLOCKED_MIGRATION_MAP_ERRORS",
            "artifact_count": len(items),
            "authoritative_domains": dict(sorted(authoritative_domains.items())),
            "duplicate_authority": duplicate_authority,
            "items": items,
            "errors": errors,
            "caveat": "Migration status preserves traceability; it does not upgrade the evidence contained in any legacy artifact.",
        }

    def generate(self) -> Path:
        destination = self.repo_root / self.registry["output"]
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(dump_yaml(self.audit()), encoding="utf-8")
        return destination

    def explain(self, artifact_id: str) -> dict[str, Any]:
        result = self.audit()
        for item in result["items"]:
            if item["id"] == artifact_id:
                return item
        raise ValueError(f"unknown migration artifact: {artifact_id}")

