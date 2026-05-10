#!/usr/bin/env python3
"""Validate the machine-readable Slate v1 specification."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC_PATH = REPO_ROOT / "specs" / "slate-v1.yaml"

REQUIRED_FIELDS = (
    "display",
    "chassis",
    "compute",
    "memory",
    "storage",
    "battery",
    "cooling",
    "camera",
    "security",
    "wireless",
    "operating_system",
    "feasibility_notes",
)


def load_spec(path: Path = SPEC_PATH) -> dict[str, Any]:
    # slate-v1.yaml is intentionally JSON-compatible YAML, so validation has no external dependency.
    with path.open("r", encoding="utf-8") as spec_file:
        data = json.load(spec_file)
    if not isinstance(data, dict):
        raise ValueError("spec root must be a mapping/object")
    return data


def assert_numeric(value: Any, field_name: str) -> None:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError(f"{field_name} must be numeric")


def validate_spec(spec: dict[str, Any]) -> None:
    missing = [field for field in REQUIRED_FIELDS if field not in spec]
    if missing:
        raise ValueError(f"missing required fields: {', '.join(missing)}")

    battery_wh = spec["battery"].get("capacity_wh")
    if battery_wh is None:
        raise ValueError("battery.capacity_wh is required")
    assert_numeric(battery_wh, "battery.capacity_wh")

    memory_capacity = spec["memory"].get("capacity_gb")
    assert_numeric(memory_capacity, "memory.capacity_gb")

    dimensions = spec["chassis"].get("dimensions_mm")
    if not isinstance(dimensions, dict):
        raise ValueError("chassis.dimensions_mm is required")
    for axis in ("width", "height", "thickness"):
        if axis not in dimensions:
            raise ValueError(f"chassis.dimensions_mm.{axis} is required")
        assert_numeric(dimensions[axis], f"chassis.dimensions_mm.{axis}")


def main() -> int:
    spec = load_spec()
    validate_spec(spec)
    print(f"PASS: {SPEC_PATH.relative_to(REPO_ROOT)} contains required Slate v1 fields")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
