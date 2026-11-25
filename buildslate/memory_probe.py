"""Exercise resident memory on a booted 128 GB target; never run implicitly."""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import mmap
import platform
import struct
import sys
import time
from collections.abc import Callable
from pathlib import Path

DEFAULT_MIN_TOTAL = 120_000_000_000
DEFAULT_ALLOCATION = 96 * 1024**3
DEFAULT_RESERVE = 8 * 1024**3
DEFAULT_CHUNK = 256 * 1024**2
PATTERN_REGION = 1024**2
PATTERN_ALGORITHM = "shake256-addressed-full-allocation-v1"
COPY_ALGORITHM = "ctypes-memmove-full-allocation-v1"
PAGE = mmap.PAGESIZE


def system_memory() -> dict[str, int | None]:
    """Return OS reported physical capacity and availability, plus swap use."""
    if sys.platform == "linux":
        values = {}
        for line in Path("/proc/meminfo").read_text(encoding="ascii").splitlines():
            key, _, value = line.partition(":")
            if key in {"MemTotal", "MemAvailable", "SwapTotal", "SwapFree"}:
                values[key] = int(value.strip().split()[0]) * 1024
        if set(values) != {"MemTotal", "MemAvailable", "SwapTotal", "SwapFree"}:
            raise OSError("Linux memory counters are incomplete")
        return {
            "total_bytes": values["MemTotal"],
            "available_bytes": values["MemAvailable"],
            "swap_used_bytes": values["SwapTotal"] - values["SwapFree"],
        }
    if sys.platform == "win32":

        class MemoryStatus(ctypes.Structure):
            _fields_ = [
                ("length", ctypes.c_ulong),
                ("load", ctypes.c_ulong),
                ("total_physical", ctypes.c_ulonglong),
                ("available_physical", ctypes.c_ulonglong),
                ("total_pagefile", ctypes.c_ulonglong),
                ("available_pagefile", ctypes.c_ulonglong),
                ("total_virtual", ctypes.c_ulonglong),
                ("available_virtual", ctypes.c_ulonglong),
                ("available_extended_virtual", ctypes.c_ulonglong),
            ]

        status = MemoryStatus()
        status.length = ctypes.sizeof(status)
        query = ctypes.windll.kernel32.GlobalMemoryStatusEx
        query.argtypes = [ctypes.POINTER(MemoryStatus)]
        query.restype = ctypes.c_int
        if not query(ctypes.byref(status)):
            raise OSError("GlobalMemoryStatusEx failed")
        return {
            "total_bytes": status.total_physical,
            "available_bytes": status.available_physical,
            "swap_used_bytes": None,
        }
    raise OSError("Memory probe supports Linux and Windows targets")


def resident_bytes() -> int:
    """Return this process's resident working set, including touched pages."""
    if sys.platform == "linux":
        for line in Path("/proc/self/status").read_text(encoding="ascii").splitlines():
            if line.startswith("VmRSS:"):
                return int(line.split()[1]) * 1024
        raise OSError("Linux VmRSS is unavailable")
    if sys.platform == "win32":

        class ProcessCounters(ctypes.Structure):
            _fields_ = [
                ("size", ctypes.c_ulong),
                ("page_fault_count", ctypes.c_ulong),
                ("peak_working_set_size", ctypes.c_size_t),
                ("working_set_size", ctypes.c_size_t),
                ("quota_peak_paged_pool_usage", ctypes.c_size_t),
                ("quota_paged_pool_usage", ctypes.c_size_t),
                ("quota_peak_nonpaged_pool_usage", ctypes.c_size_t),
                ("quota_nonpaged_pool_usage", ctypes.c_size_t),
                ("pagefile_usage", ctypes.c_size_t),
                ("peak_pagefile_usage", ctypes.c_size_t),
            ]

        counters = ProcessCounters()
        counters.size = ctypes.sizeof(counters)
        current = ctypes.windll.kernel32.GetCurrentProcess
        current.restype = ctypes.c_void_p
        query = ctypes.windll.psapi.GetProcessMemoryInfo
        query.argtypes = [
            ctypes.c_void_p,
            ctypes.POINTER(ProcessCounters),
            ctypes.c_ulong,
        ]
        query.restype = ctypes.c_int
        if not query(current(), ctypes.byref(counters), counters.size):
            raise OSError("GetProcessMemoryInfo failed")
        return counters.working_set_size
    raise OSError("Memory probe supports Linux and Windows targets")


