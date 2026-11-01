#!/usr/bin/env python3
"""Generate a consolidated Slate Pocket Phase 1 public candidate screen."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
BATTERY_PATH = REPO_ROOT / "research" / "evidence" / "battery" / "supplier-source-index.yaml"
BATTERY_ENVELOPE_PATH = REPO_ROOT / "research" / "evidence" / "battery" / "pack-envelope.yaml"
COMPUTE_PATH = REPO_ROOT / "research" / "evidence" / "compute" / "platform-comparison.yaml"
DISPLAY_STORAGE_PATH = REPO_ROOT / "research" / "evidence" / "display-storage" / "candidate-comparison.yaml"
REPORT_PATH = REPO_ROOT / "reports" / "slate-pocket-phase1-candidate-screen.txt"


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise ValueError(f"Phase 1 evidence file missing: {path.relative_to(REPO_ROOT)}")
    with path.open("r", encoding="utf-8") as input_file:
        data = yaml.safe_load(input_file)
    if not isinstance(data, dict):
        raise ValueError(f"Phase 1 evidence root must be a mapping: {path.relative_to(REPO_ROOT)}")
    return data


def _display_fit(candidate: dict[str, Any]) -> str:
    return candidate.get("disposition", "unclassified")


def build_report() -> str:
    """Build the consolidated public-source candidate report."""
    battery = _load_yaml(BATTERY_PATH)
    battery_envelope = _load_yaml(BATTERY_ENVELOPE_PATH)
    compute = _load_yaml(COMPUTE_PATH)
    display_storage = _load_yaml(DISPLAY_STORAGE_PATH)

    battery_target = battery["slate_target"]
    battery_decision = battery_envelope["decision"]
    compute_conclusion = compute["screening_conclusion"]
    display_conclusion = display_storage["display_conclusion"]
    storage_conclusion = display_storage["storage_conclusion"]

    lines = [
        "Slate Pocket Phase 1 Public Candidate Screen",
        "============================================",
        "",
        "Scope:",
        "  baseline: slate-pocket-v1r",
        "  evidence basis: public manufacturer product pages, briefs, catalogs, and technical specifications",
        "  review date: 2026-10-31",
        "  purpose: narrow supplier conversations without claiming component selection",
        "",
        "Executive decisions:",
        "  battery: retain 6000 mAh conditionally; pursue a custom Enovix AI-1-class RFQ; do not select a pack",
        "  charging: replace 100 W as a hard requirement with the highest supplier-validated level",
        "  compute: advance Snapdragon X2 Elite Extreme to supplier/NDA review at the 128 GB fallback",
        "  memory: do not carry 512 GB into CAD as a credible first-build topology",
        "  display: issue RFQs; no exact public 7.5-inch 16:10 LTPO AMOLED module match was found",
        "  storage: use 1 TB as the reviewed single-package unit; 2 TB requires multi-device or NVMe architecture",
        "",
        "Battery screen:",
        f"  target energy: {battery_target['energy_wh']:.1f} Wh",
        f"  complete pack allocation: {battery_target['complete_pack_volume_mm3']:,} mm^3",
        f"  required complete-pack density: {battery_target['required_complete_pack_density_wh_l']:.1f} Wh/L",
        f"  100 W implied charge rate: {battery_target['implied_charge_rate_c']:.2f}C",
    ]
    for candidate_id, candidate in battery["candidates"].items():
        fit = candidate.get("target_fit", {})
        fit_summary = ", ".join(f"{key}={value}" for key, value in fit.items())
        lines.append(f"  - {candidate_id}: {fit_summary or candidate.get('public_status', 'unclassified')}")
    lines.extend(
        [
            f"  pack decision: capacity={battery_decision['capacity_target']}; charge={battery_decision['charge_target']}",
            "",
            "Compute and memory screen:",
        ]
    )
    for candidate_id, candidate in compute["candidates"].items():
        memory = candidate.get("maximum_memory_gb", candidate.get("maximum_unified_memory_gb", candidate.get("memory_gb", "not_public")))
        npu = candidate.get("npu_tops_int8", candidate.get("npu_tops", candidate.get("ai_compute_fp4_tflops", "not_public")))
        lines.append(
            f"  - {candidate_id}: memory={memory} GB; AI metric={npu}; disposition={candidate['disposition']}"
        )
    lines.extend(
        [
            f"  preferred product RFQ: {compute_conclusion['preferred_product_rfq']}",
            f"  preferred RFQ memory tier: {compute_conclusion['preferred_memory_tier_for_rfq_gb']} GB",
            "  unsupported by reviewed candidates:",
            *[f"    - {item}" for item in compute_conclusion["unsupported_by_reviewed_candidates"]],
            "",
            "Display screen:",
        ]
    )
    for candidate_id, candidate in display_storage["display_candidates"].items():
        lines.append(f"  - {candidate_id}: {_display_fit(candidate)}")
    lines.extend(
        [
            f"  exact public match found: {display_conclusion['exact_public_match_found']}",
            f"  RFQ suppliers: {', '.join(display_conclusion['rfq_suppliers'])}",
            "",
            "Storage screen:",
        ]
    )
    for candidate_id, candidate in display_storage["storage_candidates"].items():
        lines.append(
            f"  - {candidate_id}: {candidate['capacity_tb']} TB; {candidate['disposition']}"
        )
    lines.extend(
        [
            f"  maximum reviewed single-package capacity: {storage_conclusion['maximum_reviewed_single_package_capacity_tb']} TB",
            f"  4 TB target: {storage_conclusion['four_tb_target_status']}",
            "",
            "Required supplier evidence before verification:",
            "  - Battery: custom cell and complete pack drawing, swelling, safety, charge curve, lifecycle, price, and supply commitment.",
            "  - Compute/memory: package and reference design, supported memory topology, PMIC/power telemetry, software access, and supply terms.",
            "  - Display: exact module outline, flex/interface, power curves, optical stack, availability, and lifecycle.",
            "  - Storage: host topology, sustained-write power/temperature, package availability, lifecycle, and multi-device support.",
            "",
            "PHASE1_DECISION: SUPPLIER_RFQ_REQUIRED",
            "",
            "Caveat:",
            "  Public product evidence narrows the search but does not constitute a supplier quote, component selection, package validation, benchmark, or supply commitment.",
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
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(report, encoding="utf-8")
    print(f"Wrote {REPORT_PATH.relative_to(REPO_ROOT)}")
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
