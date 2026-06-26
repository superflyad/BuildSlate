#!/usr/bin/env python3
"""Engineering risk scoring for Slate Pocket screening registers."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = REPO_ROOT / "engineering" / "risks" / "risk_register.yaml"

REQUIRED_RISKS = (
    "battery_volume_capacity_tradeoff",
    "thickness_stackup_margin",
    "thermal_module_effectiveness",
    "sustained_compute_power",
    "skin_temperature_target_43c",
    "memory_packaging_512gb",
    "storage_packaging_4tb",
    "npu_100_tops_sustained",
    "wireless_charging_packaging",
    "pcb_routing_density",
    "power_delivery_transients",
    "rf_antenna_window_constraints",
    "manufacturability_yield_risk",
)

REQUIRED_FIELDS = (
    "title",
    "subsystem",
    "profile_scope",
    "likelihood",
    "impact",
    "maturity",
    "status",
    "affected_reports",
    "related_assumptions",
    "mitigation",
    "evidence_required",
    "notes",
)

PROFILE_SCOPES = ("v1", "v1r", "both")
LIKELIHOOD_VALUES = ("low", "medium", "high", "critical")
IMPACT_VALUES = ("low", "medium", "high", "critical")
MATURITY_VALUES = ("concept", "screening", "first_order", "calibrated", "validated")
STATUS_VALUES = ("open", "mitigated", "accepted", "blocked", "monitoring")

LIKELIHOOD_SCORES = {
    "low": 1,
    "medium": 2,
    "high": 3,
    "critical": 4,
}
IMPACT_SCORES = LIKELIHOOD_SCORES
MATURITY_PENALTIES = {
    "concept": 2.0,
    "screening": 1.0,
    "first_order": 0.5,
    "calibrated": 0.0,
    "validated": -1.0,
}


class Severity(StrEnum):
    """Risk severity bands."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


SEVERITY_RANK = {
    Severity.CRITICAL: 0,
    Severity.HIGH: 1,
    Severity.MEDIUM: 2,
    Severity.LOW: 3,
}


@dataclass(frozen=True)
class RiskEntry:
    """Scored engineering risk entry."""

    risk_id: str
    title: str
    subsystem: str
    profile_scope: str
    likelihood: str
    impact: str
    maturity: str
    status: str
    affected_reports: tuple[str, ...]
    related_assumptions: tuple[str, ...]
    mitigation: tuple[str, ...]
    evidence_required: tuple[str, ...]
    notes: str
    likelihood_score: int
    impact_score: int
    maturity_penalty: float
    total_risk_score: float
    severity: Severity


def load_registry(path: Path = REGISTRY_PATH) -> dict[str, Any]:
    """Load the engineering risk registry."""
    if not path.exists():
        raise ValueError(f"risk register missing: {path.relative_to(REPO_ROOT)}")
    with path.open("r", encoding="utf-8") as input_file:
        data = yaml.safe_load(input_file)
    if not isinstance(data, dict):
        raise ValueError("risk register root must be a mapping")
    return data


def _require_non_empty_list(entry: dict[str, Any], field: str, risk_id: str) -> tuple[str, ...]:
    value = entry.get(field)
    if not isinstance(value, list) or not value:
        raise ValueError(f"{risk_id}.{field} must be a non-empty list")
    if not all(isinstance(item, str) and item.strip() for item in value):
        raise ValueError(f"{risk_id}.{field} must contain non-empty strings")
    return tuple(item.strip() for item in value)


