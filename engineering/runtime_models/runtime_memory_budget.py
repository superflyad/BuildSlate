#!/usr/bin/env python3
"""Combine local AI runtime memory residency, KV cache, OS reserve, and safety reserve."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from engineering.core.calculator import Calculator
from engineering.core.explanation_engine import ExplanationEngine

from common import positive_float, positive_int, print_section


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--available-memory-gb", type=positive_float, default=512.0)
    parser.add_argument("--params-billions", type=positive_float, default=70.0)
    parser.add_argument("--quantization-bits", type=positive_float, default=4.0)
    parser.add_argument("--model-overhead-factor", type=positive_float, default=1.25)
    parser.add_argument("--layers", type=positive_int, default=80)
    parser.add_argument("--hidden-size", type=positive_int, default=8192)
    parser.add_argument("--context-tokens", type=positive_int, default=32768)
    parser.add_argument("--batch-size", type=positive_int, default=1)
    parser.add_argument("--kv-bytes-per-element", type=positive_float, default=2.0)
    parser.add_argument("--multimodal-overhead-gb", type=positive_float, default=30.0)
    parser.add_argument("--os-reserve-gb", type=positive_float, default=16.0)
    parser.add_argument("--safety-reserve-gb", type=positive_float, default=32.0)
    parser.add_argument("--explain", action="store_true", help="Print centralized runtime memory calculation explanations")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    calculator = Calculator()
    raw_inputs = {
        "runtime.model_params_b": args.params_billions,
        "runtime.quantization_bits": args.quantization_bits,
        "runtime.model_overhead_factor": 1.0,
    }
    core_inputs = {
        **raw_inputs,
        "runtime.model_overhead_factor": args.model_overhead_factor,
        "runtime.layers": args.layers,
        "runtime.hidden_size": args.hidden_size,
        "runtime.context_tokens": args.context_tokens,
        "runtime.batch_size": args.batch_size,
        "runtime.kv_bytes_per_element": args.kv_bytes_per_element,
        "runtime.multimodal_overhead_gb": args.multimodal_overhead_gb,
        "runtime.os_reserve_gb": args.os_reserve_gb,
        "runtime.safety_reserve_gb": args.safety_reserve_gb,
        "runtime.available_memory_gb": args.available_memory_gb,
    }
    raw_model_gb = calculator.compute("runtime.model_memory_gb", raw_inputs)
    model_resident_gb = calculator.compute("runtime.model_memory_gb", core_inputs)
    kv_cache_gb = calculator.compute("runtime.kv_cache_gb", core_inputs)
    total_used_gb = calculator.compute("runtime.total_runtime_memory_gb", core_inputs)
    remaining_gb = calculator.compute("runtime.available_memory_margin_gb", core_inputs)
    passes = remaining_gb >= 0.0

    warnings: list[str] = []
    if remaining_gb < 64.0:
        warnings.append("remaining memory is below 64 GB")
    if kv_cache_gb > model_resident_gb:
        warnings.append("KV cache is larger than model weights/resident model estimate")
    if total_used_gb > args.available_memory_gb:
        warnings.append("total used memory exceeds available memory")
    if args.context_tokens > 32768:
        warnings.append("context length exceeds 32768 tokens; memory use scales linearly")
    if args.batch_size > 1:
        warnings.append("batch size above 1 linearly increases KV cache memory")

    primary_blocker = "none flagged by combined memory budget"
    if total_used_gb > args.available_memory_gb:
        primary_blocker = "total runtime memory budget exceeds available memory"
    elif remaining_gb < 64.0:
        primary_blocker = "limited memory headroom after reserves"
    elif kv_cache_gb > model_resident_gb:
        primary_blocker = "KV cache dominates resident model weights"

    print("Runtime memory budget estimate")
    print_section("inputs", [
        f"available_memory_gb: {args.available_memory_gb:.2f}",
        f"params_billions: {args.params_billions:.1f}",
        f"quantization_bits: {args.quantization_bits:.1f}",
        f"model_overhead_factor: {args.model_overhead_factor:.2f}",
        f"layers: {args.layers}",
        f"hidden_size: {args.hidden_size}",
        f"context_tokens: {args.context_tokens}",
        f"batch_size: {args.batch_size}",
        f"kv_bytes_per_element: {args.kv_bytes_per_element:.1f}",
        f"multimodal_overhead_gb: {args.multimodal_overhead_gb:.2f}",
        f"os_reserve_gb: {args.os_reserve_gb:.2f}",
        f"safety_reserve_gb: {args.safety_reserve_gb:.2f}",
    ])
    print_section("assumptions", [
        "model residency uses quantized weight storage plus a conservative runtime overhead factor",
        "KV cache scales linearly with context length, layers, hidden size, and batch size",
        "multimodal overhead, OS reserve, and safety reserve are additive placeholders",
        "this combined memory budget does not predict real tokens/sec",
    ])
    print_section("formulas", [
        "raw_model_gb = params_billions * 1e9 * quantization_bits / 8 / 1e9",
        "model_resident_gb = raw_model_gb * model_overhead_factor",
        "kv_cache_gb = 2 * layers * hidden_size * context_tokens * batch_size * kv_bytes_per_element / 1e9",
        "total_used_gb = model_resident_gb + kv_cache_gb + multimodal_overhead_gb + os_reserve_gb + safety_reserve_gb",
        "remaining_gb = available_memory_gb - total_used_gb",
    ])
    print_section("outputs", [
        f"model_resident_gb: {model_resident_gb:.2f}",
        f"kv_cache_gb: {kv_cache_gb:.2f}",
        f"multimodal_overhead_gb: {args.multimodal_overhead_gb:.2f}",
        f"os_reserve_gb: {args.os_reserve_gb:.2f}",
        f"safety_reserve_gb: {args.safety_reserve_gb:.2f}",
        f"total_used_gb: {total_used_gb:.2f}",
        f"remaining_gb: {remaining_gb:.2f}",
        f"pass_fail: {'pass' if passes else 'fail'}",
    ])
    print_section("warnings", warnings)
    if args.explain:
        explanation_engine = ExplanationEngine()
        print("explanation:")
        print(explanation_engine.explain("runtime.model_memory_gb", core_inputs))
        print(explanation_engine.explain("runtime.kv_cache_gb", core_inputs))
        print(explanation_engine.explain("runtime.total_runtime_memory_gb", core_inputs))
        print(explanation_engine.explain("runtime.available_memory_margin_gb", core_inputs))
    print("confidence: low for complete runtime feasibility; medium for combined memory arithmetic")
    print("basis: additive first-pass local AI runtime memory budget")
    print(f"primary blocker: {primary_blocker}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
