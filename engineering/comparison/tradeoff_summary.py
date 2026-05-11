#!/usr/bin/env python3
"""Generate qualitative engineering tradeoff summaries for BuildSlate profiles."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

COMPARISON_DIR = Path(__file__).resolve().parent
if str(COMPARISON_DIR) not in sys.path:
    sys.path.insert(0, str(COMPARISON_DIR))

from compare_profiles import DEFAULT_PROFILES, REPO_ROOT, ProfileComparison, load_comparison  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--profiles",
        nargs="+",
        default=[str(path.relative_to(REPO_ROOT)) for path in DEFAULT_PROFILES],
        help="Device profile YAML paths to summarize.",
    )
    return parser.parse_args()


def by_class_or_id(comparisons: list[ProfileComparison], token: str) -> ProfileComparison | None:
    for item in comparisons:
        haystack = f"{item.profile_id} {item.profile_class}".lower()
        if token in haystack:
            return item
    return None


def build_tradeoff_summary(comparisons: list[ProfileComparison]) -> str:
    lines = [
        "Profile Tradeoff Summary",
        "------------------------",
        "These summaries identify engineering tradeoffs and pressure points only; they do not select a winner.",
    ]
    canonical = by_class_or_id(comparisons, "canonical") or comparisons[0]
    aggressive = by_class_or_id(comparisons, "aggressive")
    conservative = by_class_or_id(comparisons, "conservative")

    if aggressive is not None:
        compute_delta = aggressive.compute_sustained_w - canonical.compute_sustained_w
        npu_delta = aggressive.npu_tops - canonical.npu_tops
        lines.append(
            f"- {aggressive.profile_id} improves compute ambition by {compute_delta:+.0f}W sustained and {npu_delta:+.0f} NPU TOPS versus {canonical.profile_id}, "
            f"but keeps thermal risk at {aggressive.thermal_risk} and manufacturing pressure at {aggressive.manufacturing_pressure}."
        )
        if aggressive.ambient_assumption_c > canonical.ambient_assumption_c or aggressive.brightness_mode != canonical.brightness_mode:
            lines.append(
                f"- {aggressive.profile_id} also raises environmental sensitivity through {aggressive.ambient_assumption_c:.0f}C ambient and {aggressive.brightness_mode} brightness assumptions."
            )

    if conservative is not None:
        power_delta = conservative.compute_sustained_w - canonical.compute_sustained_w
        memory_delta = conservative.memory_capacity_gb - canonical.memory_capacity_gb
        lines.append(
            f"- {conservative.profile_id} reduces sustained compute by {power_delta:.0f}W and memory capacity by {memory_delta:.0f}GB versus {canonical.profile_id}; "
            f"this lowers thermal risk to {conservative.thermal_risk} and stackup pressure to {conservative.stackup_pressure}."
        )
        if conservative.thickness_mm > canonical.thickness_mm:
            lines.append(
                f"- {conservative.profile_id} uses {conservative.thickness_mm - canonical.thickness_mm:.1f}mm more chassis thickness, which is useful as a grounding reference for stackup and passive spreading."
            )

    thinnest = min(comparisons, key=lambda item: item.thickness_mm)
    thickest = max(comparisons, key=lambda item: item.thickness_mm)
    if thinnest.thickness_mm < 9.0:
        thin_group = ", ".join(item.profile_id for item in comparisons if item.thickness_mm == thinnest.thickness_mm)
        lines.append(
            f"- The {thinnest.thickness_mm:.1f}mm chassis group ({thin_group}) strongly correlates with stackup, manufacturing, and thermal pressure in this screening model."
        )
    if thickest.thickness_mm > thinnest.thickness_mm:
        lines.append(
            f"- The thicker {thickest.profile_id} envelope does not prove feasibility, but it exposes how added z-height can reduce integration pressure."
        )

    high_memory = [item for item in comparisons if item.memory_capacity_gb >= 512]
    if high_memory:
        lines.append(
            "- Higher memory capacity increases package count, routing density, and package/interconnect complexity; affected profiles: "
            + ", ".join(item.profile_id for item in high_memory)
            + "."
        )

    for item in comparisons:
        if item.blockers:
            lines.append(f"- {item.profile_id} explicit blockers: {', '.join(item.blockers)}.")
        elif item.warnings:
            lines.append(f"- {item.profile_id} warnings remain visible: {'; '.join(item.warnings)}.")
        else:
            lines.append(f"- {item.profile_id} has no HIGH/EXTREME screening categories, but still requires validation before feasibility claims.")

    lines.append("- No optimization, auto-solving, or best-profile declaration is performed by this summary.")
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    print(build_tradeoff_summary(load_comparison(args.profiles)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
