#!/usr/bin/env python3
"""Run one-parameter scenario sweeps against a BuildSlate device profile."""

from __future__ import annotations

import argparse
import copy
import math
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError as exc:  # pragma: no cover - dependency guidance path
    raise SystemExit("PyYAML is required. Install dependencies with: pip install -r requirements.txt") from exc

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = REPO_ROOT / "reports" / "sweeps" / "sweep-report.txt"

REQUIRED_TOP_LEVEL_SECTIONS = (
    "identity",
    "geometry",
    "mass_targets",
    "battery",
    "display",
    "compute",
    "memory",
    "storage",
    "thermal",
    "materials",
    "chassis_composite",
    "component_assumptions",
    "interconnect",
    "runtime",
    "manufacturing",
    "environment",
    "notes",
)

SUPPORTED_PARAMETER_PATHS = {
    "geometry.thickness_mm",
    "geometry.length_mm",
    "geometry.width_mm",
    "battery.capacity_mah",
    "compute.sustained_power_w",
    "compute.peak_power_w",
    "memory.capacity_gb",
    "memory.gb_per_package",
    "storage.capacity_tb",
    "thermal.sustained_w",
    "thermal.ambient_c",
    "runtime.model_params_billions",
    "runtime.context_tokens",
    "environment.condition",
    "environment.brightness_mode",
}

THICKNESS_PARAMETERS = {"geometry.thickness_mm", "geometry.length_mm", "geometry.width_mm"}
SUSTAINED_POWER_PARAMETERS = {"compute.sustained_power_w", "thermal.sustained_w"}
MEMORY_PARAMETERS = {"memory.capacity_gb", "memory.gb_per_package"}
BATTERY_PARAMETERS = {"battery.capacity_mah"}
AMBIENT_PARAMETERS = {"thermal.ambient_c"}


@dataclass
class SweepRow:
    value: Any
    outputs: dict[str, str] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", required=True, help="Device profile YAML path")
    parser.add_argument("--parameter", required=True, help="Dot-path parameter to mutate")
    parser.add_argument("--values", required=True, nargs="+", help="Sweep values")
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT.relative_to(REPO_ROOT)),
        help="Report output path (default: reports/sweeps/sweep-report.txt)",
    )
    return parser.parse_args()


def resolve_repo_path(path_text: str) -> Path:
    path = Path(path_text)
    return path if path.is_absolute() else REPO_ROOT / path


