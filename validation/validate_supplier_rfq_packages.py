#!/usr/bin/env python3
"""Validate supplier RFQ/RFI packets and response templates."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = REPO_ROOT / "research" / "rfqs" / "rfq_registry.yaml"
GENERATOR_PATH = REPO_ROOT / "engineering" / "evidence" / "generate_supplier_rfq_readiness_report.py"
REPORT_PATH = REPO_ROOT / "reports" / "slate-pocket-supplier-rfq-readiness.txt"
REQUIRED_PACKETS = {"battery", "compute_memory", "display", "storage"}

TEMPLATE_SECTIONS = {
    "battery": {"request", "supplier", "proposal", "electrical", "mechanical", "charge_discharge", "thermal_safety", "reliability_supply", "deviations_and_unknowns", "supplier_attestation"},
    "compute_memory": {"request", "supplier", "platform", "package", "memory_topology", "power", "ai_runtime", "interfaces_security", "development_supply", "deviations_and_unknowns", "supplier_attestation"},
    "display": {"request", "supplier", "module", "mechanical", "electrical_interface", "optical", "power_thermal", "reliability_supply", "deviations_and_unknowns", "supplier_attestation"},
    "storage": {"request", "supplier", "device", "mechanical", "interface_firmware", "performance", "power_thermal_endurance", "capacity_architecture", "supply", "deviations_and_unknowns", "supplier_attestation"},
}


def _load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as input_file:
        data = yaml.safe_load(input_file)
    if not isinstance(data, dict):
        raise ValueError(f"{path.relative_to(REPO_ROOT)} must contain a mapping")
    return data


def main() -> int:
    failures: list[str] = []
    if not REGISTRY_PATH.exists():
        failures.append(f"RFQ registry missing: {REGISTRY_PATH.relative_to(REPO_ROOT)}")
        registry: dict[str, Any] = {}
    else:
        registry = _load_yaml(REGISTRY_PATH)
        print(f"PASS: RFQ registry exists: {REGISTRY_PATH.relative_to(REPO_ROOT)}")

    packets = registry.get("packets", {})
    if set(packets) != REQUIRED_PACKETS:
        failures.append(f"RFQ registry packet ids must be {sorted(REQUIRED_PACKETS)}; found {sorted(packets)}")

    for packet_id, packet in packets.items():
        if packet.get("status") != "prepared_not_sent":
            failures.append(f"{packet_id} must remain prepared_not_sent until external state proves otherwise")
        request_path = REPO_ROOT / packet["request_document"]
        template_path = REPO_ROOT / packet["response_template"]
        if not request_path.exists():
            failures.append(f"{packet_id} request missing: {request_path.relative_to(REPO_ROOT)}")
        else:
            request_text = request_path.read_text(encoding="utf-8")
            required_request_markers = ("Prepared, not sent", "Required engineering data", "Decision thresholds", "does not constitute")
            missing_markers = [marker for marker in required_request_markers if marker not in request_text]
            if missing_markers:
                failures.append(f"{packet_id} request missing markers: {', '.join(missing_markers)}")
        if not template_path.exists():
            failures.append(f"{packet_id} response template missing: {template_path.relative_to(REPO_ROOT)}")
        else:
            template = _load_yaml(template_path)
            missing_sections = TEMPLATE_SECTIONS[packet_id] - set(template)
            if missing_sections:
                failures.append(f"{packet_id} response template missing sections: {', '.join(sorted(missing_sections))}")
            if template.get("request", {}).get("status") != "prepared_not_sent":
                failures.append(f"{packet_id} response template must state prepared_not_sent")
    if not failures and packets:
        print("PASS: supplier packets, authorization states, request markers, and response schemas are valid")

    if not failures:
        result = subprocess.run(
            [sys.executable, str(GENERATOR_PATH)],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            print("PASS: supplier RFQ readiness report generator runs")
        else:
            failures.append(f"RFQ readiness generator failed: {result.stderr.strip() or result.stdout.strip()}")

    if REPORT_PATH.exists():
        report = REPORT_PATH.read_text(encoding="utf-8")
        markers = (
            "Prepared packets",
            "Authorization boundary",
            "SUPPLIER_OUTREACH_DECISION: PREPARED_AWAITING_AUTHORIZATION",
            "not supplier contact",
        )
        missing = [marker for marker in markers if marker not in report]
        if missing:
            failures.append(f"RFQ readiness report missing markers: {', '.join(missing)}")
        else:
            print("PASS: supplier RFQ readiness report contains decision and external-action caveat")
    else:
        failures.append(f"RFQ readiness report missing: {REPORT_PATH.relative_to(REPO_ROOT)}")

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1
    print("PASS: supplier RFQ package validation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
