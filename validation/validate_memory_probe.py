"""Smoke test guarded resident memory exercise without claiming a 128 GB run."""

from __future__ import annotations

import mmap
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from buildslate.memory_probe import (  # noqa: E402
    PAGE,
    PATTERN_ALGORITHM,
    PATTERN_REGION,
    _fill_block,
    _verify_block,
    run_probe,
)


def _reject(**overrides: object) -> None:
    arguments = {
        "unit_id": "fixture-unit",
        "build_id": "fixture-build",
        "minimum_total_bytes": 1,
        "allocation_bytes": 4 * 1024**2,
        "reserve_bytes": 4 * 1024**2,
        "chunk_bytes": 1024**2,
        "read_memory": lambda: {
            "total_bytes": 128 * 1024**3,
            "available_bytes": 128 * 1024**3,
            "swap_used_bytes": 0,
        },
        "read_resident": lambda: 0,
    }
    arguments.update(overrides)
    try:
        run_probe(**arguments)
    except ValueError:
        return
    raise ValueError(f"Unsafe memory request passed guards: {overrides}")


def main() -> int:
    result = run_probe(
        unit_id="fixture-unit",
        build_id="fixture-build",
        minimum_total_bytes=1,
        allocation_bytes=32 * 1024**2,
        reserve_bytes=32 * 1024**2,
        chunk_bytes=8 * 1024**2,
    )
    if (
        result["status"] != "pass"
        or result["verified_pages"] != 32 * 1024**2 // PAGE
        or result["verified_bytes"] != 32 * 1024**2
        or result["pattern_algorithm"] != PATTERN_ALGORITHM
        or result["memory_errors"] != 0
    ):
        raise ValueError(f"Small resident memory smoke failed: {result}")
    with mmap.mmap(-1, 2 * PATTERN_REGION) as block:
        _fill_block(block, 7, len(block))
        if _verify_block(block, 7, len(block)) != (len(block), 0):
            raise ValueError("Full-byte pattern did not verify")
        block[PATTERN_REGION + 100] ^= 1
        if _verify_block(block, 7, len(block)) != (len(block), 1):
            raise ValueError("Corruption outside the page marker was not detected")
    _reject(minimum_total_bytes=129 * 1024**3)
    _reject(
        read_memory=lambda: {
            "total_bytes": 128 * 1024**3,
            "available_bytes": 4 * 1024**2,
            "swap_used_bytes": 0,
        }
    )
    _reject(allocation_bytes=4 * 1024**2 + 1)
    _reject(unit_id="")
    print("PASS: guarded memory probe and 32 MiB full-byte exercise")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
