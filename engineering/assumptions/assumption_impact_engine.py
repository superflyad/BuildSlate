#!/usr/bin/env python3
"""Static assumption impact engine for Slate Pocket traceability."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = REPO_ROOT / "engineering" / "assumptions" / "assumption_registry.yaml"

REQUIRED_ASSUMPTIONS = (
    "device_thickness_mm",
    "battery_capacity_mah",
    "battery_volume_mm3",
    "sustained_compute_w",
    "peak_compute_w",
    "npu_tops",
    "memory_capacity_gb",
    "storage_capacity_tb",
    "max_skin_temp_c",
    "internal_usable_volume_factor",
    "thermal_module_thickness_mm",
    "wireless_charging_enabled",
)

REQUIRED_FIELDS = (
    "value",
    "unit",
    "profile_scope",
    "confidence",
    "maturity",
    "affected_domains",
    "affected_reports",
    "downstream_decisions",
    "evidence_required",
    "notes",
)

PROFILE_SCOPES = ("v1", "v1r", "both")
CONFIDENCE_VALUES = ("placeholder", "estimate", "supplier", "measured")
MATURITY_VALUES = ("concept", "screening", "first_order", "calibrated", "validated")


class FragilityRating(StrEnum):
    """Ordered assumption fragility ratings."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


FRAGILITY_RANK = {
    FragilityRating.CRITICAL: 0,
    FragilityRating.HIGH: 1,
    FragilityRating.MEDIUM: 2,
    FragilityRating.LOW: 3,
}


@dataclass(frozen=True)
class AssumptionImpact:
    """Rendered impact summary for one assumption."""

    assumption_id: str
    value: Any
    unit: str
    profile_scope: str
    confidence: str
    maturity: str
    affected_domains: tuple[str, ...]
    affected_reports: tuple[str, ...]
    downstream_decisions: tuple[str, ...]
    affected_gate_decisions: tuple[str, ...]
    evidence_required: tuple[str, ...]
    notes: str
    fragility: FragilityRating


def load_registry(path: Path = REGISTRY_PATH) -> dict[str, Any]:
    """Load the static assumption impact registry."""
    if not path.exists():
        raise ValueError(f"registry missing: {path.relative_to(REPO_ROOT)}")
    with path.open("r", encoding="utf-8") as input_file:
        data = yaml.safe_load(input_file)
    if not isinstance(data, dict):
        raise ValueError("assumption registry root must be a mapping")
    return data


def _require_non_empty_list(entry: dict[str, Any], field: str, assumption_id: str) -> tuple[str, ...]:
    value = entry.get(field)
    if not isinstance(value, list) or not value:
        raise ValueError(f"{assumption_id}.{field} must be a non-empty list")
    if not all(isinstance(item, str) and item.strip() for item in value):
        raise ValueError(f"{assumption_id}.{field} must contain non-empty strings")
    return tuple(item.strip() for item in value)


def validate_registry(registry: dict[str, Any]) -> None:
    """Validate assumption registry shape, required entries, and enums."""
    assumptions = registry.get("assumptions")
    if not isinstance(assumptions, dict) or not assumptions:
        raise ValueError("assumption registry must define a non-empty assumptions mapping")

    missing_assumptions = [assumption_id for assumption_id in REQUIRED_ASSUMPTIONS if assumption_id not in assumptions]
    if missing_assumptions:
        raise ValueError(f"missing required assumptions: {', '.join(missing_assumptions)}")

    for assumption_id, entry in assumptions.items():
        if not isinstance(entry, dict):
            raise ValueError(f"{assumption_id} must be a mapping")
        missing_fields = [field for field in REQUIRED_FIELDS if field not in entry]
        if missing_fields:
            raise ValueError(f"{assumption_id} missing required fields: {', '.join(missing_fields)}")
        if entry["profile_scope"] not in PROFILE_SCOPES:
            raise ValueError(f"{assumption_id}.profile_scope must be one of: {', '.join(PROFILE_SCOPES)}")
        if entry["confidence"] not in CONFIDENCE_VALUES:
            raise ValueError(f"{assumption_id}.confidence must be one of: {', '.join(CONFIDENCE_VALUES)}")
        if entry["maturity"] not in MATURITY_VALUES:
            raise ValueError(f"{assumption_id}.maturity must be one of: {', '.join(MATURITY_VALUES)}")
        if not isinstance(entry["unit"], str) or not entry["unit"].strip():
            raise ValueError(f"{assumption_id}.unit must be a non-empty string")
        if not isinstance(entry["notes"], str) or not entry["notes"].strip():
            raise ValueError(f"{assumption_id}.notes must be a non-empty string")
        for list_field in ("affected_domains", "affected_reports", "downstream_decisions", "evidence_required"):
            _require_non_empty_list(entry, list_field, assumption_id)


