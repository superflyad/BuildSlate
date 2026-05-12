#!/usr/bin/env python3
"""Validate the engineering coverage and maturity audit registry."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = REPO_ROOT / "engineering" / "audit" / "coverage_registry.yaml"

REQUIRED_FIELDS = (
    "domain",
    "coverage_status",
    "maturity_level",
    "models",
    "data_sources",
    "key_assumptions",
    "known_gaps",
    "required_next_evidence",
    "risk_if_wrong",
    "review_priority",
)
ALLOWED_COVERAGE_STATUS = {"covered", "partial", "weak", "missing"}
ALLOWED_MATURITY_LEVEL = {"screening", "first_order", "calibrated", "validated"}
ALLOWED_REVIEW_PRIORITY = {"low", "medium", "high", "critical"}


def load_registry(path: Path = REGISTRY_PATH) -> dict[str, Any]:
    if not path.exists():
        raise ValueError(f"file does not exist: {path.relative_to(REPO_ROOT)}")
    with path.open("r", encoding="utf-8") as registry_file:
        registry = yaml.safe_load(registry_file)
    if not isinstance(registry, dict):
        raise ValueError("registry root must be a mapping/object")
    return registry


def require_non_empty_string(entry: dict[str, Any], field: str, index: int) -> None:
    if not isinstance(entry[field], str) or not entry[field].strip():
        raise ValueError(f"entries[{index}].{field} must be a non-empty string")


def require_string_list(entry: dict[str, Any], field: str, index: int) -> None:
    value = entry[field]
    if not isinstance(value, list):
        raise ValueError(f"entries[{index}].{field} must be a list")
    for item_index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            raise ValueError(f"entries[{index}].{field}[{item_index}] must be a non-empty string")


def validate_entry(entry: Any, index: int) -> None:
    if not isinstance(entry, dict):
        raise ValueError(f"entries[{index}] must be a mapping/object")

    missing = [field for field in REQUIRED_FIELDS if field not in entry]
    if missing:
        raise ValueError(f"entries[{index}] missing required fields: {', '.join(missing)}")

    for field in ("domain", "coverage_status", "maturity_level", "key_assumptions", "risk_if_wrong", "review_priority"):
        require_non_empty_string(entry, field, index)
    for field in ("models", "data_sources", "known_gaps", "required_next_evidence"):
        require_string_list(entry, field, index)

    if entry["coverage_status"] not in ALLOWED_COVERAGE_STATUS:
        allowed = ", ".join(sorted(ALLOWED_COVERAGE_STATUS))
        raise ValueError(f"entries[{index}].coverage_status must be one of: {allowed}")
    if entry["maturity_level"] not in ALLOWED_MATURITY_LEVEL:
        allowed = ", ".join(sorted(ALLOWED_MATURITY_LEVEL))
        raise ValueError(f"entries[{index}].maturity_level must be one of: {allowed}")
    if entry["review_priority"] not in ALLOWED_REVIEW_PRIORITY:
        allowed = ", ".join(sorted(ALLOWED_REVIEW_PRIORITY))
        raise ValueError(f"entries[{index}].review_priority must be one of: {allowed}")


def validate_registry(registry: dict[str, Any]) -> list[dict[str, Any]]:
    entries = registry.get("entries")
    if not isinstance(entries, list) or not entries:
        raise ValueError("top-level entries list exists and must be non-empty")

    seen_domains: set[str] = set()
    for index, entry in enumerate(entries):
        validate_entry(entry, index)
        domain = entry["domain"]
        if domain in seen_domains:
            raise ValueError(f"duplicate domain: {domain}")
        seen_domains.add(domain)
    return entries


def main() -> int:
    try:
        registry = load_registry()
        entries = validate_registry(registry)
    except Exception as exc:  # noqa: BLE001 - top-level CLI should report validation errors clearly.
        print(f"FAIL: coverage registry validation failed: {exc}")
        return 1

    print(f"Validated coverage domains: {len(entries)}")
    print("PASS: engineering/audit/coverage_registry.yaml")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
