#!/usr/bin/env python3
"""Compute centralized engineering variables from registry formulas."""

from __future__ import annotations

import argparse
import ast
import re
from typing import Any

try:
    from dependency_graph import DependencyGraph
    from formula_registry import FormulaRegistry
    from variable_registry import VariableRegistry
except ImportError:  # pragma: no cover - package import path
    from engineering.core.dependency_graph import DependencyGraph
    from engineering.core.formula_registry import FormulaRegistry
    from engineering.core.variable_registry import VariableRegistry

VARIABLE_TOKEN_RE = re.compile(r"\b[a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)+\b")


class CalculationError(ValueError):
    """Raised when a variable cannot be computed from known inputs."""


def parse_value(raw_value: str) -> float | str:
    """Parse CLI values as numbers when possible, otherwise preserve strings."""
    try:
        return float(raw_value)
    except ValueError:
        return raw_value


def parse_set(assignments: list[str]) -> dict[str, float | str]:
    """Parse --set variable=value assignments."""
    values: dict[str, float | str] = {}
    for assignment in assignments:
        if "=" not in assignment:
            raise argparse.ArgumentTypeError(f"expected variable=value, got: {assignment}")
        variable_id, raw_value = assignment.split("=", 1)
        if not variable_id.strip():
            raise argparse.ArgumentTypeError(f"missing variable id in assignment: {assignment}")
        values[variable_id.strip()] = parse_value(raw_value.strip())
    return values


def safe_eval(expression: str, values: dict[str, Any]) -> float:
    """Evaluate a simple arithmetic expression after variable token substitution."""
    local_values: dict[str, Any] = {}

    def replace_token(match: re.Match[str]) -> str:
        variable_id = match.group(0)
        if variable_id not in values:
            raise CalculationError(f"missing value for {variable_id}")
        safe_name = f"v{len(local_values)}"
        local_values[safe_name] = values[variable_id]
        return safe_name

    python_expression = VARIABLE_TOKEN_RE.sub(replace_token, expression)
    parsed = ast.parse(python_expression, mode="eval")
    allowed_nodes = (
        ast.Expression,
        ast.BinOp,
        ast.UnaryOp,
        ast.Add,
        ast.Sub,
        ast.Mult,
        ast.Div,
        ast.Pow,
        ast.USub,
        ast.UAdd,
        ast.Load,
        ast.Name,
        ast.Constant,
    )
    for node in ast.walk(parsed):
        if not isinstance(node, allowed_nodes):
            raise CalculationError(f"unsupported expression element: {type(node).__name__}")
    result = eval(compile(parsed, "<formula>", "eval"), {"__builtins__": {}}, local_values)
    if not isinstance(result, (int, float)) or isinstance(result, bool):
        raise CalculationError("formula result must be numeric")
    return float(result)


class Calculator:
    """Resolve formula dependencies and compute requested variables."""

    def __init__(self) -> None:
        self.variables = VariableRegistry()
        self.formulas = FormulaRegistry()
        self.graph = DependencyGraph(self.formulas)

    def compute(self, variable_id: str, known_values: dict[str, Any] | None = None) -> float:
        values = dict(known_values or {})
        return self._compute(variable_id, values, stack=[])

    def _compute(self, variable_id: str, values: dict[str, Any], stack: list[str]) -> float:
        if variable_id in values:
            return float(values[variable_id])
        if variable_id in stack:
            cycle = " -> ".join([*stack, variable_id])
            raise CalculationError(f"dependency cycle detected: {cycle}")

        formula = self.graph.get_formula(variable_id)
        if formula is None:
            default_value = self.variables.default_value(variable_id)
            if default_value is None:
                raise CalculationError(f"no formula or default value for {variable_id}")
            values[variable_id] = default_value
            return float(default_value)

        next_stack = [*stack, variable_id]
        for input_id in formula.get("inputs", []):
            if input_id not in values:
                values[input_id] = self._compute(input_id, values, next_stack)
        values[variable_id] = safe_eval(formula["formula"], values)
        return float(values[variable_id])

    def units(self, variable_id: str) -> str:
        formula = self.graph.get_formula(variable_id)
        if formula and formula.get("units"):
            return str(formula["units"])
        return self.variables.units(variable_id) or ""


def format_number(value: float) -> str:
    rounded = round(value, 6)
    if rounded.is_integer():
        return str(int(rounded))
    return f"{rounded:g}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--set", action="append", default=[], help="Known input as variable=value")
    parser.add_argument("--compute", required=True, help="Variable id to compute")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    known_values = parse_set(args.set)
    calculator = Calculator()
    value = calculator.compute(args.compute, known_values)
    units = calculator.units(args.compute)
    suffix = f" {units}" if units else ""
    print(f"{args.compute} = {format_number(value)}{suffix}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
