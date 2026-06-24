#!/usr/bin/env python3
"""Generate the Slate Pocket v1 physical-feasibility gate report."""

from __future__ import annotations

from pathlib import Path

from physical_feasibility_gate import REPO_ROOT, SCREENING_CAVEAT, PhysicalFeasibilityResult, evaluate_gate

REPORT_PATH = REPO_ROOT / "reports" / "slate-pocket-physical-feasibility-gate.txt"


def _fmt_mm3(value_mm3: float) -> str:
    return f"{value_mm3:,.1f} mm^3 ({value_mm3 / 1000.0:,.2f} cm^3)"


def _fmt_counts(counts: dict[str, int]) -> str:
    if not counts:
        return "none"
    return ", ".join(f"{key}: {value}" for key, value in sorted(counts.items()))


def render_report(result: PhysicalFeasibilityResult) -> str:
    """Render a plain-text physical-feasibility report."""
    volume = result.volume_budget
    thickness = result.thickness_budget
    maturity = result.component_maturity
    targets = result.targets

    lines = [
        "Slate Pocket v1 Physical Feasibility Gate",
        "==========================================",
        "",
        "Scope:",
        "  device: Slate Pocket v1",
        "  gate version: physical feasibility v1",
        "  purpose: decide whether the physical package can continue to thermal/PCB/RF screening",
        "",
        "Canonical target inputs:",
        f"  display: {targets['display_size_in']} in",
        f"  battery: {targets['battery_capacity_mah']} mAh",
        f"  memory: {targets['memory_capacity_gb']} GB RAM",
        f"  storage: {targets['storage_capacity_tb']} TB",
        f"  cooling: {targets['cooling']}",
        f"  NPU: {targets['npu_tops']} TOPS",
        f"  target mass: {targets['target_mass_g']} g",
        f"  target thickness: {targets['thickness_mm']} mm",
        "",
        "Input sources:",
        "  volume budget: engineering/cad_envelope/component_volume_registry.yaml",
        "  thickness stackup: engineering/stackup/thickness_stack_registry.yaml",
        "  component candidates: research/components/component_candidates.yaml",
        "  component selection status: research/components/component_selection_status.yaml",
        "",
        "Volume budget result:",
        f"  status: {volume['status']}",
        f"  external volume: {_fmt_mm3(volume['external_volume_mm3'])}",
        f"  estimated usable internal volume: {_fmt_mm3(volume['usable_volume_mm3'])}",
        f"  allocated component volume: {_fmt_mm3(volume['total_allocated_mm3'])}",
        f"  remaining usable volume: {_fmt_mm3(volume['remaining_mm3'])}",
        f"  allocation percentage: {volume['allocation_percentage']:.1f}%",
        "",
        "Thickness stackup result:",
        f"  status: {thickness.status}",
        f"  budget: {thickness.budget_mm:.2f} mm",
        f"  total stackup: {thickness.total_thickness_mm:.2f} mm",
        f"  remaining margin: {thickness.remaining_margin_mm:.2f} mm",
        f"  percent consumed: {thickness.consumed_percent:.1f}%",
        "",
        "Component candidate maturity summary:",
        f"  categories tracked: {maturity.category_count}",
        f"  candidates tracked: {maturity.candidate_count}",
        f"  candidate statuses: {_fmt_counts(maturity.candidate_status_counts)}",
        f"  category statuses: {_fmt_counts(maturity.category_status_counts)}",
        f"  confidence levels: {_fmt_counts(maturity.confidence_counts)}",
        f"  supplier-backed research candidates: {maturity.supplier_backed_candidate_count}",
        f"  selected categories: {maturity.selected_category_count}",
        f"  speculative or low-confidence candidates: {maturity.speculative_or_placeholder_count}",
        f"  majority speculative/placeholders: {maturity.most_components_speculative_or_placeholder}",
        "",
        "Major physical blockers:",
    ]
    lines.extend(f"  - {blocker}" for blocker in result.major_blockers)
    lines.extend(
        [
            "",
            "Required evidence before next phase:",
        ]
    )
    lines.extend(f"  - {evidence}" for evidence in result.required_evidence)
    lines.extend(
        [
            "",
            "Final gate decision:",
            f"  GATE_DECISION: {result.decision.value}",
            "",
            "Decision interpretation:",
            _decision_interpretation(result.decision.value),
            "",
            "Caveat:",
            f"  {SCREENING_CAVEAT}",
            "",
        ]
    )
    return "\n".join(lines)


def _decision_interpretation(decision: str) -> str:
    if decision == "PASS_TO_THERMAL_SCREENING":
        return "  Physical budgets are clean enough to proceed to thermal, PCB, RF, and manufacturing screening."
    if decision == "CONDITIONAL_PASS":
        return "  Physical budgets are not failed, but warnings must be resolved or explicitly accepted before stronger claims."
    if decision == "BLOCKED_BY_VOLUME":
        return "  The physical package is blocked by the current volume budget."
    if decision == "BLOCKED_BY_THICKNESS":
        return "  The physical package is blocked by the current thickness stackup."
    if decision == "BLOCKED_BY_COMPONENT_UNCERTAINTY":
        return "  The physical package is blocked until component candidates mature beyond speculative placeholders."
    if decision == "BLOCKED_BY_MULTIPLE_CONSTRAINTS":
        return "  The physical package is blocked by both volume and thickness constraints."
    return "  Unknown decision value."


def build_report() -> str:
    return render_report(evaluate_gate())


def main() -> int:
    report = build_report()
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(report, encoding="utf-8")
    print(f"Wrote {REPORT_PATH.relative_to(REPO_ROOT)}")
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
