#!/usr/bin/env python3
"""Run BuildSlate engineering models against a configurable device profile."""

from __future__ import annotations

import argparse
import platform
import subprocess
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError as exc:  # pragma: no cover - dependency guidance path
    raise SystemExit("PyYAML is required. Install dependencies with: pip install -r requirements.txt") from exc

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROFILE = REPO_ROOT / "configs" / "devices" / "slate-pocket-v1.yaml"
DEFAULT_OUTPUT = REPO_ROOT / "reports" / "device-profile-slate-pocket-v1.txt"

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

WARNING_MARKERS = (
    "WARNING",
    "warning",
    "warnings:",
    "risk:",
    "over target",
    "FAIL",
    "fail",
    "exceeds",
    "blocker",
    "high risk",
)

SUMMARY_SECTIONS = (
    "geometry",
    "mass_targets",
    "battery",
    "compute",
    "memory",
    "storage",
    "thermal",
    "environment",
)

REPORT_SECTIONS = (
    "validation",
    "battery",
    "mass",
    "thermal",
    "chassis composite",
    "component models",
    "interconnect",
    "runtime memory",
    "environment",
)


@dataclass(frozen=True)
class ModelCommand:
    section: str
    title: str
    path: str
    args: tuple[str, ...] = ()


@dataclass
class ModelResult:
    command: ModelCommand
    status: str
    command_text: str
    returncode: int
    output: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", default=str(DEFAULT_PROFILE.relative_to(REPO_ROOT)), help="Device profile YAML path")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT.relative_to(REPO_ROOT)), help="Report output path")
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


def require_path(profile: dict[str, Any], section_name: str, field_name: str) -> Any:
    section = require_mapping(profile, section_name)
    if field_name not in section or section[field_name] in (None, ""):
        raise ValueError(f"{section_name}.{field_name} is required")
    return section[field_name]


def validate_required_sections(profile: dict[str, Any]) -> None:
    missing = [section for section in REQUIRED_TOP_LEVEL_SECTIONS if section not in profile]
    if missing:
        raise ValueError(f"missing required top-level sections: {', '.join(missing)}")
    for section in REQUIRED_TOP_LEVEL_SECTIONS:
        if section != "notes":
            require_mapping(profile, section)


def value(profile: dict[str, Any], section_name: str, field_name: str) -> str:
    return str(require_path(profile, section_name, field_name))


