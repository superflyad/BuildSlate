#!/usr/bin/env python3
"""First-pass memory bandwidth sufficiency screen for local AI workloads."""
from __future__ import annotations

import argparse
from common import positive_float, print_section


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--memory-capacity-gb", type=positive_float, default=512.0)
    parser.add_argument("--memory-bandwidth-gbps", type=positive_float, default=2048.0)
    parser.add_argument("--model-params-b", type=positive_float, default=70.0)
    parser.add_argument("--quantization-bits", type=positive_float, default=4.0)
    parser.add_argument("--target-tokens-per-sec", type=positive_float, default=25.0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    raw_model_size_gb = args.model_params_b * args.quantization_bits / 8.0
    active_model_footprint_gb = raw_model_size_gb * 1.25
    bytes_per_token_gb = active_model_footprint_gb
    bandwidth_demand_gbps = bytes_per_token_gb * args.target_tokens_per_sec * 8.0
    bandwidth_utilization_pct = bandwidth_demand_gbps / args.memory_bandwidth_gbps * 100.0
    capacity_headroom_gb = args.memory_capacity_gb - active_model_footprint_gb

    warnings: list[str] = []
    if active_model_footprint_gb > args.memory_capacity_gb:
        warnings.append("estimated active model footprint exceeds memory capacity")
    if bandwidth_utilization_pct > 70.0:
        warnings.append("bandwidth utilization exceeds 70%; memory bandwidth is likely a first-order limiter")
    if args.quantization_bits < 4.0:
        warnings.append("sub-4-bit quantization may add quality, kernel, or runtime constraints not modeled here")

    primary_blocker = "memory bandwidth headroom"
    if active_model_footprint_gb > args.memory_capacity_gb:
        primary_blocker = "memory capacity before bandwidth"
    elif bandwidth_utilization_pct <= 70.0:
        primary_blocker = "not flagged by this coarse bandwidth-only screen"

    print("Memory bandwidth screening model")
    print_section("assumptions", [
        "model weights dominate bytes moved per generated token in this conservative first-order screen",
        "active model footprint adds a 25% overhead allowance for metadata, activations, runtime buffers, and fragmentation",
        "memory bandwidth is treated as peak theoretical bandwidth, not sustained application bandwidth",
        "this is NOT a real inference-performance predictor",
        "KV cache, scheduling, NPU efficiency, runtime software, memory latency, batching, and sparsity are not modeled",
    ])
    print_section("formulas", [
        "raw_model_size_GB = model_params_B * quantization_bits / 8",
        "active_model_footprint_GB = raw_model_size_GB * 1.25",
        "bytes_per_token_estimate_GB = active_model_footprint_GB",
        "bandwidth_demand_Gbps = bytes_per_token_estimate_GB * target_tokens_per_sec * 8",
        "bandwidth_utilization_percent = bandwidth_demand_Gbps / memory_bandwidth_Gbps * 100",
    ])
    print_section("outputs", [
        f"memory_capacity_gb: {args.memory_capacity_gb:.0f}",
        f"memory_bandwidth_gbps: {args.memory_bandwidth_gbps:.0f}",
        f"model_params_b: {args.model_params_b:.0f}",
        f"quantization_bits: {args.quantization_bits:.0f}",
        f"target_tokens_per_sec: {args.target_tokens_per_sec:.0f}",
        f"raw_model_size_gb: {raw_model_size_gb:.1f}",
        f"estimated_active_model_footprint_gb: {active_model_footprint_gb:.1f}",
        f"bytes_per_token_estimate_gb: {bytes_per_token_gb:.1f}",
        f"estimated_bandwidth_demand_gbps: {bandwidth_demand_gbps:.0f}",
        f"bandwidth_utilization_percent: {bandwidth_utilization_pct:.0f}",
        f"capacity_headroom_gb: {capacity_headroom_gb:.1f}",
    ])
    print_section("warnings", warnings)
    print("confidence: low for performance prediction; medium for arithmetic screening")
    print("basis: conservative weight-streaming bandwidth estimate for local AI workload feasibility triage")
    print(f"primary blocker: {primary_blocker}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
