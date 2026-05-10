#!/usr/bin/env python3
"""Estimate memory required for local model inference."""

from __future__ import annotations

import argparse


def estimate_memory_gb(params_billions: float, quant_bits: float, overhead: float) -> tuple[float, float]:
    raw_gb = params_billions * 1e9 * quant_bits / 8 / 1e9
    estimated_gb = raw_gb * overhead
    return raw_gb, estimated_gb


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--params-billions", type=float, default=30.0)
    parser.add_argument("--quant-bits", type=float, default=4.0)
    parser.add_argument("--overhead", type=float, default=1.25)
    parser.add_argument("--available-memory-gb", type=float, default=512.0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    raw_gb, estimated_gb = estimate_memory_gb(
        args.params_billions,
        args.quant_bits,
        args.overhead,
    )
    passes = estimated_gb <= args.available_memory_gb

    print("Model memory estimate")
    print(f"  model params: {args.params_billions:g}B")
    print(f"  quant bits: {args.quant_bits:g}")
    print(f"  overhead: {args.overhead:g}x")
    print(f"  raw memory GB: {raw_gb:.2f}")
    print(f"  estimated memory GB: {estimated_gb:.2f}")
    print(f"  available memory GB: {args.available_memory_gb:.2f}")
    print(f"  result: {'PASS' if passes else 'FAIL'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
