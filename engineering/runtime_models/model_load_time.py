#!/usr/bin/env python3
"""Estimate local storage load time for model weights."""

from __future__ import annotations

import argparse

from common import positive_float, print_section


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-size-gb", type=positive_float, default=43.75)
    parser.add_argument("--storage-bandwidth-gbps", type=positive_float, default=7.0)
    parser.add_argument("--decompression-factor", type=positive_float, default=1.0)
    parser.add_argument("--load-overhead-factor", type=positive_float, default=1.25)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    load_seconds = args.model_size_gb / args.storage_bandwidth_gbps * args.load_overhead_factor * args.decompression_factor

    warnings = ["storage bandwidth value is theoretical, not guaranteed sustained"]
    if load_seconds > 30.0:
        warnings.append("estimated load time exceeds 30 seconds")
    elif load_seconds > 10.0:
        warnings.append("estimated load time exceeds 10 seconds")

    primary_blocker = "none flagged by load-time arithmetic"
    if load_seconds > 30.0:
        primary_blocker = "very long cold model load time"
    elif load_seconds > 10.0:
        primary_blocker = "cold model load latency"

    print("Model load time estimate")
    print_section("inputs", [
        f"model_size_gb: {args.model_size_gb:.2f}",
        f"storage_bandwidth_gbps: {args.storage_bandwidth_gbps:.2f}",
        f"decompression_factor: {args.decompression_factor:.2f}",
        f"load_overhead_factor: {args.load_overhead_factor:.2f}",
    ])
    print_section("assumptions", [
        "model size is the local weight payload to read from storage",
        "storage bandwidth is treated as GB/s and as a theoretical upper bound rather than guaranteed sustained throughput",
        "load overhead covers filesystem, runtime initialization, allocation, and staging costs",
        "this model estimates cold-load latency only and does not predict real tokens/sec",
    ])
    print_section("formulas", [
        "load_seconds = model_size_gb / storage_bandwidth_gbps * load_overhead_factor * decompression_factor",
    ])
    print_section("outputs", [
        f"load_seconds: {load_seconds:.2f}",
    ])
    print_section("warnings", warnings)
    print("confidence: medium for arithmetic; low for real sustained storage/runtime behavior")
    print("basis: first-pass sequential read time with runtime and decompression multipliers")
    print(f"primary blocker: {primary_blocker}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
