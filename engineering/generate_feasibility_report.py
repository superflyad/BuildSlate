#!/usr/bin/env python3
"""Generate a first-pass Slate Pocket v1 engineering feasibility report."""

from __future__ import annotations

import platform
import subprocess
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = REPO_ROOT / "reports" / "slate-pocket-v1-feasibility-report.txt"
REPORT_GENERATOR_VERSION = "v0.1"

WARNING_MARKERS = (
    "WARNING",
    "warning",
    "warnings:",
    "risk:",
    "over target",
    "fail",
    "FAIL",
    "exceeds",
    "blocker",
)


@dataclass(frozen=True)
class Check:
    section: str
    path: str
    args: tuple[str, ...] = ()
    required: bool = True


@dataclass
class CheckResult:
    check: Check
    status: str
    command: str
    returncode: int | None = None
    output: str = ""


REQUIRED_CHECKS = (
    Check("Validation Summary", "validation/validate_specs.py"),
    Check("Validation Summary", "validation/dimensional_constraints.py"),
    Check("Validation Summary", "validation/validate_source_registry.py"),
    Check("Validation Summary", "validation/validate_provenance.py"),
)

CORE_MODEL_CHECKS = (
    Check("Battery and Runtime", "engineering/models/battery_energy.py"),
    Check("Thermal Risk", "engineering/models/thermal_limits.py"),
    Check("Mass and Volume", "engineering/models/mass_budget.py"),
    Check(
        "Mass and Volume",
        "engineering/models/composite_chassis.py",
        ("--preset", "aluminum_heat_frame_glass_windows"),
    ),
    Check("Component Packaging", "engineering/component_models/run_all_component_models.py"),
    Check("Interconnect and Power Delivery", "engineering/interconnect_models/run_all_interconnect_models.py"),
    Check("AI Runtime Memory", "engineering/runtime_models/run_all_runtime_models.py"),
    Check("Manufacturing and Reliability", "engineering/manufacturing_models/run_all_manufacturing_models.py"),
    Check("Environmental Conditions", "engineering/environment_models/run_all_environment_models.py"),
    Check("Provenance and Assumption Confidence", "engineering/provenance/provenance_report.py"),
)

OPTIONAL_CHECKS = (
    Check("Thermal Risk", "engineering/component_models/thermal_resistance_network.py", required=False),
    Check("Local Stackup", "engineering/component_models/zone_stackup.py", required=False),
    Check("Component Packaging", "engineering/models/component_packaging.py", required=False),
    Check("AI Runtime Memory", "engineering/runtime_models/runtime_memory_budget.py", required=False),
)

CHECKS = (*REQUIRED_CHECKS, *CORE_MODEL_CHECKS, *OPTIONAL_CHECKS)

REPORT_SECTIONS = (
    "Validation Summary",
    "Mass and Volume",
    "Battery and Runtime",
    "Thermal Risk",
    "Local Stackup",
    "Component Packaging",
    "Interconnect and Power Delivery",
    "AI Runtime Memory",
    "Manufacturing and Reliability",
    "Environmental Conditions",
    "Provenance and Assumption Confidence",
)


def command_text(check: Check) -> str:
    return " ".join(("python", check.path, *check.args))


