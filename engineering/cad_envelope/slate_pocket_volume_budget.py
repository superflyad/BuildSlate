#!/usr/bin/env python3
"""First-pass Slate Pocket volume budget screening model."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = Path(__file__).with_name("component_volume_registry.yaml")

DEVICE_ENVELOPE_KEY = "device_envelope"


@dataclass(frozen=True)
class ComponentVolume:
    name: str
    length_mm: float
    width_mm: float
    height_mm: float
    count: int
    confidence: str
    notes: str

    @property
    def unit_volume_mm3(self) -> float:
        return self.length_mm * self.width_mm * self.height_mm

    @property
    def total_volume_mm3(self) -> float:
        return self.unit_volume_mm3 * self.count


def load_registry(path: Path = REGISTRY_PATH) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as registry_file:
        registry = yaml.safe_load(registry_file)
    if not isinstance(registry, dict):
        raise ValueError("volume registry root must be a mapping")
    return registry


def component_from_entry(name: str, entry: dict[str, Any]) -> ComponentVolume:
    return ComponentVolume(
        name=name,
        length_mm=float(entry["length_mm"]),
        width_mm=float(entry["width_mm"]),
        height_mm=float(entry["height_mm"]),
        count=int(entry["count"]),
        confidence=str(entry["confidence"]),
        notes=str(entry["notes"]),
    )


def calculate_volume_budget(registry: dict[str, Any]) -> dict[str, Any]:
    components_raw = registry["components"]
    components = [component_from_entry(name, entry) for name, entry in components_raw.items()]
    device = next(component for component in components if component.name == DEVICE_ENVELOPE_KEY)
    allocated_components = [component for component in components if component.name != DEVICE_ENVELOPE_KEY]

    external_volume_mm3 = device.total_volume_mm3
    usable_factor = float(registry["internal_usable_volume_factor"])
    usable_volume_mm3 = external_volume_mm3 * usable_factor
    total_allocated_mm3 = sum(component.total_volume_mm3 for component in allocated_components)
    remaining_mm3 = usable_volume_mm3 - total_allocated_mm3
    allocation_percentage = (total_allocated_mm3 / usable_volume_mm3) * 100.0

    if allocation_percentage < 70.0:
        status = "PASS"
    elif allocation_percentage <= 85.0:
        status = "WARNING"
    else:
        status = "FAIL"

    return {
        "device": device,
        "internal_usable_volume_factor": usable_factor,
        "external_volume_mm3": external_volume_mm3,
        "usable_volume_mm3": usable_volume_mm3,
        "components": allocated_components,
        "total_allocated_mm3": total_allocated_mm3,
        "remaining_mm3": remaining_mm3,
        "allocation_percentage": allocation_percentage,
        "status": status,
    }


def calculate_from_registry(path: Path = REGISTRY_PATH) -> dict[str, Any]:
    return calculate_volume_budget(load_registry(path))
