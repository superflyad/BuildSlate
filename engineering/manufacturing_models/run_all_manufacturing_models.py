#!/usr/bin/env python3
"""Run all first-pass manufacturing and reliability screening models."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SCRIPTS = [
    "tolerance_stackup.py",
    "thermal_expansion.py",
    "battery_swelling.py",
    "assembly_complexity.py",
    "reliability_hotspots.py",
    "repairability.py",
    "yield_risk.py",
]


def main() -> int:
    for index, script in enumerate(SCRIPTS, start=1):
        if index > 1:
            print("\n" + "=" * 72)
        print(f"Running {script}", flush=True)
        result = subprocess.run([sys.executable, str(SCRIPT_DIR / script)], check=False)
        if result.returncode != 0:
            return result.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
