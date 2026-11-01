#!/usr/bin/env python3
"""Validate the provisional Slate Pocket v1R mechanical integration model."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
MODEL_ROOT = REPO_ROOT / "cad" / "slate-pocket-v1r" / "envelope-model"
ENVELOPE_PATH = MODEL_ROOT / "envelope.yaml"
KEEPOUT_PATH = MODEL_ROOT / "keepouts.yaml"
STACKUP_PATH = MODEL_ROOT / "zone-stackups.yaml"
REVIEW_PATH = REPO_ROOT / "cad" / "slate-pocket-v1r" / "stackup-review.md"
GENERATOR_PATH = REPO_ROOT / "engineering" / "cad_envelope" / "generate_v1r_cad_budget.py"
REPORT_PATH = REPO_ROOT / "reports" / "slate-pocket-v1r-cad-budget.txt"


def _load(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as input_file:
        data = yaml.safe_load(input_file)
    if not isinstance(data, dict):
        raise ValueError(f"{path.relative_to(REPO_ROOT)} must contain a mapping")
    return data


def main() -> int:
    failures: list[str] = []
    for path in (ENVELOPE_PATH, KEEPOUT_PATH, STACKUP_PATH, REVIEW_PATH, GENERATOR_PATH):
        if path.exists():
            print(f"PASS: v1R CAD artifact exists: {path.relative_to(REPO_ROOT)}")
        else:
            failures.append(f"v1R CAD artifact missing: {path.relative_to(REPO_ROOT)}")

    if not failures:
        try:
            envelope = _load(ENVELOPE_PATH)
            keepouts = _load(KEEPOUT_PATH)
            stackups = _load(STACKUP_PATH)
            external = envelope["device"]["external_mm"]
            if external != {"length": 180.0, "width": 95.0, "thickness": 9.5}:
                failures.append(f"v1R external envelope changed unexpectedly: {external}")
            if len(envelope["placements"]) < 7:
                failures.append("v1R envelope must define at least seven integration placements")
            if len(keepouts["keepouts"]) < 5:
                failures.append("v1R keepout model must define at least five keepouts")
            required_zones = {"battery_without_wireless_charging", "battery_with_wireless_charging", "compute_hotspot", "rear_camera"}
            if not required_zones.issubset(stackups["zones"]):
                failures.append("v1R zone stackup model is missing required local zones")
        except (KeyError, TypeError, ValueError) as exc:
            failures.append(str(exc))
        else:
            if not failures:
                print("PASS: v1R envelope, placement, keepout, and local-zone structures are valid")

    if not failures:
        result = subprocess.run(
            [sys.executable, str(GENERATOR_PATH)], cwd=REPO_ROOT, capture_output=True, text=True, check=False
        )
        if result.returncode == 0:
            print("PASS: v1R CAD budget generator runs")
        else:
            failures.append(f"v1R CAD generator failed: {result.stderr.strip() or result.stdout.strip()}")

    if REPORT_PATH.exists():
        report = REPORT_PATH.read_text(encoding="utf-8")
        markers = (
            "Planform screen",
            "Local z-height screen",
            "battery_with_wireless_charging: FAIL",
            "PROVISIONAL_CAD_DECISION: BLOCKED_ON_SUPPLIER_GEOMETRY_AND_KEEP_OUT_RESOLUTION",
            "does not prove fit",
        )
        missing = [marker for marker in markers if marker not in report]
        if missing:
            failures.append(f"v1R CAD report missing markers: {', '.join(missing)}")
        else:
            print("PASS: v1R CAD report preserves local conflicts and provisional caveat")
    else:
        failures.append(f"v1R CAD report missing: {REPORT_PATH.relative_to(REPO_ROOT)}")

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1
    print("PASS: v1R CAD integration model validation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