def validate_registry(registry: dict[str, Any]) -> None:
    """Validate risk register shape, required entries, fields, and enums."""
    risks = registry.get("risks")
    if not isinstance(risks, dict) or not risks:
        raise ValueError("risk register must define a non-empty risks mapping")

    missing_risks = [risk_id for risk_id in REQUIRED_RISKS if risk_id not in risks]
    if missing_risks:
        raise ValueError(f"missing required risks: {', '.join(missing_risks)}")

    caveat = registry.get("caveat")
    if not isinstance(caveat, str) or "not formal FMEA" not in caveat:
        raise ValueError("risk register caveat must state that this is not formal FMEA")

    for risk_id, entry in risks.items():
        if not isinstance(entry, dict):
            raise ValueError(f"{risk_id} must be a mapping")
        missing_fields = [field for field in REQUIRED_FIELDS if field not in entry]
        if missing_fields:
            raise ValueError(f"{risk_id} missing required fields: {', '.join(missing_fields)}")
        if entry["profile_scope"] not in PROFILE_SCOPES:
            raise ValueError(f"{risk_id}.profile_scope must be one of: {', '.join(PROFILE_SCOPES)}")
        if entry["likelihood"] not in LIKELIHOOD_VALUES:
            raise ValueError(f"{risk_id}.likelihood must be one of: {', '.join(LIKELIHOOD_VALUES)}")
        if entry["impact"] not in IMPACT_VALUES:
            raise ValueError(f"{risk_id}.impact must be one of: {', '.join(IMPACT_VALUES)}")
        if entry["maturity"] not in MATURITY_VALUES:
            raise ValueError(f"{risk_id}.maturity must be one of: {', '.join(MATURITY_VALUES)}")
        if entry["status"] not in STATUS_VALUES:
            raise ValueError(f"{risk_id}.status must be one of: {', '.join(STATUS_VALUES)}")
        for text_field in ("title", "subsystem", "notes"):
            if not isinstance(entry[text_field], str) or not entry[text_field].strip():
                raise ValueError(f"{risk_id}.{text_field} must be a non-empty string")
        for list_field in ("affected_reports", "related_assumptions", "mitigation", "evidence_required"):
            _require_non_empty_list(entry, list_field, risk_id)


def severity_for_score(score: float) -> Severity:
    """Map numeric score to severity band."""
    if score >= 13:
        return Severity.CRITICAL
    if score >= 8:
        return Severity.HIGH
    if score >= 4:
        return Severity.MEDIUM
    return Severity.LOW


def build_risks(registry: dict[str, Any] | None = None) -> tuple[RiskEntry, ...]:
    """Build scored risk rows from the static register."""
    data = registry if registry is not None else load_registry()
    validate_registry(data)
    risks: list[RiskEntry] = []
    for risk_id, entry in data["risks"].items():
        likelihood_score = LIKELIHOOD_SCORES[entry["likelihood"]]
        impact_score = IMPACT_SCORES[entry["impact"]]
        maturity_penalty = MATURITY_PENALTIES[entry["maturity"]]
        total_score = likelihood_score * impact_score + maturity_penalty
        risks.append(
            RiskEntry(
                risk_id=risk_id,
                title=entry["title"].strip(),
                subsystem=entry["subsystem"].strip(),
                profile_scope=entry["profile_scope"],
                likelihood=entry["likelihood"],
                impact=entry["impact"],
                maturity=entry["maturity"],
                status=entry["status"],
                affected_reports=_require_non_empty_list(entry, "affected_reports", risk_id),
                related_assumptions=_require_non_empty_list(entry, "related_assumptions", risk_id),
                mitigation=_require_non_empty_list(entry, "mitigation", risk_id),
                evidence_required=_require_non_empty_list(entry, "evidence_required", risk_id),
                notes=entry["notes"].strip(),
                likelihood_score=likelihood_score,
                impact_score=impact_score,
                maturity_penalty=maturity_penalty,
                total_risk_score=total_score,
                severity=severity_for_score(total_score),
            )
        )
    return tuple(risks)


def ranked_risks(risks: tuple[RiskEntry, ...]) -> tuple[RiskEntry, ...]:
    """Rank risks by score, severity, blocked status, and stable id."""
    return tuple(
        sorted(
            risks,
            key=lambda risk: (
                -risk.total_risk_score,
                SEVERITY_RANK[risk.severity],
                risk.status != "blocked",
                risk.risk_id,
            ),
        )
    )


def risks_by_subsystem(risks: tuple[RiskEntry, ...]) -> dict[str, tuple[RiskEntry, ...]]:
    """Group risks by subsystem with ranked entries in each group."""
    grouped: dict[str, list[RiskEntry]] = {}
    for risk in ranked_risks(risks):
        grouped.setdefault(risk.subsystem, []).append(risk)
    return {subsystem: tuple(entries) for subsystem, entries in sorted(grouped.items())}
