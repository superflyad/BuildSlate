#!/usr/bin/env python3
"""Formula registry lookup APIs for centralized engineering calculations."""

from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    from registry_loader import FORMULAS_PATH, index_by_id, load_yaml_list
except ImportError:  # pragma: no cover - package import path
    from engineering.core.registry_loader import FORMULAS_PATH, index_by_id, load_yaml_list


class FormulaRegistry:
    """Load formulas.yaml and expose formula lookup helpers."""

    def __init__(self, path: Path = FORMULAS_PATH) -> None:
        self.path = path
        self.formulas = index_by_id(load_yaml_list(path), path)
        self.formulas_by_output = self._index_by_output()

    def _index_by_output(self) -> dict[str, dict[str, Any]]:
        indexed: dict[str, dict[str, Any]] = {}
        for formula in self.formulas.values():
            output = formula.get("output")
            if not isinstance(output, str) or not output.strip():
                raise ValueError(f"{self.path} formula {formula.get('id')} is missing output")
            if output in indexed:
                raise ValueError(f"{self.path} contains multiple formulas for output: {output}")
            indexed[output] = formula
        return indexed

    def get(self, formula_id: str) -> dict[str, Any]:
        try:
            return self.formulas[formula_id]
        except KeyError as exc:
            raise KeyError(f"unknown formula: {formula_id}") from exc

    def get_for_output(self, variable_id: str) -> dict[str, Any] | None:
        return self.formulas_by_output.get(variable_id)

    def all(self) -> list[dict[str, Any]]:
        return list(self.formulas.values())
