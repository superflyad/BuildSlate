#!/usr/bin/env python3
"""Find first-pass feasibility boundaries by sweeping one profile parameter."""

from __future__ import annotations

import argparse
import copy
import sys
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from engineering.sweeps import sweep_runner  # noqa: E402

DEFAULT_OUTPUT = REPO_ROOT / "reports" / "constraints" / "boundary-report.txt"
SUPPORTED_CONSTRAINTS = {
    "zone_stackup_pass",
    "thermal_risk_not_extreme",
    "skin_temp_pass",
    "runtime_minimum",
    "mass_within_engineering_range",
    "memory_runtime_pass",
}


@dataclass
class BoundaryRow:
    value: Any
    passed: bool
    reason: str
    outputs: dict[str, str] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", required=True, help="Device profile YAML path")
    parser.add_argument("--vary", required=True, help="Dot-path parameter to mutate")
    parser.add_argument("--min", required=True, type=float, dest="min_value", help="Minimum scan value")
    parser.add_argument("--max", required=True, type=float, dest="max_value", help="Maximum scan value")
    parser.add_argument("--step", required=True, type=float, help="Positive scan step")
    parser.add_argument("--constraint", required=True, choices=sorted(SUPPORTED_CONSTRAINTS))
    parser.add_argument("--target-runtime-h", type=float, default=1.0, help="Target runtime for runtime_minimum")
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT.relative_to(REPO_ROOT)),
        help="Report output path (default: reports/constraints/boundary-report.txt)",
    )
    return parser.parse_args()


def resolve_repo_path(path_text: str) -> Path:
    path = Path(path_text)
    return path if path.is_absolute() else REPO_ROOT / path


