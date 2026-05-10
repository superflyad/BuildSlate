#!/usr/bin/env python3
"""Estimate memory required for local model inference."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
COMPUTE_CONSTANTS_PATH = REPO_ROOT / "engineering" / "constants" / "compute.yaml"


def load_constants() -> dict[str, Any]:
    with COMPUTE_CONSTANTS_PATH.open("r", encoding="utf-8") as constants_file:
        data = yaml.safe_load(constants_file)
    if not isinstance(data, dict):
        raise ValueError("compute constants must be a mapping")
    return data


def positive_float(value: str) -> float:
    parsed = float(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("value must be greater than zero")
    return parsed


def parse_args() -> argparse.Namespace:
    constants = load_constants()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--params-billions", type=positive_float, default=70.0)
    parser.add_argument("--quantization", choices=sorted(constants["bytes_per_parameter"].keys()), default="int4")
    parser.add_argument(
        "--overhead-profile",
        choices=sorted(constants["quantization_overhead_factor"].keys()),
        default="nominal",
    )
    parser.add_argument("--available-memory-gb", type=positive_float, default=512.0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    constants = load_constants()

    bytes_per_parameter = constants["bytes_per_parameter"][args.quantization]
    overhead_factor = constants["quantization_overhead_factor"][args.overhead_profile]
    raw_gb = args.params_billions * 1e9 * bytes_per_parameter / 1e9
    estimated_gb = raw_gb * overhead_factor
    passes = estimated_gb <= args.available_memory_gb

    print("Model memory estimate")
    print("inputs:")
    print(f"  params_billions: {args.params_billions:.1f}")
    print(f"  quantization: {args.quantization}")
    print(f"  overhead_profile: {args.overhead_profile}")
    print(f"  available_memory_gb: {args.available_memory_gb:.1f}")
    print("assumptions:")
    print("  constants_source: engineering/constants/compute.yaml")
    print("  overhead factor represents runtime metadata, quantization scales, allocator reserve, and implementation overhead")
    print("  estimate does not prove memory bandwidth, latency, KV-cache capacity, or sustained thermal behavior")
    print("formulas:")
    print("  raw_GB = params_billions * 1e9 * bytes_per_parameter / 1e9")
    print("  estimated_GB = raw_GB * overhead_factor")
    print("outputs:")
    print(f"  bytes_per_parameter: {bytes_per_parameter:.2f}")
    print(f"  overhead_factor: {overhead_factor:.2f}")
    print(f"  raw_memory_gb: {raw_gb:.1f}")
    print(f"  estimated_memory_gb: {estimated_gb:.1f}")
    print(f"  available_memory_gb: {args.available_memory_gb:.1f}")
    print(f"  pass_fail: {'pass' if passes else 'fail'}")
    print("confidence: medium for parameter storage arithmetic; low for full runtime feasibility")
    print("basis: estimated")
    print("primary blocker: package availability, bandwidth, KV cache, NPU throughput, software stack, and thermals")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
