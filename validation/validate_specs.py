#!/usr/bin/env python3
"""Validate normalized and baseline Slate specifications."""

from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError as exc:  # pragma: no cover - dependency guidance path
    raise SystemExit("PyYAML is required. Install dependencies with: pip install -r requirements.txt") from exc

REPO_ROOT = Path(__file__).resolve().parents[1]
NORMALIZED_SPEC_PATH = REPO_ROOT / "specs" / "slate-pocket-v1.yaml"
BASELINE_SPEC_PATH = REPO_ROOT / "specs" / "slate-v1.yaml"

REQUIRED_TOP_LEVEL_SECTIONS = (
    "identity",
    "display",
    "compute",
    "memory",
    "storage",
    "battery",
    "thermal",
    "camera",
    "wireless",
    "security",
    "materials",
    "dimensions",
    "weight",
    "runtime_targets",
    "feasibility",
)

FEASIBILITY_SECTIONS = (
    "display",
    "compute",
    "memory",
    "storage",
    "battery",
    "thermal",
    "camera",
    "wireless",
    "security",
    "materials",
    "dimensions",
    "weight",
    "runtime_targets",
    "feasibility",
)

ALLOWED_FEASIBILITY_STATUSES = {
    "feasible_today",
    "near_term",
    "conceptual_extrapolation",
    "research_required",
}

BASELINE_REQUIRED_FIELDS = (
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


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as spec_file:
        data = yaml.safe_load(spec_file)
    if not isinstance(data, dict):
        raise ValueError("spec root must be a mapping/object")
    return data


def assert_numeric(value: Any, field_name: str) -> None:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError(f"{field_name} must be numeric")


def require_mapping(value: Any, field_name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{field_name} must be a mapping")
    return value


def validate_feasibility(section_name: str, section: dict[str, Any]) -> None:
    metadata = section if section_name == "feasibility" else section.get("feasibility")
    metadata = require_mapping(metadata, f"{section_name}.feasibility")

    for key in ("status", "rationale", "blockers"):
        if key not in metadata:
            raise ValueError(f"{section_name}.feasibility.{key} is required")

    status = metadata["status"]
    if status not in ALLOWED_FEASIBILITY_STATUSES:
        allowed = ", ".join(sorted(ALLOWED_FEASIBILITY_STATUSES))
        raise ValueError(f"{section_name}.feasibility.status must be one of: {allowed}")

    if not isinstance(metadata["rationale"], str) or not metadata["rationale"].strip():
        raise ValueError(f"{section_name}.feasibility.rationale must be a non-empty string")
    if not isinstance(metadata["blockers"], list):
        raise ValueError(f"{section_name}.feasibility.blockers must be a list")


def validate_normalized_spec(spec: dict[str, Any]) -> None:
    missing = [section for section in REQUIRED_TOP_LEVEL_SECTIONS if section not in spec]
    if missing:
        raise ValueError(f"missing required top-level sections: {', '.join(missing)}")

    for section_name in FEASIBILITY_SECTIONS:
        section = require_mapping(spec[section_name], section_name)
        validate_feasibility(section_name, section)

    required_paths = (
        ("identity", "product_name"),
        ("identity", "version"),
        ("identity", "device_class"),
        ("identity", "source_document"),
        ("display", "size_in"),
        ("display", "technology"),
        ("display", "resolution"),
        ("display", "refresh_rate_hz"),
        ("display", "aspect_ratio"),
        ("memory", "capacity_gb"),
        ("memory", "type"),
        ("memory", "packaging"),
        ("storage", "capacity_tb"),
        ("battery", "capacity_mah"),
        ("dimensions", "thickness_mm"),
        ("dimensions", "display_size_in"),
        ("weight", "target_g"),
    )
    for section_name, key in required_paths:
        if key not in spec[section_name]:
            raise ValueError(f"{section_name}.{key} is required")

    for path, value in (
        ("display.size_in", spec["display"]["size_in"]),
        ("display.refresh_rate_hz", spec["display"]["refresh_rate_hz"]),
        ("memory.capacity_gb", spec["memory"]["capacity_gb"]),
        ("storage.capacity_tb", spec["storage"]["capacity_tb"]),
        ("battery.capacity_mah", spec["battery"]["capacity_mah"]),
        ("dimensions.thickness_mm", spec["dimensions"]["thickness_mm"]),
        ("dimensions.display_size_in", spec["dimensions"]["display_size_in"]),
        ("weight.target_g", spec["weight"]["target_g"]),
    ):
        assert_numeric(value, path)


def validate_baseline_spec(spec: dict[str, Any]) -> None:
    missing = [field for field in BASELINE_REQUIRED_FIELDS if field not in spec]
    if missing:
        raise ValueError(f"missing baseline fields: {', '.join(missing)}")

    battery = require_mapping(spec["battery"], "battery")
    if "capacity_wh" not in battery:
        raise ValueError("battery.capacity_wh is required")
    assert_numeric(battery["capacity_wh"], "battery.capacity_wh")

    memory = require_mapping(spec["memory"], "memory")
    if "capacity_gb" not in memory:
        raise ValueError("memory.capacity_gb is required")
    assert_numeric(memory["capacity_gb"], "memory.capacity_gb")

    chassis = require_mapping(spec["chassis"], "chassis")
    dimensions = require_mapping(chassis.get("dimensions_mm"), "chassis.dimensions_mm")
    for axis in ("width", "height", "thickness"):
        if axis not in dimensions:
            raise ValueError(f"chassis.dimensions_mm.{axis} is required")
        assert_numeric(dimensions[axis], f"chassis.dimensions_mm.{axis}")


def validate_file(path: Path, normalized: bool) -> bool:
    rel_path = path.relative_to(REPO_ROOT)
    try:
        spec = load_yaml(path)
        if normalized:
            validate_normalized_spec(spec)
        else:
            validate_baseline_spec(spec)
    except Exception as exc:  # noqa: BLE001 - top-level CLI should report all validation errors clearly.
        print(f"FAIL: {rel_path}: {exc}")
        return False

    print(f"PASS: {rel_path}")
    return True


def main() -> int:
    checks = [validate_file(NORMALIZED_SPEC_PATH, normalized=True)]
    if BASELINE_SPEC_PATH.exists():
        checks.append(validate_file(BASELINE_SPEC_PATH, normalized=False))

    if all(checks):
        print("All spec validations passed.")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