def repo_relative(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def load_profile(profile_path: Path) -> dict[str, Any]:
    with profile_path.open("r", encoding="utf-8") as profile_file:
        data = yaml.safe_load(profile_file)
    if not isinstance(data, dict):
        raise ValueError("profile root must be a mapping/object")
    return data


def require_mapping(profile: dict[str, Any], section_name: str) -> dict[str, Any]:
    section = profile.get(section_name)
    if not isinstance(section, dict):
        raise ValueError(f"{section_name} must be a mapping")
    return section


def validate_profile_basic(profile: dict[str, Any]) -> list[str]:
    warnings: list[str] = []
    missing = [section for section in REQUIRED_TOP_LEVEL_SECTIONS if section not in profile]
    if missing:
        warnings.append("validation_fail")
        return warnings
    for section in REQUIRED_TOP_LEVEL_SECTIONS:
        if section != "notes" and not isinstance(profile.get(section), dict):
            warnings.append("validation_fail")
            return warnings
    return warnings


def get_path(profile: dict[str, Any], parameter_path: str) -> Any:
    current: Any = profile
    for part in parameter_path.split("."):
        if not isinstance(current, dict) or part not in current:
            raise ValueError(f"parameter path does not exist in profile: {parameter_path}")
        current = current[part]
    return current


def coerce_value(raw_value: str, reference_value: Any) -> Any:
    if isinstance(reference_value, bool):
        lowered = raw_value.lower()
        if lowered in {"1", "true", "yes", "y", "on"}:
            return True
        if lowered in {"0", "false", "no", "n", "off"}:
            return False
        raise ValueError(f"cannot parse boolean sweep value: {raw_value}")
    if isinstance(reference_value, int) and not isinstance(reference_value, bool):
        parsed = float(raw_value)
        if not parsed.is_integer():
            raise ValueError(f"expected integer-like value for this parameter: {raw_value}")
        return int(parsed)
    if isinstance(reference_value, float):
        return float(raw_value)
    return raw_value


def set_path(profile: dict[str, Any], parameter_path: str, value: Any) -> None:
    parts = parameter_path.split(".")
    current: Any = profile
    for part in parts[:-1]:
        if not isinstance(current, dict) or part not in current:
            raise ValueError(f"parameter path does not exist in profile: {parameter_path}")
        current = current[part]
    if not isinstance(current, dict) or parts[-1] not in current:
        raise ValueError(f"parameter path does not exist in profile: {parameter_path}")
    current[parts[-1]] = value


def numeric(profile: dict[str, Any], section: str, key: str) -> float:
    return float(require_mapping(profile, section)[key])


def text_value(profile: dict[str, Any], section: str, key: str) -> str:
    return str(require_mapping(profile, section).get(key, "unknown"))


def rectangular_volume_cm3(length_mm: float, width_mm: float, thickness_mm: float) -> float:
    return length_mm * width_mm * thickness_mm / 1000.0


def rectangular_surface_area_cm2(length_mm: float, width_mm: float, thickness_mm: float) -> float:
    return 2.0 * (length_mm * width_mm + length_mm * thickness_mm + width_mm * thickness_mm) / 100.0


def classify_thermal_risk(heat_density_w_cm3: float) -> str:
    # Matches the conservative first-pass bands used by the thermal limits model constants.
    if heat_density_w_cm3 <= 0.08:
        return "low"
    if heat_density_w_cm3 <= 0.15:
        return "moderate"
    if heat_density_w_cm3 <= 0.25:
        return "high"
    return "extreme"


def zone_stackup_margin_mm(thickness_mm: float) -> float:
    # Current maximum nominal zone stack is camera_zone: 0.6 + 1.2 + 0.2 + 5.0 + 1.0 + 0.8 = 8.8 mm.
    worst_nominal_zone_mm = 8.8
    return thickness_mm - worst_nominal_zone_mm


def battery_metrics(profile: dict[str, Any], workload_w: float | None = None) -> dict[str, float]:
    capacity_mah = numeric(profile, "battery", "capacity_mah")
    nominal_voltage_v = numeric(profile, "battery", "nominal_voltage_v")
    workload = workload_w if workload_w is not None else numeric(profile, "compute", "sustained_power_w")
    wh = capacity_mah / 1000.0 * nominal_voltage_v
    usable_wh = wh * 0.86
    runtime_h = usable_wh / workload
    volume_cm3 = wh / 0.65
    mass_g = wh / 0.24
    return {
        "battery_wh": wh,
        "usable_wh": usable_wh,
        "battery_runtime_h": runtime_h,
        "battery_volume_cm3": volume_cm3,
        "battery_mass_g": mass_g,
    }


def thermal_metrics(profile: dict[str, Any], sustained_w: float | None = None) -> dict[str, Any]:
    length_mm = numeric(profile, "geometry", "length_mm")
    width_mm = numeric(profile, "geometry", "width_mm")
    thickness_mm = numeric(profile, "geometry", "thickness_mm")
    heat_w = sustained_w if sustained_w is not None else numeric(profile, "thermal", "sustained_w")
    volume_cm3 = rectangular_volume_cm3(length_mm, width_mm, thickness_mm)
    surface_area_cm2 = rectangular_surface_area_cm2(length_mm, width_mm, thickness_mm)
    heat_density = heat_w / volume_cm3
    heat_flux = heat_w / surface_area_cm2
    return {
        "volume_cm3": volume_cm3,
        "surface_area_cm2": surface_area_cm2,
        "heat_density_w_cm3": heat_density,
        "heat_flux_w_cm2": heat_flux,
        "thermal_risk": classify_thermal_risk(heat_density),
    }


def memory_metrics(profile: dict[str, Any]) -> dict[str, Any]:
    capacity_gb = numeric(profile, "memory", "capacity_gb")
    gb_per_package = numeric(profile, "memory", "gb_per_package")
    package_count = math.ceil(capacity_gb / gb_per_package)
    package_area_mm2 = package_count * 120.0
    active_memory_power_w = capacity_gb * 0.025

    params_billions = numeric(profile, "runtime", "model_params_billions")
    quantization_bits = numeric(profile, "runtime", "quantization_bits")
    context_tokens = int(numeric(profile, "runtime", "context_tokens"))
    model_resident_gb = params_billions * quantization_bits / 8.0 * 1.25
    kv_cache_gb = 2 * 80 * 8192 * context_tokens * 1 * 2.0 / 1e9
    total_used_gb = model_resident_gb + kv_cache_gb + 30.0 + 16.0 + 32.0
    remaining_gb = capacity_gb - total_used_gb

    return {
        "memory_package_count": package_count,
        "memory_area_mm2": package_area_mm2,
        "active_memory_power_w": active_memory_power_w,
        "runtime_used_gb": total_used_gb,
        "runtime_remaining_gb": remaining_gb,
        "runtime_pass": remaining_gb >= 0.0,
    }


def ambient_metrics(profile: dict[str, Any]) -> dict[str, Any]:
    ambient_c = numeric(profile, "thermal", "ambient_c")
    max_skin_c = numeric(profile, "thermal", "max_skin_c")
    skin_rise_c = 18.0
    estimated_skin_c = ambient_c + skin_rise_c
    margin_c = max_skin_c - estimated_skin_c
    if estimated_skin_c >= 45:
        throttle_pressure = "critical"
    elif estimated_skin_c >= max_skin_c:
        throttle_pressure = "limit"
    elif margin_c < 5:
        throttle_pressure = "caution"
    else:
        throttle_pressure = "normal"
    return {
        "estimated_skin_c": estimated_skin_c,
        "skin_margin_c": margin_c,
        "throttle_pressure": throttle_pressure,
    }


def add_common_warnings(row: SweepRow, outputs: dict[str, str]) -> None:
    if outputs.get("thermal_risk") in {"high", "extreme"}:
        row.warnings.append("high_thermal_risk")
    if "battery_runtime_h" in outputs and float(outputs["battery_runtime_h"]) < 1.0:
        row.warnings.append("runtime_low")
    if "zone_margin_mm" in outputs and float(outputs["zone_margin_mm"]) < 0.0:
        row.warnings.append("stackup_fail")
    if "runtime_remaining_gb" in outputs and float(outputs["runtime_remaining_gb"]) < 64.0:
        row.warnings.append("memory_pressure")
    if "memory_package_count" in outputs and int(outputs["memory_package_count"]) > 8:
        row.warnings.append("memory_pressure")
    if "battery_mass_g" in outputs and float(outputs["battery_mass_g"]) > 110.0:
        row.warnings.append("mass_pressure")
    if outputs.get("throttle_pressure") in {"caution", "limit", "critical"}:
        row.warnings.append("throttle_pressure")


def format_float(value: float, digits: int = 2) -> str:
    return f"{value:.{digits}f}"


def evaluate_profile(profile: dict[str, Any], parameter_path: str, value: Any) -> SweepRow:
    row = SweepRow(value=value)
    row.warnings.extend(validate_profile_basic(profile))

    outputs: dict[str, str] = {"profile_value": str(get_path(profile, parameter_path))}

    if parameter_path in THICKNESS_PARAMETERS:
        thermal = thermal_metrics(profile)
        base_volume = rectangular_volume_cm3(180.0, 95.0, 8.8)
        outputs.update(
            {
                "battery_runtime_h": format_float(battery_metrics(profile)["battery_runtime_h"]),
                "thermal_risk": str(thermal["thermal_risk"]),
                "zone_margin_mm": format_float(zone_stackup_margin_mm(numeric(profile, "geometry", "thickness_mm")), 1),
                "volume_cm3": format_float(float(thermal["volume_cm3"]), 1),
                "volume_delta_cm3": format_float(float(thermal["volume_cm3"]) - base_volume, 1),
            }
        )
    elif parameter_path in SUSTAINED_POWER_PARAMETERS:
        heat_w = numeric(profile, "compute", "sustained_power_w") if parameter_path == "compute.sustained_power_w" else numeric(profile, "thermal", "sustained_w")
        thermal = thermal_metrics(profile, sustained_w=heat_w)
        battery = battery_metrics(profile, workload_w=heat_w)
        combined_overlap_heat_w = heat_w + numeric(profile, "battery", "charging_wired_w") * (1 - 0.88) + numeric(profile, "battery", "charging_wired_w") * 0.08
        charging_overlap_risk = "high" if combined_overlap_heat_w > 35 else "moderate"
        outputs.update(
            {
                "battery_runtime_h": format_float(battery["battery_runtime_h"]),
                "thermal_risk": str(thermal["thermal_risk"]),
                "heat_density_w_cm3": format_float(float(thermal["heat_density_w_cm3"]), 3),
                "charging_overlap_risk": charging_overlap_risk,
            }
        )
    elif parameter_path in MEMORY_PARAMETERS:
        memory = memory_metrics(profile)
        outputs.update(
            {
                "memory_package_count": str(memory["memory_package_count"]),
                "memory_area_mm2": format_float(float(memory["memory_area_mm2"]), 0),
                "active_memory_power_w": format_float(float(memory["active_memory_power_w"]), 1),
                "runtime_used_gb": format_float(float(memory["runtime_used_gb"]), 1),
                "runtime_remaining_gb": format_float(float(memory["runtime_remaining_gb"]), 1),
                "runtime_pass": "pass" if memory["runtime_pass"] else "fail",
            }
        )
    elif parameter_path in BATTERY_PARAMETERS:
        battery = battery_metrics(profile)
        outputs.update(
            {
                "battery_wh": format_float(battery["battery_wh"]),
                "battery_mass_g": format_float(battery["battery_mass_g"], 1),
                "battery_volume_cm3": format_float(battery["battery_volume_cm3"], 1),
                "battery_runtime_h": format_float(battery["battery_runtime_h"]),
            }
        )
    elif parameter_path in AMBIENT_PARAMETERS:
        ambient = ambient_metrics(profile)
        outputs.update(
            {
                "estimated_skin_c": format_float(float(ambient["estimated_skin_c"]), 1),
                "skin_margin_c": format_float(float(ambient["skin_margin_c"]), 1),
                "throttle_pressure": str(ambient["throttle_pressure"]),
            }
        )
    else:
        outputs["engineering_outputs"] = "not yet mapped"
        row.warnings.append("not_mapped")

    add_common_warnings(row, outputs)
    if not row.warnings:
        row.warnings.append("none")
    row.warnings = list(dict.fromkeys(row.warnings))
    row.outputs = outputs
    return row


def select_columns(rows: list[SweepRow]) -> list[str]:
    preferred = [
        "profile_value",
        "battery_runtime_h",
        "thermal_risk",
        "zone_margin_mm",
        "volume_cm3",
        "volume_delta_cm3",
        "heat_density_w_cm3",
        "charging_overlap_risk",
        "memory_package_count",
        "memory_area_mm2",
        "active_memory_power_w",
        "runtime_used_gb",
        "runtime_remaining_gb",
        "runtime_pass",
        "battery_wh",
        "battery_mass_g",
        "battery_volume_cm3",
        "estimated_skin_c",
        "skin_margin_c",
        "throttle_pressure",
        "engineering_outputs",
    ]
    present = {key for row in rows for key in row.outputs}
    return [column for column in preferred if column in present]


def render_table(headers: list[str], rows: list[list[str]]) -> list[str]:
    widths = [len(header) for header in headers]
    for row in rows:
        widths = [max(width, len(cell)) for width, cell in zip(widths, row)]
    lines = [" | ".join(header.ljust(width) for header, width in zip(headers, widths))]
    lines.append(" | ".join("-" * width for width in widths))
    lines.extend(" | ".join(cell.ljust(width) for cell, width in zip(row, widths)) for row in rows)
    return lines


def render_report(profile: dict[str, Any], profile_path: Path, parameter_path: str, rows: list[SweepRow]) -> str:
    identity = require_mapping(profile, "identity")
    profile_label = identity.get("profile_id") or identity.get("name", "unknown")
    generated = datetime.now(UTC).isoformat(timespec="seconds")
    columns = select_columns(rows)
    headers = ["value", *columns, "warnings"]
    table_rows = [
        [str(row.value), *[row.outputs.get(column, "") for column in columns], ",".join(row.warnings)]
        for row in rows
    ]

    report_lines = [
        "Scenario Sweep",
        f"generated: {generated}",
        f"profile: {profile_label}",
        f"profile_path: {repo_relative(profile_path)}",
        f"parameter: {parameter_path}",
        "",
        *render_table(headers, table_rows),
        "",
        "Notes:",
        "- Each row mutates one parameter in an in-memory copy of the source profile.",
        "- Source YAML profiles are not edited by this sweep runner.",
        "- Results are conservative first-pass sensitivity screens, not optimization or automatic target solving.",
        "- Warning labels are engineering information for follow-up review.",
    ]
    if parameter_path not in SUPPORTED_PARAMETER_PATHS:
        report_lines.append("- Parameter is outside the documented sweep path list; basic validation only was applied.")
    return "\n".join(report_lines) + "\n"


def run_sweep(profile_path: Path, parameter_path: str, raw_values: list[str]) -> tuple[dict[str, Any], list[SweepRow]]:
    base_profile = load_profile(profile_path)
    reference_value = get_path(base_profile, parameter_path)
    rows: list[SweepRow] = []
    for raw_value in raw_values:
        mutated_profile = copy.deepcopy(base_profile)
        value = coerce_value(raw_value, reference_value)
        set_path(mutated_profile, parameter_path, value)
        rows.append(evaluate_profile(mutated_profile, parameter_path, value))
    return base_profile, rows


def main() -> int:
    args = parse_args()
    profile_path = resolve_repo_path(args.profile)
    output_path = resolve_repo_path(args.output)

    try:
        base_profile, rows = run_sweep(profile_path, args.parameter, args.values)
        report = render_report(base_profile, profile_path, args.parameter, rows)
    except (OSError, ValueError, KeyError) as exc:
        print(f"FAIL: {exc}")
        return 1

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report, encoding="utf-8")
    print(report, end="")
    print(f"Report written to: {repo_relative(output_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
