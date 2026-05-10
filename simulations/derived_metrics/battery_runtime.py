#!/usr/bin/env python3
"""Estimate runtime from battery capacity and workload draw."""

from __future__ import annotations

import argparse


def mah_to_wh(capacity_mah: float, nominal_voltage: float) -> float:
    return capacity_mah * nominal_voltage / 1000


def runtime_hours(capacity_wh: float, draw_w: float) -> float:
    if draw_w <= 0:
        raise ValueError("workload draw must be greater than zero")
    return capacity_wh / draw_w


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capacity-mah", type=float, default=6000.0)
    parser.add_argument("--nominal-voltage", type=float, default=3.85)
    parser.add_argument("--idle-w", type=float, default=2.5)
    parser.add_argument("--light-inference-w", type=float, default=8.0)
    parser.add_argument("--heavy-inference-w", type=float, default=18.0)
    parser.add_argument("--sustained-ai-w", type=float, default=28.0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    battery_wh = mah_to_wh(args.capacity_mah, args.nominal_voltage)
    workloads = {
        "idle": args.idle_w,
        "light inference": args.light_inference_w,
        "heavy inference": args.heavy_inference_w,
        "sustained AI": args.sustained_ai_w,
    }

    print("Battery runtime estimate")
    print(f"  capacity: {args.capacity_mah:.0f} mAh")
    print(f"  nominal voltage: {args.nominal_voltage:.2f} V")
    print(f"  battery energy: {battery_wh:.2f} Wh")
    for name, draw_w in workloads.items():
        print(f"  {name}: {runtime_hours(battery_wh, draw_w):.2f} hours at {draw_w:.1f} W")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
