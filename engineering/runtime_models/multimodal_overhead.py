#!/usr/bin/env python3
"""Estimate additional resident memory pressure from multimodal runtime components."""

from __future__ import annotations

import argparse

from common import positive_float, print_section


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--llm-resident-gb", type=positive_float, default=43.75)
    parser.add_argument("--vision-model-gb", type=positive_float, default=3.0)
    parser.add_argument("--whisper-model-gb", type=positive_float, default=2.0)
    parser.add_argument("--embedding-model-gb", type=positive_float, default=1.0)
    parser.add_argument("--vector-index-gb", type=positive_float, default=8.0)
    parser.add_argument("--runtime-reserve-gb", type=positive_float, default=16.0)
    parser.add_argument("--available-memory-gb", type=positive_float, default=512.0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    total_gb = (
        args.llm_resident_gb
        + args.vision_model_gb
        + args.whisper_model_gb
        + args.embedding_model_gb
        + args.vector_index_gb
        + args.runtime_reserve_gb
    )
    remaining_gb = args.available_memory_gb - total_gb
    percent_used = total_gb / args.available_memory_gb * 100.0

    warnings: list[str] = []
    if percent_used > 75.0:
        warnings.append("multimodal resident memory exceeds 75% of available memory before KV cache and OS reserve")
    if remaining_gb < 64.0:
        warnings.append("remaining memory is below 64 GB before KV cache and OS reserve")
    if remaining_gb < 0.0:
        warnings.append("multimodal resident memory exceeds available memory")

    primary_blocker = "none flagged by multimodal residency arithmetic"
    if remaining_gb < 0.0:
        primary_blocker = "multimodal resident set exceeds available memory"
    elif remaining_gb < 64.0:
        primary_blocker = "limited memory headroom after multimodal residency"

    print("Multimodal overhead estimate")
    print_section("inputs", [
        f"llm_resident_gb: {args.llm_resident_gb:.2f}",
        f"vision_model_gb: {args.vision_model_gb:.2f}",
        f"whisper_model_gb: {args.whisper_model_gb:.2f}",
        f"embedding_model_gb: {args.embedding_model_gb:.2f}",
        f"vector_index_gb: {args.vector_index_gb:.2f}",
        f"runtime_reserve_gb: {args.runtime_reserve_gb:.2f}",
        f"available_memory_gb: {args.available_memory_gb:.2f}",
    ])
    print_section("assumptions", [
        "vision, speech, embedding, vector index, and runtime reserve may need resident memory alongside the LLM",
        "component sizes are placeholders until model choices, precision, and runtime implementation are known",
        "power overhead is acknowledged qualitatively but not converted into watts in this first-pass memory model",
        "this model estimates resident memory pressure only and does not predict real tokens/sec",
    ])
    print_section("formulas", [
        "total_multimodal_resident_gb = llm_resident_gb + vision_model_gb + whisper_model_gb + embedding_model_gb + vector_index_gb + runtime_reserve_gb",
        "remaining_memory_gb = available_memory_gb - total_multimodal_resident_gb",
        "percent_used = total_multimodal_resident_gb / available_memory_gb * 100",
    ])
    print_section("outputs", [
        f"total_multimodal_resident_memory_gb: {total_gb:.2f}",
        f"remaining_memory_gb: {remaining_gb:.2f}",
        f"percent_used: {percent_used:.2f}",
    ])
    print_section("warnings", warnings)
    print("confidence: low; multimodal component sizes are placeholders")
    print("basis: additive resident-memory budget for local multimodal runtime components")
    print(f"primary blocker: {primary_blocker}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
