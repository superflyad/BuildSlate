#!/usr/bin/env python3
"""First-order Slate v1 runtime estimates from battery energy and workload power."""

from __future__ import annotations

import argparse
from dataclasses import dataclass

DEFAULT_BATTERY_WH = 58.0


@dataclass(frozen=True)
class WorkloadMode:
    name: str
    watts: float
    description: str


DEFAULT_MODES = (
    WorkloadMode("idle", 3.2, "display on, radios associated, background services"),
    WorkloadMode("light_inference", 8.0, "small local model bursts with UI interaction"),
    WorkloadMode("heavy_inference", 16.0, "continuous accelerator-heavy inference"),
    WorkloadMode("sustained_workload", 22.0, "combined compute, display, storage, and radio load"),
)


def estimate_runtime_hours(battery_wh: float, workload_watts: float) -> float:
    if workload_watts <= 0:
        raise ValueError("workload_watts must be greater than zero")
    return battery_wh / workload_watts


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--battery-wh", type=float, default=DEFAULT_BATTERY_WH, help="Battery capacity in watt-hours.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    print("Slate v1 power budget estimate")
    print(f"battery_wh: {args.battery_wh:.1f}")
    print("mode,watts,runtime_hours,runtime_minutes,description")
    for mode in DEFAULT_MODES:
        hours = estimate_runtime_hours(args.battery_wh, mode.watts)
        print(f"{mode.name},{mode.watts:.1f},{hours:.2f},{hours * 60:.0f},{mode.description}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
