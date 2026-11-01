#!/usr/bin/env python3
"""Validate the provisional Slate Pocket v1R PCB and power architecture package."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
FLOORPLAN_ROOT = REPO_ROOT / "engineering" / "pcb" / "slate-pocket-v1r-floorplan"
FLOORPLAN_PATH = FLOORPLAN_ROOT / "floorplan.yaml"
POWER_TREE_PATH = REPO_ROOT / "engineering" / "pcb" / "power-tree.yaml"
REVIEW_PATH = REPO_ROOT / "engineering" / "pcb" / "placement-routing-review.md"
GENERATOR_PATH = REPO_ROOT / "engineering" / "pcb" / "generate_v1r_pcb_power_report.py"
REPORT_PATH = REPO_ROOT / "reports" / "slate-pocket-v1r-pcb-power-architecture.txt"


def _load(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as input_file:
        data = yaml.safe_load(input_file)
    if not isinstance(data, dict):
        raise ValueError(f"{path.relative_to(REPO_ROOT)} must contain a mapping")
    return data


def main() -> int:
    failures: list[str] = []
    required = (FLOORPLAN_ROOT / "README.md", FLOORPLAN_PATH, POWER_TREE_PATH, REVIEW_PATH, GENERATOR_PATH)
    for path in required:
        if path.exists():
            print(f"PASS: v1R PCB/power artifact exists: {path.relative_to(REPO_ROOT)}")
        else:
            failures.append(f"v1R PCB/power artifact missing: {path.relative_to(REPO_ROOT)}")

    if not failures:
        try:
            floorplan = _load(FLOORPLAN_PATH)
            power_tree = _load(POWER_TREE_PATH)
            if floorplan["metadata"]["modeled_memory_tier_gb"] != 128:
                failures.append("provisional floorplan must model the locked 128 GB fallback")
            memory_sites = [
                item for item in floorplan["placements"].values() if item["function"] == "lpddr5x_32gb_planning_site"
            ]
            if len(memory_sites) != 4:
                failures.append("128 GB fallback must have exactly four 32 GB planning sites")
            if floorplan["layer_stack"]["assumed_total_layers"] != len(floorplan["layer_stack"]["layers"]):
                failures.append("PCB layer count does not match layer role inventory")
            policy = power_tree["charging_policy"]
            if policy["full_power_wired_overlap_with_sustained_ai"] != "prohibited_until_validated":
                failures.append("full-power wired charging overlap must remain prohibited")
            if policy["wireless_overlap_with_sustained_ai"] != "prohibited_until_validated":
                failures.append("wireless charging overlap must remain prohibited")
            if policy["evt0_wireless_enabled"] is not False:
                failures.append("wireless charging must remain disabled for EVT0")
            if power_tree["source_constraints"]["wired_input_target_w"] != 100:
                failures.append("locked 100 W wired target changed unexpectedly")
        except (KeyError, TypeError, ValueError) as exc:
            failures.append(str(exc))
        else:
            if not failures:
                print("PASS: v1R floorplan, fallback topology, layer stack, and charging policy are valid")

    if not failures:
        result = subprocess.run(
            [sys.executable, str(GENERATOR_PATH)], cwd=REPO_ROOT, capture_output=True, text=True, check=False
        )
        if result.returncode == 0:
            print("PASS: v1R PCB/power report generator runs")
        else:
            failures.append(f"v1R PCB/power generator failed: {result.stderr.strip() or result.stdout.strip()}")

    if REPORT_PATH.exists():
        report = REPORT_PATH.read_text(encoding="utf-8")
        markers = (
            "modeled memory tier: 128 GB",
            "512 GB topology modeled: no",
            "full-power wired plus sustained AI: PROHIBITED_UNTIL_VALIDATED",
            "EVT0 wireless charging: DISABLED",
            "PROVISIONAL_PCB_POWER_DECISION: BLOCKED_ON_PLATFORM_REFERENCE_DESIGN_AND_BATTERY_CHARGE_LIMITS",
            "does not prove routing closure",
        )
        missing = [marker for marker in markers if marker not in report]
        if missing:
            failures.append(f"v1R PCB/power report missing markers: {', '.join(missing)}")
        else:
            print("PASS: v1R PCB/power report preserves fallbacks, prohibitions, decision, and caveat")
    else:
        failures.append(f"v1R PCB/power report missing: {REPORT_PATH.relative_to(REPO_ROOT)}")

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1
    print("PASS: v1R PCB and power architecture validation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
