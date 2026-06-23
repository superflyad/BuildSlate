#!/usr/bin/env python3
"""Validate the Slate Pocket CAD-envelope volume registry."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = REPO_ROOT / "engineering" / "cad_envelope" / "component_volume_registry.yaml"

REQUIRED_COMPONENTS = (
    "device_envelope",
    "display_stack",
    "battery_pack",
    "main_pcb",
    "soc_package",
    "memory_package",
    "storage_package",
    "thermal_module",
    "rear_lateral_camera_system",
    "front_camera",
    "speaker_modules",
    "antenna_windows",
    "wireless_charging_coil",
    "structural_frame_allowance",
    "adhesive_gasket_fastener_allowance",
)
REQUIRED_FIELDS = ("length_mm", "width_mm", "height_mm", "count", "confidence", "notes")
ALLOWED_CONFIDENCE = {"placeholder", "estimate", "supplier", "measured"}


def load_registry(path: Path = REGISTRY_PATH) -> dict[str, Any]:
    if not path.exists():
        raise ValueError(f"file does not exist: {path.relative_to(REPO_ROOT)}")
    with path.open("r", encoding="utf-8") as registry_file:
        registry = yaml.safe_load(registry_file)
    if not isinstance(registry, dict):
        raise ValueError("registry root must be a mapping/object")
    return registry


def require_positive_number(entry: dict[str, Any], component: str, field: str) -> None:
    value = entry[field]
    if not isinstance(value, (int, float)) or value <= 0:
        raise ValueError(f"components.{component}.{field} must be a positive number")


def validate_component(name: str, entry: Any) -> None:
    if not isinstance(entry, dict):
        raise ValueError(f"components.{name} must be a mapping/object")
    missing = [field for field in REQUIRED_FIELDS if field not in entry]
    if missing:
        raise ValueError(f"components.{name} missing required fields: {', '.join(missing)}")

    for field in ("length_mm", "width_mm", "height_mm"):
        require_positive_number(entry, name, field)

    count = entry["count"]
    if not isinstance(count, int) or count <= 0:
        raise ValueError(f"components.{name}.count must be a positive integer")

    confidence = entry["confidence"]
    if confidence not in ALLOWED_CONFIDENCE:
        allowed = ", ".join(sorted(ALLOWED_CONFIDENCE))
        raise ValueError(f"components.{name}.confidence must be one of: {allowed}")

    notes = entry["notes"]
    if not isinstance(notes, str) or not notes.strip():
        raise ValueError(f"components.{name}.notes must be a non-empty string")


def validate_registry(registry: dict[str, Any]) -> None:
    factor = registry.get("internal_usable_volume_factor")
    if not isinstance(factor, (int, float)) or not 0.3 <= factor <= 0.95:
        raise ValueError("internal_usable_volume_factor must exist and be between 0.3 and 0.95")

    components = registry.get("components")
    if not isinstance(components, dict):
        raise ValueError("components must be a mapping/object")

    missing_components = [name for name in REQUIRED_COMPONENTS if name not in components]
    if missing_components:
        raise ValueError(f"missing required components: {', '.join(missing_components)}")

    for name in REQUIRED_COMPONENTS:
        validate_component(name, components[name])


def main() -> int:
    try:
        registry = load_registry()
        validate_registry(registry)
    except Exception as exc:  # noqa: BLE001 - top-level CLI reports validation failures clearly.
        print(f"FAIL: CAD envelope volume registry validation failed: {exc}")
        return 1

    print(f"Validated CAD envelope volume components: {len(REQUIRED_COMPONENTS)}")
    print("PASS: engineering/cad_envelope/component_volume_registry.yaml")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
