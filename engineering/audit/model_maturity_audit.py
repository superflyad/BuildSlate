#!/usr/bin/env python3
"""Summarize BuildSlate engineering coverage and model maturity."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
import sys
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from validation.validate_coverage_registry import load_registry, validate_registry  # noqa: E402


def print_counter(title: str, counter: Counter[str], order: tuple[str, ...]) -> None:
    print(title)
    for key in order:
        print(f"  {key}: {counter.get(key, 0)}")


def print_domains(title: str, entries: list[dict[str, Any]]) -> None:
    print(title)
    if not entries:
        print("  none")
        return
    for entry in entries:
        print(
            f"  - {entry['domain']} "
            f"({entry['coverage_status']}, {entry['maturity_level']}, priority={entry['review_priority']})"
        )


def main() -> int:
    try:
        registry = load_registry()
        entries = validate_registry(registry)
    except Exception as exc:  # noqa: BLE001 - CLI should return a clear validation failure.
        print(f"FAIL: model maturity audit failed: {exc}")
        return 1

    coverage_counts = Counter(entry["coverage_status"] for entry in entries)
    maturity_counts = Counter(entry["maturity_level"] for entry in entries)
    critical_high = [entry for entry in entries if entry["review_priority"] in {"critical", "high"}]
    missing_weak = [entry for entry in entries if entry["coverage_status"] in {"missing", "weak"}]
    screening = [entry for entry in entries if entry["maturity_level"] == "screening"]

    print("BuildSlate Engineering Coverage and Maturity Audit")
    print("==================================================")
    print(f"Total domains: {len(entries)}")
    print_counter("Count by coverage_status:", coverage_counts, ("covered", "partial", "weak", "missing"))
    print_counter("Count by maturity_level:", maturity_counts, ("screening", "first_order", "calibrated", "validated"))
    print_domains("Critical/high review items:", critical_high)
    print_domains("Missing/weak domains:", missing_weak)
    print_domains("Domains still at screening maturity:", screening)
    print("Top required next evidence items:")
    for entry in critical_high[:10]:
        evidence = "; ".join(entry["required_next_evidence"][:2])
        print(f"  - {entry['domain']}: {evidence}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
