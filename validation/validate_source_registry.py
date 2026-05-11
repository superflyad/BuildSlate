#!/usr/bin/env python3
"""Validate the source confidence registry structure."""

from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError as exc:  # pragma: no cover - dependency guidance path
    raise SystemExit("PyYAML is required. Install dependencies with: pip install -r requirements.txt") from exc

REPO_ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = REPO_ROOT / "engineering" / "assumptions" / "source_registry.yaml"
REQUIRED_FIELDS = ("id", "category", "description", "applies_to", "confidence", "notes")
ALLOWED_CATEGORIES = {
    "measured_fact",
    "industry_reference",
    "modeled_estimate",
    "conceptual_extrapolation",
    "unresolved_research_blocker",
}
ALLOWED_CONFIDENCE = {"low", "medium", "high"}


def load_registry(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise ValueError(f"file does not exist: {path.relative_to(REPO_ROOT)}")
    with path.open("r", encoding="utf-8") as registry_file:
        data = yaml.safe_load(registry_file)
    if not isinstance(data, dict):
        raise ValueError("registry root must be a mapping/object")
    return data


def validate_entry(entry: Any, index: int) -> None:
    if not isinstance(entry, dict):
        raise ValueError(f"entries[{index}] must be a mapping/object")
    missing = [field for field in REQUIRED_FIELDS if field not in entry]
    if missing:
        raise ValueError(f"entries[{index}] missing required fields: {', '.join(missing)}")
    if entry["category"] not in ALLOWED_CATEGORIES:
        allowed = ", ".join(sorted(ALLOWED_CATEGORIES))
        raise ValueError(f"entries[{index}].category must be one of: {allowed}")
    if entry["confidence"] not in ALLOWED_CONFIDENCE:
        allowed = ", ".join(sorted(ALLOWED_CONFIDENCE))
        raise ValueError(f"entries[{index}].confidence must be one of: {allowed}")
    for field in ("id", "category", "description", "confidence", "notes"):
        if not isinstance(entry[field], str) or not entry[field].strip():
            raise ValueError(f"entries[{index}].{field} must be a non-empty string")
    if not isinstance(entry["applies_to"], list) or not entry["applies_to"]:
        raise ValueError(f"entries[{index}].applies_to must be a non-empty list")


def validate_registry(registry: dict[str, Any]) -> None:
    entries = registry.get("entries")
    if not isinstance(entries, list) or not entries:
        raise ValueError("entries list exists and must be non-empty")
    seen_ids = set()
    for index, entry in enumerate(entries):
        validate_entry(entry, index)
        entry_id = entry["id"]
        if entry_id in seen_ids:
            raise ValueError(f"duplicate entry id: {entry_id}")
        seen_ids.add(entry_id)


def main() -> int:
    try:
        registry = load_registry(REGISTRY_PATH)
        validate_registry(registry)
    except Exception as exc:  # noqa: BLE001 - top-level CLI should report validation errors clearly.
        print(f"FAIL: source registry validation failed: {exc}")
        return 1

    print("PASS: engineering/assumptions/source_registry.yaml")
    print("All source registry validations passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
