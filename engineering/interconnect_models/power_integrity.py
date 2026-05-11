#!/usr/bin/env python3
"""First-pass power integrity and transient droop risk screen."""
from __future__ import annotations

import argparse
from common import positive_float, print_section


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--peak-power-w", type=positive_float, default=45.0)
    parser.add_argument("--voltage-v", type=positive_float, default=0.9)
    parser.add_argument("--pdn-resistance-mohm", type=positive_float, default=0.5)
    parser.add_argument("--transient-current-factor", type=positive_float, default=1.8)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    peak_current_a = args.peak_power_w / args.voltage_v
    transient_current_a = peak_current_a * args.transient_current_factor
    pdn_resistance_ohm = args.pdn_resistance_mohm / 1000.0
    estimated_droop_v = transient_current_a * pdn_resistance_ohm
    droop_percent = estimated_droop_v / args.voltage_v * 100.0

    warnings: list[str] = []
    if droop_percent > 5.0:
        warnings.append("estimated voltage droop exceeds 5% of rail voltage")
    if args.transient_current_factor > 1.5:
        warnings.append("transient current spikes require close VRM, capacitor, package, and workload-step review")
    if transient_current_a > 75.0:
        warnings.append("thin-device capacitor/VRM constraint risk is high at this transient current")

    print("Power integrity screening model")
    print_section("assumptions", [
        "peak power is applied to a low-voltage compute rail for worst-case current screening",
        "PDN resistance is a lumped effective resistance placeholder",
        "transient current factor approximates fast workload steps and simultaneous switching demand",
        "inductance, capacitor ESR/ESL, control-loop response, package parasitics, and board layout are not modeled",
    ])
    print_section("formulas", [
        "peak_current_A = peak_power_W / voltage_V",
        "transient_current_A = peak_current_A * transient_current_factor",
        "pdn_resistance_ohm = pdn_resistance_mohm / 1000",
        "estimated_voltage_droop_V = transient_current_A * pdn_resistance_ohm",
        "droop_percent = estimated_voltage_droop_V / voltage_V * 100",
    ])
    print_section("outputs", [
        f"peak_power_w: {args.peak_power_w:.1f}",
        f"voltage_v: {args.voltage_v:.2f}",
        f"pdn_resistance_mohm: {args.pdn_resistance_mohm:.2f}",
        f"transient_current_factor: {args.transient_current_factor:.1f}",
        f"peak_current_a: {peak_current_a:.1f}",
        f"transient_current_a: {transient_current_a:.1f}",
        f"estimated_voltage_droop_v: {estimated_droop_v:.3f}",
        f"droop_percent: {droop_percent:.1f}",
    ])
    print_section("warnings", warnings)
    print("confidence: low; real power integrity depends on impedance versus frequency and layout")
    print("basis: conservative Ohm-law transient droop screen for low-voltage AI rails")
    print("primary blocker: transient current delivery with limited decoupling and VRM area in a thin device")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