def _affected_gate_decisions(decisions: tuple[str, ...]) -> tuple[str, ...]:
    gate_terms = ("gate", "physical feasibility", "thermal consequence", "recovery planner")
    gate_decisions = [decision for decision in decisions if any(term in decision.lower() for term in gate_terms)]
    return tuple(gate_decisions)


def score_fragility(
    confidence: str,
    maturity: str,
    affected_domains: tuple[str, ...],
    affected_reports: tuple[str, ...],
    affected_gate_decisions: tuple[str, ...],
    evidence_required: tuple[str, ...],
) -> FragilityRating:
    """Score assumption fragility from static traceability metadata."""
    affects_gate = bool(affected_gate_decisions)
    if confidence == "placeholder" and affects_gate:
        return FragilityRating.CRITICAL
    if len(evidence_required) >= 3 and len(affected_domains) >= 3:
        return FragilityRating.CRITICAL
    if confidence == "estimate" and len(affected_reports) >= 3:
        return FragilityRating.HIGH
    if maturity in {"concept", "screening"} and affects_gate:
        return FragilityRating.HIGH
    if len(affected_reports) >= 2 or len(affected_domains) >= 2:
        return FragilityRating.MEDIUM
    return FragilityRating.LOW


def build_impacts(registry: dict[str, Any] | None = None) -> tuple[AssumptionImpact, ...]:
    """Build scored assumption impact rows from the static registry."""
    data = registry if registry is not None else load_registry()
    validate_registry(data)
    impacts: list[AssumptionImpact] = []
    for assumption_id, entry in data["assumptions"].items():
        affected_domains = _require_non_empty_list(entry, "affected_domains", assumption_id)
        affected_reports = _require_non_empty_list(entry, "affected_reports", assumption_id)
        downstream_decisions = _require_non_empty_list(entry, "downstream_decisions", assumption_id)
        evidence_required = _require_non_empty_list(entry, "evidence_required", assumption_id)
        affected_gate_decisions = _affected_gate_decisions(downstream_decisions)
        fragility = score_fragility(
            confidence=entry["confidence"],
            maturity=entry["maturity"],
            affected_domains=affected_domains,
            affected_reports=affected_reports,
            affected_gate_decisions=affected_gate_decisions,
            evidence_required=evidence_required,
        )
        impacts.append(
            AssumptionImpact(
                assumption_id=assumption_id,
                value=entry["value"],
                unit=entry["unit"],
                profile_scope=entry["profile_scope"],
                confidence=entry["confidence"],
                maturity=entry["maturity"],
                affected_domains=affected_domains,
                affected_reports=affected_reports,
                downstream_decisions=downstream_decisions,
                affected_gate_decisions=affected_gate_decisions,
                evidence_required=evidence_required,
                notes=entry["notes"],
                fragility=fragility,
            )
        )
    return tuple(impacts)


def ranked_impacts(impacts: tuple[AssumptionImpact, ...]) -> tuple[AssumptionImpact, ...]:
    """Rank assumptions by fragility and breadth of impact."""
    return tuple(
        sorted(
            impacts,
            key=lambda impact: (
                FRAGILITY_RANK[impact.fragility],
                -len(impact.affected_gate_decisions),
                -len(impact.affected_domains),
                -len(impact.affected_reports),
                impact.assumption_id,
            ),
        )
    )


