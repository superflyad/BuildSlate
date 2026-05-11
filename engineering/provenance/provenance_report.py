#!/usr/bin/env python3
"""Print a readable summary of engineering constants provenance."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
PROVENANCE_PATH = REPO_ROOT / "engineering" / "provenance" / "constants_provenance.yaml"
HIGH_RISK_IDS = (
    "slate_512gb_memory_target",
    "slate_100tops_npu_target",
    "slate_8_8mm_thickness_target",
    "slate_250g_mass_target",
    "passive_sustained_power_pocket_w",
)


def load_entries() -> list[dict[str, Any]]:
    with PROVENANCE_PATH.open("r", encoding="utf-8") as provenance_file:
        registry = yaml.safe_load(provenance_file)
    entries = registry.get("entries", []) if isinstance(registry, dict) else []
    if not isinstance(entries, list):
        return []
    return entries


def print_counter(title: str, counter: Counter[str]) -> None:
    print(title)
    for key in sorted(counter):
        print(f"  - {key}: {counter[key]}")


def print_entry_list(title: str, entries: list[dict[str, Any]]) -> None:
    print(title)
    if not entries:
        print("  - none")
        return
    for entry in entries:
        print(f"  - {entry['id']} ({entry['confidence']}): {entry['name']}")


def main() -> int:
    entries = load_entries()
    by_category = Counter(entry.get("category", "unknown") for entry in entries)
    by_confidence = Counter(entry.get("confidence", "unknown") for entry in entries)
    needing_citation = [
        entry
        for entry in entries
        if "needs" in str(entry.get("source_notes", {}).get("citation_status", "")).lower()
    ]
    conceptual = [entry for entry in entries if entry.get("category") == "conceptual_extrapolation"]
    blockers = [entry for entry in entries if entry.get("category") == "unresolved_research_blocker"]
    entries_by_id = {entry.get("id"): entry for entry in entries}

    print("BuildSlate constants provenance report")
    print(f"Total entries: {len(entries)}")
    print_counter("Counts by category:", by_category)
    print_counter("Counts by confidence:", by_confidence)
    print_entry_list("Entries needing citation:", needing_citation)
    print_entry_list("Conceptual extrapolations:", conceptual)
    print_entry_list("Unresolved research blockers:", blockers)

    print("Top high-risk assumptions:")
    for entry_id in HIGH_RISK_IDS:
        entry = entries_by_id.get(entry_id)
        if entry is None:
            print(f"  - MISSING: {entry_id}")
            continue
        print(f"  - {entry['id']} [{entry['category']}, {entry['confidence']}]")
        print(f"    value_or_range: {entry['value_or_range']} {entry['units']}")
        print(f"    limitation: {entry['limitations']}")
        print(f"    future_validation: {entry['future_validation']}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
