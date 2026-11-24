"""Exercise live PCB proof and release binding with synthetic KiCad output."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from buildslate.hardware_readiness import _evidence_result  # noqa: E402
from buildslate.pcb_proof import CRITICAL_RULES, POSITIVE_RULES, audit  # noqa: E402
from validation.validate_netlist_proof import _write_fixture  # noqa: E402


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    with TemporaryDirectory() as temporary:
        root = Path(temporary)
        released = root / "engineering/hardware/released"
        released.mkdir(parents=True)
        netlist, _, _, _ = _write_fixture(released)
        board = released / "board.kicad_pcb"
        schematic = released / "board.kicad_sch"
        project = released / "board.kicad_pro"
        copper = ["F.Cu", *(f"In{index}.Cu" for index in range(1, 11)), "B.Cu"]
        layers = [*copper, "F.Mask", "B.Mask", "Edge.Cuts"]
        board_source = (
            "(kicad_pcb\n  (layers\n"
            + "".join(
                f'    ({number} "{name}" {"signal" if name.endswith(".Cu") else "user"})\n'
                for number, name in enumerate(layers)
            )
            + "  )\n)\n"
        )
        board.write_text(board_source, encoding="utf-8")
        schematic.write_text("synthetic schematic source", encoding="utf-8")
        project_settings = {
            "board": {
                "design_settings": {
                    "drc_exclusions": [],
                    "rule_severities": {rule: "error" for rule in CRITICAL_RULES},
                    "rules": {rule: 0.1 for rule in POSITIVE_RULES},
                }
            }
        }
        project.write_text(json.dumps(project_settings), encoding="utf-8")
        fault = {
            "drc": False,
            "drc_json": False,
            "drc_unconnected": False,
            "drc_parity": False,
            "netlist": False,
            "gerber": False,
            "inner_gerber": False,
        }

        def runner(command: list[str]) -> subprocess.CompletedProcess[str]:
            if command[1:4] == ["sch", "export", "netlist"]:
                destination = Path(command[command.index("--output") + 1])
                if fault["netlist"]:
                    destination.write_text("<export/>", encoding="utf-8")
                else:
                    shutil.copyfile(netlist, destination)
            elif command[1:3] == ["pcb", "drc"]:
                destination = Path(command[command.index("--output") + 1])
                if (
                    not {
                        "--schematic-parity",
                        "--severity-all",
                        "--exit-code-violations",
                        "--all-track-errors",
                        "--units",
                    }.issubset(command)
                    or command[command.index("--units") + 1] != "mm"
                ):
                    raise AssertionError("DRC command omitted required scope")
                destination.write_text(
                    json.dumps(
                        {
                            "$schema": "https://schemas.kicad.org/drc.v1.json",
                            "source": board.name,
                            "date": "2026-11-24T00:00:00Z",
                            "kicad_version": "9.0.1",
                            "coordinate_units": "mm",
                            "violations": [{"type": "shorting_items"}]
                            if fault["drc_json"]
                            else [],
                            "unconnected_items": [{"type": "unconnected_items"}]
                            if fault["drc_unconnected"]
                            else [],
                            "schematic_parity": [{"type": "footprint_symbol_mismatch"}]
                            if fault["drc_parity"]
                            else [],
                        }
                    ),
                    encoding="utf-8",
                )
                if fault["drc"]:
                    return subprocess.CompletedProcess(command, 5, "", "DRC violation")
            elif command[1:4] == ["pcb", "export", "gerbers"]:
                directory = Path(command[command.index("--output") + 1])
                selected = command[command.index("--layers") + 1].split(",")
                if selected != layers or "--no-protel-ext" not in command:
                    raise AssertionError(
                        "Gerber export omitted a configured board layer"
                    )
                for layer in selected:
                    if (fault["gerber"] and layer == "Edge.Cuts") or (
                        fault["inner_gerber"] and layer == "In5.Cu"
                    ):
                        continue
                    (directory / f"board-{layer.replace('.', '_')}.gbr").write_text(
                        "G04 fixture*", encoding="utf-8"
                    )
            elif command[1:4] == ["pcb", "export", "drill"]:
                directory = Path(command[command.index("--output") + 1])
                (directory / "board.drl").write_text("M48", encoding="utf-8")
            elif command[1:4] == ["pcb", "export", "pos"]:
                destination = Path(command[command.index("--output") + 1])
                destination.write_text("Ref,PosX,PosY\nU1,1,1\n", encoding="utf-8")
            else:
                raise AssertionError(f"Unexpected KiCad invocation: {command}")
            return subprocess.CompletedProcess(command, 0, "", "")

        proof = audit(board, schematic, netlist, runner=runner)
        if (
            proof["status"] != "pass"
            or proof["copper_layer_count"] != 12
            or proof["required_gerber_layers"] != layers
            or len(proof["exports"]) != 17
        ):
            raise ValueError("Complete synthetic KiCad command sequence failed")
        for key in fault:
            fault[key] = True
            if audit(board, schematic, netlist, runner=runner)["status"] != "fail":
                raise ValueError(f"{key} fault passed PCB proof")
            fault[key] = False
        project_settings["board"]["design_settings"]["drc_exclusions"] = [
            "synthetic ignored violation"
        ]
        project.write_text(json.dumps(project_settings), encoding="utf-8")
        if audit(board, schematic, netlist, runner=runner)["status"] != "fail":
            raise ValueError("DRC exclusion passed project-settings proof")
        project_settings["board"]["design_settings"]["drc_exclusions"] = []
        project_settings["board"]["design_settings"]["rule_severities"]["clearance"] = (
            "ignore"
        )
        project.write_text(json.dumps(project_settings), encoding="utf-8")
        if audit(board, schematic, netlist, runner=runner)["status"] != "fail":
            raise ValueError("Ignored critical DRC rule passed")
        project_settings["board"]["design_settings"]["rule_severities"]["clearance"] = (
            "error"
        )
        project_settings["board"]["design_settings"]["rules"]["min_clearance"] = 0
        project.write_text(json.dumps(project_settings), encoding="utf-8")
        if audit(board, schematic, netlist, runner=runner)["status"] != "fail":
            raise ValueError("Zero fabrication clearance passed")
        project_settings["board"]["design_settings"]["rules"]["min_clearance"] = 0.1
        project.write_text(json.dumps(project_settings), encoding="utf-8")
        board.write_text('(kicad_pcb (layers (0 "F.Cu" signal)))', encoding="utf-8")
        if audit(board, schematic, netlist, runner=runner)["status"] != "fail":
            raise ValueError("Incomplete copper layer table passed PCB proof")
        board.write_text(board_source, encoding="utf-8")
        record = {
            "path": "engineering/hardware/released/board.kicad_pcb",
            "sha256": _hash(board),
            "schematic_sha256": _hash(schematic),
            "netlist_sha256": _hash(netlist),
            "project_sha256": _hash(project),
            "revision": "fixture-A",
            "reviewed_by": "fixture reviewer",
            "disposition": "approved",
        }
        related = {
            "schematic_source": {
                "path": "engineering/hardware/released/board.kicad_sch",
                "sha256": _hash(schematic),
                "disposition": "approved",
            },
            "schematic_netlist": {
                "path": "engineering/hardware/released/board.xml",
                "sha256": _hash(netlist),
                "disposition": "approved",
            },
            "erc_report": {
                "project_sha256": _hash(project),
                "schematic_sha256": _hash(schematic),
                "disposition": "approved",
            },
        }
        requirement = {"id": "routed_pcb", "stage": "design_release"}
        with patch("buildslate.hardware_readiness.audit_pcb", return_value=proof):
            accepted = _evidence_result(
                root, requirement, record, related_records=related
            )
            if accepted["status"] != "accepted":
                raise ValueError("Bound routed PCB fixture was rejected")
            changed = {**record, "netlist_sha256": "0" * 64}
            if (
                _evidence_result(root, requirement, changed, related_records=related)[
                    "status"
                ]
                != "rejected"
            ):
                raise ValueError("Stale schematic netlist binding passed")
            changed = {**record, "project_sha256": "0" * 64}
            if (
                _evidence_result(root, requirement, changed, related_records=related)[
                    "status"
                ]
                != "rejected"
            ):
                raise ValueError("Stale PCB project settings binding passed")
            erc_mismatch = {
                **related,
                "erc_report": {**related["erc_report"], "project_sha256": "0" * 64},
            }
            if (
                _evidence_result(
                    root, requirement, record, related_records=erc_mismatch
                )["status"]
                != "rejected"
            ):
                raise ValueError("PCB project differed from approved ERC")
            changed = {**record, "path": "engineering/hardware/released/board.pdf"}
            (released / "board.pdf").write_text("reviewed picture", encoding="utf-8")
            changed["sha256"] = _hash(released / "board.pdf")
            if (
                _evidence_result(root, requirement, changed, related_records=related)[
                    "status"
                ]
                != "rejected"
            ):
                raise ValueError("PDF accepted as routed PCB")
        if (
            audit(
                board,
                schematic,
                netlist,
                runner=lambda command: subprocess.CompletedProcess(
                    command, 5, "", "failed"
                ),
            )["status"]
            != "fail"
        ):
            raise ValueError("Failed KiCad invocation passed")
    print("PASS: PCB parity, DRC, fabrication output, and evidence binding faults")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
