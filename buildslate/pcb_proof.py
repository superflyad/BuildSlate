"""Rebuild electrical and fabrication proof from a released KiCad PCB source."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path
from tempfile import TemporaryDirectory

from buildslate.netlist_proof import _netlist

Runner = Callable[[list[str]], subprocess.CompletedProcess[str]]


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command, capture_output=True, text=True, timeout=180, check=False
    )


def audit(
    board: Path,
    schematic: Path,
    released_netlist: Path,
    *,
    runner: Runner | None = None,
) -> dict:
    """Run KiCad on source files; require parity, zero DRC violations and fab exports.

    This proves tool reproducibility and rule compliance, not board function or
    manufacturer acceptance. A caller may inject a runner for fault fixtures.
    """
    errors: list[str] = []
    for path, suffix in (
        (board, ".kicad_pcb"),
        (schematic, ".kicad_sch"),
        (released_netlist, ".xml"),
    ):
        if not path.is_file() or path.suffix.lower() != suffix:
            errors.append(f"Missing editable or exported KiCad source: {path.name}")
    if board.stem != schematic.stem or board.parent != schematic.parent:
        errors.append("PCB and schematic must share a project name and directory")
    if errors:
        return {"status": "fail", "errors": errors, "exports": []}
    if runner is None and shutil.which("kicad-cli") is None:
        return {
            "status": "fail",
            "errors": ["kicad-cli is required to rerun board proof"],
            "exports": [],
        }
    execute = runner or _run
    with TemporaryDirectory(prefix="buildslate-pcb-proof-") as temporary:
        output = Path(temporary)
        netlist = output / "fresh.xml"
        drc = output / "drc.json"
        gerbers = output / "gerbers"
        drills = output / "drills"
        position = output / "position.csv"
        gerbers.mkdir()
        drills.mkdir()
        commands = (
            [
                "kicad-cli",
                "sch",
                "export",
                "netlist",
                "--format",
                "kicadxml",
                "--output",
                str(netlist),
                str(schematic),
            ],
            [
                "kicad-cli",
                "pcb",
                "drc",
                "--schematic-parity",
                "--severity-all",
                "--exit-code-violations",
                "--format",
                "json",
                "--output",
                str(drc),
                str(board),
            ],
            [
                "kicad-cli",
                "pcb",
                "export",
                "gerbers",
                "--layers",
                "F.Cu,B.Cu,F.Mask,B.Mask,Edge.Cuts",
                "--output",
                str(gerbers),
                str(board),
            ],
            [
                "kicad-cli",
                "pcb",
                "export",
                "drill",
                "--output",
                str(drills),
                str(board),
            ],
            [
                "kicad-cli",
                "pcb",
                "export",
                "pos",
                "--format",
                "csv",
                "--units",
                "mm",
                "--output",
                str(position),
                str(board),
            ],
        )
        for command in commands:
            try:
                result = execute(command)
            except (OSError, subprocess.TimeoutExpired) as error:
                errors.append(f"KiCad command could not run: {error}")
                break
            if result.returncode != 0:
                errors.append(
                    f"KiCad {' '.join(command[1:4])} failed ({result.returncode}): "
                    f"{(result.stderr or result.stdout).strip()[:500]}"
                )
                break
        if errors:
            return {"status": "fail", "errors": errors, "exports": []}
        try:
            source_components, source_pins = _netlist(released_netlist)
            fresh_components, fresh_pins = _netlist(netlist)
        except ValueError as error:
            errors.append(str(error))
        else:
            if source_components != fresh_components or source_pins != fresh_pins:
                errors.append("Released netlist differs from fresh schematic export")
        if not drc.is_file() or not drc.read_bytes().strip():
            errors.append("KiCad did not produce a DRC report")
        else:
            try:
                json.loads(drc.read_text(encoding="utf-8"))
            except (UnicodeError, json.JSONDecodeError):
                errors.append("KiCad DRC report is not valid JSON")
        output_files = sorted(
            (
                path
                for path in (*gerbers.iterdir(), *drills.iterdir(), position)
                if path.is_file()
            ),
            key=lambda path: str(path),
        )
        for layer in ("F_Cu", "B_Cu", "F_Mask", "B_Mask", "Edge_Cuts"):
            if not any(
                layer in path.stem
                and path.suffix.lower() == ".gbr"
                and path.stat().st_size
                for path in output_files
            ):
                errors.append(f"Missing nonempty {layer} Gerber")
        if not any(
            path.suffix.lower() == ".drl" and path.stat().st_size
            for path in output_files
        ):
            errors.append("Missing nonempty Excellon drill export")
        if not position.is_file() or not position.stat().st_size:
            errors.append("Missing nonempty assembly position CSV")
        return {
            "status": "pass" if not errors else "fail",
            "errors": errors,
            "board_sha256": _sha(board),
            "schematic_sha256": _sha(schematic),
            "netlist_sha256": _sha(released_netlist),
            "exports": [
                {"name": path.name, "sha256": _sha(path)}
                for path in output_files
                if path.stat().st_size
            ],
            "caveat": "Rule checks and exportability do not establish signal integrity, fabrication yield, assembly quality, or physical function.",
        }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("board", type=Path)
    parser.add_argument("schematic", type=Path)
    parser.add_argument("netlist", type=Path)
    args = parser.parse_args()
    report = audit(args.board, args.schematic, args.netlist)
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
