#!/usr/bin/env python3
"""Deterministic regression tests for centralized core formula outputs."""

from __future__ import annotations

import math
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from engineering.core.calculator import Calculator  # noqa: E402


def assert_close(label: str, actual: float, expected: float, tolerance: float = 1e-6) -> None:
    if not math.isclose(actual, expected, rel_tol=tolerance, abs_tol=tolerance):
        raise AssertionError(f"{label}: expected {expected}, got {actual}")
    print(f"PASS: {label} = {actual:.6g}")


def main() -> int:
    calculator = Calculator()

    assert_close(
        "battery.energy_wh",
        calculator.compute(
            "battery.energy_wh",
            {"battery.capacity_mah": 6000, "battery.nominal_voltage_v": 3.85},
        ),
        23.1,
    )
    assert_close(
        "geometry.volume_cm3",
        calculator.compute(
            "geometry.volume_cm3",
            {"geometry.length_mm": 180, "geometry.width_mm": 95, "geometry.thickness_mm": 8.8},
        ),
        150.48,
    )
    assert_close(
        "geometry.surface_area_cm2",
        calculator.compute(
            "geometry.surface_area_cm2",
            {"geometry.length_mm": 180, "geometry.width_mm": 95, "geometry.thickness_mm": 8.8},
        ),
        390.37,
        tolerance=0.005,
    )
    assert_close(
        "thermal.heat_density_w_cm3",
        calculator.compute(
            "thermal.heat_density_w_cm3",
            {"thermal.sustained_w": 28, "geometry.volume_cm3": 150.48},
        ),
        28 / 150.48,
        tolerance=0.0005,
    )
    assert_close(
        "runtime.model_memory_gb",
        calculator.compute(
            "runtime.model_memory_gb",
            {
                "runtime.model_params_b": 70,
                "runtime.quantization_bits": 4,
                "runtime.model_overhead_factor": 1.25,
            },
        ),
        43.75,
    )

    expected_kv_cache_gb = (2 * 32 * 4096 * 8192 * 1 * 2) / 1_000_000_000
    assert_close("runtime.kv_cache_gb", calculator.compute("runtime.kv_cache_gb"), expected_kv_cache_gb)

    print("All deterministic core formula output checks passed.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001 - validation CLI should report actionable failures.
        print(f"FAIL: {exc}")
        raise SystemExit(1) from exc
