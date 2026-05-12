#!/usr/bin/env python3
"""Map two-parameter engineering tradeoffs as first-pass screening regions."""

from __future__ import annotations

import argparse
import copy
import sys
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from engineering.constraints import feasibility_boundary as boundary  # noqa: E402
from engineering.sweeps import sweep_runner  # noqa: E402

DEFAULT_OUTPUT = REPO_ROOT / "reports" / "tradeoffs" / "tradeoff-map.txt"

SUPPORTED_PARAMETER_PATHS = {
    "geometry.thickness_mm",
    "battery.capacity_mah",
    "compute.sustained_power_w",
    "compute.peak_power_w",
    "memory.capacity_gb",
    "storage.capacity_tb",
    "thermal.ambient_c",
    "runtime.context_tokens",
    # Extra path used by the default battery-capacity-vs-mass screening map.
    "mass_targets.engineering_estimate_g",
}

PRESSURE_CODES = {
    "PASS": "P",
    "MODERATE": "M",
    "HIGH": "H",
    "EXTREME": "E",
    "FAIL": "F",
}

PRESSURE_ORDER = ["PASS", "MODERATE", "HIGH", "EXTREME", "FAIL"]


@dataclass(frozen=True)
class AxisSpec:
    parameter_path: str
    min_value: float
    max_value: float
    step: float


@dataclass
class TradeoffPoint:
    x_value: Any
    y_value: Any
    passed: bool
    pressure: str
    reason: str
    outputs: dict[str, str] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    explanation: str = ""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", required=True, help="Device profile YAML path")
    parser.add_argument("--x", required=True, nargs=4, metavar=("PARAMETER", "MIN", "MAX", "STEP"))
    parser.add_argument("--y", required=True, nargs=4, metavar=("PARAMETER", "MIN", "MAX", "STEP"))
    parser.add_argument("--constraint", required=True, choices=sorted(boundary.SUPPORTED_CONSTRAINTS))
    parser.add_argument("--target-runtime-h", type=float, default=1.0, help="Target runtime for runtime_minimum")
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT.relative_to(REPO_ROOT)),
        help="Report output path (default: reports/tradeoffs/tradeoff-map.txt)",
    )
    return parser.parse_args()


def resolve_repo_path(path_text: str) -> Path:
    path = Path(path_text)
    return path if path.is_absolute() else REPO_ROOT / path


def repo_relative(path: Path) -> str:
    return boundary.repo_relative(path)


def parse_axis(raw_axis: list[str]) -> AxisSpec:
    parameter_path, min_text, max_text, step_text = raw_axis
    if parameter_path not in SUPPORTED_PARAMETER_PATHS:
        raise ValueError(f"unsupported tradeoff parameter path: {parameter_path}")
    return AxisSpec(parameter_path, float(min_text), float(max_text), float(step_text))


def coerce_axis_value(base_profile: dict[str, Any], parameter_path: str, raw_value: float) -> Any:
    reference_value = sweep_runner.get_path(base_profile, parameter_path)
    if isinstance(reference_value, (int, float)) and not isinstance(reference_value, bool):
        return int(raw_value) if float(raw_value).is_integer() and isinstance(reference_value, int) else raw_value
    return sweep_runner.coerce_value(str(raw_value), reference_value)


def clean_warnings(warnings: list[str]) -> list[str]:
    cleaned = [warning for warning in warnings if warning != "none"]
    return list(dict.fromkeys(cleaned)) or ["none"]


def combined_sweep_outputs(profile: dict[str, Any], x_path: str, x_value: Any, y_path: str, y_value: Any) -> tuple[dict[str, str], list[str]]:
    outputs: dict[str, str] = {}
    warnings: list[str] = []
    mapped_by_constraint = {
        "compute.peak_power_w",
        "storage.capacity_tb",
        "runtime.context_tokens",
        "mass_targets.engineering_estimate_g",
    }
    for parameter_path, value in ((x_path, x_value), (y_path, y_value)):
        row = sweep_runner.evaluate_profile(profile, parameter_path, value)
        for key, output_value in row.outputs.items():
            if key == "profile_value":
                outputs[f"{parameter_path}.profile_value"] = output_value
            elif key != "engineering_outputs":
                outputs[key] = output_value
        row_warnings = row.warnings
        if parameter_path in mapped_by_constraint:
            row_warnings = [warning for warning in row_warnings if warning != "not_mapped"]
        warnings.extend(row_warnings)
    return outputs, clean_warnings(warnings)


