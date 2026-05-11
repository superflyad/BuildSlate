#!/usr/bin/env python3
"""Run the default Slate Pocket v1 feasibility boundary checks."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from engineering.constraints import feasibility_boundary as boundary  # noqa: E402

DEFAULT_PROFILE = REPO_ROOT / "configs" / "devices" / "slate-pocket-v1.yaml"
DEFAULT_OUTPUT = REPO_ROOT / "reports" / "constraints" / "boundary-report.txt"


@dataclass(frozen=True)
class BoundaryCheck:
    label: str
    vary: str
    min_value: float
    max_value: float
    step: float
    constraint: str
    target_runtime_h: float = 1.0


DEFAULT_CHECKS = (
    BoundaryCheck(
        label="Minimum thickness for stackup",
        vary="geometry.thickness_mm",
        min_value=8.0,
        max_value=14.0,
        step=0.25,
        constraint="zone_stackup_pass",
    ),
    BoundaryCheck(
        label="Maximum sustained power before thermal becomes extreme",
        vary="compute.sustained_power_w",
        min_value=4.0,
        max_value=40.0,
        step=2.0,
        constraint="thermal_risk_not_extreme",
    ),
    BoundaryCheck(
        label="Maximum ambient temperature before skin temp fails",
        vary="thermal.ambient_c",
        min_value=20.0,
        max_value=50.0,
        step=2.5,
        constraint="skin_temp_pass",
    ),
    BoundaryCheck(
        label="Minimum battery capacity for 1 hour at sustained power",
        vary="battery.capacity_mah",
        min_value=4000.0,
        max_value=10000.0,
        step=500.0,
        constraint="runtime_minimum",
        target_runtime_h=1.0,
    ),
    BoundaryCheck(
        label="Memory capacity runtime budget",
        vary="memory.capacity_gb",
        min_value=64.0,
        max_value=512.0,
        step=64.0,
        constraint="memory_runtime_pass",
    ),
)


def render_default_report(profile_path: Path = DEFAULT_PROFILE) -> str:
    generated = datetime.now(UTC).isoformat(timespec="seconds")
    report_lines = [
        "Default Constraint Boundary Checks",
        f"generated: {generated}",
        f"profile_path: {boundary.repo_relative(profile_path)}",
        "screening_result: screening result, not production validation",
        "",
    ]

    for check in DEFAULT_CHECKS:
        base_profile, rows = boundary.run_boundary(
            profile_path=profile_path,
            parameter_path=check.vary,
            min_value=check.min_value,
            max_value=check.max_value,
            step=check.step,
            constraint=check.constraint,
            target_runtime_h=check.target_runtime_h,
        )
        single_report = boundary.render_report(
            profile=base_profile,
            profile_path=profile_path,
            parameter_path=check.vary,
            min_value=check.min_value,
            max_value=check.max_value,
            step=check.step,
            constraint=check.constraint,
            rows=rows,
        )
        report_lines.extend([f"## {check.label}", single_report.strip(), ""])

    report_lines.extend(
        [
            "Global Notes:",
            "- These checks evaluate explicit constraints over fixed numeric ranges.",
            "- They do not optimize, rank architectures, or modify source device profiles.",
            "- Model limits and warning labels must be reviewed before making engineering decisions.",
        ]
    )
    return "\n".join(report_lines) + "\n"


def main() -> int:
    try:
        report = render_default_report(DEFAULT_PROFILE)
    except (OSError, ValueError, KeyError) as exc:
        print(f"FAIL: {exc}")
        return 1

    DEFAULT_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    DEFAULT_OUTPUT.write_text(report, encoding="utf-8")
    print(report, end="")
    print(f"Report written to: {boundary.repo_relative(DEFAULT_OUTPUT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
