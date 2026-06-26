#!/usr/bin/env python3
"""Validate BuildSlate device profile YAML files."""

from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError as exc:  # pragma: no cover - dependency guidance path
    raise SystemExit("PyYAML is required. Install dependencies with: pip install -r requirements.txt") from exc

REPO_ROOT = Path(__file__).resolve().parents[1]
PROFILE_DIR = REPO_ROOT / "configs" / "devices"

REQUIRED_TOP_LEVEL_SECTIONS = (
    "identity",
    "geometry",
    "mass_targets",
    "battery",
    "display",
    "compute",
    "memory",
    "storage",
    "thermal",
    "materials",
    "chassis_composite",
    "component_assumptions",
    "interconnect",
    "runtime",
    "manufacturing",
    "environment",
    "notes",
)

REQUIRED_FIELD_PATHS = (
    ("identity", "profile_id"),
    ("geometry", "length_mm"),
    ("geometry", "width_mm"),
    ("geometry", "thickness_mm"),
    ("battery", "capacity_mah"),
    ("battery", "nominal_voltage_v"),
    ("compute", "sustained_power_w"),
    ("memory", "capacity_gb"),
    ("storage", "capacity_tb"),
    ("thermal", "sustained_w"),
    ("runtime", "model_params_billions"),
    ("runtime", "quantization_bits"),
    ("environment", "condition"),
)

NUMERIC_FIELD_PATHS = tuple(path for path in REQUIRED_FIELD_PATHS if path not in (("identity", "profile_id"), ("environment", "condition")))

OPTIONAL_PROFILE_CLASSES = {"aggressive", "canonical", "conservative", "experimental", "recovery"}
OPTIONAL_PROFILE_TYPES = {"recovery"}
OPTIONAL_FEASIBILITY_STATUSES = {"conceptual", "research_required", "screening_candidate"}
REQUIRED_RECOVERY_FIELDS = (
    "profile_type",
    "base_profile",
    "recovery_source",
    "recovery_strategy",
    "maturity",
    "caveat",
)


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as profile_file:
        data = yaml.safe_load(profile_file)
    if not isinstance(data, dict):
        raise ValueError("profile root must be a mapping/object")
    return data


def require_mapping(profile: dict[str, Any], section_name: str) -> dict[str, Any]:
    section = profile.get(section_name)
    if not isinstance(section, dict):
        raise ValueError(f"{section_name} must be a mapping")
    return section


def get_path(profile: dict[str, Any], path: tuple[str, str]) -> Any:
    section_name, field_name = path
    section = require_mapping(profile, section_name)
    if field_name not in section:
        raise ValueError(f"{section_name}.{field_name} is required")
    return section[field_name]


def validate_optional_metadata(profile: dict[str, Any]) -> None:
    profile_class = profile.get("profile_class")
    if profile_class is not None:
        if profile_class not in OPTIONAL_PROFILE_CLASSES:
            allowed = ", ".join(sorted(OPTIONAL_PROFILE_CLASSES))
            raise ValueError(f"profile_class must be one of: {allowed}")

    feasibility_status = profile.get("feasibility_status")
    if feasibility_status is not None:
        if feasibility_status not in OPTIONAL_FEASIBILITY_STATUSES:
            allowed = ", ".join(sorted(OPTIONAL_FEASIBILITY_STATUSES))
            raise ValueError(f"feasibility_status must be one of: {allowed}")

    review_notes = profile.get("review_notes")
    if review_notes is not None:
        if not isinstance(review_notes, list):
            raise ValueError("review_notes must be a list when present")
        for index, note in enumerate(review_notes, start=1):
            if not isinstance(note, str) or not note.strip():
                raise ValueError(f"review_notes[{index}] must be a non-empty string")

    profile_type = profile.get("profile_type")
    if profile_type is not None:
        if profile_type not in OPTIONAL_PROFILE_TYPES:
            allowed = ", ".join(sorted(OPTIONAL_PROFILE_TYPES))
            raise ValueError(f"profile_type must be one of: {allowed}")

    if profile_type == "recovery":
        missing = [field for field in REQUIRED_RECOVERY_FIELDS if field not in profile]
        if missing:
            raise ValueError(f"recovery profile missing required fields: {', '.join(missing)}")
        if not isinstance(profile["recovery_strategy"], list) or not profile["recovery_strategy"]:
            raise ValueError("recovery_strategy must be a non-empty list")
        for index, strategy in enumerate(profile["recovery_strategy"], start=1):
            if not isinstance(strategy, str) or not strategy.strip():
                raise ValueError(f"recovery_strategy[{index}] must be a non-empty string")
        for field in ("base_profile", "recovery_source", "maturity", "caveat"):
            if not isinstance(profile[field], str) or not profile[field].strip():
                raise ValueError(f"{field} must be a non-empty string for recovery profiles")


def validate_profile(path: Path) -> str:
    profile = load_yaml(path)

    missing_sections = [section for section in REQUIRED_TOP_LEVEL_SECTIONS if section not in profile]
    if missing_sections:
        raise ValueError(f"missing required top-level sections: {', '.join(missing_sections)}")

    for section in REQUIRED_TOP_LEVEL_SECTIONS:
        if section == "notes":
            continue
        require_mapping(profile, section)

    for field_path in REQUIRED_FIELD_PATHS:
        value = get_path(profile, field_path)
        if value in (None, ""):
            raise ValueError(f"{'.'.join(field_path)} must be populated")

    validate_optional_metadata(profile)

    for field_path in NUMERIC_FIELD_PATHS:
        value = get_path(profile, field_path)
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ValueError(f"{'.'.join(field_path)} must be numeric")
        if value <= 0:
            raise ValueError(f"{'.'.join(field_path)} must be greater than zero")

    return str(get_path(profile, ("identity", "profile_id")))


def main() -> int:
    if not PROFILE_DIR.exists():
        print(f"FAIL: profile directory not found: {PROFILE_DIR.relative_to(REPO_ROOT)}")
        return 1

    profile_paths = sorted(PROFILE_DIR.glob("*.yaml"))
    if not profile_paths:
        print(f"FAIL: no device profiles found in {PROFILE_DIR.relative_to(REPO_ROOT)}")
        return 1

    failed = False
    for path in profile_paths:
        try:
            profile_id = validate_profile(path)
        except ValueError as exc:
            failed = True
            print(f"FAIL: {path.relative_to(REPO_ROOT)}: {exc}")
        else:
            print(f"PASS: {path.relative_to(REPO_ROOT)} ({profile_id})")

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