def repo_relative(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def scan_values(min_value: float, max_value: float, step: float) -> list[float]:
    if step <= 0:
        raise ValueError("--step must be greater than zero")
    if max_value < min_value:
        raise ValueError("--max must be greater than or equal to --min")

    values: list[float] = []
    current = min_value
    tolerance = abs(step) / 1_000_000.0
    while current <= max_value + tolerance:
        rounded = round(current, 10)
        values.append(int(rounded) if float(rounded).is_integer() else rounded)
        current += step
    return values


def estimated_mass_g(profile: dict[str, Any], base_profile: dict[str, Any]) -> float:
    mass_targets = sweep_runner.require_mapping(profile, "mass_targets")
    base_mass_targets = sweep_runner.require_mapping(base_profile, "mass_targets")
    base_estimate = float(mass_targets.get("engineering_estimate_g", base_mass_targets.get("engineering_estimate_g", 0.0)))
    if base_estimate <= 0:
        raise ValueError("mass_targets.engineering_estimate_g is required for mass constraint")

    # Keep the profile estimate as the anchor, but adjust for battery-capacity changes so
    # capacity boundary checks reflect the largest mass driver available in the profile.
    current_battery_mass = sweep_runner.battery_metrics(profile)["battery_mass_g"]
    base_battery_mass = sweep_runner.battery_metrics(base_profile)["battery_mass_g"]
    return base_estimate + current_battery_mass - base_battery_mass


def evaluate_constraint(
    profile: dict[str, Any],
    base_profile: dict[str, Any],
    constraint: str,
    target_runtime_h: float,
) -> tuple[bool, str, dict[str, str]]:
    if constraint == "zone_stackup_pass":
        margin = sweep_runner.zone_stackup_margin_mm(sweep_runner.numeric(profile, "geometry", "thickness_mm"))
        return margin >= 0.0, f"worst zone margin {margin:.2f} mm", {"zone_margin_mm": f"{margin:.2f}"}

    if constraint == "thermal_risk_not_extreme":
        heat_w = sweep_runner.numeric(profile, "compute", "sustained_power_w")
        thermal = sweep_runner.thermal_metrics(profile, sustained_w=heat_w)
        risk = str(thermal["thermal_risk"])
        return risk != "extreme", f"thermal risk {risk}", {
            "thermal_risk": risk,
            "heat_density_w_cm3": f"{float(thermal['heat_density_w_cm3']):.3f}",
        }

    if constraint == "skin_temp_pass":
        ambient = sweep_runner.ambient_metrics(profile)
        estimated_skin = float(ambient["estimated_skin_c"])
        max_skin = sweep_runner.numeric(profile, "thermal", "max_skin_c")
        return estimated_skin <= max_skin, f"skin {estimated_skin:.1f} C <= max {max_skin:.1f} C", {
            "estimated_skin_c": f"{estimated_skin:.1f}",
            "max_skin_c": f"{max_skin:.1f}",
            "skin_margin_c": f"{float(ambient['skin_margin_c']):.1f}",
        }

    if constraint == "runtime_minimum":
        runtime = sweep_runner.battery_metrics(profile)["battery_runtime_h"]
        return runtime >= target_runtime_h, f"runtime {runtime:.2f} h >= target {target_runtime_h:.2f} h", {
            "battery_runtime_h": f"{runtime:.2f}",
            "target_runtime_h": f"{target_runtime_h:.2f}",
        }

    if constraint == "mass_within_engineering_range":
        mass_targets = sweep_runner.require_mapping(profile, "mass_targets")
        acceptable_range = mass_targets.get("acceptable_range_g")
        if not isinstance(acceptable_range, dict) or "max" not in acceptable_range:
            raise ValueError("mass_targets.acceptable_range_g.max is required for mass constraint")
        mass_g = estimated_mass_g(profile, base_profile)
        max_mass_g = float(acceptable_range["max"])
        return mass_g <= max_mass_g, f"estimated mass {mass_g:.1f} g <= max {max_mass_g:.1f} g", {
            "estimated_mass_g": f"{mass_g:.1f}",
            "max_mass_g": f"{max_mass_g:.1f}",
        }

    if constraint == "memory_runtime_pass":
        memory = sweep_runner.memory_metrics(profile)
        used = float(memory["runtime_used_gb"])
        available = sweep_runner.numeric(profile, "memory", "capacity_gb")
        return used <= available, f"runtime memory {used:.1f} GB <= available {available:.1f} GB", {
            "runtime_used_gb": f"{used:.1f}",
            "available_memory_gb": f"{available:.1f}",
            "runtime_remaining_gb": f"{float(memory['runtime_remaining_gb']):.1f}",
        }

    raise ValueError(f"unsupported constraint: {constraint}")


def run_boundary(
    profile_path: Path,
    parameter_path: str,
    min_value: float,
    max_value: float,
    step: float,
    constraint: str,
    target_runtime_h: float = 1.0,
) -> tuple[dict[str, Any], list[BoundaryRow]]:
    base_profile = sweep_runner.load_profile(profile_path)
    reference_value = sweep_runner.get_path(base_profile, parameter_path)
    rows: list[BoundaryRow] = []

    for raw_value in scan_values(min_value, max_value, step):
        mutated_profile = copy.deepcopy(base_profile)
        if isinstance(reference_value, bool):
            value = sweep_runner.coerce_value(str(raw_value), reference_value)
        elif isinstance(reference_value, (int, float)):
            value = int(raw_value) if float(raw_value).is_integer() else float(raw_value)
        else:
            value = sweep_runner.coerce_value(str(raw_value), reference_value)
        sweep_runner.set_path(mutated_profile, parameter_path, value)
        sweep_row = sweep_runner.evaluate_profile(mutated_profile, parameter_path, value)
        passed, reason, constraint_outputs = evaluate_constraint(mutated_profile, base_profile, constraint, target_runtime_h)
        outputs = {**sweep_row.outputs, **constraint_outputs}
        warnings = list(dict.fromkeys(sweep_row.warnings if sweep_row.warnings else ["none"]))
        rows.append(BoundaryRow(value=value, passed=passed, reason=reason, outputs=outputs, warnings=warnings))
    return base_profile, rows


def boundary_findings(rows: list[BoundaryRow]) -> dict[str, BoundaryRow | None | str]:
    first_passing = next((row for row in rows if row.passed), None)
    last_failing_before_pass = None
    if first_passing is not None:
        for row in rows[: rows.index(first_passing)]:
            if not row.passed:
                last_failing_before_pass = row
    passing_rows = [row for row in rows if row.passed]
    best_passing = passing_rows[-1] if passing_rows else None

    last_passing_before_fail = None
    first_failing_after_pass = None
    seen_pass = False
    for row in rows:
        if row.passed:
            seen_pass = True
            if first_failing_after_pass is None:
                last_passing_before_fail = row
        elif seen_pass and first_failing_after_pass is None:
            first_failing_after_pass = row

    return {
        "first_passing": first_passing,
        "last_failing_before_pass": last_failing_before_pass,
        "best_passing": best_passing,
        "last_passing_before_fail": last_passing_before_fail,
        "first_failing_after_pass": first_failing_after_pass,
        "sequence": "".join("P" if row.passed else "F" for row in rows),
    }


def select_columns(rows: list[BoundaryRow]) -> list[str]:
    preferred = [
        "profile_value",
        "zone_margin_mm",
        "thermal_risk",
        "heat_density_w_cm3",
        "estimated_skin_c",
        "max_skin_c",
        "skin_margin_c",
        "battery_runtime_h",
        "target_runtime_h",
        "estimated_mass_g",
        "max_mass_g",
        "runtime_used_gb",
        "available_memory_gb",
        "runtime_remaining_gb",
    ]
    present = {key for row in rows for key in row.outputs}
    return [column for column in preferred if column in present]


def row_value(row: BoundaryRow | None) -> str:
    return "none" if row is None else str(row.value)


def render_report(
    profile: dict[str, Any],
    profile_path: Path,
    parameter_path: str,
    min_value: float,
    max_value: float,
    step: float,
    constraint: str,
    rows: list[BoundaryRow],
) -> str:
    identity = sweep_runner.require_mapping(profile, "identity")
    profile_label = identity.get("profile_id") or identity.get("name", "unknown")
    generated = datetime.now(UTC).isoformat(timespec="seconds")
    findings = boundary_findings(rows)
    columns = select_columns(rows)
    headers = ["value", "pass", "reason", *columns, "warnings"]
    table_rows = [
        [
            str(row.value),
            "PASS" if row.passed else "FAIL",
            row.reason,
            *[row.outputs.get(column, "") for column in columns],
            ",".join(row.warnings),
        ]
        for row in rows
    ]

    report_lines = [
        "Feasibility Boundary Analysis",
        f"generated: {generated}",
        f"profile: {profile_label}",
        f"profile_path: {repo_relative(profile_path)}",
        f"parameter_varied: {parameter_path}",
        f"range_tested: {min_value:g} to {max_value:g} step {step:g}",
        f"constraint_evaluated: {constraint}",
        f"first_passing_value: {row_value(findings['first_passing'])}",
        f"last_failing_value_before_pass: {row_value(findings['last_failing_before_pass'])}",
        f"best_passing_value_in_scan_order: {row_value(findings['best_passing'])}",
        f"last_passing_value_before_fail: {row_value(findings['last_passing_before_fail'])}",
        f"first_failing_value_after_pass: {row_value(findings['first_failing_after_pass'])}",
        f"fail_pass_sequence: {findings['sequence']}",
        "screening_result: screening result, not production validation",
        "",
        *sweep_runner.render_table(headers, table_rows),
        "",
        "Notes:",
        "- Each row mutates one parameter in an in-memory copy of the source profile.",
        "- Source YAML profiles are not edited by this boundary tool.",
        "- Boundary results identify explicit pass/fail transitions; they do not optimize or automatically redesign Slate.",
        "- Constraints and outputs are model-dependent screening classifications, not certification results.",
        "- Warnings highlight model limitations and follow-up engineering review needs.",
    ]
    return "\n".join(report_lines) + "\n"


def main() -> int:
    args = parse_args()
    profile_path = resolve_repo_path(args.profile)
    output_path = resolve_repo_path(args.output)

    try:
        base_profile, rows = run_boundary(
            profile_path,
            args.vary,
            args.min_value,
            args.max_value,
            args.step,
            args.constraint,
            args.target_runtime_h,
        )
        report = render_report(
            base_profile,
            profile_path,
            args.vary,
            args.min_value,
            args.max_value,
            args.step,
            args.constraint,
            rows,
        )
    except (OSError, ValueError, KeyError) as exc:
        print(f"FAIL: {exc}")
        return 1

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report, encoding="utf-8")
    print(report, end="")
    print(f"Report written to: {repo_relative(output_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
