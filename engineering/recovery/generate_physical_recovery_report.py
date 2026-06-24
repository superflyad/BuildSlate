#!/usr/bin/env python3
"""Generate the Slate Pocket v1 physical recovery plan report."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from engineering.recovery.physical_recovery_planner import (  # noqa: E402
    RecoveryEvaluation,
    RecoveryPlan,
    build_recovery_plan,
)

REPORT_PATH = REPO_ROOT / "reports" / "slate-pocket-physical-recovery-plan.txt"
SCREENING_CAVEAT = (
    "These are screening-level tradeoffs, not validated design changes. They do not replace CAD packaging, "
    "supplier drawings, thermal simulation, RF validation, certification work, or prototype measurements."
)


def _fmt_mm3(value_mm3: float) -> str:
    return f"{value_mm3:,.1f} mm^3 ({value_mm3 / 1000.0:,.2f} cm^3)"


def _fmt_mm(value_mm: float) -> str:
    return f"{value_mm:.2f} mm"


def _scenario_label(evaluation: RecoveryEvaluation) -> str:
    return " + ".join(evaluation.scenario_ids)


def _render_evaluation_summary(evaluation: RecoveryEvaluation) -> list[str]:
    return [
        f"    projected allocated volume: {_fmt_mm3(evaluation.projected_allocated_volume_mm3)}",
        f"    projected usable volume: {_fmt_mm3(evaluation.projected_usable_volume_mm3)}",
        f"    projected volume allocation: {evaluation.projected_volume_allocation_percent:.1f}% "
        f"({evaluation.volume_status}); margin: {_fmt_mm3(evaluation.projected_volume_remaining_mm3)}",
        f"    projected thickness stackup: {_fmt_mm(evaluation.projected_stackup_mm)}",
        f"    projected thickness budget: {_fmt_mm(evaluation.projected_thickness_budget_mm)}",
        f"    projected thickness consumption: {evaluation.projected_thickness_consumed_percent:.1f}% "
        f"({evaluation.thickness_status}); margin: {_fmt_mm(evaluation.projected_thickness_margin_mm)}",
        f"    fixes: {evaluation.fix_classification}",
    ]


def render_report(plan: RecoveryPlan) -> str:
    """Render the physical recovery plan as plain text."""
    gate = plan.gate_result
    volume = gate.volume_budget
    thickness = gate.thickness_budget
    recommendation_status = "SUFFICIENT" if plan.recommendation_is_sufficient else "INSUFFICIENT"

    lines = [
        "Slate Pocket v1 Physical Recovery Planner v1",
        "=============================================",
        "",
        "Current blocked state:",
        f"  GATE_DECISION: {gate.decision.value}",
        f"  volume status: {volume['status']}",
        f"  thickness status: {thickness.status}",
        "",
        "Current physical budget:",
        f"  usable internal volume: {_fmt_mm3(volume['usable_volume_mm3'])}",
        f"  allocated component volume: {_fmt_mm3(volume['total_allocated_mm3'])}",
        f"  current volume margin: {_fmt_mm3(plan.current_volume_margin_mm3)}",
        f"  current volume recovery gap to 85% allocation: {_fmt_mm3(plan.current_volume_gap_to_conditional_mm3)}",
        f"  current volume allocation: {volume['allocation_percentage']:.1f}%",
        f"  thickness budget: {_fmt_mm(thickness.budget_mm)}",
        f"  thickness stackup: {_fmt_mm(thickness.total_thickness_mm)}",
        f"  current thickness margin: {_fmt_mm(plan.current_thickness_margin_mm)}",
        f"  current thickness recovery gap to 100% budget: {_fmt_mm(plan.current_thickness_gap_to_conditional_mm)}",
        f"  current thickness consumption: {thickness.consumed_percent:.1f}%",
        "",
        "Input sources:",
        "  volume budget data: engineering/cad_envelope/component_volume_registry.yaml",
        "  thickness stackup data: engineering/stackup/thickness_stack_registry.yaml",
        "  physical feasibility gate result: engineering/physical_feasibility/physical_feasibility_gate.py",
        "  recovery scenarios: engineering/recovery/recovery_scenarios.yaml",
        "",
        "Single-scenario results:",
    ]

    for evaluation in plan.single_scenario_results:
        scenario = evaluation.scenarios[0]
        lines.extend(
            [
                f"  - {scenario.scenario_id}",
                f"    description: {scenario.description}",
                f"    affected components: {', '.join(scenario.affected_components)}",
                f"    estimated volume delta: {_fmt_mm3(scenario.estimated_volume_delta_mm3)}",
                f"    estimated thickness delta: {_fmt_mm(scenario.estimated_thickness_delta_mm)}",
                f"    engineering cost: {scenario.engineering_cost}",
                f"    product impact: {scenario.product_impact}",
                f"    maturity: {scenario.maturity}",
                f"    notes: {scenario.notes}",
            ]
        )
        lines.extend(_render_evaluation_summary(evaluation))

    lines.extend(["", "Top 10 combined recovery paths:"])
    for index, evaluation in enumerate(plan.ranked_combined_results[:10], start=1):
        lines.append(f"  {index}. {_scenario_label(evaluation)}")
        lines.extend(_render_evaluation_summary(evaluation))
        lines.append(
            "    ranking inputs: "
            f"product impact score {evaluation.total_product_impact_score}, "
            f"engineering cost score {evaluation.total_engineering_cost_score}, "
            f"maturity score {evaluation.total_maturity_score}"
        )

    lines.extend(
        [
            "",
            "Recommended recovery path:",
            f"  status: {recommendation_status}",
            f"  path: {_scenario_label(plan.recommendation)}",
        ]
    )
    lines.extend(_render_evaluation_summary(plan.recommendation))

    if plan.recommendation_is_sufficient:
        lines.append(
            "  recommendation: Prefer this as the least disruptive ranked combination that fixes both physical constraints."
        )
    else:
        lines.append(
            "  recommendation: No evaluated combination fixes both constraints; this path is closest but Slate Pocket v1 remains physically blocked."
        )

    lines.extend(["", "Caveat:", f"  {SCREENING_CAVEAT}", ""])
    return "\n".join(lines)


def build_report() -> str:
    return render_report(build_recovery_plan())


def main() -> int:
    report = build_report()
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(report, encoding="utf-8")
    print(f"Wrote {REPORT_PATH.relative_to(REPO_ROOT)}")
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