def _pattern(block: int, offset: int, length: int) -> bytes:
    """Generate address-derived data for a bounded region."""
    return hashlib.shake_256(struct.pack("<QQ", block, offset)).digest(length)


def _fill_block(block: mmap.mmap, block_index: int, size: int) -> None:
    for offset in range(0, size, PATTERN_REGION):
        length = min(PATTERN_REGION, size - offset)
        block[offset : offset + length] = _pattern(block_index, offset, length)


def _verify_block(block: mmap.mmap, block_index: int, size: int) -> tuple[int, int]:
    verified_bytes = 0
    mismatched_regions = 0
    for offset in range(0, size, PATTERN_REGION):
        length = min(PATTERN_REGION, size - offset)
        verified_bytes += length
        if block[offset : offset + length] != _pattern(block_index, offset, length):
            mismatched_regions += 1
    return verified_bytes, mismatched_regions


def _stream_copy(
    blocks: list[mmap.mmap], lengths: list[int], chunk_bytes: int
) -> tuple[int, int]:
    """Time one sequential copy of every resident block into a reusable buffer."""
    with mmap.mmap(-1, chunk_bytes) as scratch:
        destination = ctypes.addressof(ctypes.c_char.from_buffer(scratch))
        started = time.perf_counter_ns()
        copied = 0
        for block, size in zip(blocks, lengths, strict=True):
            source = ctypes.addressof(ctypes.c_char.from_buffer(block))
            ctypes.memmove(destination, source, size)
            if (
                scratch[:64] != block[:64]
                or scratch[size - 64 : size] != block[size - 64 : size]
            ):
                raise ValueError("Memory stream copy sample did not match its source")
            copied += size
        elapsed_ns = max(1, time.perf_counter_ns() - started)
    return copied, elapsed_ns


