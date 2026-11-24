"""Reproduce KiCad schematic ERC from an editable released source."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path, PureWindowsPath
from tempfile import TemporaryDirectory

Runner = Callable[[list[str]], subprocess.CompletedProcess[str]]
CRITICAL_RULES = (
    "duplicate_reference",
    "missing_power_pin",
    "pin_not_connected",
    "pin_not_driven",
    "pin_to_pin",
    "power_pin_not_driven",
    "unannotated",
    "unconnected_wire_endpoint",
    "unresolved_variable",
    "wire_dangling",
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command, capture_output=True, text=True, timeout=180, check=False
    )


def _report(path: Path, schematic: Path) -> tuple[dict, list[str]]:
    errors: list[str] = []
    if not path.is_file() or not path.stat().st_size:
        return {}, [f"Missing or empty KiCad ERC JSON: {path.name}"]
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        return {}, [f"Invalid KiCad ERC JSON: {error}"]
    if not isinstance(report, dict):
        return {}, ["KiCad ERC report must be an object"]
    source = report.get("source")
    if not isinstance(source, str) or (
        Path(source).name != schematic.name
        and PureWindowsPath(source).name != schematic.name
    ):
        errors.append("ERC report source is not the released schematic")
    if report.get("$schema") != "https://schemas.kicad.org/erc.v1.json":
        errors.append("ERC report has an unknown KiCad schema")
    for field in ("date", "kicad_version"):
        if not isinstance(report.get(field), str) or not report[field].strip():
            errors.append(f"ERC report is missing {field}")
    if report.get("coordinate_units") != "mm":
        errors.append("ERC report must use millimeters")
    sheets = report.get("sheets")
    if not isinstance(sheets, list) or not sheets:
        errors.append("ERC report has no schematic sheets")
        sheets = []
    seen: set[str] = set()
    for sheet in sheets:
        if not isinstance(sheet, dict):
            errors.append("ERC sheet record is malformed")
            continue
        uuid_path = sheet.get("uuid_path")
        if not isinstance(uuid_path, str) or not uuid_path or uuid_path in seen:
            errors.append("ERC sheet identity is missing or duplicated")
        else:
            seen.add(uuid_path)
        if not isinstance(sheet.get("path"), str) or not sheet["path"]:
            errors.append("ERC sheet path is missing")
        violations = sheet.get("violations")
        if not isinstance(violations, list):
            errors.append("ERC sheet violations are malformed")
        elif violations:
            errors.append(
                f"ERC sheet {sheet.get('path')} has {len(violations)} findings"
            )
    return report, errors


def _comparable(report: dict) -> dict:
    return {
        "kicad_version": report.get("kicad_version"),
        "coordinate_units": report.get("coordinate_units"),
        "sheets": report.get("sheets"),
    }


def _project_settings(project: Path) -> list[str]:
    if not project.is_file() or not project.stat().st_size:
        return ["Missing KiCad project settings"]
    try:
        source = json.loads(project.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        return [f"Invalid KiCad project settings: {error}"]
    if not isinstance(source, dict) or not isinstance(source.get("erc"), dict):
        return ["KiCad project has no ERC settings"]
    erc = source["erc"]
    errors = []
    if erc.get("erc_exclusions") != []:
        errors.append("KiCad project contains ERC exclusions")
    severities = erc.get("rule_severities")
    if not isinstance(severities, dict) or any(
        severities.get(rule) not in ("error", "warning") for rule in CRITICAL_RULES
    ):
        errors.append("Critical ERC rules are missing or ignored")
    return errors


def audit(
    schematic: Path,
    released_report: Path,
    *,
    runner: Runner | None = None,
) -> dict:
    """Require zero KiCad ERC findings and a matching reviewed JSON report."""
    errors: list[str] = []
    if not schematic.is_file() or schematic.suffix.lower() != ".kicad_sch":
        errors.append("Missing editable KiCad schematic")
    if not released_report.is_file() or released_report != schematic.with_suffix(
        ".erc.json"
    ):
        errors.append("Released ERC JSON must share the schematic basename")
    if errors:
        return {"status": "fail", "errors": errors}
    project = schematic.with_suffix(".kicad_pro")
    errors.extend(_project_settings(project))
    if errors:
        return {"status": "fail", "errors": errors}
    if runner is None and shutil.which("kicad-cli") is None:
        return {"status": "fail", "errors": ["kicad-cli is required to rerun ERC"]}
    released, released_errors = _report(released_report, schematic)
    errors.extend(released_errors)
    execute = runner or _run
    with TemporaryDirectory(prefix="buildslate-erc-proof-") as temporary:
        fresh_path = Path(temporary) / "fresh.erc.json"
        command = [
            "kicad-cli",
            "sch",
            "erc",
            "--format",
            "json",
            "--severity-all",
            "--exit-code-violations",
            "--units",
            "mm",
            "--output",
            str(fresh_path),
            str(schematic),
        ]
        try:
            result = execute(command)
        except (OSError, subprocess.TimeoutExpired) as error:
            return {"status": "fail", "errors": [f"KiCad ERC could not run: {error}"]}
        if result.returncode != 0:
            errors.append(
                f"KiCad ERC failed ({result.returncode}): "
                f"{(result.stderr or result.stdout).strip()[:500]}"
            )
        fresh, fresh_errors = _report(fresh_path, schematic)
        errors.extend(fresh_errors)
        if (
            not released_errors
            and not fresh_errors
            and _comparable(released) != _comparable(fresh)
        ):
            errors.append("Released ERC report differs from fresh schematic check")
    return {
        "status": "pass" if not errors else "fail",
        "errors": errors,
        "schematic_sha256": _sha(schematic),
        "project_sha256": _sha(project),
        "released_report_sha256": _sha(released_report),
        "kicad_version": fresh.get("kicad_version"),
        "sheets_checked": len(fresh.get("sheets", []))
        if isinstance(fresh.get("sheets"), list)
        else 0,
        "caveat": "ERC checks configured schematic rules, not circuit function, electrical margins, or physical safety.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("schematic", type=Path)
    parser.add_argument("report", type=Path)
    args = parser.parse_args()
    proof = audit(args.schematic, args.report)
    print(json.dumps(proof, indent=2))
    return 0 if proof["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
