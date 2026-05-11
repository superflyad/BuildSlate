#!/usr/bin/env python3
"""Print a compact pressure matrix for BuildSlate device profiles."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

COMPARISON_DIR = Path(__file__).resolve().parent
if str(COMPARISON_DIR) not in sys.path:
    sys.path.insert(0, str(COMPARISON_DIR))

from compare_profiles import DEFAULT_PROFILES, REPO_ROOT, ProfileComparison, load_comparison, repo_relative, table  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--profiles",
        nargs="+",
        default=[str(path.relative_to(REPO_ROOT)) for path in DEFAULT_PROFILES],
        help="Device profile YAML paths to include in the pressure matrix.",
    )
    return parser.parse_args()


def confidence_level(item: ProfileComparison) -> str:
    if item.blockers:
        return "LOW"
    if item.warnings:
        return "MODERATE"
    return "HIGH"


def build_matrix(profile_paths: list[str]) -> str:
    comparisons = load_comparison(profile_paths)
    return table(
        "Profile Engineering Pressure Matrix",
        [
            "profile",
            "status",
            "targets",
            "confidence",
            "warnings",
            "blockers",
            "thermal",
            "mass",
            "stackup",
            "runtime",
            "manufacturing",
            "environment",
        ],
        [
            [
                item.profile_id,
                item.feasibility_status,
                f"{item.profile_class}; {item.compute_sustained_w:.0f}W; {item.memory_capacity_gb:.0f}GB",
                confidence_level(item),
                "; ".join(item.warnings) if item.warnings else "none",
                "; ".join(item.blockers) if item.blockers else "none",
                item.thermal_risk,
                item.mass_pressure,
                item.stackup_pressure,
                item.memory_reserve_pressure,
                item.manufacturing_pressure,
                item.environmental_sensitivity,
            ]
            for item in comparisons
        ],
    )


def main() -> int:
    args = parse_args()
    print(build_matrix(args.profiles))
    print("\nLegend: LOW, MODERATE, HIGH, and EXTREME are qualitative screening categories, not optimization scores.")
    print("Profiles compared:")
    for path_text in args.profiles:
        print(f"- {repo_relative((REPO_ROOT / path_text).resolve()) if not Path(path_text).is_absolute() else path_text}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
