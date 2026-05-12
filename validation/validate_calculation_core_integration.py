#!/usr/bin/env python3
"""Validate battery model integration with the centralized calculation core."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def run_command(command: list[str]) -> str:
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"command failed ({completed.returncode}): {' '.join(command)}\n"
            f"stdout:\n{completed.stdout}\n"
            f"stderr:\n{completed.stderr}"
        )
    return completed.stdout


def require_contains(output: str, expected_values: tuple[str, ...], context: str) -> None:
    if not any(expected in output for expected in expected_values):
        expected = " or ".join(repr(value) for value in expected_values)
        raise AssertionError(f"{context} did not contain {expected}\noutput:\n{output}")


def main() -> int:
    checks = (
        (
            [sys.executable, "engineering/models/battery_energy.py"],
            ("total_energy_wh: 23.10", "total_energy_wh: 23.1"),
            "battery model output",
        ),
        (
            [sys.executable, "engineering/models/battery_energy.py", "--explain"],
            ("battery.energy_wh",),
            "battery model explanation",
        ),
        (
            [
                sys.executable,
                "engineering/core/calculator.py",
                "--set",
                "battery.capacity_mah=6000",
                "--set",
                "battery.nominal_voltage_v=3.85",
                "--compute",
                "battery.energy_wh",
            ],
            ("battery.energy_wh = 23.1 Wh", "battery.energy_wh = 23.10 Wh"),
            "calculator output",
        ),
    )

    for command, expected_values, context in checks:
        output = run_command(list(command))
        require_contains(output, expected_values, context)
        print(f"PASS: {context}")

    print("All calculation core integration validations passed.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001 - validation CLI should report actionable failures.
        print(f"FAIL: {exc}")
        raise SystemExit(1) from exc
