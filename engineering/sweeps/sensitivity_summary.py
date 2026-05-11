#!/usr/bin/env python3
"""Generate conservative sensitivity summaries from default BuildSlate sweeps."""

from __future__ import annotations

import argparse
from pathlib import Path
from statistics import mean
from typing import Any

from sweep_runner import REPO_ROOT, SweepRow, render_table, resolve_repo_path, run_sweep

DEFAULT_PROFILE = REPO_ROOT / "configs" / "devices" / "slate-pocket-v1.yaml"
DEFAULT_SWEEPS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("geometry.thickness_mm", ("8.8", "9.5", "10.5", "12.0")),
    ("compute.sustained_power_w", ("8", "12", "18", "28")),
    ("battery.capacity_mah", ("5000", "6000", "7000", "8000")),
    ("memory.capacity_gb", ("128", "256", "512")),
    ("thermal.ambient_c", ("25", "35", "40")),
)

RISK_SCORE = {"low": 0, "moderate": 1, "high": 2, "extreme": 3}
THROTTLE_SCORE = {"normal": 0, "caution": 1, "limit": 2, "critical": 3}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--profile",
        default=str(DEFAULT_PROFILE.relative_to(REPO_ROOT)),
        help="Device profile YAML path",
    )
    return parser.parse_args()


def numeric_output(row: SweepRow, key: str) -> float | None:
    value = row.outputs.get(key)
    if value is None:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def range_for(rows: list[SweepRow], key: str) -> float | None:
    values = [value for row in rows if (value := numeric_output(row, key)) is not None]
    if not values:
        return None
    return max(values) - min(values)


def categorical_range(rows: list[SweepRow], key: str, score_map: dict[str, int]) -> int | None:
    values = [score_map[value] for row in rows if (value := row.outputs.get(key)) in score_map]
    if not values:
        return None
    return max(values) - min(values)


def warning_rate(rows: list[SweepRow], warning: str) -> float:
    return mean(1.0 if warning in row.warnings else 0.0 for row in rows)


def summarize_sweep(parameter: str, rows: list[SweepRow]) -> dict[str, Any]:
    return {
        "parameter": parameter,
        "thermal_risk_range": categorical_range(rows, "thermal_risk", RISK_SCORE),
        "throttle_range": categorical_range(rows, "throttle_pressure", THROTTLE_SCORE),
        "runtime_range_h": range_for(rows, "battery_runtime_h"),
        "stackup_range_mm": range_for(rows, "zone_margin_mm"),
        "runtime_low_rate": warning_rate(rows, "runtime_low"),
        "stackup_fail_rate": warning_rate(rows, "stackup_fail"),
        "memory_pressure_rate": warning_rate(rows, "memory_pressure"),
        "mass_pressure_rate": warning_rate(rows, "mass_pressure"),
    }


def label_top(scored: list[tuple[str, float | int | None]]) -> str:
    valid = [(name, float(score)) for name, score in scored if score is not None]
    if not valid:
        return "not mapped by the default sweep set"
    valid.sort(key=lambda item: item[1], reverse=True)
    best_score = valid[0][1]
    if best_score == 0:
        return f"no material first-pass change detected ({valid[0][0]} had the largest mapped score of 0)"
    winners = [name for name, score in valid if score == best_score]
    return ", ".join(winners)


def format_optional(value: Any, digits: int = 2) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def main() -> int:
    args = parse_args()
    profile_path = resolve_repo_path(args.profile)
    summaries: list[dict[str, Any]] = []

    print("Scenario Sweep Sensitivity Summary")
    print(f"profile: {profile_path.relative_to(REPO_ROOT) if profile_path.is_relative_to(REPO_ROOT) else profile_path}")
    print("scope: one-parameter screening sweeps; no optimization or automatic target solving")
    print("")

    for parameter, values in DEFAULT_SWEEPS:
        try:
            _, rows = run_sweep(profile_path, parameter, list(values))
        except (OSError, ValueError, KeyError) as exc:
            print(f"FAIL: {parameter}: {exc}")
            return 1
        summaries.append(summarize_sweep(parameter, rows))

    table_rows = [
        [
            str(summary["parameter"]),
            format_optional(summary["thermal_risk_range"], 0),
            format_optional(summary["throttle_range"], 0),
            format_optional(summary["runtime_range_h"]),
            format_optional(summary["stackup_range_mm"], 1),
            format_optional(summary["runtime_low_rate"]),
            format_optional(summary["stackup_fail_rate"]),
            format_optional(summary["memory_pressure_rate"]),
        ]
        for summary in summaries
    ]
    print("Default sweep metrics:")
    print("\n".join(render_table([
        "parameter",
        "thermal_risk_range",
        "throttle_range",
        "runtime_range_h",
        "stackup_range_mm",
        "runtime_low_rate",
        "stackup_fail_rate",
        "memory_pressure_rate",
    ], table_rows)))
    print("")

    thermal_scores = [
        (str(summary["parameter"]), max(summary["thermal_risk_range"] or 0, summary["throttle_range"] or 0))
        for summary in summaries
    ]
    runtime_scores = [(str(summary["parameter"]), summary["runtime_range_h"]) for summary in summaries]
    stackup_scores = [(str(summary["parameter"]), summary["stackup_range_mm"]) for summary in summaries]

    print("Summary recommendations:")
    print(f"- Parameters most affecting thermal risk in this first-pass set: {label_top(thermal_scores)}.")
    print(f"- Parameters most affecting runtime in this first-pass set: {label_top(runtime_scores)}.")
    print(f"- Parameters most affecting stackup in this first-pass set: {label_top(stackup_scores)}.")
    print("- Treat warning labels as screening signals for engineering review, not pass/fail optimization targets.")
    print("- No optimization claim is made; these sweeps only show response direction and relative sensitivity.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