def build_model_commands(profile: dict[str, Any]) -> list[ModelCommand]:
    battery_wh = float(require_path(profile, "battery", "capacity_mah")) / 1000.0 * float(
        require_path(profile, "battery", "nominal_voltage_v")
    )

    return [
        ModelCommand("validation", "Spec validation", "validation/validate_specs.py"),
        ModelCommand("validation", "Source registry validation", "validation/validate_source_registry.py"),
        ModelCommand("validation", "Provenance validation", "validation/validate_provenance.py"),
        ModelCommand(
            "battery",
            "Battery energy model",
            "engineering/models/battery_energy.py",
            (
                "--capacity-mah",
                value(profile, "battery", "capacity_mah"),
                "--nominal-voltage-v",
                value(profile, "battery", "nominal_voltage_v"),
                "--workload-w",
                value(profile, "compute", "sustained_power_w"),
            ),
        ),
        ModelCommand(
            "thermal",
            "Thermal limits model",
            "engineering/models/thermal_limits.py",
            (
                "--length-mm",
                value(profile, "geometry", "length_mm"),
                "--width-mm",
                value(profile, "geometry", "width_mm"),
                "--thickness-mm",
                value(profile, "geometry", "thickness_mm"),
                "--sustained-w",
                value(profile, "thermal", "sustained_w"),
            ),
        ),
        ModelCommand(
            "mass",
            "Mass budget model",
            "engineering/models/mass_budget.py",
            (
                "--target-mass-g",
                value(profile, "mass_targets", "aspirational_target_g"),
                "--battery-wh",
                f"{battery_wh:.3f}",
            ),
        ),
        ModelCommand(
            "chassis composite",
            "Composite chassis model",
            "engineering/models/composite_chassis.py",
            ("--preset", value(profile, "chassis_composite", "preset")),
        ),
        ModelCommand(
            "component models",
            "Battery pack component model",
            "engineering/component_models/battery_pack.py",
            (
                "--capacity-mah",
                value(profile, "battery", "capacity_mah"),
                "--nominal-voltage-v",
                value(profile, "battery", "nominal_voltage_v"),
                "--workload-w",
                value(profile, "compute", "sustained_power_w"),
                "--charging-w",
                value(profile, "battery", "charging_wired_w"),
            ),
        ),
        ModelCommand(
            "component models",
            "Display module component model",
            "engineering/component_models/display_module.py",
            (
                "--diagonal-in",
                value(profile, "display", "diagonal_in"),
                "--aspect-width",
                value(profile, "display", "aspect_width"),
                "--aspect-height",
                value(profile, "display", "aspect_height"),
                "--device-length-mm",
                value(profile, "geometry", "length_mm"),
                "--device-width-mm",
                value(profile, "geometry", "width_mm"),
                "--power-w",
                value(profile, "display", "display_power_w"),
            ),
        ),
        ModelCommand(
            "component models",
            "SoC package component model",
            "engineering/component_models/soc_package.py",
            (
                "--sustained-power-w",
                value(profile, "compute", "sustained_power_w"),
                "--peak-power-w",
                value(profile, "compute", "peak_power_w"),
                "--npu-tops",
                value(profile, "compute", "npu_tops"),
            ),
        ),
        ModelCommand(
            "component models",
            "Memory package component model",
            "engineering/component_models/memory_package.py",
            (
                "--capacity-gb",
                value(profile, "memory", "capacity_gb"),
                "--gb-per-package",
                value(profile, "memory", "gb_per_package"),
            ),
        ),
        ModelCommand(
            "component models",
            "Storage package component model",
            "engineering/component_models/storage_package.py",
            (
                "--capacity-tb",
                value(profile, "storage", "capacity_tb"),
                "--tb-per-package",
                value(profile, "storage", "tb_per_package"),
                "--active-power-w",
                value(profile, "storage", "active_power_w"),
            ),
        ),
        ModelCommand(
            "component models",
            "Thermal resistance network component model",
            "engineering/component_models/thermal_resistance_network.py",
            (
                "--heat-w",
                value(profile, "thermal", "sustained_w"),
                "--ambient-c",
                value(profile, "thermal", "ambient_c"),
                "--max-skin-c",
                value(profile, "thermal", "max_skin_c"),
            ),
        ),
        ModelCommand(
            "component models",
            "Zone stackup component model",
            "engineering/component_models/zone_stackup.py",
            ("--target-thickness-mm", value(profile, "geometry", "thickness_mm")),
        ),
        ModelCommand(
            "interconnect",
            "Memory bandwidth interconnect model",
            "engineering/interconnect_models/memory_bandwidth.py",
            (
                "--memory-capacity-gb",
                value(profile, "memory", "capacity_gb"),
                "--memory-bandwidth-gbps",
                value(profile, "memory", "bandwidth_gbps"),
                "--model-params-b",
                value(profile, "runtime", "model_params_billions"),
                "--quantization-bits",
                value(profile, "runtime", "quantization_bits"),
            ),
        ),
        ModelCommand(
            "runtime memory",
            "Runtime memory budget model",
            "engineering/runtime_models/runtime_memory_budget.py",
            (
                "--available-memory-gb",
                value(profile, "runtime", "available_memory_gb"),
                "--params-billions",
                value(profile, "runtime", "model_params_billions"),
                "--quantization-bits",
                value(profile, "runtime", "quantization_bits"),
                "--context-tokens",
                value(profile, "runtime", "context_tokens"),
            ),
        ),
        ModelCommand(
            "environment",
            "Ambient temperature environment model",
            "engineering/environment_models/ambient_temperature.py",
            (
                "--ambient-c",
                value(profile, "thermal", "ambient_c"),
                "--max-skin-c",
                value(profile, "thermal", "max_skin_c"),
            ),
        ),
        ModelCommand(
            "environment",
            "Enclosure condition environment model",
            "engineering/environment_models/enclosure_condition.py",
            (
                "--condition",
                value(profile, "environment", "condition"),
                "--sustained-w",
                value(profile, "thermal", "sustained_w"),
                "--ambient-c",
                value(profile, "thermal", "ambient_c"),
            ),
        ),
        ModelCommand(
            "environment",
            "Sunlight display-load environment model",
            "engineering/environment_models/sunlight_display_load.py",
            (
                "--base-display-w",
                value(profile, "display", "display_power_w"),
                "--brightness-mode",
                value(profile, "environment", "brightness_mode"),
            ),
        ),
    ]


def command_text(command: ModelCommand) -> str:
    return " ".join(("python", command.path, *command.args))


