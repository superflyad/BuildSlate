#!/usr/bin/env python3
"""Validate stable physics formula migration into the centralized calculation core."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def run_command(command: list[str]) -> str:
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"command failed ({completed.returncode}): {' '.join(command)}\n"
            f"stdout:\n{completed.stdout}\n"
            f"stderr:\n{completed.stderr}"
        )
    return completed.stdout


def require_contains(output: str, expected_values: tuple[str, ...], context: str) -> None:
    missing = [expected for expected in expected_values if expected not in output]
    if missing:
        raise AssertionError(f"{context} missing {missing!r}\noutput:\n{output}")


def validate_dependency_graph() -> None:
    sys.path.insert(0, str(REPO_ROOT))
    from engineering.core.calculator import Calculator
    from engineering.core.dependency_graph import DependencyGraph

    calculator = Calculator()
    checks = {
        "geometry.volume_cm3": {"geometry.length_mm", "geometry.width_mm", "geometry.thickness_mm"},
        "thermal.heat_flux_w_cm2": {"thermal.sustained_w", "geometry.surface_area_cm2"},
        "runtime.available_memory_margin_gb": {
            "runtime.available_memory_gb",
            "runtime.total_runtime_memory_gb",
            "runtime.model_memory_gb",
            "runtime.kv_cache_gb",
        },
    }
    graph = DependencyGraph(calculator.formulas)
    for variable_id, expected in checks.items():
        resolved = set(graph.resolve_dependencies(variable_id))
        missing = expected - resolved
        if missing:
            raise AssertionError(f"{variable_id} dependency graph missing: {sorted(missing)}")


def main() -> int:
    command_checks = (
        ([sys.executable, "engineering/models/surface_area.py"], ("Surface area estimate", "surface_area_cm2:", "volume_cm3:"), "surface area model"),
        ([sys.executable, "engineering/models/surface_area.py", "--explain"], ("geometry.surface_area_cm2", "geometry.volume_cm3"), "surface area explanation"),
        ([sys.executable, "engineering/models/thermal_limits.py"], ("Thermal limits estimate", "heat_density_w_cm3:", "heat_flux_w_cm2:"), "thermal limits model"),
        ([sys.executable, "engineering/models/thermal_limits.py", "--explain"], ("thermal.heat_density_w_cm3", "thermal.heat_flux_w_cm2"), "thermal limits explanation"),
        ([sys.executable, "engineering/models/model_memory.py"], ("Model memory estimate", "estimated_memory_gb:", "pass_fail:"), "model memory model"),
        ([sys.executable, "engineering/models/model_memory.py", "--explain"], ("runtime.model_memory_gb", "runtime.model_overhead_factor"), "model memory explanation"),
        (
            [
                sys.executable,
                "engineering/core/calculator.py",
                "--set",
                "geometry.length_mm=180",
                "--set",
                "geometry.width_mm=95",
                "--set",
                "geometry.thickness_mm=8.8",
                "--compute",
                "geometry.volume_cm3",
            ],
            ("geometry.volume_cm3 = 150.48 cm3",),
            "calculator geometry formula",
        ),
        (
            [
                sys.executable,
                "engineering/core/calculator.py",
                "--set",
                "thermal.sustained_w=28",
                "--set",
                "geometry.volume_cm3=150.48",
                "--compute",
                "thermal.heat_density_w_cm3",
            ],
            ("thermal.heat_density_w_cm3 = 0.186071 W/cm3",),
            "calculator thermal formula",
        ),
        (
            [
                sys.executable,
                "engineering/core/calculator.py",
                "--set",
                "runtime.model_params_b=70",
                "--set",
                "runtime.quantization_bits=4",
                "--set",
                "runtime.model_overhead_factor=1.25",
                "--set",
                "runtime.layers=80",
                "--set",
                "runtime.hidden_size=8192",
                "--set",
                "runtime.context_tokens=32768",
                "--set",
                "runtime.batch_size=1",
                "--set",
                "runtime.kv_bytes_per_element=2",
                "--set",
                "runtime.multimodal_overhead_gb=30",
                "--set",
                "runtime.os_reserve_gb=16",
                "--set",
                "runtime.safety_reserve_gb=32",
                "--set",
                "runtime.available_memory_gb=512",
                "--compute",
                "runtime.available_memory_margin_gb",
            ],
            ("runtime.available_memory_margin_gb = 304.351 GB",),
            "calculator runtime memory formula",
        ),
    )

    for command, expected_values, context in command_checks:
        output = run_command(list(command))
        require_contains(output, expected_values, context)
        print(f"PASS: {context}")

    validate_dependency_graph()
    print("PASS: dependency graph migrated dependencies")
    print("All core formula migration validations passed.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001 - validation CLI should report actionable failures.
        print(f"FAIL: {exc}")
        raise SystemExit(1) from exc
