#!/usr/bin/env python3
"""Validate Slate Pocket Phase 1 public candidate evidence."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
BATTERY_PATH = REPO_ROOT / "research" / "evidence" / "battery" / "supplier-source-index.yaml"
BATTERY_ENVELOPE_PATH = REPO_ROOT / "research" / "evidence" / "battery" / "pack-envelope.yaml"
COMPUTE_PATH = REPO_ROOT / "research" / "evidence" / "compute" / "platform-comparison.yaml"
DISPLAY_STORAGE_PATH = REPO_ROOT / "research" / "evidence" / "display-storage" / "candidate-comparison.yaml"
GENERATOR_PATH = REPO_ROOT / "engineering" / "evidence" / "generate_phase1_candidate_report.py"
REPORT_PATH = REPO_ROOT / "reports" / "slate-pocket-phase1-candidate-screen.txt"


def _load(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as input_file:
        data = yaml.safe_load(input_file)
    if not isinstance(data, dict):
        raise ValueError(f"{path.relative_to(REPO_ROOT)} must contain a mapping")
    return data


def main() -> int:
    failures: list[str] = []
    paths = (BATTERY_PATH, BATTERY_ENVELOPE_PATH, COMPUTE_PATH, DISPLAY_STORAGE_PATH, GENERATOR_PATH)
    for path in paths:
        if path.exists():
            print(f"PASS: Phase 1 artifact exists: {path.relative_to(REPO_ROOT)}")
        else:
            failures.append(f"Phase 1 artifact missing: {path.relative_to(REPO_ROOT)}")

    if not failures:
        try:
            battery = _load(BATTERY_PATH)
            envelope = _load(BATTERY_ENVELOPE_PATH)
            compute = _load(COMPUTE_PATH)
            display_storage = _load(DISPLAY_STORAGE_PATH)

            density = battery["slate_target"]["required_complete_pack_density_wh_l"]
            if density < 800:
                failures.append(f"battery density pressure unexpectedly low: {density}")
            if battery["screening_conclusion"]["selected_candidate"] is not None:
                failures.append("battery evidence must not claim a selected candidate")
            if envelope["decision"]["charge_target"] != "fallback_to_highest_supplier_validated_level":
                failures.append("battery charging fallback decision is missing")

            compute_conclusion = compute["screening_conclusion"]
            if compute_conclusion["selected_platform"] is not None:
                failures.append("compute evidence must not claim a selected platform")
            if compute_conclusion["preferred_memory_tier_for_rfq_gb"] != 128:
                failures.append("compute evidence must preserve the locked 128 GB RFQ tier")
            if not any("512 GB" in item for item in compute_conclusion["unsupported_by_reviewed_candidates"]):
                failures.append("compute evidence must identify the unsupported 512 GB topology")

            display_conclusion = display_storage["display_conclusion"]
            storage_conclusion = display_storage["storage_conclusion"]
            if display_conclusion["selected_candidate"] is not None:
                failures.append("display evidence must not claim a selected candidate")
            if display_conclusion["exact_public_match_found"] is not False:
                failures.append("display evidence must preserve the no-exact-public-match result")
            if storage_conclusion["selected_candidate"] is not None:
                failures.append("storage evidence must not claim a selected candidate")
            if storage_conclusion["maximum_reviewed_single_package_capacity_tb"] != 1:
                failures.append("storage evidence must preserve the reviewed 1 TB package ceiling")
        except (KeyError, TypeError, ValueError) as exc:
            failures.append(str(exc))
        else:
            if not failures:
                print("PASS: Phase 1 candidate evidence preserves conservative decisions and locked fallbacks")

    if not failures:
        result = subprocess.run(
            [sys.executable, str(GENERATOR_PATH)],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            print("PASS: Phase 1 candidate report generator runs")
        else:
            failures.append(f"Phase 1 generator failed: {result.stderr.strip() or result.stdout.strip()}")

    if REPORT_PATH.exists():
        report = REPORT_PATH.read_text(encoding="utf-8")
        markers = (
            "Executive decisions",
            "Battery screen",
            "Compute and memory screen",
            "Display screen",
            "Storage screen",
            "PHASE1_DECISION: SUPPLIER_RFQ_REQUIRED",
            "does not constitute a supplier quote",
        )
        missing = [marker for marker in markers if marker not in report]
        if missing:
            failures.append(f"Phase 1 report missing markers: {', '.join(missing)}")
        else:
            print("PASS: Phase 1 candidate report contains required decisions and caveat")
    else:
        failures.append(f"Phase 1 report missing: {REPORT_PATH.relative_to(REPO_ROOT)}")

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1

    print("PASS: Phase 1 candidate evidence validation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
