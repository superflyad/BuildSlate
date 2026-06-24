#!/usr/bin/env python3
"""Slate Pocket v1 first-pass thickness stackup budget model."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


REQUIRED_COMPONENT_IDS = {
    "display_cover_glass",
    "touch_layer",
    "oled_stack",
    "frame",
    "battery",
    "pcb",
    "soc_package",
    "memory_package",
    "storage_package",
    "vapor_chamber",
    "wireless_charging_coil",
    "rear_camera_system",
    "adhesives",
    "manufacturing_tolerance_reserve",
}


@dataclass(frozen=True)
class ThicknessComponent:
    """One z-height consumer in the stackup."""

    component_id: str
    name: str
    thickness_mm: float
    rationale: str


@dataclass(frozen=True)
class ThicknessBudgetResult:
    """Calculated thickness budget status."""

    device_name: str
    device_version: str
    budget_mm: float
    total_thickness_mm: float
    remaining_margin_mm: float
    consumed_percent: float
    status: str
    components: tuple[ThicknessComponent, ...]


def _require_mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a mapping")
    return value


def _require_positive_number(value: Any, label: str) -> float:
    if not isinstance(value, int | float) or isinstance(value, bool):
        raise ValueError(f"{label} must be a number")
    parsed = float(value)
    if parsed <= 0:
        raise ValueError(f"{label} must be greater than zero")
    return parsed


def _require_non_empty_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value.strip()


def _parse_scalar(value: str) -> str | float:
    cleaned = value.strip()
    if cleaned.startswith('"') and cleaned.endswith('"'):
        return cleaned[1:-1]
    try:
        return float(cleaned)
    except ValueError:
        return cleaned


def _load_stackup_yaml(path: Path) -> dict[str, Any]:
    """Parse the intentionally small stackup registry YAML subset."""
    registry: dict[str, Any] = {}
    current_section: str | None = None
    current_component: dict[str, Any] | None = None

    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line_without_comment = raw_line.split("#", 1)[0].rstrip()
        if not line_without_comment.strip():
            continue
        stripped = line_without_comment.strip()
        indent = len(line_without_comment) - len(line_without_comment.lstrip(" "))

        if indent == 0 and stripped.endswith(":"):
            current_section = stripped[:-1]
            if current_section == "components":
                registry[current_section] = []
            else:
                registry[current_section] = {}
            current_component = None
            continue

        if current_section is None:
            raise ValueError(f"line {line_number}: expected a top-level section")

        if current_section == "device" and indent == 2 and ":" in stripped:
            key, value = stripped.split(":", 1)
            registry["device"][key.strip()] = _parse_scalar(value)
            continue

        if current_section == "components" and indent == 2 and stripped.startswith("- "):
            current_component = {}
            registry["components"].append(current_component)
            item = stripped[2:]
            if item:
                key, value = item.split(":", 1)
                current_component[key.strip()] = _parse_scalar(value)
            continue

        if current_section == "components" and indent == 4 and current_component is not None and ":" in stripped:
            key, value = stripped.split(":", 1)
            current_component[key.strip()] = _parse_scalar(value)
            continue

        raise ValueError(f"line {line_number}: unsupported stackup registry syntax")

    return registry


def load_registry(path: Path) -> dict[str, Any]:
    """Load and validate raw registry structure."""
    registry = _require_mapping(_load_stackup_yaml(path), "registry")
    validate_registry(registry)
    return registry


def validate_registry(registry: dict[str, Any]) -> None:
    """Validate the stackup registry schema and required component coverage."""
    device = _require_mapping(registry.get("device"), "device")
    _require_non_empty_string(device.get("name"), "device.name")
    _require_non_empty_string(device.get("version"), "device.version")
    _require_positive_number(device.get("thickness_budget_mm"), "device.thickness_budget_mm")
    pass_threshold = _require_positive_number(device.get("pass_threshold_percent"), "device.pass_threshold_percent")
    warning_threshold = _require_positive_number(device.get("warning_threshold_percent"), "device.warning_threshold_percent")
    if pass_threshold >= warning_threshold:
        raise ValueError("device.pass_threshold_percent must be less than device.warning_threshold_percent")

    components = registry.get("components")
    if not isinstance(components, list) or not components:
        raise ValueError("components must be a non-empty list")

    seen_ids: set[str] = set()
    for index, component in enumerate(components):
        entry = _require_mapping(component, f"components[{index}]")
        component_id = _require_non_empty_string(entry.get("id"), f"components[{index}].id")
        if component_id in seen_ids:
            raise ValueError(f"duplicate component id: {component_id}")
        seen_ids.add(component_id)
        _require_non_empty_string(entry.get("name"), f"components[{index}].name")
        _require_positive_number(entry.get("thickness_mm"), f"components[{index}].thickness_mm")
        _require_non_empty_string(entry.get("rationale"), f"components[{index}].rationale")

    missing = sorted(REQUIRED_COMPONENT_IDS - seen_ids)
    if missing:
        raise ValueError("missing required stackup components: " + ", ".join(missing))


def calculate_thickness_budget(registry: dict[str, Any]) -> ThicknessBudgetResult:
    """Calculate total thickness, remaining margin, consumption, and status."""
    validate_registry(registry)
    device = registry["device"]
    components = tuple(
        ThicknessComponent(
            component_id=component["id"],
            name=component["name"],
            thickness_mm=float(component["thickness_mm"]),
            rationale=component["rationale"],
        )
        for component in registry["components"]
    )
    budget_mm = float(device["thickness_budget_mm"])
    total_mm = sum(component.thickness_mm for component in components)
    consumed_percent = total_mm / budget_mm * 100.0
    if consumed_percent <= float(device["pass_threshold_percent"]):
        status = "PASS"
    elif consumed_percent <= float(device["warning_threshold_percent"]):
        status = "WARNING"
    else:
        status = "FAIL"

    return ThicknessBudgetResult(
        device_name=device["name"],
        device_version=device["version"],
        budget_mm=budget_mm,
        total_thickness_mm=total_mm,
        remaining_margin_mm=budget_mm - total_mm,
        consumed_percent=consumed_percent,
        status=status,
        components=components,
    )