def run_probe(
    *,
    unit_id: str,
    build_id: str,
    minimum_total_bytes: int = DEFAULT_MIN_TOTAL,
    allocation_bytes: int = DEFAULT_ALLOCATION,
    reserve_bytes: int = DEFAULT_RESERVE,
    chunk_bytes: int = DEFAULT_CHUNK,
    read_memory: Callable[[], dict[str, int | None]] = system_memory,
    read_resident: Callable[[], int] = resident_bytes,
) -> dict:
    """Write and verify every allocated byte, with physical headroom guards."""
    if not unit_id.strip() or not build_id.strip():
        raise ValueError("Unit and build IDs are required")
    if any(
        not isinstance(value, int) or isinstance(value, bool) or value <= 0
        for value in (minimum_total_bytes, allocation_bytes, reserve_bytes, chunk_bytes)
    ):
        raise ValueError("Memory limits must be positive integers")
    if chunk_bytes > allocation_bytes or chunk_bytes % PAGE or allocation_bytes % PAGE:
        raise ValueError("Allocation and chunk must be page-aligned; chunk must fit")
    before = read_memory()
    if before["total_bytes"] < minimum_total_bytes:
        raise ValueError("OS physical memory is below the required capacity")
    if before["available_bytes"] < allocation_bytes + reserve_bytes + chunk_bytes:
        raise ValueError(
            "Insufficient available physical memory plus copy buffer and reserve"
        )
    resident_before = read_resident()
    swap_before = before["swap_used_bytes"]
    blocks: list[mmap.mmap] = []
    lengths: list[int] = []
    started = time.monotonic()
    verified_bytes = 0
    errors = 0
    try:
        remaining = allocation_bytes
        while remaining:
            size = min(chunk_bytes, remaining)
            if read_memory()["available_bytes"] < size + reserve_bytes:
                raise MemoryError("Physical reserve fell below the requested minimum")
            block_index = len(blocks)
            block = mmap.mmap(-1, size)
            blocks.append(block)
            lengths.append(size)
            _fill_block(block, block_index, size)
            if read_memory()["available_bytes"] < reserve_bytes:
                raise MemoryError("Physical reserve fell below the requested minimum")
            remaining -= size
        during = read_memory()
        resident_during = max(0, read_resident() - resident_before)
        if during["available_bytes"] < reserve_bytes + chunk_bytes:
            raise MemoryError("Physical reserve cannot support the copy buffer")
        copied_bytes, copy_duration_ns = _stream_copy(blocks, lengths, chunk_bytes)
        if read_memory()["available_bytes"] < reserve_bytes:
            raise MemoryError("Physical reserve fell below the requested minimum")
        for index, (block, size) in enumerate(zip(blocks, lengths, strict=True)):
            checked, mismatches = _verify_block(block, index, size)
            verified_bytes += checked
            errors += mismatches
        after = read_memory()
        resident_after = max(0, read_resident() - resident_before)
        resident_delta = min(resident_during, resident_after)
        swap_during = during["swap_used_bytes"]
        swap_after = after["swap_used_bytes"]
        swap_delta = (
            max(0, swap_after - swap_before, swap_during - swap_before)
            if all(
                isinstance(value, int)
                for value in (swap_before, swap_during, swap_after)
            )
            else None
        )
        resident_floor = allocation_bytes * 99 // 100
        return {
            "status": (
                "pass"
                if errors == 0
                and verified_bytes == allocation_bytes
                and copied_bytes == allocation_bytes
                and resident_delta >= resident_floor
                and (
                    swap_delta == 0 or (sys.platform == "win32" and swap_delta is None)
                )
                else "fail"
            ),
            "unit_id": unit_id,
            "build_id": build_id,
            "host": platform.node(),
            "system": platform.platform(),
            "os_name": platform.system(),
            "os_total_physical_bytes": before["total_bytes"],
            "os_available_before_bytes": before["available_bytes"],
            "allocated_bytes": allocation_bytes,
            "resident_delta_bytes": resident_delta,
            "resident_during_bytes": resident_during,
            "resident_after_bytes": resident_after,
            "resident_floor_bytes": resident_floor,
            "verified_pages": verified_bytes // PAGE,
            "verified_bytes": verified_bytes,
            "stream_copy_algorithm": COPY_ALGORITHM,
            "stream_copy_bytes": copied_bytes,
            "stream_copy_duration_ns": copy_duration_ns,
            "stream_copy_bytes_per_s": copied_bytes * 1_000_000_000 // copy_duration_ns,
            "pattern_algorithm": PATTERN_ALGORITHM,
            "pattern_region_bytes": PATTERN_REGION,
            "memory_errors": errors,
            "swap_used_delta_bytes": swap_delta,
            "duration_s": round(time.monotonic() - started, 3),
            "caveat": "The full allocated-byte exercise and one-pass stream-copy rate do not identify DRAM MPNs, cover unallocated physical memory, isolate DRAM bandwidth from software and cache effects, validate routing, or establish a Slate phone build. Windows swap use is not independently measured; the working-set threshold is enforced.",
        }
    finally:
        for block in blocks:
            block.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--execute", action="store_true", help="Explicitly enable memory allocation"
    )
    parser.add_argument("--unit-id", required=True)
    parser.add_argument("--build-id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--minimum-total-bytes", type=int, default=DEFAULT_MIN_TOTAL)
    parser.add_argument("--allocation-bytes", type=int, default=DEFAULT_ALLOCATION)
    parser.add_argument("--reserve-bytes", type=int, default=DEFAULT_RESERVE)
    parser.add_argument("--chunk-bytes", type=int, default=DEFAULT_CHUNK)
    args = parser.parse_args()
    if not args.execute:
        parser.error("--execute is required; this test can allocate 96 GiB")
    try:
        result = run_probe(
            unit_id=args.unit_id,
            build_id=args.build_id,
            minimum_total_bytes=args.minimum_total_bytes,
            allocation_bytes=args.allocation_bytes,
            reserve_bytes=args.reserve_bytes,
            chunk_bytes=args.chunk_bytes,
        )
    except (OSError, ValueError, MemoryError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1
    args.output.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(result, indent=2) + "\n"
    args.output.write_text(serialized, encoding="utf-8")
    print(
        f"Wrote {args.output} (SHA-256 {hashlib.sha256(serialized.encode()).hexdigest()})"
    )
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
