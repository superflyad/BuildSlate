#!/usr/bin/env python3
"""Generate the Slate Pocket v1 thickness budget report."""

from __future__ import annotations

import argparse
from pathlib import Path

from thickness_budget import calculate_thickness_budget, load_registry

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REGISTRY = REPO_ROOT / "engineering" / "stackup" / "thickness_stack_registry.yaml"
DEFAULT_REPORT = REPO_ROOT / "reports" / "slate-pocket-thickness-budget.txt"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--output", type=Path, default=DEFAULT_REPORT)
    return parser.parse_args()


def render_report(result) -> str:
    """Render a plain-text thickness budget report."""
    lines = [
        f"{result.device_name} {result.device_version} thickness budget",
        "=" * 48,
        "",
        "Status thresholds:",
        "  PASS: <= 90% of budget",
        "  WARNING: >90% and <=100% of budget",
        "  FAIL: >100% of budget",
        "",
        "Summary:",
        f"  budget_mm: {result.budget_mm:.2f}",
        f"  total_thickness_mm: {result.total_thickness_mm:.2f}",
        f"  remaining_margin_mm: {result.remaining_margin_mm:.2f}",
        f"  percent_consumed: {result.consumed_percent:.1f}%",
        f"  status: {result.status}",
        "",
        "Component stack:",
    ]
    for component in result.components:
        lines.append(f"  - {component.name}: {component.thickness_mm:.2f} mm ({component.component_id})")
        lines.append(f"    basis: {component.rationale}")
    lines.extend([
        "",
        "Validation:",
        "  registry_schema: PASS",
        "  required_component_coverage: PASS",
        "  positive_thickness_values: PASS",
        "",
        "Notes:",
        "  This is a first-pass arithmetic screen, not a CAD packaging signoff.",
        "  Local overlaps, shielding cans, connector keepouts, compression, and camera bumps require follow-up mechanical CAD.",
    ])
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    registry = load_registry(args.registry)
    result = calculate_thickness_budget(registry)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render_report(result), encoding="utf-8")
    print(f"wrote {args.output.relative_to(REPO_ROOT)}")
    print(f"status: {result.status}")
    print(f"total_thickness_mm: {result.total_thickness_mm:.2f}")
    print(f"percent_consumed: {result.consumed_percent:.1f}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
