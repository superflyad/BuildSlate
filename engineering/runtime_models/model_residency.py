#!/usr/bin/env python3
"""Estimate whether local model weights can reside in memory with runtime overhead."""

from __future__ import annotations

import argparse

from common import positive_float, print_section


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--params-billions", type=positive_float, default=70.0)
    parser.add_argument("--quantization-bits", type=positive_float, default=4.0)
    parser.add_argument("--overhead-factor", type=positive_float, default=1.25)
    parser.add_argument("--available-memory-gb", type=positive_float, default=512.0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    raw_gb = args.params_billions * 1e9 * args.quantization_bits / 8.0 / 1e9
    resident_gb = raw_gb * args.overhead_factor
    remaining_gb = args.available_memory_gb - resident_gb
    passes = remaining_gb >= 0.0

    warnings: list[str] = []
    if not passes:
        warnings.append("estimated resident model size exceeds available memory")
    if args.quantization_bits < 4.0:
        warnings.append("sub-4-bit quantization can add quality and runtime compatibility risks not modeled here")
    if args.overhead_factor < 1.1:
        warnings.append("overhead factor below 1.10 may understate allocator, metadata, and runtime buffer pressure")
    if remaining_gb < 64.0:
        warnings.append("remaining memory is below 64 GB before KV cache, OS reserve, and multimodal components")

    primary_blocker = "none flagged by weight residency arithmetic"
    if not passes:
        primary_blocker = "resident model weights exceed available memory"
    elif remaining_gb < 64.0:
        primary_blocker = "limited post-residency memory headroom"

    print("Model residency estimate")
    print_section("inputs", [
        f"params_billions: {args.params_billions:.1f}",
        f"quantization_bits: {args.quantization_bits:.1f}",
        f"overhead_factor: {args.overhead_factor:.2f}",
        f"available_memory_gb: {args.available_memory_gb:.1f}",
    ])
    print_section("assumptions", [
        "quantization affects weight storage only; KV cache, activations, buffers, and runtime metadata remain additional costs",
        "overhead factor represents scales, metadata, allocator fragmentation, and runtime buffers",
        "this model estimates residency only and does not predict real tokens/sec",
    ])
    print_section("formulas", [
        "raw_gb = params_billions * 1e9 * quantization_bits / 8 / 1e9",
        "resident_gb = raw_gb * overhead_factor",
        "remaining_gb = available_memory_gb - resident_gb",
    ])
    print_section("outputs", [
        f"raw_model_weight_gb: {raw_gb:.2f}",
        f"estimated_resident_model_gb: {resident_gb:.2f}",
        f"remaining_memory_gb: {remaining_gb:.2f}",
        f"pass_fail: {'pass' if passes else 'fail'}",
    ])
    print_section("warnings", warnings)
    print("confidence: medium for weight-size arithmetic; low for full local runtime feasibility")
    print("basis: first-pass parameter storage calculation with conservative residency overhead")
    print(f"primary blocker: {primary_blocker}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
