#!/usr/bin/env python3
"""Validate engineering constants provenance registry structure."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
PROVENANCE_PATH = REPO_ROOT / "engineering" / "provenance" / "constants_provenance.yaml"

REQUIRED_FIELDS = (
    "id",
    "name",
    "value_or_range",
    "units",
    "category",
    "confidence",
    "used_by",
    "rationale",
    "limitations",
    "future_validation",
    "source_notes",
)
SOURCE_NOTE_FIELDS = ("source_type", "citation_status", "notes")
ALLOWED_CATEGORIES = {
    "measured_fact",
    "industry_reference",
    "modeled_estimate",
    "conceptual_extrapolation",
    "unresolved_research_blocker",
}
ALLOWED_CONFIDENCE = {"low", "medium", "high"}


def load_registry() -> dict[str, Any]:
    if not PROVENANCE_PATH.exists():
        raise ValueError(f"file does not exist: {PROVENANCE_PATH.relative_to(REPO_ROOT)}")
    with PROVENANCE_PATH.open("r", encoding="utf-8") as provenance_file:
        registry = yaml.safe_load(provenance_file)
    if not isinstance(registry, dict):
        raise ValueError("registry root must be a mapping/object")
    return registry


def require_non_empty_string(entry: dict[str, Any], field: str, index: int) -> None:
    if not isinstance(entry[field], str) or not entry[field].strip():
        raise ValueError(f"entries[{index}].{field} must be a non-empty string")


def validate_source_notes(source_notes: Any, index: int) -> None:
    if not isinstance(source_notes, dict):
        raise ValueError(f"entries[{index}].source_notes must be a mapping/object")
    missing = [field for field in SOURCE_NOTE_FIELDS if field not in source_notes]
    if missing:
        raise ValueError(f"entries[{index}].source_notes missing required fields: {', '.join(missing)}")
    for field in ("source_type", "citation_status"):
        if not isinstance(source_notes[field], str) or not source_notes[field].strip():
            raise ValueError(f"entries[{index}].source_notes.{field} must be a non-empty string")
    notes = source_notes["notes"]
    if not isinstance(notes, list) or not notes:
        raise ValueError(f"entries[{index}].source_notes.notes must be a non-empty list")
    for note_index, note in enumerate(notes):
        if not isinstance(note, str) or not note.strip():
            raise ValueError(
                f"entries[{index}].source_notes.notes[{note_index}] must be a non-empty string"
            )


def validate_entry(entry: Any, index: int) -> None:
    if not isinstance(entry, dict):
        raise ValueError(f"entries[{index}] must be a mapping/object")
    missing = [field for field in REQUIRED_FIELDS if field not in entry]
    if missing:
        raise ValueError(f"entries[{index}] missing required fields: {', '.join(missing)}")

    for field in ("id", "name", "units", "category", "confidence", "rationale", "limitations", "future_validation"):
        require_non_empty_string(entry, field, index)
    if entry["value_or_range"] is None or entry["value_or_range"] == "":
        raise ValueError(f"entries[{index}].value_or_range must be present")
    if entry["category"] not in ALLOWED_CATEGORIES:
        allowed = ", ".join(sorted(ALLOWED_CATEGORIES))
        raise ValueError(f"entries[{index}].category must be one of: {allowed}")
    if entry["confidence"] not in ALLOWED_CONFIDENCE:
        allowed = ", ".join(sorted(ALLOWED_CONFIDENCE))
        raise ValueError(f"entries[{index}].confidence must be one of: {allowed}")
    if not isinstance(entry["used_by"], list) or not entry["used_by"]:
        raise ValueError(f"entries[{index}].used_by must be a non-empty list")
    for used_by_index, used_by in enumerate(entry["used_by"]):
        if not isinstance(used_by, str) or not used_by.strip():
            raise ValueError(f"entries[{index}].used_by[{used_by_index}] must be a non-empty string")
    validate_source_notes(entry["source_notes"], index)


def validate_registry(registry: dict[str, Any]) -> list[dict[str, Any]]:
    entries = registry.get("entries")
    if not isinstance(entries, list) or not entries:
        raise ValueError("top-level entries list exists and must be non-empty")

    seen_ids: set[str] = set()
    for index, entry in enumerate(entries):
        validate_entry(entry, index)
        entry_id = entry["id"]
        if entry_id in seen_ids:
            raise ValueError(f"duplicate entry id: {entry_id}")
        seen_ids.add(entry_id)
    return entries


def main() -> int:
    try:
        registry = load_registry()
        entries = validate_registry(registry)
    except Exception as exc:  # noqa: BLE001 - top-level CLI should report validation errors clearly.
        print(f"FAIL: provenance validation failed: {exc}")
        return 1

    print(f"Validated entries: {len(entries)}")
    warning_count = 0
    for entry in entries:
        citation_status = entry["source_notes"]["citation_status"]
        if "needs" in citation_status.lower():
            warning_count += 1
            print(f"WARNING: {entry['id']} citation_status={citation_status}")
    print(f"Citation warnings: {warning_count}")
    print("PASS: engineering/provenance/constants_provenance.yaml")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
