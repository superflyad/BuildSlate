#!/usr/bin/env python3
"""Run all environmental operating condition models with default and stress-case inputs."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

MODEL_DIR = Path(__file__).resolve().parent

COMMANDS = [
    ["ambient_temperature.py"],
    ["hand_contact.py"],
    ["enclosure_condition.py"],
    ["sunlight_display_load.py"],
    ["charging_overlap.py"],
    ["thermal_throttle_policy.py"],
    ["ambient_temperature.py", "--ambient-c", "35"],
    ["enclosure_condition.py", "--condition", "pocket"],
    ["sunlight_display_load.py", "--brightness-mode", "sunlight"],
    ["charging_overlap.py", "--wireless", "true"],
]


def main() -> int:
    for index, command in enumerate(COMMANDS, start=1):
        full_command = [sys.executable, str(MODEL_DIR / command[0]), *command[1:]]
        print("=" * 80, flush=True)
        print(f"environment model {index}: {' '.join(command)}", flush=True)
        print("=" * 80, flush=True)
        completed = subprocess.run(full_command, check=False)
        if completed.returncode != 0:
            return completed.returncode
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