def numeric_output(outputs: dict[str, str], key: str) -> float | None:
    value = outputs.get(key)
    if value is None:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def classify_pressure(passed: bool, outputs: dict[str, str], warnings: list[str], constraint: str) -> tuple[str, str]:
    """Classify a point with explicit first-pass screening heuristics."""
    active_warnings = [warning for warning in warnings if warning != "none"]
    severe_warnings = {"stackup_fail", "high_thermal_risk", "runtime_low", "throttle_pressure", "memory_pressure"}

    if not passed:
        return "FAIL", "explicit constraint failure from selected constraint check"

    if constraint == "thermal_risk_not_extreme":
        risk = outputs.get("thermal_risk")
        heat_density = numeric_output(outputs, "heat_density_w_cm3")
        if risk == "high" or (heat_density is not None and heat_density >= 0.22):
            return "EXTREME", "thermal risk is high or heat density is near the extreme threshold"
        if risk == "moderate" or (heat_density is not None and heat_density >= 0.15):
            return "HIGH", "thermal margin is low under the screening heat-density bands"
        if active_warnings:
            return "MODERATE", "constraint passes but warnings are active"
        return "PASS", "constraint passes with no active warnings"

    if constraint == "zone_stackup_pass":
        margin = numeric_output(outputs, "zone_margin_mm")
        if margin is not None:
            if margin < 0.25:
                return "EXTREME", "stackup margin is below 0.25 mm"
            if margin < 0.75:
                return "HIGH", "stackup margin is below 0.75 mm"
            if margin < 1.5 or active_warnings:
                return "MODERATE", "stackup passes but margin is modest or warnings are active"
        return "PASS", "constraint passes with comfortable stackup margin"

    if constraint == "skin_temp_pass":
        margin = numeric_output(outputs, "skin_margin_c")
        throttle_pressure = outputs.get("throttle_pressure")
        if margin is not None:
            if margin <= 1.0 or throttle_pressure in {"limit", "critical"}:
                return "EXTREME", "skin-temperature margin is within 1 C or throttle pressure is severe"
            if margin <= 3.0:
                return "HIGH", "skin-temperature margin is 3 C or less"
            if margin <= 6.0 or active_warnings:
                return "MODERATE", "skin-temperature margin is modest or warnings are active"
        return "PASS", "constraint passes with no active skin-temperature warnings"

    if constraint == "runtime_minimum":
        runtime = numeric_output(outputs, "battery_runtime_h")
        target = numeric_output(outputs, "target_runtime_h") or 1.0
        if runtime is not None:
            ratio = runtime / target
            if ratio <= 1.05:
                return "EXTREME", "runtime is within 5% of the minimum target"
            if ratio <= 1.20:
                return "HIGH", "runtime margin is 20% or less"
            if ratio <= 1.50 or active_warnings:
                return "MODERATE", "runtime passes but margin is limited or warnings are active"
        return "PASS", "runtime passes with comfortable margin"

    if constraint == "mass_within_engineering_range":
        mass = numeric_output(outputs, "estimated_mass_g")
        max_mass = numeric_output(outputs, "max_mass_g")
        if mass is not None and max_mass is not None and max_mass > 0:
            ratio = mass / max_mass
            if ratio >= 0.98:
                return "EXTREME", "estimated mass is within 2% of the engineering maximum"
            if ratio >= 0.90:
                return "HIGH", "estimated mass uses at least 90% of the engineering maximum"
            if ratio >= 0.80 or active_warnings:
                return "MODERATE", "mass passes but uses at least 80% of the engineering maximum or warnings are active"
        return "PASS", "mass passes with comfortable screening margin"

    if constraint == "memory_runtime_pass":
        remaining = numeric_output(outputs, "runtime_remaining_gb")
        available = numeric_output(outputs, "available_memory_gb")
        if remaining is not None and available is not None and available > 0:
            ratio = remaining / available
            if ratio <= 0.05:
                return "EXTREME", "runtime memory remaining is 5% or less of installed memory"
            if ratio <= 0.15:
                return "HIGH", "runtime memory remaining is 15% or less of installed memory"
            if ratio <= 0.25 or active_warnings:
                return "MODERATE", "runtime memory passes but remaining headroom is limited or warnings are active"
        return "PASS", "memory runtime passes with comfortable headroom"

    if len(active_warnings) >= 2 or any(warning in severe_warnings for warning in active_warnings):
        return "HIGH", "constraint passes with multiple or severe warnings"
    if active_warnings:
        return "MODERATE", "constraint passes but warnings are active"
    return "PASS", "constraint passes with no active warnings"


