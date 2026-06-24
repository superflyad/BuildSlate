#!/usr/bin/env python3
"""Slate Pocket v1 physical recovery planner."""

from __future__ import annotations

import itertools
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from engineering.physical_feasibility.physical_feasibility_gate import (  # noqa: E402
    GateDecision,
    PhysicalFeasibilityResult,
    evaluate_gate,
)

SCENARIO_PATH = REPO_ROOT / "engineering" / "recovery" / "recovery_scenarios.yaml"

ENGINEERING_COST_VALUES = ("low", "medium", "high", "extreme")
PRODUCT_IMPACT_VALUES = ("low", "medium", "high", "extreme")
MATURITY_VALUES = ("placeholder", "estimate", "supplier", "measured")
REQUIRED_SCENARIO_FIELDS = (
    "description",
    "affected_components",
    "estimated_volume_delta_mm3",
    "estimated_thickness_delta_mm",
    "engineering_cost",
    "product_impact",
    "maturity",
    "notes",
)


@dataclass(frozen=True)
class RecoveryScenario:
    """One screening-level packaging recovery option."""

    scenario_id: str
    description: str
    affected_components: tuple[str, ...]
    estimated_volume_delta_mm3: float
    estimated_thickness_delta_mm: float
    engineering_cost: str
    product_impact: str
    maturity: str
    notes: str

    @property
    def increases_envelope(self) -> bool:
        return self.scenario_id.startswith("increase_thickness_to_")


@dataclass(frozen=True)
class RecoveryEvaluation:
    """Projected physical budget state after one or more recovery scenarios."""

    scenario_ids: tuple[str, ...]
    scenarios: tuple[RecoveryScenario, ...]
    projected_allocated_volume_mm3: float
    projected_usable_volume_mm3: float
    projected_volume_remaining_mm3: float
    projected_volume_allocation_percent: float
    projected_stackup_mm: float
    projected_thickness_budget_mm: float
    projected_thickness_margin_mm: float
    projected_thickness_consumed_percent: float
    volume_status: str
    thickness_status: str
    fix_classification: str
    total_product_impact_score: int
    total_engineering_cost_score: int
    total_maturity_score: int
    volume_gap_to_conditional_mm3: float
    thickness_gap_to_conditional_mm: float


@dataclass(frozen=True)
class RecoveryPlan:
    """Full physical recovery planning result."""

    gate_result: PhysicalFeasibilityResult
    current_volume_margin_mm3: float
    current_volume_gap_to_conditional_mm3: float
    current_thickness_margin_mm: float
    current_thickness_gap_to_conditional_mm: float
    scenarios: tuple[RecoveryScenario, ...]
    single_scenario_results: tuple[RecoveryEvaluation, ...]
    combined_results: tuple[RecoveryEvaluation, ...]
    ranked_combined_results: tuple[RecoveryEvaluation, ...]
    recommendation: RecoveryEvaluation
    recommendation_is_sufficient: bool


def _load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as input_file:
        data = yaml.safe_load(input_file)
    if not isinstance(data, dict):
        raise ValueError(f"{path.relative_to(REPO_ROOT)} must contain a mapping")
    return data


