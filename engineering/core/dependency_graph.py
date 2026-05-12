#!/usr/bin/env python3
"""Dependency graph built from centralized formula definitions."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

try:
    from formula_registry import FormulaRegistry
except ImportError:  # pragma: no cover - package import path
    from engineering.core.formula_registry import FormulaRegistry


class DependencyGraph:
    """Map formula outputs to inputs and reverse dependents."""

    def __init__(self, formula_registry: FormulaRegistry | None = None) -> None:
        self.formula_registry = formula_registry or FormulaRegistry()
        self.inputs_by_output: dict[str, list[str]] = {}
        self.dependents_by_input: dict[str, list[str]] = defaultdict(list)
        self.formula_by_output: dict[str, dict[str, Any]] = {}
        self._build()

    def _build(self) -> None:
        for formula in self.formula_registry.all():
            output = formula["output"]
            inputs = list(formula.get("inputs", []))
            self.inputs_by_output[output] = inputs
            self.formula_by_output[output] = formula
            for input_id in inputs:
                self.dependents_by_input[input_id].append(output)

    def get_inputs(self, variable: str) -> list[str]:
        return list(self.inputs_by_output.get(variable, []))

    def get_dependents(self, variable: str) -> list[str]:
        return list(self.dependents_by_input.get(variable, []))

    def get_formula(self, variable: str) -> dict[str, Any] | None:
        return self.formula_by_output.get(variable)

    def resolve_dependencies(self, variable: str) -> list[str]:
        """Return transitive formula dependencies in dependency-first order."""
        resolved: list[str] = []
        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(current: str) -> None:
            if current in visiting:
                cycle = " -> ".join([*visiting, current])
                raise ValueError(f"dependency cycle detected while resolving {variable}: {cycle}")
            if current in visited:
                return
            visiting.add(current)
            for input_id in self.get_inputs(current):
                visit(input_id)
                if input_id not in resolved:
                    resolved.append(input_id)
            visiting.remove(current)
            visited.add(current)

        visit(variable)
        return resolved
