#!/usr/bin/env python3
"""Validate feasibility report required and core model script paths."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from engineering.generate_feasibility_report import CORE_MODEL_CHECKS, REQUIRED_CHECKS  # noqa: E402


def main() -> int:
    missing: list[str] = []
    for check in (*REQUIRED_CHECKS, *CORE_MODEL_CHECKS):
        script_path = REPO_ROOT / check.path
        if script_path.exists():
            print(f"PASS: {check.path}")
        else:
            print(f"FAIL: {check.path} missing")
            missing.append(check.path)

    if missing:
        print(f"FAIL: {len(missing)} required/core model path(s) missing")
        return 1

    print("PASS: all feasibility report required/core model paths exist")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