def validate_scenario_registry(path: Path = SCENARIO_PATH) -> None:
    """Validate scenario registry shape and enums."""
    if not path.exists():
        raise ValueError(f"recovery scenario registry missing: {path.relative_to(REPO_ROOT)}")

    data = _load_yaml(path)
    scenarios = data.get("scenarios")
    if not isinstance(scenarios, dict) or not scenarios:
        raise ValueError("recovery_scenarios.yaml must define a non-empty scenarios mapping")

    for scenario_id, entry in scenarios.items():
        if not isinstance(scenario_id, str) or not scenario_id.strip():
            raise ValueError("scenario ids must be non-empty strings")
        if not isinstance(entry, dict):
            raise ValueError(f"{scenario_id} must be a mapping")

        missing = [field for field in REQUIRED_SCENARIO_FIELDS if field not in entry]
        if missing:
            raise ValueError(f"{scenario_id} missing required fields: {', '.join(missing)}")

        if not isinstance(entry["description"], str) or not entry["description"].strip():
            raise ValueError(f"{scenario_id}.description must be a non-empty string")
        if not isinstance(entry["affected_components"], list) or not entry["affected_components"]:
            raise ValueError(f"{scenario_id}.affected_components must be a non-empty list")
        if not all(isinstance(component, str) and component.strip() for component in entry["affected_components"]):
            raise ValueError(f"{scenario_id}.affected_components values must be non-empty strings")
        if not isinstance(entry["estimated_volume_delta_mm3"], int | float) or isinstance(
            entry["estimated_volume_delta_mm3"], bool
        ):
            raise ValueError(f"{scenario_id}.estimated_volume_delta_mm3 must be numeric")
        if not isinstance(entry["estimated_thickness_delta_mm"], int | float) or isinstance(
            entry["estimated_thickness_delta_mm"], bool
        ):
            raise ValueError(f"{scenario_id}.estimated_thickness_delta_mm must be numeric")
        if entry["engineering_cost"] not in ENGINEERING_COST_VALUES:
            raise ValueError(f"{scenario_id}.engineering_cost must be one of {ENGINEERING_COST_VALUES}")
        if entry["product_impact"] not in PRODUCT_IMPACT_VALUES:
            raise ValueError(f"{scenario_id}.product_impact must be one of {PRODUCT_IMPACT_VALUES}")
        if entry["maturity"] not in MATURITY_VALUES:
            raise ValueError(f"{scenario_id}.maturity must be one of {MATURITY_VALUES}")
        if not isinstance(entry["notes"], str) or not entry["notes"].strip():
            raise ValueError(f"{scenario_id}.notes must be a non-empty string")


def load_scenarios(path: Path = SCENARIO_PATH) -> tuple[RecoveryScenario, ...]:
    """Load validated recovery scenarios."""
    validate_scenario_registry(path)
    data = _load_yaml(path)
    scenarios = []
    for scenario_id, entry in data["scenarios"].items():
        scenarios.append(
            RecoveryScenario(
                scenario_id=scenario_id,
                description=entry["description"].strip(),
                affected_components=tuple(component.strip() for component in entry["affected_components"]),
                estimated_volume_delta_mm3=float(entry["estimated_volume_delta_mm3"]),
                estimated_thickness_delta_mm=float(entry["estimated_thickness_delta_mm"]),
                engineering_cost=entry["engineering_cost"],
                product_impact=entry["product_impact"],
                maturity=entry["maturity"],
                notes=entry["notes"].strip(),
            )
        )
    return tuple(scenarios)


def _volume_status(allocation_percent: float) -> str:
    if allocation_percent < 70.0:
        return "PASS"
    if allocation_percent <= 85.0:
        return "WARNING"
    return "FAIL"


def _thickness_status(consumed_percent: float) -> str:
    if consumed_percent <= 90.0:
        return "PASS"
    if consumed_percent <= 100.0:
        return "WARNING"
    return "FAIL"


def _impact_score(value: str) -> int:
    return PRODUCT_IMPACT_VALUES.index(value)


def _cost_score(value: str) -> int:
    return ENGINEERING_COST_VALUES.index(value)


def _maturity_score(value: str) -> int:
    return MATURITY_VALUES.index(value)


def _fix_classification(volume_fixed: bool, thickness_fixed: bool) -> str:
    if volume_fixed and thickness_fixed:
        return "both"
    if volume_fixed:
        return "volume only"
    if thickness_fixed:
        return "thickness only"
    return "neither"


