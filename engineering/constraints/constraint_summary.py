#!/usr/bin/env python3
"""Summarize default feasibility boundary findings in plain language."""

from __future__ import annotations

import sys
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from engineering.constraints import constraint_runner  # noqa: E402
from engineering.constraints import feasibility_boundary as boundary  # noqa: E402

DEFAULT_OUTPUT = REPO_ROOT / "reports" / "constraints" / "constraint-summary.txt"


def finding_value(rows: list[boundary.BoundaryRow], key: str) -> str:
    findings = boundary.boundary_findings(rows)
    row = findings[key]
    return "not found" if row is None else str(row.value)


def summarize_default_boundaries() -> str:
    generated = datetime.now(UTC).isoformat(timespec="seconds")
    lines = [
        "Constraint Boundary Summary",
        f"generated: {generated}",
        f"profile_path: {boundary.repo_relative(constraint_runner.DEFAULT_PROFILE)}",
        "screening result, not production validation",
        "",
        "Plain-language findings:",
    ]

    check_rows: dict[str, list[boundary.BoundaryRow]] = {}
    for check in constraint_runner.DEFAULT_CHECKS:
        _, rows = boundary.run_boundary(
            profile_path=constraint_runner.DEFAULT_PROFILE,
            parameter_path=check.vary,
            min_value=check.min_value,
            max_value=check.max_value,
            step=check.step,
            constraint=check.constraint,
            target_runtime_h=check.target_runtime_h,
        )
        check_rows[check.constraint] = rows

    thickness = finding_value(check_rows["zone_stackup_pass"], "first_passing")
    runtime_capacity = finding_value(check_rows["runtime_minimum"], "first_passing")
    sustained_power = finding_value(check_rows["thermal_risk_not_extreme"], "last_passing_before_fail")
    first_extreme_power = finding_value(check_rows["thermal_risk_not_extreme"], "first_failing_after_pass")
    ambient_last_pass = finding_value(check_rows["skin_temp_pass"], "last_passing_before_fail")
    ambient_first_fail = finding_value(check_rows["skin_temp_pass"], "first_failing_after_pass")
    memory_capacity = finding_value(check_rows["memory_runtime_pass"], "first_passing")

    lines.extend(
        [
            f"- Minimum passing thickness for current stack assumptions: {thickness} mm.",
            f"- Runtime target requires at least {runtime_capacity} mAh under current sustained load.",
            f"- Sustained power should remain at or below {sustained_power} W before thermal risk escalates to EXTREME at {first_extreme_power} W in this scan.",
            f"- Ambient sensitivity becomes critical above {ambient_last_pass} C; the first failing scan point is {ambient_first_fail} C.",
            f"- Runtime memory budget first passes at {memory_capacity} GB available memory in this scan.",
            "",
            "Model limitation warnings:",
            "- Boundary values depend on simplified stackup, thermal, battery, mass, and runtime-memory equations.",
            "- Scan steps discretize the transition; the true boundary may sit between adjacent tested values.",
            "- Passing a screening constraint is not certification, production validation, regulatory evidence, or a complete device architecture decision.",
            "- These tools do not optimize or automatically redesign Slate; they only classify explicit constraints against mutated in-memory profiles.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    try:
        summary = summarize_default_boundaries()
    except (OSError, ValueError, KeyError) as exc:
        print(f"FAIL: {exc}")
        return 1

    DEFAULT_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    DEFAULT_OUTPUT.write_text(summary, encoding="utf-8")
    print(summary, end="")
    print(f"Summary written to: {boundary.repo_relative(DEFAULT_OUTPUT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
