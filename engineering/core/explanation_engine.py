#!/usr/bin/env python3
"""Explain centralized engineering calculations from registry formulas."""

from __future__ import annotations

import argparse
import re
from typing import Any

try:
    from calculator import Calculator, format_number, parse_set
except ImportError:  # pragma: no cover - package import path
    from engineering.core.calculator import Calculator, format_number, parse_set

VARIABLE_TOKEN_RE = re.compile(r"\b[a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)+\b")


class ExplanationEngine:
    """Generate compact formula and substitution explanations."""

    def __init__(self) -> None:
        self.calculator = Calculator()

    def explain(self, variable_id: str, known_values: dict[str, Any] | None = None) -> str:
        values = dict(known_values or {})
        value = self.calculator._compute(variable_id, values, stack=[])
        formula = self.calculator.graph.get_formula(variable_id)
        units = self.calculator.units(variable_id)
        lines = [variable_id]
        if formula is None:
            suffix = f" {units}" if units else ""
            lines.append(f"= {format_number(value)}{suffix}")
            return "\n".join(lines)

        expression = formula["formula"]
        lines.append(f"= {expression}")
        lines.append(f"= {self._substitute(expression, values)}")
        suffix = f" {units}" if units else ""
        lines.append(f"= {format_number(value)}{suffix}")
        return "\n".join(lines)

    def _substitute(self, expression: str, values: dict[str, Any]) -> str:
        def replace_token(match: re.Match[str]) -> str:
            variable_id = match.group(0)
            if variable_id not in values:
                return variable_id
            return format_number(float(values[variable_id]))

        return VARIABLE_TOKEN_RE.sub(replace_token, expression)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--set", action="append", default=[], help="Known input as variable=value")
    parser.add_argument("--compute", required=True, help="Variable id to explain")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    known_values = parse_set(args.set)
    print(ExplanationEngine().explain(args.compute, known_values))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
