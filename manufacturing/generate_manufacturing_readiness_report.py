#!/usr/bin/env python3
"""Generate the Slate Pocket v1R supplier DFM and pilot readiness gate."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
MANUFACTURING_ROOT = REPO_ROOT / "manufacturing"
PILOT_PATH = MANUFACTURING_ROOT / "pilot-build-plan.yaml"
DEFECT_PATH = MANUFACTURING_ROOT / "defect-taxonomy.yaml"
SUPPLIER_RESPONSE_PATH = MANUFACTURING_ROOT / "supplier-dfm-response.yaml"
REGISTRY_PATH = REPO_ROOT / "engineering" / "evidence" / "evidence_registry.yaml"
REPORT_PATH = REPO_ROOT / "reports" / "slate-pocket-v1r-manufacturing-readiness.txt"
ANALYTICS_PATH = REPO_ROOT / "reports" / "program" / "manufacturing-pilot-analytics.yaml"


def _load(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as input_file:
        data = yaml.safe_load(input_file)
    if not isinstance(data, dict):
        raise ValueError(f"{path.relative_to(REPO_ROOT)} must contain a mapping")
    return data


def _real_pilot_files() -> list[Path]:
    root = MANUFACTURING_ROOT / "pilot-results"
    return sorted(path for path in root.rglob("*") if path.is_file() and path.name.lower() != "readme.md")


def build_report() -> str:
    pilot = _load(PILOT_PATH)
    defects = _load(DEFECT_PATH)
    supplier_response = _load(SUPPLIER_RESPONSE_PATH)
    registry = _load(REGISTRY_PATH)
    analytics = _load(ANALYTICS_PATH)
    evt_status = registry["packages"]["evt0_prototype_evidence"]["status"]
    prerequisites = pilot["prerequisites"]
    unmet = [field for field, value in prerequisites.items() if value is not True and field != "evt0_prototype_evidence_status"]
    gates = pilot["provisional_yield_gates"]
    pilot_results = _real_pilot_files()
    analytics_gate = analytics["MANUFACTURING_ANALYTICS_GATE"]
    campaign_count = analytics["campaign_count"]
    if evt_status != "verified" or unmet or supplier_response["review"]["status"] == "template_not_completed":
        gate = "BLOCKED_ON_VERIFIED_EVT0_SUPPLIER_DFM_RELEASED_PROCESS_AND_PILOT_EVIDENCE"
    elif analytics_gate == "PILOT_QUALITY_REVIEW_READY":
        gate = "PILOT_QUALITY_REVIEW_READY"
    else:
        gate = "BLOCKED_ON_INVALID_INCOMPLETE_OR_FAILED_PILOT_EVIDENCE"

    required_artifacts = (
        "dfm-review.md",
        "assembly-plan.md",
        "pilot-build-plan.yaml",
        "defect-taxonomy.yaml",
        "reliability-plan.yaml",
        "compliance-pretest-plan.yaml",
        "serviceability-plan.md",
        "quality-gate.md",
        "supplier-dfm-response.yaml",
    )
    existing = [name for name in required_artifacts if (MANUFACTURING_ROOT / name).exists()]

    lines = [
        "Slate Pocket v1R Manufacturing Readiness Gate",
        "================================================",
        "",
        "Package coverage:",
        f"  planned artifacts present: {len(existing)}/{len(required_artifacts)}",
        "  supplier DFM response status: " + supplier_response["review"]["status"],
        f"  EVT0 evidence status: {evt_status}",
        f"  pilot plan status: {pilot['metadata']['status']}",
        "  pilot authorized: no",
        "",
        "Pilot proposal:",
        f"  input units: {pilot['lot']['proposed_input_units']}",
        f"  first-pass yield gate: >= {gates['first_pass_yield_percent']['minimum']:.1f}%",
        f"  final yield gate: >= {gates['final_yield_percent']['minimum']:.1f}%",
        f"  rework gate: <= {gates['rework_rate_percent']['maximum']:.1f}%",
        f"  unknown/no-trouble-found gate: <= {gates['unknown_or_no_trouble_found_rate_percent']['maximum']:.1f}%",
        f"  critical safety/regulatory defects: {gates['critical_safety_or_regulatory_defects']['maximum_count']} allowed",
        f"  critical-characteristic Cpk planning target: {gates['critical_characteristic_capability']['target_cpk']:.2f} after prerequisites",
        "",
        "Quality infrastructure:",
        f"  defect code families: {len(defects['codes'])}",
        f"  severity levels: {len(defects['severity'])}",
        f"  inspection points: {len(pilot['inspection_points'])}",
        f"  stop rules: {len(pilot['stop_rules'])}",
        "  assembly/rework concept: available",
        "  reliability plan: available",
        "  compliance-pretest plan: available",
        "  serviceability plan: available",
        "",
        "Manufacturing evidence:",
        f"  completed supplier DFM responses: {0 if supplier_response['review']['status'] == 'template_not_completed' else 1}",
        f"  pilot result files excluding instructions: {len(pilot_results)}",
        "  units built: no evidence",
        "  measured yield: no evidence",
        "  process capability: no evidence",
        "  reliability/compliance/service validation: no evidence",
        f"  ingested analytics campaigns: {campaign_count}",
        f"  manufacturing analytics gate: {analytics_gate}",
        "",
        "Unmet prerequisites:",
        f"  - EVT0 must be verified; current status is {evt_status}.",
    ]
    for field in unmet:
        lines.append(f"  - {field}")

    lines.extend(
        [
            "",
            f"MANUFACTURING_GATE: {gate}",
            "",
            "Caveat:",
            "  This package prepares supplier and pilot work; it does not prove manufacturability, process capability, yield, reliability, compliance, serviceability, supplier approval, or production readiness.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    try:
        report = build_report()
    except (KeyError, TypeError, ValueError) as exc:
        print(f"FAIL: {exc}")
        return 1
    REPORT_PATH.write_text(report, encoding="utf-8")
    print(f"Wrote {REPORT_PATH.relative_to(REPO_ROOT)}")
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
