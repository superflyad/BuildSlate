#!/usr/bin/env python3
"""Show how KV cache memory scales with context length."""

from __future__ import annotations

import argparse

from common import positive_float, positive_int, print_section

CONTEXT_LENGTHS = (4096, 8192, 16384, 32768, 65536, 131072)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--layers", type=positive_int, default=80)
    parser.add_argument("--hidden-size", type=positive_int, default=8192)
    parser.add_argument("--batch-size", type=positive_int, default=1)
    parser.add_argument("--kv-bytes-per-element", type=positive_float, default=2.0)
    parser.add_argument("--available-memory-gb", type=positive_float, default=512.0)
    return parser.parse_args()


def kv_cache_gb(layers: int, hidden_size: int, context_tokens: int, batch_size: int, kv_bytes_per_element: float) -> float:
    kv_bytes = 2 * layers * hidden_size * context_tokens * batch_size * kv_bytes_per_element
    return kv_bytes / 1e9


def main() -> int:
    args = parse_args()
    rows = []
    warnings: list[str] = []
    for context_tokens in CONTEXT_LENGTHS:
        kv_gb = kv_cache_gb(args.layers, args.hidden_size, context_tokens, args.batch_size, args.kv_bytes_per_element)
        percent_available = kv_gb / args.available_memory_gb * 100.0
        rows.append((context_tokens, kv_gb, percent_available))
        if context_tokens > 32768 and percent_available > 25.0:
            warnings.append(f"{context_tokens} tokens exceeds 32768 and consumes {percent_available:.1f}% of available memory")
    if args.batch_size > 1:
        warnings.append("batch size above 1 linearly multiplies every context-length row")

    primary_blocker = "long-context KV cache memory growth" if warnings else "none flagged by context scaling table"

    print("Context scaling estimate")
    print_section("inputs", [
        f"layers: {args.layers}",
        f"hidden_size: {args.hidden_size}",
        f"batch_size: {args.batch_size}",
        f"kv_bytes_per_element: {args.kv_bytes_per_element:.1f}",
        f"available_memory_gb: {args.available_memory_gb:.1f}",
    ])
    print_section("assumptions", [
        "KV cache scales linearly with context length, layers, hidden size, and batch size",
        "factor 2 represents keys and values",
        "architecture choices such as grouped-query attention can change the realized cache size",
        "this model does not predict real tokens/sec",
    ])
    print_section("formulas", [
        "kv_bytes = 2 * layers * hidden_size * context_tokens * batch_size * kv_bytes_per_element",
        "kv_cache_gb = kv_bytes / 1e9",
        "percent_available_memory = kv_cache_gb / available_memory_gb * 100",
    ])
    print("outputs:")
    print("  context_tokens | kv_cache_gb | percent_available_memory")
    for context_tokens, kv_gb, percent_available in rows:
        print(f"  {context_tokens:14d} | {kv_gb:11.2f} | {percent_available:24.2f}")
    print_section("warnings", warnings)
    print("confidence: medium for relative scaling; low for architecture-specific runtime residency")
    print("basis: repeated first-pass KV cache formula across fixed context lengths")
    print(f"primary blocker: {primary_blocker}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
