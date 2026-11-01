#!/usr/bin/env python3
"""Validate evidence-driven Slate Pocket v1R fallbacks across operational artifacts."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
PROFILE_PATH = REPO_ROOT / "configs" / "devices" / "slate-pocket-v1r.yaml"
ASSUMPTION_PATH = REPO_ROOT / "engineering" / "assumptions" / "assumption_registry.yaml"
RISK_PATH = REPO_ROOT / "engineering" / "risks" / "risk_register.yaml"
PROFILE_REPORT = REPO_ROOT / "reports" / "device-profile-slate-pocket-v1r.txt"
GATE_REPORT = REPO_ROOT / "reports" / "slate-pocket-v1r-physical-feasibility-gate.txt"
INTELLIGENCE_REPORT = REPO_ROOT / "reports" / "slate-pocket-v1r-engineering-intelligence.txt"


def _load(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as input_file:
        data = yaml.safe_load(input_file)
    if not isinstance(data, dict):
        raise ValueError(f"{path.relative_to(REPO_ROOT)} must contain a mapping")
    return data


def main() -> int:
    failures: list[str] = []
    try:
        profile = _load(PROFILE_PATH)
        assumptions = _load(ASSUMPTION_PATH)["assumptions"]
        risks = _load(RISK_PATH)["risks"]
        expected_profile = {
            ("compute", "npu_tops"): 80,
            ("memory", "capacity_gb"): 128,
            ("memory", "gb_per_package"): 32,
            ("storage", "capacity_tb"): 1,
            ("storage", "tb_per_package"): 1,
            ("battery", "charging_wired_w"): 30,
            ("battery", "charging_wireless_w"): 0,
            ("runtime", "available_memory_gb"): 128,
        }
        for (section, field), expected in expected_profile.items():
            actual = profile[section][field]
            if actual != expected:
                failures.append(f"{section}.{field} expected {expected}, got {actual}")
        if profile["decision_baseline"]["locked_trade_rules"]["memory"]["aspirational_target_gb"] != 512:
            failures.append("locked 512 GB aspiration is not preserved separately")
        if profile["decision_baseline"]["locked_trade_rules"]["storage"]["target_tb"] != 4:
            failures.append("locked 4 TB target is not preserved separately")
        if profile["integration_configuration"]["wireless_charging"] != "removed":
            failures.append("integration configuration must remove wireless charging")
        expected_assumptions = {
            "npu_tops": 80,
            "memory_capacity_gb": 128,
            "storage_capacity_tb": 1,
            "wireless_charging_enabled": False,
        }
        for assumption_id, expected in expected_assumptions.items():
            actual = assumptions[assumption_id]["value"]
            if actual != expected:
                failures.append(f"assumption {assumption_id} expected {expected}, got {actual}")
        if risks["memory_packaging_512gb"]["status"] != "blocked":
            failures.append("512 GB packaging risk must remain blocked")
        if risks["storage_packaging_4tb"]["status"] != "blocked":
            failures.append("4 TB storage risk must remain blocked")
        if risks["wireless_charging_packaging"]["status"] != "mitigated":
            failures.append("wireless charging EVT0 exposure must be mitigated by removal")
    except (KeyError, TypeError, ValueError) as exc:
        failures.append(str(exc))

    reports_and_markers = {
        PROFILE_REPORT: ("capacity_gb: 128", "capacity_tb: 1", "npu_tops: 80", "charging_wireless_w: 0"),
        GATE_REPORT: ("memory: 128 GB RAM", "storage: 1 TB", "NPU: 80 TOPS"),
        INTELLIGENCE_REPORT: (
            "Operational integration values are 128 GB memory and 1 TB internal storage",
            "512 GB memory and 4 TB internal storage are rejected as first-build configurations",
        ),
    }
    for path, markers in reports_and_markers.items():
        if not path.exists():
            failures.append(f"fallback report missing: {path.relative_to(REPO_ROOT)}")
            continue
        report = path.read_text(encoding="utf-8")
        missing = [marker for marker in markers if marker not in report]
        if missing:
            failures.append(f"{path.name} missing fallback markers: {', '.join(missing)}")

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1
    print("PASS: v1R operational profile, assumptions, risks, and reports use evidence-driven fallbacks")
    print("PASS: unsupported headline targets remain separately traceable and blocked")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
