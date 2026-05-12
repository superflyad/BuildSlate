#!/usr/bin/env python3
"""Validate centralized calculation registries and formula safety."""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from engineering.core.registry_loader import FORMULAS_PATH, UNITS_PATH, VARIABLES_PATH, load_yaml_list  # noqa: E402

REQUIRED_VARIABLE_FIELDS = {
    "id",
    "name",
    "units",
    "category",
    "description",
    "source_type",
    "default_value",
    "confidence",
    "depends_on",
    "used_by",
}
REQUIRED_FORMULA_FIELDS = {
    "id",
    "output",
    "formula",
    "inputs",
    "units",
    "description",
    "limitations",
    "confidence",
}
IDENTIFIER_RE = re.compile(r"\b[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*\b")
ALLOWED_FORMULA_CHARS_RE = re.compile(r"^[A-Za-z0-9_./*+\-()\s]+$")
UNSAFE_TOKEN_PATTERNS = ("//", "**", "%", "=", "[", "]", "{", "}", ":", ";", ",", "'", '"', "`", "\\")


class ValidationError(ValueError):
    """Raised when a registry invariant is violated."""


def require_registry_files() -> None:
    for path in (VARIABLES_PATH, FORMULAS_PATH, UNITS_PATH):
        if not path.exists():
            raise ValidationError(f"required registry file missing: {path.relative_to(REPO_ROOT)}")


def require_unique_ids(entries: list[dict[str, Any]], label: str) -> None:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for entry in entries:
        entry_id = entry.get("id")
        if not isinstance(entry_id, str) or not entry_id.strip():
            raise ValidationError(f"{label} entry missing non-empty id: {entry!r}")
        if entry_id in seen:
            duplicates.add(entry_id)
        seen.add(entry_id)
    if duplicates:
        raise ValidationError(f"duplicate {label} ids: {sorted(duplicates)}")


def require_fields(entries: list[dict[str, Any]], required_fields: set[str], label: str) -> None:
    for entry in entries:
        missing = sorted(required_fields - set(entry))
        if missing:
            raise ValidationError(f"{label} {entry.get('id', '<missing id>')} missing fields: {missing}")


def require_list_field(entry: dict[str, Any], field: str, label: str) -> list[Any]:
    value = entry.get(field)
    if not isinstance(value, list):
        raise ValidationError(f"{label} {entry.get('id')} field {field!r} must be a list")
    return value


def extract_formula_references(expression: str) -> set[str]:
    return set(IDENTIFIER_RE.findall(expression))


def substitute_references(expression: str, references: set[str]) -> str:
    substituted = expression
    for index, variable_id in enumerate(sorted(references, key=len, reverse=True)):
        substituted = re.sub(rf"(?<![A-Za-z0-9_.]){re.escape(variable_id)}(?![A-Za-z0-9_.])", f"v{index}", substituted)
    return substituted


def lint_formula_expression(formula: dict[str, Any], variable_ids: set[str]) -> None:
    formula_id = formula["id"]
    expression = formula.get("formula")
    if not isinstance(expression, str) or not expression.strip():
        raise ValidationError(f"formula {formula_id} formula must be a non-empty string")
    if not ALLOWED_FORMULA_CHARS_RE.fullmatch(expression):
        raise ValidationError(f"formula {formula_id} contains unsupported characters")
    unsafe = [pattern for pattern in UNSAFE_TOKEN_PATTERNS if pattern in expression]
    if unsafe:
        raise ValidationError(f"formula {formula_id} contains unsafe token(s): {unsafe}")

    references = extract_formula_references(expression)
    inputs = set(require_list_field(formula, "inputs", "formula"))
    undeclared_references = references - inputs
    unused_inputs = inputs - references
    if undeclared_references:
        raise ValidationError(f"formula {formula_id} references undeclared inputs: {sorted(undeclared_references)}")
    if unused_inputs:
        raise ValidationError(f"formula {formula_id} declares unused inputs: {sorted(unused_inputs)}")
    unknown_references = references - variable_ids
    if unknown_references:
        raise ValidationError(f"formula {formula_id} references unknown variables: {sorted(unknown_references)}")

    python_expression = substitute_references(expression, references)
    try:
        parsed = ast.parse(python_expression, mode="eval")
    except SyntaxError as exc:
        raise ValidationError(f"formula {formula_id} is not valid arithmetic: {exc}") from exc

    allowed_nodes = (
        ast.Expression,
        ast.BinOp,
        ast.UnaryOp,
        ast.Add,
        ast.Sub,
        ast.Mult,
        ast.Div,
        ast.UAdd,
        ast.USub,
        ast.Load,
        ast.Name,
        ast.Constant,
    )
    for node in ast.walk(parsed):
        if not isinstance(node, allowed_nodes):
            raise ValidationError(f"formula {formula_id} contains unsupported expression element: {type(node).__name__}")
        if isinstance(node, ast.Constant) and not isinstance(node.value, (int, float)):
            raise ValidationError(f"formula {formula_id} contains non-numeric constant: {node.value!r}")


