#!/usr/bin/env python3
"""Compare BuildSlate device profiles with the same first-pass engineering framework."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

try:
    import yaml
except ImportError as exc:  # pragma: no cover - dependency guidance path
    raise SystemExit("PyYAML is required. Install dependencies with: pip install -r requirements.txt") from exc

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PROFILES = (
    REPO_ROOT / "configs" / "devices" / "slate-pocket-v1.yaml",
    REPO_ROOT / "configs" / "devices" / "slate-pocket-aggressive.yaml",
    REPO_ROOT / "configs" / "devices" / "slate-pocket-conservative.yaml",
)
DEFAULT_REPORT = REPO_ROOT / "reports" / "profile-comparisons" / "comparison-report.txt"

RISK_LEVELS = ("LOW", "MODERATE", "HIGH", "EXTREME")


@dataclass(frozen=True)
class ProfileComparison:
    """Normalized engineering comparison values for one device profile."""

    path: Path
    profile_id: str
    profile_class: str
    feasibility_status: str
    review_notes: tuple[str, ...]
    thickness_mm: float
    display_diagonal_in: float
    aspirational_mass_g: float
    engineering_mass_g: float
    acceptable_mass_min_g: float
    acceptable_mass_max_g: float
    battery_capacity_mah: float
    battery_wh: float
    charging_wired_w: float
    charging_wireless_w: float
    estimated_runtime_h: float
    compute_sustained_w: float
    compute_peak_w: float
    npu_tops: float
    memory_capacity_gb: float
    memory_bandwidth_gbps: float
    memory_package_assumption: str
    storage_capacity_tb: float
    storage_active_power_w: float
    thermal_sustained_w: float
    thermal_risk: str
    model_params_billions: float
    context_tokens: float
    memory_reserve_gb: float
    memory_reserve_pressure: str
    ambient_assumption_c: float
    operating_condition: str
    brightness_mode: str
    mass_pressure: str
    stackup_pressure: str
    manufacturing_pressure: str
    environmental_sensitivity: str
    blockers: tuple[str, ...]
    warnings: tuple[str, ...]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--profiles",
        nargs="+",
        default=[str(path.relative_to(REPO_ROOT)) for path in DEFAULT_PROFILES],
        help="Device profile YAML paths to compare.",
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_REPORT.relative_to(REPO_ROOT)),
        help="Report output path. Use --no-save to print only.",
    )
    parser.add_argument("--no-save", action="store_true", help="Do not write the comparison report to disk.")
    return parser.parse_args()


def resolve_repo_path(path_text: str) -> Path:
    path = Path(path_text)
    return path if path.is_absolute() else REPO_ROOT / path


def repo_relative(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def load_profile(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as profile_file:
        data = yaml.safe_load(profile_file)
    if not isinstance(data, dict):
        raise ValueError(f"{repo_relative(path)} root must be a mapping/object")
    return data


def mapping(profile: dict[str, Any], section: str) -> dict[str, Any]:
    value = profile.get(section)
    if not isinstance(value, dict):
        raise ValueError(f"{section} must be a mapping")
    return value


def numeric(profile: dict[str, Any], section: str, field: str, default: float | None = None) -> float:
    section_data = mapping(profile, section)
    if field not in section_data:
        if default is None:
            raise ValueError(f"{section}.{field} is required")
        return default
    value = section_data[field]
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError(f"{section}.{field} must be numeric")
    return float(value)


def text(profile: dict[str, Any], section: str, field: str, default: str = "unspecified") -> str:
    section_data = mapping(profile, section)
    value = section_data.get(field, default)
    return str(value) if value not in (None, "") else default


def optional_text(profile: dict[str, Any], field: str, default: str = "unspecified") -> str:
    value = profile.get(field, default)
    return str(value) if value not in (None, "") else default


def optional_notes(profile: dict[str, Any]) -> tuple[str, ...]:
    notes = profile.get("review_notes", ())
    if notes in (None, ""):
        return ()
    if isinstance(notes, list):
        return tuple(str(note) for note in notes)
    return (str(notes),)


def level_from_score(score: int) -> str:
    return RISK_LEVELS[max(0, min(score, len(RISK_LEVELS) - 1))]


def required_model_memory_gb(params_billions: float, quantization_bits: float, context_tokens: float) -> float:
    weight_memory_gb = params_billions * quantization_bits / 8.0
    # Conservative compact KV/cache and runtime overhead allowance for first-pass comparison.
    context_memory_gb = params_billions * context_tokens / 131_072.0 * 0.16
    runtime_overhead_gb = max(8.0, weight_memory_gb * 0.15)
    return weight_memory_gb + context_memory_gb + runtime_overhead_gb


def pressure_level_for_reserve(reserve_gb: float, available_memory_gb: float) -> str:
    reserve_ratio = reserve_gb / available_memory_gb if available_memory_gb else -1.0
    if reserve_gb < 0:
        return "EXTREME"
    if reserve_ratio < 0.10:
        return "HIGH"
    if reserve_ratio < 0.25:
        return "MODERATE"
    return "LOW"


def thermal_risk(sustained_w: float, thickness_mm: float, ambient_c: float) -> str:
    score = 0
    if sustained_w > 14:
        score += 1
    if sustained_w > 24:
        score += 1
    if sustained_w > 32:
        score += 1
    if thickness_mm < 9.0:
        score += 1
    if ambient_c >= 35:
        score += 1
    return level_from_score(score)


def mass_pressure(estimate_g: float, target_g: float, max_g: float) -> str:
    if estimate_g > max_g:
        return "EXTREME"
    if estimate_g > target_g * 1.20:
        return "HIGH"
    if estimate_g > target_g * 1.08:
        return "MODERATE"
    return "LOW"


def stackup_pressure(thickness_mm: float, memory_gb: float, storage_tb: float) -> str:
    score = 0
    if thickness_mm < 9.0:
        score += 2
    elif thickness_mm < 10.0:
        score += 1
    if memory_gb >= 512:
        score += 1
    if storage_tb >= 4:
        score += 1
    return level_from_score(score)


def manufacturing_pressure(thickness_mm: float, memory_gb: float, charging_w: float, thermal_level: str) -> str:
    score = 0
    if thickness_mm < 9.0:
        score += 1
    if memory_gb >= 512:
        score += 1
    if charging_w >= 100:
        score += 1
    if thermal_level in ("HIGH", "EXTREME"):
        score += 1
    return level_from_score(score)


def environmental_sensitivity(ambient_c: float, brightness_mode: str, condition: str) -> str:
    score = 0
    if ambient_c >= 30:
        score += 1
    if ambient_c >= 35:
        score += 1
    if brightness_mode in {"sunlight", "high_brightness"}:
        score += 1
    if condition not in {"open_air", "nominal"}:
        score += 1
    return level_from_score(score)


def collect_warnings_and_blockers(
    *,
    thermal_level: str,
    mass_level: str,
    stackup_level: str,
    runtime_level: str,
    manufacturing_level: str,
    environmental_level: str,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    categories = {
        "thermal risk": thermal_level,
        "mass pressure": mass_level,
        "stackup pressure": stackup_level,
        "runtime memory pressure": runtime_level,
        "manufacturing pressure": manufacturing_level,
        "environmental sensitivity": environmental_level,
    }
    blockers = tuple(name for name, level in categories.items() if level == "EXTREME")
    warnings = tuple(f"{name}: {level}" for name, level in categories.items() if level in {"HIGH", "EXTREME"})
    return blockers, warnings


def normalize_profile(path: Path) -> ProfileComparison:
    profile = load_profile(path)
    identity = mapping(profile, "identity")
    profile_id = str(identity.get("profile_id") or path.stem)

    thickness_mm = numeric(profile, "geometry", "thickness_mm")
    display_diagonal_in = numeric(profile, "display", "diagonal_in", numeric(profile, "geometry", "display_diagonal_in", 0.0))
    target_mass_g = numeric(profile, "mass_targets", "aspirational_target_g")
    estimate_mass_g = numeric(profile, "mass_targets", "engineering_estimate_g")
    acceptable_range = mapping(mapping(profile, "mass_targets"), "acceptable_range_g")
    acceptable_min = float(acceptable_range["min"])
    acceptable_max = float(acceptable_range["max"])
    battery_capacity_mah = numeric(profile, "battery", "capacity_mah")
    battery_wh = battery_capacity_mah / 1000.0 * numeric(profile, "battery", "nominal_voltage_v")
    compute_sustained_w = numeric(profile, "compute", "sustained_power_w")
    thermal_sustained_w = numeric(profile, "thermal", "sustained_w")
    ambient_c = numeric(profile, "thermal", "ambient_c", 25.0)
    memory_capacity_gb = numeric(profile, "memory", "capacity_gb")
    storage_capacity_tb = numeric(profile, "storage", "capacity_tb")
    model_params_billions = numeric(profile, "runtime", "model_params_billions")
    quantization_bits = numeric(profile, "runtime", "quantization_bits")
    context_tokens = numeric(profile, "runtime", "context_tokens")
    available_memory_gb = numeric(profile, "runtime", "available_memory_gb", memory_capacity_gb)
    required_memory_gb = required_model_memory_gb(model_params_billions, quantization_bits, context_tokens)
    memory_reserve_gb = available_memory_gb - required_memory_gb
    runtime_pressure = pressure_level_for_reserve(memory_reserve_gb, available_memory_gb)
    brightness_mode = text(profile, "environment", "brightness_mode", "normal")
    condition = text(profile, "environment", "condition", "open_air")
    thermal_level = thermal_risk(thermal_sustained_w, thickness_mm, ambient_c)
    mass_level = mass_pressure(estimate_mass_g, target_mass_g, acceptable_max)
    stackup_level = stackup_pressure(thickness_mm, memory_capacity_gb, storage_capacity_tb)
    manufacturing_level = manufacturing_pressure(
        thickness_mm,
        memory_capacity_gb,
        numeric(profile, "battery", "charging_wired_w"),
        thermal_level,
    )
    environmental_level = environmental_sensitivity(ambient_c, brightness_mode, condition)
    blockers, warnings = collect_warnings_and_blockers(
        thermal_level=thermal_level,
        mass_level=mass_level,
        stackup_level=stackup_level,
        runtime_level=runtime_pressure,
        manufacturing_level=manufacturing_level,
        environmental_level=environmental_level,
    )

    return ProfileComparison(
        path=path,
        profile_id=profile_id,
        profile_class=optional_text(profile, "profile_class", str(identity.get("label", "unspecified"))),
        feasibility_status=optional_text(profile, "feasibility_status", "conceptual"),
        review_notes=optional_notes(profile),
        thickness_mm=thickness_mm,
        display_diagonal_in=display_diagonal_in,
        aspirational_mass_g=target_mass_g,
        engineering_mass_g=estimate_mass_g,
        acceptable_mass_min_g=acceptable_min,
        acceptable_mass_max_g=acceptable_max,
        battery_capacity_mah=battery_capacity_mah,
        battery_wh=battery_wh,
        charging_wired_w=numeric(profile, "battery", "charging_wired_w"),
        charging_wireless_w=numeric(profile, "battery", "charging_wireless_w", 0.0),
        estimated_runtime_h=battery_wh / compute_sustained_w if compute_sustained_w else 0.0,
        compute_sustained_w=compute_sustained_w,
        compute_peak_w=numeric(profile, "compute", "peak_power_w"),
        npu_tops=numeric(profile, "compute", "npu_tops"),
        memory_capacity_gb=memory_capacity_gb,
        memory_bandwidth_gbps=numeric(profile, "memory", "bandwidth_gbps", 0.0),
        memory_package_assumption=f"{numeric(profile, 'memory', 'gb_per_package', 0.0):.0f}GB/pkg; {text(profile, 'interconnect', 'memory_topology')}",
        storage_capacity_tb=storage_capacity_tb,
        storage_active_power_w=numeric(profile, "storage", "active_power_w"),
        thermal_sustained_w=thermal_sustained_w,
        thermal_risk=thermal_level,
        model_params_billions=model_params_billions,
        context_tokens=context_tokens,
        memory_reserve_gb=memory_reserve_gb,
        memory_reserve_pressure=runtime_pressure,
        ambient_assumption_c=ambient_c,
        operating_condition=condition,
        brightness_mode=brightness_mode,
        mass_pressure=mass_level,
        stackup_pressure=stackup_level,
        manufacturing_pressure=manufacturing_level,
        environmental_sensitivity=environmental_level,
        blockers=blockers,
        warnings=warnings,
    )


def load_comparison(profile_paths: Iterable[str | Path]) -> list[ProfileComparison]:
    return [normalize_profile(resolve_repo_path(str(path))) for path in profile_paths]


def fmt_number(value: float, suffix: str = "", decimals: int = 0) -> str:
    if decimals == 0:
        rendered = f"{value:.0f}"
    else:
        rendered = f"{value:.{decimals}f}"
    return f"{rendered}{suffix}"


def table(title: str, headers: list[str], rows: list[list[str]]) -> str:
    widths = [len(header) for header in headers]
    for row in rows:
        widths = [max(width, len(cell)) for width, cell in zip(widths, row, strict=True)]
    divider = "  ".join("-" * width for width in widths)
    header_line = "  ".join(header.ljust(width) for header, width in zip(headers, widths, strict=True))
    row_lines = ["  ".join(cell.ljust(width) for cell, width in zip(row, widths, strict=True)) for row in rows]
    return "\n".join([title, divider, header_line, divider, *row_lines])


def build_report(comparisons: list[ProfileComparison]) -> str:
    sections = [
        table(
            "Profile Comparison",
            ["profile", "class", "thickness", "est_mass", "sustained_w", "memory"],
            [
                [
                    item.profile_id,
                    item.profile_class,
                    fmt_number(item.thickness_mm, "mm", 1),
                    fmt_number(item.engineering_mass_g, "g"),
                    fmt_number(item.thermal_sustained_w, "W"),
                    fmt_number(item.memory_capacity_gb, "GB"),
                ]
                for item in comparisons
            ],
        ),
        table(
            "Geometry and Mass",
            ["profile", "thickness", "display", "target", "estimate", "acceptable"],
            [
                [
                    item.profile_id,
                    fmt_number(item.thickness_mm, "mm", 1),
                    fmt_number(item.display_diagonal_in, "in", 1),
                    fmt_number(item.aspirational_mass_g, "g"),
                    fmt_number(item.engineering_mass_g, "g"),
                    f"{fmt_number(item.acceptable_mass_min_g, 'g')}-{fmt_number(item.acceptable_mass_max_g, 'g')}",
                ]
                for item in comparisons
            ],
        ),
        table(
            "Battery and Compute",
            ["profile", "capacity", "charge", "runtime", "sustained", "peak", "NPU"],
            [
                [
                    item.profile_id,
                    f"{fmt_number(item.battery_capacity_mah, 'mAh')} / {fmt_number(item.battery_wh, 'Wh', 1)}",
                    f"{fmt_number(item.charging_wired_w, 'W')} wired / {fmt_number(item.charging_wireless_w, 'W')} wireless",
                    fmt_number(item.estimated_runtime_h, "h", 2),
                    fmt_number(item.compute_sustained_w, "W"),
                    fmt_number(item.compute_peak_w, "W"),
                    fmt_number(item.npu_tops, " TOPS"),
                ]
                for item in comparisons
            ],
        ),
        table(
            "Memory, Storage, and Runtime",
            ["profile", "memory", "bandwidth", "package", "storage", "storage_power", "model/context", "reserve"],
            [
                [
                    item.profile_id,
                    fmt_number(item.memory_capacity_gb, "GB"),
                    fmt_number(item.memory_bandwidth_gbps, "Gbps"),
                    item.memory_package_assumption,
                    fmt_number(item.storage_capacity_tb, "TB"),
                    fmt_number(item.storage_active_power_w, "W"),
                    f"{fmt_number(item.model_params_billions, 'B')}/{fmt_number(item.context_tokens, ' tok')}",
                    f"{fmt_number(item.memory_reserve_gb, 'GB', 1)} ({item.memory_reserve_pressure})",
                ]
                for item in comparisons
            ],
        ),
        table(
            "Thermal and Environment",
            ["profile", "sustained", "thermal_risk", "ambient", "condition", "brightness", "environment"],
            [
                [
                    item.profile_id,
                    fmt_number(item.thermal_sustained_w, "W"),
                    item.thermal_risk,
                    fmt_number(item.ambient_assumption_c, "C"),
                    item.operating_condition,
                    item.brightness_mode,
                    item.environmental_sensitivity,
                ]
                for item in comparisons
            ],
        ),
        table(
            "Engineering Pressure Matrix",
            ["profile", "thermal", "mass", "stackup", "runtime", "manufacturing", "environment", "blockers"],
            [
                [
                    item.profile_id,
                    item.thermal_risk,
                    item.mass_pressure,
                    item.stackup_pressure,
                    item.memory_reserve_pressure,
                    item.manufacturing_pressure,
                    item.environmental_sensitivity,
                    ", ".join(item.blockers) if item.blockers else "none",
                ]
                for item in comparisons
            ],
        ),
    ]
    notes = ["", "Notes", "-----", "Comparison is exploratory: no profile is selected as best and no auto-solving is performed."]
    for item in comparisons:
        if item.review_notes:
            notes.append(f"{item.profile_id}: " + " | ".join(item.review_notes))
    return "\n\n".join(sections + ["\n".join(notes)])


def main() -> int:
    args = parse_args()
    comparisons = load_comparison(args.profiles)
    report = build_report(comparisons)
    print(report)
    if not args.no_save:
        output_path = resolve_repo_path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(report + "\n", encoding="utf-8")
        print(f"\nSaved comparison report: {repo_relative(output_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
