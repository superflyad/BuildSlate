#!/usr/bin/env python3
"""Generate the final local/public Slate Pocket v1R readiness and blocker handoff."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = REPO_ROOT / "engineering" / "evidence" / "evidence_registry.yaml"
BLOCKER_PATH = REPO_ROOT / "engineering" / "evidence" / "external_blocker_registry.yaml"
PROFILE_PATH = REPO_ROOT / "configs" / "devices" / "slate-pocket-v1r.yaml"
REPORT_PATH = REPO_ROOT / "reports" / "slate-pocket-v1r-program-readiness.txt"


def _load(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as input_file:
        data = yaml.safe_load(input_file)
    if not isinstance(data, dict):
        raise ValueError(f"{path.relative_to(REPO_ROOT)} must contain a mapping")
    return data


def build_report() -> str:
    registry = _load(REGISTRY_PATH)
    blockers = _load(BLOCKER_PATH)["blockers"]
    profile = _load(PROFILE_PATH)
    packages = registry["packages"]
    verified = [package_id for package_id, package in packages.items() if package["status"] == "verified"]
    available = [package_id for package_id, package in packages.items() if package["status"] == "available"]
    modeled = [
        package_id
        for package_id, package in packages.items()
        if package["status"] == "planned" and int(package["phase"]) == 2
    ]
    execution_prepared = [
        package_id
        for package_id, package in packages.items()
        if package["status"] == "planned" and int(package["phase"]) >= 3
    ]
    nonverified = [package_id for package_id, package in packages.items() if package["status"] != "verified"]

    integration = profile["integration_configuration"]
    rejected = (
        ("512 GB memory first-build configuration", "unsupported by reviewed platform limits; 128 GB fallback modeled"),
        ("4 TB internal storage first-build configuration", "unsupported by reviewed embedded packages; 1 TB internal reference modeled"),
        ("100 TOPS sustained requirement", "headline TOPS does not substitute for measured workload performance per watt"),
        ("50 W wireless charging in EVT0", "local stack exceeds envelope and certification path is unestablished"),
        ("optional 5G in EVT0", "market, bands, operators, antenna topology, SAR, and certification scope are unset"),
        ("100 W charging as an authorized EVT0 mode", "battery/charger limits and thermal evidence are absent; planning cap is 30 W input"),
    )

    lines = [
        "Slate Pocket v1R Program Readiness and External Handoff",
        "=======================================================",
        "",
        "Executive state:",
        "  local/public engineering program: complete to the defensible pre-supplier/pre-hardware boundary",
        "  supplier handoff: prepared, not sent",
        "  prototype execution package: prepared, not authorized",
        "  manufacturing/pilot package: prepared, not authorized",
        "  evidence gate: BLOCKED_ON_FOUNDATIONAL_EVIDENCE",
        "",
        "Operational integration configuration:",
        f"  memory: {integration['memory_gb']} GB fallback planning tier",
        f"  internal storage: {integration['internal_storage_tb']} TB reference; {integration['product_storage_fallback_tb']} TB product fallback needs modular/external path",
        f"  compute: {integration['npu_public_reference_tops_int8']} TOPS INT8 public reference, not selected or sustained",
        f"  wired charging: {integration['wired_charge_evt0_input_cap_w']} W EVT0 input cap before supplier derating",
        f"  wireless charging: {integration['wireless_charging']}",
        f"  cellular: {integration['cellular']}",
        "",
        f"Verified evidence ({len(verified)}):",
    ]
    lines.extend(f"  - {package_id}: {packages[package_id]['title']}" for package_id in verified)
    lines.extend(["", f"Available public evidence ({len(available)}; not verified):"])
    lines.extend(f"  - {package_id}: {packages[package_id]['title']}" for package_id in available)
    lines.extend(["", f"Modeled Phase 2 planning evidence ({len(modeled)}; not verified):"])
    lines.extend(f"  - {package_id}: {packages[package_id]['title']}" for package_id in modeled)
    lines.extend(["", f"Prepared execution packages ({len(execution_prepared)}; no physical evidence):"])
    lines.extend(f"  - {package_id}: {packages[package_id]['title']}" for package_id in execution_prepared)

    lines.extend(["", f"Rejected, removed, or unsupported configurations ({len(rejected)}):"])
    for item, reason in rejected:
        lines.append(f"  - {item}: {reason}")

    lines.extend(["", f"Externally blocked work ({len(blockers)}):"])
    for blocker_id, blocker in blockers.items():
        lines.extend(
            [
                f"  - {blocker_id} [{blocker['category']}]",
                f"    affects: {', '.join(blocker['affects'])}",
                f"    missing: {blocker['missing_evidence']}",
                f"    exact request: {blocker['exact_request']}",
                f"    authorization: {blocker['authorization_required']}",
            ]
        )

    lines.extend(
        [
            "",
            "Coverage and evidence integrity:",
            f"  evidence packages tracked: {len(packages)}",
            f"  nonverified packages mapped to external blockers: {len(nonverified)}",
            "  supplier RFQ/NDA packets: battery, compute/memory, display, and storage prepared",
            "  Phase 2: mechanical, PCB/power, thermal, and RF planning packages prepared",
            "  EVT0: BOM strategy, instrumentation, workloads, tests, schemas, hard stops, and correlation workflow prepared",
            "  manufacturing: DFM, assembly, reliability, compliance-pretest, serviceability, pilot, defects, and quality gates prepared",
            "  external messages/purchases/builds/tests performed: none",
            "",
            "LOCAL_PROGRAM_DECISION: SUPPLIER_READY_AND_PROTOTYPE_PLAN_READY_EXTERNALLY_BLOCKED",
            "",
            "Caveat:",
            "  Supplier-ready and prototype-plan-ready describe the handoff artifacts, not supplier approval or permission to build. BuildSlate does not yet have selected components, released production design, validated CAD/ECAD/thermal/RF performance, prototype measurements, manufacturability evidence, certification, or production readiness.",
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