def evaluate_tradeoff_grid(
    profile_path: Path,
    x_axis: AxisSpec,
    y_axis: AxisSpec,
    constraint: str,
    target_runtime_h: float = 1.0,
) -> tuple[dict[str, Any], list[Any], list[Any], list[list[TradeoffPoint]]]:
    base_profile = sweep_runner.load_profile(profile_path)
    # Validate paths against the source profile before generating the grid.
    sweep_runner.get_path(base_profile, x_axis.parameter_path)
    sweep_runner.get_path(base_profile, y_axis.parameter_path)

    x_values = [coerce_axis_value(base_profile, x_axis.parameter_path, value) for value in boundary.scan_values(x_axis.min_value, x_axis.max_value, x_axis.step)]
    y_values = [coerce_axis_value(base_profile, y_axis.parameter_path, value) for value in boundary.scan_values(y_axis.min_value, y_axis.max_value, y_axis.step)]

    grid: list[list[TradeoffPoint]] = []
    for x_value in x_values:
        row: list[TradeoffPoint] = []
        for y_value in y_values:
            mutated_profile = copy.deepcopy(base_profile)
            sweep_runner.set_path(mutated_profile, x_axis.parameter_path, x_value)
            sweep_runner.set_path(mutated_profile, y_axis.parameter_path, y_value)
            outputs, warnings = combined_sweep_outputs(mutated_profile, x_axis.parameter_path, x_value, y_axis.parameter_path, y_value)
            passed, reason, constraint_outputs = boundary.evaluate_constraint(mutated_profile, base_profile, constraint, target_runtime_h)
            outputs.update(constraint_outputs)
            warnings = clean_warnings(warnings)
            pressure, explanation = classify_pressure(passed, outputs, warnings, constraint)
            row.append(
                TradeoffPoint(
                    x_value=x_value,
                    y_value=y_value,
                    passed=passed,
                    pressure=pressure,
                    reason=reason,
                    outputs=outputs,
                    warnings=warnings,
                    explanation=explanation,
                )
            )
        grid.append(row)
    return base_profile, x_values, y_values, grid


def format_axis_value(parameter_path: str, value: Any) -> str:
    suffixes = {
        "geometry.thickness_mm": "mm",
        "battery.capacity_mah": "mAh",
        "compute.sustained_power_w": "W",
        "compute.peak_power_w": "W",
        "memory.capacity_gb": "GB",
        "storage.capacity_tb": "TB",
        "thermal.ambient_c": "C",
        "runtime.context_tokens": "tok",
        "mass_targets.engineering_estimate_g": "g",
    }
    if isinstance(value, float) and value.is_integer():
        value_text = str(int(value))
    else:
        value_text = str(value)
    return f"{value_text}{suffixes.get(parameter_path, '')}"