def _evaluate_scenario_set(
    gate_result: PhysicalFeasibilityResult,
    scenarios: tuple[RecoveryScenario, ...],
) -> RecoveryEvaluation:
    volume = gate_result.volume_budget
    thickness = gate_result.thickness_budget

    allocated_volume_mm3 = float(volume["total_allocated_mm3"])
    usable_volume_mm3 = float(volume["usable_volume_mm3"])
    stackup_mm = float(thickness.total_thickness_mm)
    thickness_budget_mm = float(thickness.budget_mm)

    for scenario in scenarios:
        if scenario.increases_envelope:
            usable_volume_mm3 += scenario.estimated_volume_delta_mm3
            thickness_budget_mm += scenario.estimated_thickness_delta_mm
        else:
            allocated_volume_mm3 += scenario.estimated_volume_delta_mm3
            stackup_mm += scenario.estimated_thickness_delta_mm

    volume_remaining_mm3 = usable_volume_mm3 - allocated_volume_mm3
    allocation_percent = allocated_volume_mm3 / usable_volume_mm3 * 100.0
    thickness_margin_mm = thickness_budget_mm - stackup_mm
    thickness_consumed_percent = stackup_mm / thickness_budget_mm * 100.0
    volume_status = _volume_status(allocation_percent)
    thickness_status = _thickness_status(thickness_consumed_percent)
    volume_fixed = volume_status != "FAIL"
    thickness_fixed = thickness_status != "FAIL"
    volume_target_mm3 = usable_volume_mm3 * 0.85

    return RecoveryEvaluation(
        scenario_ids=tuple(scenario.scenario_id for scenario in scenarios),
        scenarios=scenarios,
        projected_allocated_volume_mm3=allocated_volume_mm3,
        projected_usable_volume_mm3=usable_volume_mm3,
        projected_volume_remaining_mm3=volume_remaining_mm3,
        projected_volume_allocation_percent=allocation_percent,
        projected_stackup_mm=stackup_mm,
        projected_thickness_budget_mm=thickness_budget_mm,
        projected_thickness_margin_mm=thickness_margin_mm,
        projected_thickness_consumed_percent=thickness_consumed_percent,
        volume_status=volume_status,
        thickness_status=thickness_status,
        fix_classification=_fix_classification(volume_fixed, thickness_fixed),
        total_product_impact_score=sum(_impact_score(scenario.product_impact) for scenario in scenarios),
        total_engineering_cost_score=sum(_cost_score(scenario.engineering_cost) for scenario in scenarios),
        total_maturity_score=sum(_maturity_score(scenario.maturity) for scenario in scenarios),
        volume_gap_to_conditional_mm3=max(0.0, allocated_volume_mm3 - volume_target_mm3),
        thickness_gap_to_conditional_mm=max(0.0, stackup_mm - thickness_budget_mm),
    )


def _sort_key(evaluation: RecoveryEvaluation) -> tuple[float, ...]:
    fixes_both_rank = 0 if evaluation.fix_classification == "both" else 1
    mutually_exclusive_rank = 1 if sum(scenario.increases_envelope for scenario in evaluation.scenarios) > 1 else 0
    closeness_gap = evaluation.volume_gap_to_conditional_mm3 / 1000.0 + evaluation.thickness_gap_to_conditional_mm * 100.0
    return (
        fixes_both_rank,
        mutually_exclusive_rank,
        evaluation.total_product_impact_score,
        evaluation.total_engineering_cost_score,
        -evaluation.total_maturity_score,
        closeness_gap,
        len(evaluation.scenario_ids),
        evaluation.projected_volume_allocation_percent,
        evaluation.projected_thickness_consumed_percent,
    )


def build_recovery_plan() -> RecoveryPlan:
    """Evaluate single and combined recovery scenarios from the current gate result."""
    gate_result = evaluate_gate()
    scenarios = load_scenarios()
    single_results = tuple(_evaluate_scenario_set(gate_result, (scenario,)) for scenario in scenarios)

    combined: list[RecoveryEvaluation] = []
    for combination_size in (2, 3):
        for scenario_set in itertools.combinations(scenarios, combination_size):
            combined.append(_evaluate_scenario_set(gate_result, scenario_set))

    ranked = tuple(sorted(combined, key=_sort_key))
    recommendation = ranked[0]
    return RecoveryPlan(
        gate_result=gate_result,
        current_volume_margin_mm3=float(gate_result.volume_budget["remaining_mm3"]),
        current_volume_gap_to_conditional_mm3=max(
            0.0,
            float(gate_result.volume_budget["total_allocated_mm3"])
            - float(gate_result.volume_budget["usable_volume_mm3"]) * 0.85,
        ),
        current_thickness_margin_mm=float(gate_result.thickness_budget.remaining_margin_mm),
        current_thickness_gap_to_conditional_mm=max(0.0, -float(gate_result.thickness_budget.remaining_margin_mm)),
        scenarios=scenarios,
        single_scenario_results=single_results,
        combined_results=tuple(combined),
        ranked_combined_results=ranked,
        recommendation=recommendation,
        recommendation_is_sufficient=recommendation.fix_classification == "both",
    )