def run_model_command(command: ModelCommand) -> ModelResult:
    script_path = REPO_ROOT / command.path
    text = command_text(command)
    if not script_path.exists():
        output = f"FAIL: required path missing for {text}"
        print(output)
        return ModelResult(command=command, status="failed", command_text=text, returncode=1, output=output)

    completed = subprocess.run(
        [sys.executable, str(script_path), *command.args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    output = "\n".join(part.rstrip() for part in (completed.stdout, completed.stderr) if part.strip())
    status = "passed" if completed.returncode == 0 else "failed"
    print(f"{status.upper()}: {text}")
    return ModelResult(command=command, status=status, command_text=text, returncode=completed.returncode, output=output)


def render_scalar_mapping(mapping: dict[str, Any], indent: str = "  ") -> list[str]:
    rows: list[str] = []
    for key, value_item in mapping.items():
        if isinstance(value_item, dict):
            rows.append(f"{indent}{key}:")
            rows.extend(render_scalar_mapping(value_item, indent + "  "))
        elif isinstance(value_item, list):
            rows.append(f"{indent}{key}: {', '.join(str(item) for item in value_item)}")
        else:
            rows.append(f"{indent}{key}: {value_item}")
    return rows


def extract_warning_lines(results: list[ModelResult]) -> list[str]:
    warning_lines: list[str] = []
    seen: set[str] = set()
    for result in results:
        for line in result.output.splitlines():
            if any(marker in line for marker in WARNING_MARKERS):
                entry = f"{result.command.path}: {line.strip()}"
                if entry not in seen:
                    seen.add(entry)
                    warning_lines.append(entry)
    return warning_lines


def render_result(result: ModelResult) -> str:
    lines = [f"### {result.command.title}", f"Command: {result.command_text}", f"Status: {result.status.upper()} (exit code {result.returncode})"]
    lines.append(result.output.rstrip() if result.output.strip() else "No output captured.")
    return "\n".join(lines)


def render_report(profile: dict[str, Any], profile_path: Path, results: list[ModelResult]) -> str:
    generated = datetime.now(UTC).isoformat(timespec="seconds")
    identity = require_mapping(profile, "identity")
    by_section: dict[str, list[ModelResult]] = {section: [] for section in REPORT_SECTIONS}
    for result in results:
        by_section.setdefault(result.command.section, []).append(result)

    warning_lines = extract_warning_lines(results)
    failed = [result for result in results if result.status == "failed"]

    report: list[str] = [
        "BuildSlate Device Profile Report",
        "Report Metadata:",
        f"  generated timestamp: {generated}",
        f"  Python version: {platform.python_version()}",
        f"  platform: {platform.platform()}",
        f"  repo root: {REPO_ROOT}",
        "Profile Identity:",
        f"  name: {identity.get('name', 'unknown')}",
        f"  profile_id: {identity.get('profile_id', 'unknown')}",
        f"  source_spec: {identity.get('source_spec', 'not specified')}",
        f"  intent: {identity.get('intent', 'not specified')}",
        f"  label: {identity.get('label', 'not specified')}",
        f"Profile source file: {repo_relative(profile_path)}",
        "",
        "Profile Summary:",
    ]

    for section_name in SUMMARY_SECTIONS:
        report.append(f"- {section_name}:")
        report.extend(render_scalar_mapping(require_mapping(profile, section_name), indent="    "))
    report.append("")

    report.append("Model Results:")
    for section_name in REPORT_SECTIONS:
        report.append(section_name)
        section_results = by_section.get(section_name, [])
        if section_results:
            report.extend(render_result(result) for result in section_results)
        else:
            report.append("No commands configured for this section.")
        report.append("")

    report.append("Warnings and Blockers:")
    if failed:
        report.append("Failed commands:")
        report.extend(f"- {result.command_text} (exit code {result.returncode})" for result in failed)
    if warning_lines:
        report.append("Warning/risk lines:")
        report.extend(f"- {line}" for line in warning_lines)
    if not failed and not warning_lines:
        report.append("No warning or blocker keywords were detected in captured model output.")
    report.append("")

    report.append("Conclusion:")
    report.append("- This profile report is a screening evaluation, not production validation.")
    report.append("- No optimization or automatic target adjustment was performed.")
    report.append("- Failures and warnings are engineering information, not defects in the profile system.")
    report.append("- Manufacturability, safety, certification, and supplier feasibility remain unproven until validated with detailed design data and prototypes.")

    return "\n".join(report) + "\n"


def main() -> int:
    args = parse_args()
    profile_path = resolve_repo_path(args.profile)
    output_path = resolve_repo_path(args.output)

    try:
        profile = load_profile(profile_path)
        validate_required_sections(profile)
        commands = build_model_commands(profile)
    except (OSError, ValueError) as exc:
        print(f"FAIL: {exc}")
        return 1

    results = [run_model_command(command) for command in commands]
    report = render_report(profile, profile_path, results)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report, encoding="utf-8")
    print(f"Report written to: {repo_relative(output_path)}")
    return 1 if any(result.status == "failed" for result in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
