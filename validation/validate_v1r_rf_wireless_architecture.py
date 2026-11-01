#!/usr/bin/env python3
"""Validate the Slate Pocket v1R provisional RF/wireless architecture."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
RF_ROOT = REPO_ROOT / "engineering" / "rf"
ARCHITECTURE_PATH = RF_ROOT / "architecture.md"
MAP_PATH = RF_ROOT / "keepout-map" / "map.yaml"
VALIDATION_PLAN_PATH = RF_ROOT / "validation-plan.md"
GENERATOR_PATH = RF_ROOT / "generate_rf_architecture_report.py"
REPORT_PATH = REPO_ROOT / "reports" / "slate-pocket-v1r-rf-wireless-architecture.txt"


def _load(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as input_file:
        data = yaml.safe_load(input_file)
    if not isinstance(data, dict):
        raise ValueError(f"{path.relative_to(REPO_ROOT)} must contain a mapping")
    return data


def main() -> int:
    failures: list[str] = []
    for path in (ARCHITECTURE_PATH, MAP_PATH, VALIDATION_PLAN_PATH, GENERATOR_PATH):
        if path.exists():
            print(f"PASS: v1R RF artifact exists: {path.relative_to(REPO_ROOT)}")
        else:
            failures.append(f"v1R RF artifact missing: {path.relative_to(REPO_ROOT)}")

    if not failures:
        try:
            keepout_map = _load(MAP_PATH)
            if len(keepout_map["antenna_reservations"]) != 4:
                failures.append("RF map must preserve four perimeter negotiation zones")
            wireless = keepout_map["wireless_power_reservation"]
            if wireless["evt0_state"] != "removed":
                failures.append("wireless charging must remain removed from EVT0")
            if wireless["stack_height_mm"] != 0.8:
                failures.append("wireless planning stack changed unexpectedly")
            architecture = ARCHITECTURE_PATH.read_text(encoding="utf-8")
            required_sources = ("docs.fcc.gov", "eur-lex.europa.eu", "ptcrb.com", "wirelesspowerconsortium.com")
            missing_sources = [source for source in required_sources if source not in architecture]
            if missing_sources:
                failures.append(f"RF architecture missing primary compliance anchors: {', '.join(missing_sources)}")
            if "Optional 5G cellular is deferred" not in architecture:
                failures.append("RF architecture must defer cellular until market and band scope exists")
        except (KeyError, TypeError, ValueError) as exc:
            failures.append(str(exc))
        else:
            if not failures:
                print("PASS: v1R RF reservations, wireless fallback, cellular deferral, and compliance anchors are valid")

    if not failures:
        result = subprocess.run(
            [sys.executable, str(GENERATOR_PATH)], cwd=REPO_ROOT, capture_output=True, text=True, check=False
        )
        if result.returncode == 0:
            print("PASS: v1R RF architecture report generator runs")
        else:
            failures.append(f"v1R RF generator failed: {result.stderr.strip() or result.stdout.strip()}")

    if REPORT_PATH.exists():
        report = REPORT_PATH.read_text(encoding="utf-8")
        markers = (
            "exact band matrix: UNSET_BY_DESIGN",
            "EVT0 state: REMOVED",
            "50 W product claim: UNSUPPORTED",
            "RF_WIRELESS_DECISION: EVT0_MODULAR_RADIOS_WIRELESS_CHARGING_REMOVED_CELLULAR_DEFERRED",
            "does not prove RF performance",
        )
        missing = [marker for marker in markers if marker not in report]
        if missing:
            failures.append(f"v1R RF report missing markers: {', '.join(missing)}")
        else:
            print("PASS: v1R RF report preserves unset bands, fallbacks, decision, and caveat")
    else:
        failures.append(f"v1R RF report missing: {REPORT_PATH.relative_to(REPO_ROOT)}")

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1
    print("PASS: v1R RF and wireless architecture validation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
