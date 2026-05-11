#!/usr/bin/env python3
"""Estimate local LLM KV cache memory requirements."""

from __future__ import annotations

import argparse

from common import positive_float, positive_int, print_section


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--layers", type=positive_int, default=80)
    parser.add_argument("--hidden-size", type=positive_int, default=8192)
    parser.add_argument("--context-tokens", type=positive_int, default=32768)
    parser.add_argument("--batch-size", type=positive_int, default=1)
    parser.add_argument("--kv-bytes-per-element", type=positive_float, default=2.0)
    parser.add_argument("--available-memory-gb", type=positive_float, default=512.0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    kv_bytes = 2 * args.layers * args.hidden_size * args.context_tokens * args.batch_size * args.kv_bytes_per_element
    kv_gb = kv_bytes / 1e9
    percent_available = kv_gb / args.available_memory_gb * 100.0

    warnings: list[str] = []
    if percent_available > 25.0:
        warnings.append("KV cache exceeds 25% of available memory")
    if args.context_tokens > 32768:
        warnings.append("context length exceeds 32768 tokens; long-context residency pressure is high")
    if args.batch_size > 1:
        warnings.append("batch size above 1 linearly increases KV cache memory")

    primary_blocker = "none flagged by KV cache arithmetic"
    if percent_available > 25.0:
        primary_blocker = "KV cache consumes more than 25% of available memory"
    elif args.context_tokens > 32768:
        primary_blocker = "long context length"
    elif args.batch_size > 1:
        primary_blocker = "batch-size-driven KV cache growth"

    print("KV cache memory estimate")
    print_section("inputs", [
        f"layers: {args.layers}",
        f"hidden_size: {args.hidden_size}",
        f"context_tokens: {args.context_tokens}",
        f"batch_size: {args.batch_size}",
        f"kv_bytes_per_element: {args.kv_bytes_per_element:.1f}",
        f"available_memory_gb: {args.available_memory_gb:.1f}",
    ])
    print_section("assumptions", [
        "factor 2 represents keys and values",
        "KV cache sizing is architecture-dependent",
        "grouped-query attention and implementation details can reduce KV size",
        "this model estimates memory pressure only and does not predict real tokens/sec",
    ])
    print_section("formulas", [
        "kv_bytes = 2 * layers * hidden_size * context_tokens * batch_size * kv_bytes_per_element",
        "kv_gb = kv_bytes / 1e9",
        "percent_available_memory = kv_gb / available_memory_gb * 100",
    ])
    print_section("outputs", [
        f"kv_cache_gb: {kv_gb:.2f}",
        f"percent_available_memory: {percent_available:.2f}",
    ])
    print_section("warnings", warnings)
    print("confidence: medium for dense KV arithmetic; low for architecture-specific runtime residency")
    print("basis: standard first-pass keys-plus-values cache capacity estimate")
    print(f"primary blocker: {primary_blocker}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
