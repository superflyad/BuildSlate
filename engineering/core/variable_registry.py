#!/usr/bin/env python3
"""Variable registry lookup APIs for centralized engineering calculations."""

from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    from registry_loader import VARIABLES_PATH, index_by_id, load_yaml_list
except ImportError:  # pragma: no cover - package import path
    from engineering.core.registry_loader import VARIABLES_PATH, index_by_id, load_yaml_list


class VariableRegistry:
    """Load variables.yaml and expose variable lookup helpers."""

    def __init__(self, path: Path = VARIABLES_PATH) -> None:
        self.path = path
        self.variables = index_by_id(load_yaml_list(path), path)

    def get(self, variable_id: str) -> dict[str, Any]:
        try:
            return self.variables[variable_id]
        except KeyError as exc:
            raise KeyError(f"unknown variable: {variable_id}") from exc

    def has(self, variable_id: str) -> bool:
        return variable_id in self.variables

    def default_value(self, variable_id: str) -> Any:
        return self.get(variable_id).get("default_value")

    def units(self, variable_id: str) -> str | None:
        units = self.get(variable_id).get("units")
        return units if isinstance(units, str) else None

    def all(self) -> list[dict[str, Any]]:
        return list(self.variables.values())

    def by_category(self, category: str) -> list[dict[str, Any]]:
        return [variable for variable in self.variables.values() if variable.get("category") == category]