def render_tradeoff_map(
    profile: dict[str, Any],
    profile_path: Path,
    x_axis: AxisSpec,
    y_axis: AxisSpec,
    constraint: str,
    x_values: list[Any],
    y_values: list[Any],
    grid: list[list[TradeoffPoint]],
) -> str:
    identity = sweep_runner.require_mapping(profile, "identity")
    profile_label = identity.get("profile_id") or identity.get("name", "unknown")
    generated = datetime.now(UTC).isoformat(timespec="seconds")
    y_headers = [format_axis_value(y_axis.parameter_path, value) for value in y_values]
    x_labels = [format_axis_value(x_axis.parameter_path, value) for value in x_values]
    row_label_width = max(len(x_axis.parameter_path), *(len(label) for label in x_labels)) + 2
    cell_width = max(3, *(len(header) for header in y_headers))

    matrix_lines = [" " * row_label_width + " ".join(header.rjust(cell_width) for header in y_headers)]
    for label, points in zip(x_labels, grid):
        codes = [PRESSURE_CODES[point.pressure].rjust(cell_width) for point in points]
        matrix_lines.append(label.ljust(row_label_width) + " ".join(codes))

    counts = {pressure: 0 for pressure in PRESSURE_ORDER}
    for row in grid:
        for point in row:
            counts[point.pressure] += 1

    sample_lines = []
    for pressure in PRESSURE_ORDER:
        sample = next((point for row in grid for point in row if point.pressure == pressure), None)
        if sample is not None:
            sample_lines.append(
                f"- {pressure}: x={format_axis_value(x_axis.parameter_path, sample.x_value)}, "
                f"y={format_axis_value(y_axis.parameter_path, sample.y_value)}; {sample.explanation}; "
                f"constraint_reason={sample.reason}; warnings={','.join(sample.warnings)}"
            )

    lines = [
        "Tradeoff Map",
        f"generated: {generated}",
        f"profile: {profile_label}",
        f"profile_path: {repo_relative(profile_path)}",
        f"constraint: {constraint}",
        f"x: {x_axis.parameter_path}",
        f"y: {y_axis.parameter_path}",
        f"x_range: {x_axis.min_value:g} to {x_axis.max_value:g} step {x_axis.step:g}",
        f"y_range: {y_axis.min_value:g} to {y_axis.max_value:g} step {y_axis.step:g}",
        "screening_classification: first-pass engineering pressure regions, not exact engineering standards",
        "optimization: none; this tool maps interactions and does not auto-solve designs",
        "source_profiles_modified: no",
        "",
        *matrix_lines,
        "",
        "Legend:",
        "P = PASS",
        "M = MODERATE",
        "H = HIGH",
        "E = EXTREME",
        "F = FAIL",
        "",
        "Region counts:",
        *[f"- {pressure}: {counts[pressure]}" for pressure in PRESSURE_ORDER],
        "",
        "Classification heuristics:",
        "- FAIL means the selected explicit constraint returned failure.",
        "- PASS means the constraint passed with no active warnings or comfortable screening margin.",
        "- MODERATE means warnings are active or margin is modest.",
        "- HIGH means severe warnings, multiple warnings, or low margin are present.",
        "- EXTREME means the point is near a modeled threshold but has not necessarily failed.",
        "- Heuristics are intentionally transparent screening labels, not certification or manufacturability claims.",
        "",
        "Representative classified points:",
        *(sample_lines or ["- none"]),
        "",
        "Notes:",
        "- Each grid point loads the source profile into an in-memory copy, mutates the x and y parameters, evaluates the selected constraint, and records warnings.",
        "- Interactions are model-dependent and may be nonlinear; review equations and assumptions before using results for engineering decisions.",
        "- PASS does not mean manufacturable. FAIL does not mean impossible forever.",
    ]
    return "\n".join(lines) + "\n"


def generate_tradeoff_report(
    profile_path: Path,
    x_axis: AxisSpec,
    y_axis: AxisSpec,
    constraint: str,
    target_runtime_h: float = 1.0,
) -> str:
    profile, x_values, y_values, grid = evaluate_tradeoff_grid(profile_path, x_axis, y_axis, constraint, target_runtime_h)
    return render_tradeoff_map(profile, profile_path, x_axis, y_axis, constraint, x_values, y_values, grid)


def main() -> int:
    args = parse_args()
    profile_path = resolve_repo_path(args.profile)
    output_path = resolve_repo_path(args.output)

    try:
        x_axis = parse_axis(args.x)
        y_axis = parse_axis(args.y)
        report = generate_tradeoff_report(profile_path, x_axis, y_axis, args.constraint, args.target_runtime_h)
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
