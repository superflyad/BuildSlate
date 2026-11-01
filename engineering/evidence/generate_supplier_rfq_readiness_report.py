#!/usr/bin/env python3
"""Generate supplier RFQ/RFI packet readiness report."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = REPO_ROOT / "research" / "rfqs" / "rfq_registry.yaml"
REPORT_PATH = REPO_ROOT / "reports" / "slate-pocket-supplier-rfq-readiness.txt"


def _load_registry() -> dict[str, Any]:
    if not REGISTRY_PATH.exists():
        raise ValueError(f"RFQ registry missing: {REGISTRY_PATH.relative_to(REPO_ROOT)}")
    with REGISTRY_PATH.open("r", encoding="utf-8") as input_file:
        data = yaml.safe_load(input_file)
    if not isinstance(data, dict) or not isinstance(data.get("packets"), dict):
        raise ValueError("RFQ registry must contain a packets mapping")
    return data


def build_report() -> str:
    """Render packet inventory and authorization boundary."""
    registry = _load_registry()
    packets = registry["packets"]
    missing: list[str] = []
    lines = [
        "Slate Pocket Supplier RFQ/RFI Readiness",
        "========================================",
        "",
        "Scope:",
        f"  baseline: {registry['metadata']['baseline_profile']}",
        f"  prepared on: {registry['metadata']['prepared_on']}",
        f"  request status: {registry['metadata']['request_status']}",
        f"  packet count: {len(packets)}",
        "",
        "Prepared packets:",
    ]
    for packet_id, packet in packets.items():
        request_path = REPO_ROOT / packet["request_document"]
        template_path = REPO_ROOT / packet["response_template"]
        for path in (request_path, template_path):
            if not path.exists():
                missing.append(str(path.relative_to(REPO_ROOT)))
        lines.extend(
            [
                f"  - {packet_id}: {packet['request_type']}",
                f"    status: {packet['status']}",
                f"    evidence package: {packet['linked_evidence_package']}",
                f"    target suppliers: {', '.join(packet['target_suppliers'])}",
                f"    objective: {packet['objective']}",
                f"    request: {packet['request_document']}",
                f"    response template: {packet['response_template']}",
            ]
        )

    lines.extend(
        [
            "",
            "Common supplier requirements:",
            *[f"  - {item}" for item in registry["common_requirements"]],
            "",
            "Authorization boundary:",
            f"  {registry['metadata']['authorization_boundary']}",
            "  No packet has been sent and no supplier relationship is implied.",
            "",
            "Next external actions after authorization:",
            "  - Confirm the legal entity and contact identity used for outreach.",
            "  - Send the non-confidential packet or review the supplier NDA before restricted disclosure.",
            "  - Store responses with revision, confidentiality, and source metadata intact.",
            "  - Score each response against the evidence registry acceptance criteria.",
            "",
        ]
    )
    if missing:
        lines.extend(["Missing packet artifacts:", *[f"  - {path}" for path in missing], ""])
        decision = "PACKETS_INCOMPLETE"
    elif all(packet["status"] == "prepared_not_sent" for packet in packets.values()):
        decision = "PREPARED_AWAITING_AUTHORIZATION"
    else:
        decision = "PACKET_STATUS_REVIEW_REQUIRED"
    lines.extend(
        [
            f"SUPPLIER_OUTREACH_DECISION: {decision}",
            "",
            "Caveat:",
            "  Packet readiness is not supplier contact, NDA acceptance, quotation, component approval, or supply commitment.",
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