def run_check(check: Check) -> CheckResult:
    script_path = REPO_ROOT / check.path
    command = command_text(check)
    if not script_path.exists():
        if check.required:
            message = f"FAIL: required path missing for {command}"
            print(message)
            return CheckResult(check=check, status="failed", command=command, returncode=1, output=message)
        message = f"SKIP: optional path missing for {command}"
        print(message)
        return CheckResult(check=check, status="skipped", command=command, output=message)

    completed = subprocess.run(
        [sys.executable, str(script_path), *check.args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    output = "\n".join(part.rstrip() for part in (completed.stdout, completed.stderr) if part.strip())
    if completed.returncode == 0:
        print(f"PASS: {command}")
        status = "passed"
    else:
        print(f"FAIL: {command} (exit code {completed.returncode})")
        status = "failed"
    return CheckResult(
        check=check,
        status=status,
        command=command,
        returncode=completed.returncode,
        output=output,
    )


def extract_warning_lines(results: list[CheckResult]) -> list[str]:
    warnings: list[str] = []
    seen: set[str] = set()
    for result in results:
        for line in result.output.splitlines():
            if any(marker in line for marker in WARNING_MARKERS):
                entry = f"{result.check.path}: {line.strip()}"
                if entry not in seen:
                    seen.add(entry)
                    warnings.append(entry)
    return warnings


def render_result(result: CheckResult) -> str:
    lines = [f"### {result.command}"]
    if result.status == "skipped":
        lines.append(result.output)
        return "\n".join(lines)

    lines.append(f"Status: {result.status.upper()} (exit code {result.returncode})")
    if result.output.strip():
        lines.append(result.output.rstrip())
    else:
        lines.append("No output captured.")
    return "\n".join(lines)


def render_report(results: list[CheckResult]) -> str:
    generated = datetime.now(UTC).isoformat(timespec="seconds")
    warning_lines = extract_warning_lines(results)
    skipped = [result for result in results if result.status == "skipped"]
    failed = [result for result in results if result.status == "failed"]

    by_section: dict[str, list[CheckResult]] = {section: [] for section in REPORT_SECTIONS}
    for result in results:
        by_section.setdefault(result.check.section, []).append(result)

    report: list[str] = [
        "BuildSlate Engineering Feasibility Report",
        "Report Metadata:",
        f"  generated timestamp: {generated}",
        f"  Python version: {platform.python_version()}",
        f"  platform: {platform.platform()}",
        f"  repo root: {REPO_ROOT}",
        f"  report generator version: {REPORT_GENERATOR_VERSION}",
        "Scope:",
        "  device: Slate Pocket v1",
        "  purpose: first-pass engineering screening",
        "  status: not production validation",
        "Device Profile Reporting:",
        "  configurable profile reports are available alongside this general report",
        "  example: python engineering/run_device_profile.py --profile configs/devices/slate-pocket-v1.yaml",
        "",
    ]

    for section in REPORT_SECTIONS:
        report.append(section)
        section_results = by_section.get(section, [])
        if section_results:
            report.extend(render_result(result) for result in section_results)
        else:
            report.append("No checks configured for this section.")
        report.append("")

    report.append("Top Engineering Blockers")
    if failed:
        report.append("Failed checks:")
        for result in failed:
            report.append(f"- {result.command} (exit code {result.returncode})")
    if warning_lines:
        report.append("Warning/risk lines:")
        report.extend(f"- {line}" for line in warning_lines)
    if not failed and not warning_lines:
        report.append("No blocker keywords were detected in captured check output.")
    report.append("")

    report.append("Skipped Checks")
    if skipped:
        report.extend(f"- {result.output}" for result in skipped)
    else:
        report.append("No configured checks were skipped.")
    report.append("")

    report.append("Conclusion")
    if failed:
        report.append(
            "One or more feasibility checks failed. Treat this report as incomplete until failed checks are resolved."
        )
    elif warning_lines:
        report.append(
            "Required validations and core model checks completed, but warning/risk lines require engineering review before feasibility claims are strengthened."
        )
    else:
        report.append(
            "Required validations and core model checks completed without detected blocker keywords. This remains first-pass screening, not production validation."
        )

    return "\n".join(report) + "\n"


def should_exit_with_failure(results: list[CheckResult]) -> bool:
    return any(result.status == "failed" for result in results)


def main() -> int:
    results = [run_check(check) for check in CHECKS]
    report = render_report(results)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(report, encoding="utf-8")
    print(report)
    print(f"Report written to: {REPORT_PATH.relative_to(REPO_ROOT)}")
    return 1 if should_exit_with_failure(results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
