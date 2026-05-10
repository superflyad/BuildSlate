#!/usr/bin/env python3
"""Estimate whether a quantized model fits in Slate v1 memory."""

from __future__ import annotations

import argparse

SLATE_V1_MEMORY_GB = 64.0
DEFAULT_OVERHEAD_MULTIPLIER = 1.20
BYTES_PER_GB = 1024 ** 3


def parse_parameter_count(value: str) -> float:
    """Return parameter count as an absolute number of parameters."""
    text = value.strip().lower().replace("_", "")
    multipliers = {
        "k": 1_000,
        "m": 1_000_000,
        "b": 1_000_000_000,
        "t": 1_000_000_000_000,
    }
    if text[-1:] in multipliers:
        return float(text[:-1]) * multipliers[text[-1]]
    return float(text)


def estimate_memory_gb(parameter_count: float, quantization_bits: float, overhead_multiplier: float) -> float:
    raw_bytes = parameter_count * (quantization_bits / 8.0)
    return (raw_bytes * overhead_multiplier) / BYTES_PER_GB


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "parameter_count",
        nargs="?",
        default="7B",
        help="Model parameter count. Suffixes k, m, b, and t are supported. Default: 7B.",
    )
    parser.add_argument(
        "quantization_bits",
        nargs="?",
        type=float,
        default=4.0,
        help="Bits per parameter after quantization. Default: 4.",
    )
    parser.add_argument(
        "--overhead",
        type=float,
        default=DEFAULT_OVERHEAD_MULTIPLIER,
        help="Runtime overhead multiplier for metadata, KV cache, allocator slack, and buffers.",
    )
    parser.add_argument(
        "--capacity-gb",
        type=float,
        default=SLATE_V1_MEMORY_GB,
        help="Slate v1 memory capacity in GB. Default: 64.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    parameter_count = parse_parameter_count(args.parameter_count)
    required_gb = estimate_memory_gb(parameter_count, args.quantization_bits, args.overhead)
    fits = required_gb <= args.capacity_gb

    print("Slate v1 model-fit estimate")
    print(f"parameters: {parameter_count:,.0f}")
    print(f"quantization_bits: {args.quantization_bits:g}")
    print(f"overhead_multiplier: {args.overhead:.2f}")
    print(f"estimated_memory_required_gb: {required_gb:.2f}")
    print(f"slate_v1_memory_capacity_gb: {args.capacity_gb:.2f}")
    print(f"fit_result: {'PASS' if fits else 'FAIL'}")
    return 0 if fits else 1


if __name__ == "__main__":
    raise SystemExit(main())
