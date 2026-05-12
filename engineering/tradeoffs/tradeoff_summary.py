#!/usr/bin/env python3
"""Generate qualitative summaries from default tradeoff maps."""

from __future__ import annotations

import sys
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from engineering.tradeoffs import tradeoff_map, tradeoff_matrix  # noqa: E402

DEFAULT_OUTPUT = REPO_ROOT / "reports" / "tradeoffs" / "tradeoff-summary.txt"
PRESSURE_SET = {"HIGH", "EXTREME", "FAIL"}


def pressure_counts(grid: list[list[tradeoff_map.TradeoffPoint]]) -> dict[str, int]:
    counts = {pressure: 0 for pressure in tradeoff_map.PRESSURE_ORDER}
    for row in grid:
        for point in row:
            counts[point.pressure] += 1
    return counts


def first_pressure_point(grid: list[list[tradeoff_map.TradeoffPoint]], pressures: set[str]) -> tradeoff_map.TradeoffPoint | None:
    return next((point for row in grid for point in row if point.pressure in pressures), None)


def summarize_map(default_map: tradeoff_matrix.DefaultMap) -> list[str]:
    _, _, _, grid = tradeoff_map.evaluate_tradeoff_grid(
        profile_path=tradeoff_matrix.DEFAULT_PROFILE,
        x_axis=default_map.x,
        y_axis=default_map.y,
        constraint=default_map.constraint,
    )
    counts = pressure_counts(grid)
    first_pressure = first_pressure_point(grid, PRESSURE_SET)
    pressure_total = sum(counts[pressure] for pressure in PRESSURE_SET)
    total = sum(counts.values())
    first_text = "none observed"
    if first_pressure is not None:
        first_text = (
            f"x={tradeoff_map.format_axis_value(default_map.x.parameter_path, first_pressure.x_value)}, "
            f"y={tradeoff_map.format_axis_value(default_map.y.parameter_path, first_pressure.y_value)} "
            f"({first_pressure.pressure})"
        )
    return [
        f"- {default_map.label}: {pressure_total}/{total} grid points are HIGH, EXTREME, or FAIL; first pressure point: {first_text}.",
        f"  Counts: PASS={counts['PASS']}, MODERATE={counts['MODERATE']}, HIGH={counts['HIGH']}, EXTREME={counts['EXTREME']}, FAIL={counts['FAIL']}.",
    ]


def render_summary() -> str:
    generated = datetime.now(UTC).isoformat(timespec="seconds")
    lines = [
        "Tradeoff Summary",
        f"generated: {generated}",
        f"profile_path: {tradeoff_map.repo_relative(tradeoff_matrix.DEFAULT_PROFILE)}",
        "screening_classification: qualitative first-pass engineering interaction summary",
        "",
        "Qualitative engineering findings:",
        "- Thin chassis strongly amplifies thermal pressure at sustained AI loads because the same heat load occupies less modeled volume and surface area.",
        "- Increasing battery capacity can create mass pressure even when runtime improves, so energy storage cannot be interpreted as a free margin increase.",
        "- Increasing memory capacity creates stackup and package-count pressure faster than it resolves every runtime-memory scenario.",
        "- Ambient temperature meaningfully reduces skin-temperature operating margin; hot environments can dominate otherwise acceptable sustained-load assumptions.",
        "- Runtime memory pressure escalates rapidly with large context windows because KV-cache demand grows with context length.",
        "",
        "Generated-map observations:",
    ]
    for default_map in tradeoff_matrix.DEFAULT_MAPS:
        lines.extend(summarize_map(default_map))
    lines.extend(
        [
            "",
            "Limitations and interpretation warnings:",
            "- These are first-pass screening summaries, not validation, certification, optimization, or automated design recommendations.",
            "- Interactions are model-dependent; changing thermal, mass, memory, battery, or stackup equations can change the pressure regions.",
            "- PASS does not mean manufacturable or supplier-ready; it means the selected model and constraint did not show pressure beyond the configured heuristic bands.",
            "- FAIL does not mean impossible forever; it means this screening model violates the selected explicit constraint for that grid point.",
            "- Use the map outputs to focus review, not to replace CAD, thermal simulation, prototyping, safety testing, or manufacturing analysis.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    try:
        report = render_summary()
    except (OSError, ValueError, KeyError) as exc:
        print(f"FAIL: {exc}")
        return 1

    DEFAULT_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    DEFAULT_OUTPUT.write_text(report, encoding="utf-8")
    print(report, end="")
    print(f"Report written to: {tradeoff_map.repo_relative(DEFAULT_OUTPUT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
