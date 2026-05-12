#!/usr/bin/env python3
"""Shared YAML loading utilities for the centralized calculation registry."""

from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError as exc:  # pragma: no cover - dependency guidance path
    raise SystemExit("PyYAML is required. Install dependencies with: pip install -r requirements.txt") from exc

REPO_ROOT = Path(__file__).resolve().parents[2]
REGISTRY_DIR = REPO_ROOT / "engineering" / "registry"
VARIABLES_PATH = REGISTRY_DIR / "variables.yaml"
FORMULAS_PATH = REGISTRY_DIR / "formulas.yaml"
UNITS_PATH = REGISTRY_DIR / "units.yaml"


def load_yaml_list(path: Path) -> list[dict[str, Any]]:
    """Load a YAML registry file whose root must be a list of mappings."""
    with path.open("r", encoding="utf-8") as registry_file:
        data = yaml.safe_load(registry_file)
    if data is None:
        return []
    if not isinstance(data, list):
        raise ValueError(f"{path} registry root must be a list")
    for index, item in enumerate(data):
        if not isinstance(item, dict):
            raise ValueError(f"{path} entry {index} must be a mapping")
    return data


def index_by_id(entries: list[dict[str, Any]], path: Path) -> dict[str, dict[str, Any]]:
    """Index registry entries by their required id field."""
    indexed: dict[str, dict[str, Any]] = {}
    for entry in entries:
        entry_id = entry.get("id")
        if not isinstance(entry_id, str) or not entry_id.strip():
            raise ValueError(f"{path} entry is missing a non-empty id")
        if entry_id in indexed:
            raise ValueError(f"{path} contains duplicate id: {entry_id}")
        indexed[entry_id] = entry
    return indexed
