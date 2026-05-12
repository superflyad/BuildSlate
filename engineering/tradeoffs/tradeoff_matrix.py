#!/usr/bin/env python3
"""Generate default two-parameter tradeoff maps for BuildSlate screening."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from engineering.tradeoffs import tradeoff_map  # noqa: E402

DEFAULT_PROFILE = REPO_ROOT / "configs" / "devices" / "slate-pocket-v1.yaml"
DEFAULT_OUTPUT = REPO_ROOT / "reports" / "tradeoffs" / "tradeoff-matrix.txt"


@dataclass(frozen=True)
class DefaultMap:
    label: str
    x: tradeoff_map.AxisSpec
    y: tradeoff_map.AxisSpec
    constraint: str


DEFAULT_MAPS = (
    DefaultMap(
        label="A. Thickness vs sustained power",
        x=tradeoff_map.AxisSpec("geometry.thickness_mm", 8.0, 14.0, 1.0),
        y=tradeoff_map.AxisSpec("compute.sustained_power_w", 4.0, 40.0, 4.0),
        constraint="thermal_risk_not_extreme",
    ),
    DefaultMap(
        label="B. Battery capacity vs mass estimate",
        x=tradeoff_map.AxisSpec("battery.capacity_mah", 4000.0, 10000.0, 1000.0),
        y=tradeoff_map.AxisSpec("mass_targets.engineering_estimate_g", 180.0, 260.0, 20.0),
        constraint="mass_within_engineering_range",
    ),
    DefaultMap(
        label="C. Memory capacity vs thickness",
        x=tradeoff_map.AxisSpec("memory.capacity_gb", 64.0, 512.0, 64.0),
        y=tradeoff_map.AxisSpec("geometry.thickness_mm", 8.0, 14.0, 1.0),
        constraint="zone_stackup_pass",
    ),
    DefaultMap(
        label="D. Ambient temperature vs sustained power",
        x=tradeoff_map.AxisSpec("thermal.ambient_c", 20.0, 50.0, 5.0),
        y=tradeoff_map.AxisSpec("compute.sustained_power_w", 4.0, 40.0, 4.0),
        constraint="skin_temp_pass",
    ),
    DefaultMap(
        label="E. Memory capacity vs context length",
        x=tradeoff_map.AxisSpec("memory.capacity_gb", 64.0, 512.0, 64.0),
        y=tradeoff_map.AxisSpec("runtime.context_tokens", 4096.0, 131072.0, 16384.0),
        constraint="memory_runtime_pass",
    ),
)


def render_default_matrix(profile_path: Path = DEFAULT_PROFILE) -> str:
    generated = datetime.now(UTC).isoformat(timespec="seconds")
    sections = [
        "Default Tradeoff Matrix",
        f"generated: {generated}",
        f"profile_path: {tradeoff_map.repo_relative(profile_path)}",
        "screening_classification: first-pass engineering pressure regions, not exact engineering standards",
        "optimization: none; these maps do not auto-solve or rank designs",
        "",
    ]
    for default_map in DEFAULT_MAPS:
        report = tradeoff_map.generate_tradeoff_report(
            profile_path=profile_path,
            x_axis=default_map.x,
            y_axis=default_map.y,
            constraint=default_map.constraint,
        )
        sections.extend([f"## {default_map.label}", report.strip(), ""])
    sections.extend(
        [
            "Global Notes:",
            "- Tradeoff maps are screening tools for interaction review.",
            "- PASS regions still require CAD, supplier, thermal, reliability, and manufacturing validation.",
            "- FAIL regions show where this model violates an explicit constraint; they are not permanent impossibility claims.",
            "- Source YAML profiles are loaded read-only and mutated only in memory.",
        ]
    )
    return "\n".join(sections) + "\n"


def main() -> int:
    try:
        report = render_default_matrix(DEFAULT_PROFILE)
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