def require_registry_references(
    variables: list[dict[str, Any]], formulas: list[dict[str, Any]], units: list[dict[str, Any]]
) -> None:
    variable_ids = {variable["id"] for variable in variables}
    unit_ids = {unit["id"] for unit in units}

    for variable in variables:
        if variable.get("units") not in unit_ids:
            raise ValidationError(f"variable {variable['id']} references unknown unit: {variable.get('units')}")
        for field in ("depends_on", "used_by"):
            for referenced_id in require_list_field(variable, field, "variable"):
                if referenced_id not in variable_ids:
                    raise ValidationError(f"variable {variable['id']} {field} references unknown variable: {referenced_id}")

    for formula in formulas:
        if formula.get("output") not in variable_ids:
            raise ValidationError(f"formula {formula['id']} output references unknown variable: {formula.get('output')}")
        if formula.get("units") not in unit_ids:
            raise ValidationError(f"formula {formula['id']} references unknown unit: {formula.get('units')}")
        for input_id in require_list_field(formula, "inputs", "formula"):
            if input_id not in variable_ids:
                raise ValidationError(f"formula {formula['id']} input references unknown variable: {input_id}")
        lint_formula_expression(formula, variable_ids)


def require_acyclic_dependency_graph(variables: list[dict[str, Any]], formulas: list[dict[str, Any]]) -> None:
    variable_edges: dict[str, list[str]] = {variable["id"]: list(variable.get("depends_on", [])) for variable in variables}
    formula_edges: dict[str, list[str]] = {formula["output"]: list(formula.get("inputs", [])) for formula in formulas}
    graph: dict[str, list[str]] = {**variable_edges, **formula_edges}
    visiting: set[str] = set()
    visited: set[str] = set()
    stack: list[str] = []

    def visit(node: str) -> None:
        if node in visiting:
            cycle_start = stack.index(node) if node in stack else 0
            cycle = " -> ".join([*stack[cycle_start:], node])
            raise ValidationError(f"dependency cycle detected: {cycle}")
        if node in visited:
            return
        visiting.add(node)
        stack.append(node)
        for dependency in graph.get(node, []):
            visit(dependency)
        stack.pop()
        visiting.remove(node)
        visited.add(node)

    for variable_id in graph:
        visit(variable_id)


def main() -> int:
    require_registry_files()
    variables = load_yaml_list(VARIABLES_PATH)
    formulas = load_yaml_list(FORMULAS_PATH)
    units = load_yaml_list(UNITS_PATH)

    require_unique_ids(variables, "variable")
    require_unique_ids(formulas, "formula")
    require_unique_ids(units, "unit")
    require_fields(variables, REQUIRED_VARIABLE_FIELDS, "variable")
    require_fields(formulas, REQUIRED_FORMULA_FIELDS, "formula")
    require_registry_references(variables, formulas, units)
    require_acyclic_dependency_graph(variables, formulas)

    print("All calculation registry validations passed.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001 - validation CLI should report actionable failures.
        print(f"FAIL: {exc}")
        raise SystemExit(1) from exc
