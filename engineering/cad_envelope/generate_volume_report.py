#!/usr/bin/env python3
"""Generate the Slate Pocket first-pass volume-budget report."""

from __future__ import annotations

from pathlib import Path

from slate_pocket_volume_budget import REPO_ROOT, calculate_from_registry

REPORT_PATH = REPO_ROOT / "reports" / "slate-pocket-volume-budget.txt"


def fmt_volume(value_mm3: float) -> str:
    return f"{value_mm3:,.1f} mm^3 ({value_mm3 / 1000.0:,.2f} cm^3)"


def build_report() -> str:
    budget = calculate_from_registry()
    device = budget["device"]
    rows = []
    for component in budget["components"]:
        rows.append(
            f"{component.name:<38} "
            f"{component.length_mm:>7.2f} "
            f"{component.width_mm:>7.2f} "
            f"{component.height_mm:>7.2f} "
            f"{component.count:>5d} "
            f"{component.total_volume_mm3:>14,.1f} "
            f"{component.confidence:<11} "
            f"{component.notes}"
        )

    return "\n".join(
        [
            "Slate Pocket v1 First-Pass Volume Budget",
            "==========================================",
            "",
            "CAVEAT: This is a first-pass bounding-box screening model, not CAD validation,",
            "manufacturability proof, thermal validation, RF validation, CFD, FEA, or supplier-backed packaging evidence.",
            "",
            "Device envelope:",
            f"  Length: {device.length_mm:.2f} mm",
            f"  Width: {device.width_mm:.2f} mm",
            f"  Thickness: {device.height_mm:.2f} mm",
            f"  External volume: {fmt_volume(budget['external_volume_mm3'])}",
            f"  Internal usable volume factor: {budget['internal_usable_volume_factor']:.2f}",
            f"  Estimated internal usable volume: {fmt_volume(budget['usable_volume_mm3'])}",
            "",
            "Component allocation table:",
            f"{'component':<38} {'length':>7} {'width':>7} {'height':>7} {'count':>5} {'volume_mm3':>14} {'confidence':<11} notes",
            f"{'-' * 38} {'-' * 7} {'-' * 7} {'-' * 7} {'-' * 5} {'-' * 14} {'-' * 11} {'-' * 40}",
            *rows,
            "",
            f"Total allocated component volume: {fmt_volume(budget['total_allocated_mm3'])}",
            f"Remaining usable volume: {fmt_volume(budget['remaining_mm3'])}",
            f"Allocation percentage: {budget['allocation_percentage']:.1f}%",
            f"Result: {budget['status']}",
            "",
            "Status thresholds: PASS < 70%; WARNING 70% to 85%; FAIL > 85% of estimated internal usable volume.",
            "",
        ]
    )


def main() -> int:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    report = build_report()
    REPORT_PATH.write_text(report, encoding="utf-8")
    print(f"Wrote {REPORT_PATH.relative_to(REPO_ROOT)}")
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
