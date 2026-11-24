"""Check KiCad ERC rerun and schematic evidence binding with fault fixtures."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from buildslate.erc_proof import CRITICAL_RULES, audit  # noqa: E402
from buildslate.hardware_readiness import _evidence_result  # noqa: E402


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    with TemporaryDirectory() as temporary:
        root = Path(temporary)
        released = root / "engineering/hardware/released"
        released.mkdir(parents=True)
        schematic = released / "board.kicad_sch"
        project = released / "board.kicad_pro"
        report_path = released / "board.erc.json"
        schematic.write_text("synthetic schematic source", encoding="utf-8")
        settings = {
            "erc": {
                "erc_exclusions": [],
                "rule_severities": {rule: "error" for rule in CRITICAL_RULES},
            }
        }
        project.write_text(json.dumps(settings), encoding="utf-8")
        report = {
            "$schema": "https://schemas.kicad.org/erc.v1.json",
            "source": schematic.name,
            "date": "2026-11-24T00:00:00Z",
            "kicad_version": "9.0.1",
            "coordinate_units": "mm",
            "sheets": [
                {
                    "path": "/",
                    "uuid_path": "/11111111-1111-4111-8111-111111111111",
                    "violations": [],
                }
            ],
        }
        report_path.write_text(json.dumps(report), encoding="utf-8")
        fault = {"exit": False, "finding": False, "missing": False, "stale": False}

        def runner(command: list[str]) -> subprocess.CompletedProcess[str]:
            if command[:3] != ["kicad-cli", "sch", "erc"] or not {
                "--format",
                "--severity-all",
                "--exit-code-violations",
                "--units",
                "--output",
            }.issubset(command):
                raise AssertionError("KiCad ERC command omitted required flags")
            if command[command.index("--format") + 1] != "json":
                raise AssertionError("KiCad ERC did not request JSON")
            if command[command.index("--units") + 1] != "mm":
                raise AssertionError("KiCad ERC did not request millimeters")
            if command[-1] != str(schematic):
                raise AssertionError("KiCad ERC did not check released schematic")
            output = Path(command[command.index("--output") + 1])
            fresh = json.loads(json.dumps(report))
            fresh["date"] = "2026-11-25T00:00:00Z"
            if fault["finding"]:
                fresh["sheets"][0]["violations"] = [
                    {"type": "pin_not_connected", "severity": "warning"}
                ]
            if fault["stale"]:
                fresh["kicad_version"] = "9.0.2"
            if not fault["missing"]:
                output.write_text(json.dumps(fresh), encoding="utf-8")
            return subprocess.CompletedProcess(
                command, 5 if fault["exit"] else 0, "", "ERC violation"
            )

        proof = audit(schematic, report_path, runner=runner)
        if proof["status"] != "pass" or proof["sheets_checked"] != 1:
            raise ValueError(f"Clean synthetic ERC was rejected: {proof}")
        for key in fault:
            fault[key] = True
            if audit(schematic, report_path, runner=runner)["status"] != "fail":
                raise ValueError(f"ERC {key} fault passed")
            fault[key] = False
        settings["erc"]["erc_exclusions"] = ["synthetic ignored violation"]
        project.write_text(json.dumps(settings), encoding="utf-8")
        if audit(schematic, report_path, runner=runner)["status"] != "fail":
            raise ValueError("ERC exclusion passed project-settings proof")
        settings["erc"]["erc_exclusions"] = []
        settings["erc"]["rule_severities"]["pin_not_connected"] = "ignore"
        project.write_text(json.dumps(settings), encoding="utf-8")
        if audit(schematic, report_path, runner=runner)["status"] != "fail":
            raise ValueError("Ignored critical ERC rule passed")
        settings["erc"]["rule_severities"]["pin_not_connected"] = "error"
        project.write_text(json.dumps(settings), encoding="utf-8")
        stale = {**report, "sheets": [{**report["sheets"][0], "path": "/stale"}]}
        report_path.write_text(json.dumps(stale), encoding="utf-8")
        if audit(schematic, report_path, runner=runner)["status"] != "fail":
            raise ValueError("Stale reviewed ERC report passed")
        report_path.write_text(json.dumps(report), encoding="utf-8")
        record = {
            "path": "engineering/hardware/released/board.erc.json",
            "sha256": _sha(report_path),
            "schematic_sha256": _sha(schematic),
            "project_sha256": _sha(project),
            "revision": "fixture-A",
            "reviewed_by": "fixture reviewer",
            "disposition": "approved",
        }
        related = {
            "schematic_source": {
                "path": "engineering/hardware/released/board.kicad_sch",
                "sha256": _sha(schematic),
                "disposition": "approved",
            }
        }
        requirement = {"id": "erc_report", "stage": "design_release"}
        with patch("buildslate.hardware_readiness.audit_erc", return_value=proof):
            if (
                _evidence_result(root, requirement, record, related_records=related)[
                    "status"
                ]
                != "accepted"
            ):
                raise ValueError("Bound ERC fixture was rejected")
            for changed, upstream in (
                ({**record, "schematic_sha256": "0" * 64}, related),
                ({**record, "project_sha256": "0" * 64}, related),
                (
                    record,
                    {
                        "schematic_source": {
                            **related["schematic_source"],
                            "disposition": "draft",
                        }
                    },
                ),
                (
                    {**record, "path": "engineering/hardware/released/board.pdf"},
                    related,
                ),
            ):
                if changed["path"].endswith(".pdf"):
                    pdf = released / "board.pdf"
                    pdf.write_bytes(b"reviewed picture")
                    changed["sha256"] = _sha(pdf)
                if (
                    _evidence_result(
                        root, requirement, changed, related_records=upstream
                    )["status"]
                    == "accepted"
                ):
                    raise ValueError("ERC evidence escaped schematic binding")
    print("PASS: KiCad ERC command, report, and evidence binding faults")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