def _fmt_value(value: Any, unit: str) -> str:
    if unit == "boolean":
        return str(value).lower()
    return f"{value} {unit}"


def _render_list(items: tuple[str, ...], indent: str = "    ") -> list[str]:
    return [f"{indent}- {item}" for item in items]


def _what_breaks_first() -> tuple[str, ...]:
    return (
        "If sustained_compute_w increases, thermal consequence and skin temperature risk are affected first.",
        "If device_thickness_mm decreases, thickness stackup and physical feasibility gate are affected first.",
        "If battery_volume_mm3 decreases, volume improves but runtime, C-rate, charging heat, swelling, and safety risk may worsen.",
        "If internal_usable_volume_factor decreases, the CAD envelope report and physical feasibility gate can fail before component targets change.",
        "If memory_capacity_gb increases, package count, routing, power, thermal load, and runtime memory reports are affected first.",
        "If max_skin_temp_c decreases, thermal consequence, throttle policy, and operating-condition decisions become tighter first.",
        "If wireless_charging_enabled remains true, z-height, rear-material, RF, and charging heat constraints stay coupled to the package.",
    )


def render_report(impacts: tuple[AssumptionImpact, ...] | None = None) -> str:
    """Render the static assumption impact report."""
    impact_rows = impacts if impacts is not None else build_impacts()
    ranked = ranked_impacts(impact_rows)
    lines = [
        "Slate Pocket Assumption Impact Engine v1",
        "=========================================",
        "",
        "Scope:",
        "  device profiles: slate-pocket-v1 and slate-pocket-v1r",
        "  purpose: explain which reports, gates, risks, and downstream decisions are affected when a tracked assumption changes",
        "  method: static traceability over assumption metadata; no dynamic model recomputation is performed",
        "",
        "Caveat:",
        "  This is a static traceability layer, not validated engineering proof. It does not validate assumptions, recompute CAD, prove manufacturability, verify thermal behavior, or certify prototype readiness.",
        "",
        "Top fragile assumptions (top risks):",
    ]
    for index, impact in enumerate(ranked[:10], start=1):
        gate_text = ", ".join(impact.affected_gate_decisions) if impact.affected_gate_decisions else "none"
        lines.extend(
            [
                f"  {index}. {impact.assumption_id} - {impact.fragility.value}",
                f"     value: {_fmt_value(impact.value, impact.unit)}",
                f"     affected gate decisions: {gate_text}",
                f"     affected reports: {len(impact.affected_reports)}",
                f"     evidence items: {len(impact.evidence_required)}",
            ]
        )

    lines.extend(["", "What breaks first:"])
    lines.extend(f"  - {chain}" for chain in _what_breaks_first())
    lines.extend(["", "Assumption impacts:"])
    for impact in ranked:
        gate_decisions = impact.affected_gate_decisions or ("none",)
        lines.extend(
            [
                f"  - {impact.assumption_id}",
                f"    value: {_fmt_value(impact.value, impact.unit)}",
                f"    profile_scope: {impact.profile_scope}",
                f"    confidence: {impact.confidence}",
                f"    maturity: {impact.maturity}",
                f"    fragility rating: {impact.fragility.value}",
                "    affected engineering domains:",
            ]
        )
        lines.extend(_render_list(impact.affected_domains))
        lines.append("    affected generated reports:")
        lines.extend(_render_list(impact.affected_reports))
        lines.append("    affected gate decisions:")
        lines.extend(_render_list(gate_decisions))
        lines.append("    downstream decisions:")
        lines.extend(_render_list(impact.downstream_decisions))
        lines.append("    Evidence required:")
        lines.extend(_render_list(impact.evidence_required))
        lines.extend(["    notes:", f"      {impact.notes}"])

    lines.append("")
    return "\n".join(lines)


def build_report() -> str:
    """Build the rendered static assumption impact report."""
    return render_report(build_impacts())
