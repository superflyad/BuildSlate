"""Phase 2 integration-contract and cross-domain consistency checks."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .configuration import MISSING, value_at
from .io import dump_yaml, load_yaml


class IntegrationContractRepository:
    def __init__(self, repo_root: Path, manifest_path: str = "engineering/program/integration_contracts.yaml") -> None:
        self.repo_root = repo_root.resolve()
        self.manifest_path = self._repo_path(manifest_path)
        self.manifest = load_yaml(self.manifest_path)
        self._documents: dict[str, dict[str, Any]] = {}
        self._validate_manifest()

    def _repo_path(self, value: str | Path) -> Path:
        path = Path(value)
        candidate = path.resolve() if path.is_absolute() else (self.repo_root / path).resolve()
        try:
            candidate.relative_to(self.repo_root)
        except ValueError as exc:
            raise ValueError(f"path escapes repository: {value}") from exc
        return candidate

    def _document(self, relative_path: str) -> dict[str, Any]:
        if relative_path not in self._documents:
            self._documents[relative_path] = load_yaml(self._repo_path(relative_path))
        return self._documents[relative_path]

    def _reference(self, reference: str) -> Any:
        if "#" not in reference:
            raise ValueError(f"contract reference must use file#field syntax: {reference}")
        path, field = reference.split("#", 1)
        value = value_at(self._document(path), field)
        if value is MISSING:
            raise ValueError(f"contract reference field is missing: {reference}")
        return value

    def _validate_manifest(self) -> None:
        if self.manifest.get("metadata", {}).get("schema_version") != 1:
            raise ValueError("integration contracts require schema_version 1")
        domains = self.manifest.get("domains")
        checks = self.manifest.get("checks")
        if not isinstance(domains, dict) or set(domains) != {"mechanical", "ecad", "power", "thermal", "rf", "firmware", "manufacturing"}:
            raise ValueError("integration contracts must cover all seven Phase 2 domains")
        if not isinstance(checks, list) or not checks:
            raise ValueError("integration contracts require checks")
        for domain, contract in domains.items():
            if not isinstance(contract, dict) or not contract.get("status"):
                raise ValueError(f"integration contract {domain} requires status")
            for field in ("inputs", "outputs"):
                if not isinstance(contract.get(field), list) or not contract[field]:
                    raise ValueError(f"integration contract {domain} requires {field}")
                for path in contract[field]:
                    if not self._repo_path(path).is_file():
                        raise ValueError(f"integration contract {domain} missing artifact: {path}")
        identifiers = [check.get("id") for check in checks if isinstance(check, dict)]
        if len(identifiers) != len(checks) or len(set(identifiers)) != len(identifiers):
            raise ValueError("integration check identifiers must be unique")

    def evaluate(self) -> dict[str, Any]:
        results: list[dict[str, Any]] = []
        contradictions: list[dict[str, Any]] = []
        for check in self.manifest["checks"]:
            operator = check.get("operator")
            left = self._reference(check["left"])
            right: Any = None
            if operator == "equal":
                right = self._reference(check["right"])
                if "keys" in check:
                    passed = all(left.get(key) == right.get(key) for key in check["keys"])
                else:
                    passed = left == right
            elif operator == "expected":
                right = check.get("expected")
                passed = left == right
            elif operator == "subset_keys":
                right = self._reference(check["right"])
                passed = isinstance(left, list) and isinstance(right, dict) and set(left).issubset(right)
            else:
                raise ValueError(f"unsupported integration check operator: {operator}")
            result = {"id": check["id"], "operator": operator, "passed": passed, "left": check["left"], "right": check.get("right"), "left_value": left, "right_value": right}
            results.append(result)
            if not passed:
                contradictions.append(result)
        statuses = {domain: contract["status"] for domain, contract in self.manifest["domains"].items()}
        if contradictions:
            gate = "BLOCKED_CROSS_DOMAIN_CONTRADICTION"
        elif any(status != "released" for status in statuses.values()):
            gate = "CONTRACTS_CONSISTENT_NOT_RELEASED"
        else:
            gate = "CONTRACTS_RELEASED"
        return {
            "INTEGRATION_CONTRACT_GATE": gate,
            "domain_statuses": statuses,
            "check_count": len(results),
            "contradiction_count": len(contradictions),
            "checks": results,
            "contradictions": contradictions,
            "caveat": "Consistency means interfaces agree; it does not verify provisional values, release designs, or authorize a build.",
        }

    def generate(self) -> Path:
        destination = self._repo_path(self.manifest["outputs"]["report"])
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(dump_yaml(self.evaluate()), encoding="utf-8")
        return destination

