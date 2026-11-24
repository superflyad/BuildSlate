"""Exercise RF release identity, feed, placement, and sweep failures."""

from __future__ import annotations

import copy
import csv
import hashlib
import io
import json
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from buildslate.io import dump_yaml  # noqa: E402
from buildslate.firmware_proof import RELEASE as FIRMWARE_RELEASE  # noqa: E402
from buildslate.hardware_readiness import _evidence_result  # noqa: E402
from buildslate.rf_proof import (  # noqa: E402
    ASSEMBLY,
    BOARD,
    COEXISTENCE,
    COEXISTENCE_CASES,
    CONDITIONS,
    ELECTRICAL_BOM,
    KEEP_OUT,
    MECHANICAL_MANIFEST,
    MECHANICAL_PROOF,
    NETLIST,
    PARTS,
    RELEASE,
    SELECTED_BOM,
    SWEEPS,
    audit,
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def _frequencies() -> list[int]:
    return [2400, 2420, 2440, 2460, 2480, 5200, 5220, 5240, 5260, 5280]


def _touchstone(path: Path, marker: str, ports: int, magnitude: float) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [marker, "# MHz S RI R 50"]
    for frequency in _frequencies():
        if ports == 1:
            lines.append(f"{frequency} {magnitude} 0")
        else:
            lines.append(f"{frequency} 0.2 0 {magnitude} 0 {magnitude} 0 0.2 0")
    path.write_text("\n".join(lines) + "\n", encoding="ascii")


def _efficiency(
    path: Path, condition: str, antenna_id: str, value: float = 55.0
) -> None:
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(("condition", "antenna_id", "frequency_mhz", "efficiency_percent"))
    for frequency in _frequencies():
        writer.writerow((condition, antenna_id, frequency, value))
    path.write_text(stream.getvalue(), encoding="utf-8")


def _seal(
    root: Path, release: dict, parts: dict, sweeps: dict, mechanical: dict
) -> None:
    for item in sweeps["sweeps"]:
        item["sha256"] = _sha(root / item["path"])
        item["efficiency_sha256"] = _sha(root / item["efficiency_path"])
    for item in sweeps["isolation"]:
        item["sha256"] = _sha(root / item["path"])
    _json(root / PARTS, parts)
    _json(root / SWEEPS, sweeps)
    _json(root / MECHANICAL_PROOF, mechanical)
    paths = {
        "radio_parts_sha256": PARTS,
        "sweep_manifest_sha256": SWEEPS,
        "coexistence_sha256": COEXISTENCE,
        "routed_pcb_sha256": BOARD,
        "netlist_sha256": NETLIST,
        "electrical_bom_sha256": ELECTRICAL_BOM,
        "selected_bom_sha256": SELECTED_BOM,
        "firmware_bundle_sha256": FIRMWARE_RELEASE,
        "mechanical_assembly_sha256": ASSEMBLY,
        "mechanical_manifest_sha256": MECHANICAL_MANIFEST,
        "mechanical_proof_sha256": MECHANICAL_PROOF,
    }
    for field, path in paths.items():
        release[field] = _sha(root / path)
    _json(root / RELEASE, release)


def _fixture(root: Path) -> tuple[dict, dict, dict, dict]:
    keepout = root / KEEP_OUT
    keepout.parent.mkdir(parents=True, exist_ok=True)
    keepout.write_bytes((ROOT / KEEP_OUT).read_bytes())
    source = root / "engineering/hardware/released/rf/sources/supplier.pdf"
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_bytes(b"synthetic supplier and lab source")
    evidence = {
        "evidence_path": source.relative_to(root).as_posix(),
        "evidence_sha256": _sha(source),
    }
    selected = root / SELECTED_BOM
    _json(
        selected,
        {
            "parts": {
                "compute_platform": {
                    "mpn": "FIXTURE-HOST",
                    "capabilities": {"radio_interfaces": ["pcie"]},
                }
            }
        },
    )
    _json(
        root / FIRMWARE_RELEASE,
        {
            "images": [{"id": "kernel"}],
            "drivers": [{"role": "antenna_modules", "image_id": "kernel"}],
            "radio_kill": {
                "image_id": "kernel",
                "hardware_ref": "U6",
                "hardware_action": "fixture power cut",
                "states": ["boot", "fault", "update", "suspend", "resume"],
            },
        },
    )
    board = root / BOARD
    board.parent.mkdir(parents=True, exist_ok=True)
    board.write_bytes(b"synthetic routed board")
    bom = root / ELECTRICAL_BOM
    bom.write_text(
        "ref,manufacturer,mpn\nU5,Fixture,RF-MODULE\nU6,Fixture,RF-SWITCH\nC1,Fixture,MATCH\nC2,Fixture,MATCH\nJ1,Fixture,FEED\nJ2,Fixture,FEED\n",
        encoding="utf-8",
    )
    netlist = root / NETLIST
    netlist.write_text(
        "<export><components>"
        + "".join(
            f'<comp ref="{ref}"><value>{ref}</value><footprint>Fixture</footprint></comp>'
            for ref in ("U5", "U6", "C1", "C2", "J1", "J2")
        )
        + "</components><nets>"
        + '<net code="1" name="RF1"><node ref="U5" pin="1"/><node ref="C1" pin="1"/></net>'
        + '<net code="2" name="RF1_OUT"><node ref="C1" pin="2"/><node ref="J1" pin="1"/></net>'
        + '<net code="3" name="RF2"><node ref="U5" pin="2"/><node ref="C2" pin="1"/></net>'
        + '<net code="4" name="RF2_OUT"><node ref="C2" pin="2"/><node ref="J2" pin="1"/></net>'
        + '<net code="5" name="RF_KILL"><node ref="U6" pin="1"/><node ref="U5" pin="3"/></net>'
        + "</nets></export>",
        encoding="utf-8",
    )
    assembly = root / ASSEMBLY
    assembly.parent.mkdir(parents=True, exist_ok=True)
    assembly.write_bytes(b"synthetic mechanical STEP")
    manifest = root / MECHANICAL_MANIFEST
    manifest.write_text(
        dump_yaml(
            {
                "parts": [
                    {
                        "id": "ant1",
                        "part_number": "ANT-1",
                        "roles": ["antenna_modules"],
                    },
                    {
                        "id": "ant2",
                        "part_number": "ANT-2",
                        "roles": ["antenna_modules"],
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    mechanical = {
        "status": "pass",
        "assembly_sha256": _sha(assembly),
        "manifest_sha256": _sha(manifest),
        "parts": [
            {
                "id": "ant1",
                "roles": ["antenna_modules"],
                "bounds_mm": [5, 87, 1, 20, 90, 2],
            },
            {
                "id": "ant2",
                "roles": ["antenna_modules"],
                "bounds_mm": [145, 87, 1, 160, 90, 2],
            },
        ],
    }
    antennas = []
    for index in (1, 2):
        antennas.append(
            {
                "id": f"A{index}",
                "manufacturer": "Fixture",
                "mpn": f"ANT-{index}",
                "feed_ref": f"J{index}",
                "feed_pin": "1",
                "feed_mpn": "FEED",
                "mechanical_part_id": f"ant{index}",
                "reservation": "top_left" if index == 1 else "top_right",
                "matching_parts": {f"C{index}": "MATCH"},
                "rf_path": [
                    {"ref": "U5", "pin": str(index)},
                    {"ref": f"C{index}", "pin": "1"},
                    {"ref": f"C{index}", "pin": "2"},
                    {"ref": f"J{index}", "pin": "1"},
                ],
                **evidence,
            }
        )
    parts = {
        "schema_version": 1,
        "device": "slate-pocket-v1r",
        "module": {
            "manufacturer": "Fixture",
            "mpn": "RF-MODULE",
            "board_ref": "U5",
            "host_interface": "pcie",
            "driver_image_id": "kernel",
            "wifi_generation": 7,
            "bluetooth_major": 6,
            "band_ids": ["b24", "b5"],
            **evidence,
        },
        "antennas": antennas,
    }
    bands = [
        {
            "id": "b24",
            "start_mhz": 2400,
            "end_mhz": 2480,
            "max_step_mhz": 20,
            "min_return_loss_db": 8,
            "min_isolation_db": 15,
            "min_efficiency_percent": 30,
            "max_desense_db": 3,
            **evidence,
        },
        {
            "id": "b5",
            "start_mhz": 5200,
            "end_mhz": 5280,
            "max_step_mhz": 20,
            "min_return_loss_db": 8,
            "min_isolation_db": 15,
            "min_efficiency_percent": 30,
            "max_desense_db": 3,
            **evidence,
        },
    ]
    sweeps = {"schema_version": 1, "bands": bands, "sweeps": [], "isolation": []}
    coexistence = root / COEXISTENCE
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(("scenario", "band_id", "desense_db"))
    for scenario in COEXISTENCE_CASES:
        for band in bands:
            writer.writerow((scenario, band["id"], 1.0))
    coexistence.write_text(stream.getvalue(), encoding="utf-8")
    for condition in CONDITIONS:
        for antenna_id in ("A1", "A2"):
            prefix = f"engineering/hardware/released/rf/sweeps/{condition}-{antenna_id}"
            s1p = root / f"{prefix}.s1p"
            efficiency = root / f"{prefix}.csv"
            _touchstone(
                s1p, f"! buildslate condition={condition} antenna={antenna_id}", 1, 0.2
            )
            _efficiency(efficiency, condition, antenna_id)
            sweeps["sweeps"].append(
                {
                    "condition": condition,
                    "antenna_id": antenna_id,
                    "path": s1p.relative_to(root).as_posix(),
                    "efficiency_path": efficiency.relative_to(root).as_posix(),
                }
            )
        s2p = root / f"engineering/hardware/released/rf/sweeps/{condition}-pair.s2p"
        _touchstone(s2p, f"! buildslate condition={condition} antennas=A1,A2", 2, 0.1)
        sweeps["isolation"].append(
            {
                "condition": condition,
                "antenna_ids": ["A1", "A2"],
                "path": s2p.relative_to(root).as_posix(),
            }
        )
    release = {
        "schema_version": 1,
        "device": "slate-pocket-v1r",
        "revision": "R1",
        "reviewed_by": "fixture reviewer",
        "solver_name": "fixture EM solver",
        "solver_version": "fixture-1",
        "cellular_enabled": False,
        "uwb_enabled": False,
        "wireless_charging_enabled": False,
        "minimum_antenna_separation_mm": 40,
        "separation_evidence_path": evidence["evidence_path"],
        "separation_evidence_sha256": evidence["evidence_sha256"],
        "markets": [
            {
                "id": "fixture-market",
                "band_ids": ["b24", "b5"],
                "lab_plan_path": evidence["evidence_path"],
                "lab_plan_sha256": evidence["evidence_sha256"],
            }
        ],
    }
    _seal(root, release, parts, sweeps, mechanical)
    return release, parts, sweeps, mechanical


def main() -> int:
    if audit(ROOT)["status"] != "missing":
        raise ValueError("Public checkout must not imply a released RF design")
    with TemporaryDirectory() as temp:
        root = Path(temp)
        baseline = _fixture(root)
        if audit(root)["status"] != "pass":
            raise ValueError(f"Valid RF fixture was rejected: {audit(root)}")
        for name, kind, mutate in (
            ("module MPN", "parts", lambda x: x["module"].update(mpn="wrong")),
            (
                "radio capability",
                "parts",
                lambda x: x["module"].update(wifi_generation=6),
            ),
            (
                "host interface",
                "parts",
                lambda x: x["module"].update(host_interface="unsupported"),
            ),
            (
                "driver image",
                "parts",
                lambda x: x["module"].update(driver_image_id="missing"),
            ),
            (
                "matching path",
                "parts",
                lambda x: x["antennas"][0]["rf_path"][2].update(pin="9"),
            ),
            (
                "antenna placement",
                "mechanical",
                lambda x: x["parts"][0].update(bounds_mm=[50, 87, 1, 60, 90, 2]),
            ),
            ("missing condition", "sweeps", lambda x: x["sweeps"].pop()),
            (
                "band threshold",
                "sweeps",
                lambda x: x["bands"][0].update(min_return_loss_db=20),
            ),
            (
                "market band",
                "release",
                lambda x: x["markets"][0].update(band_ids=["b24"]),
            ),
            (
                "wireless charging",
                "release",
                lambda x: x.update(wireless_charging_enabled=True),
            ),
        ):
            release, parts, sweeps, mechanical = copy.deepcopy(baseline)
            mutate(
                {
                    "release": release,
                    "parts": parts,
                    "sweeps": sweeps,
                    "mechanical": mechanical,
                }[kind]
            )
            _seal(root, release, parts, sweeps, mechanical)
            if audit(root)["status"] == "pass":
                raise ValueError(f"Invalid RF fixture passed: {name}")
        release, parts, sweeps, mechanical = copy.deepcopy(baseline)
        _seal(root, release, parts, sweeps, mechanical)
        first_sweep = root / sweeps["sweeps"][0]["path"]
        original = first_sweep.read_bytes()
        first_sweep.write_bytes(original.replace(b"0.2 0", b"0.8 0"))
        _seal(root, release, parts, sweeps, mechanical)
        if audit(root)["status"] == "pass":
            raise ValueError("Poor return loss passed RF audit")
        first_sweep.write_bytes(original)
        _seal(root, release, parts, sweeps, mechanical)
        first_efficiency = root / sweeps["sweeps"][0]["efficiency_path"]
        original = first_efficiency.read_bytes()
        first_efficiency.write_bytes(original.replace(b",55.0", b",10.0"))
        _seal(root, release, parts, sweeps, mechanical)
        if audit(root)["status"] == "pass":
            raise ValueError("Poor radiation efficiency passed RF audit")
        first_efficiency.write_bytes(original)
        _seal(root, release, parts, sweeps, mechanical)
        first_isolation = root / sweeps["isolation"][0]["path"]
        original = first_isolation.read_bytes()
        first_isolation.write_bytes(original.replace(b"0.1 0", b"0.4 0"))
        _seal(root, release, parts, sweeps, mechanical)
        if audit(root)["status"] == "pass":
            raise ValueError("Poor antenna isolation passed RF audit")
        first_isolation.write_bytes(original)
        _seal(root, release, parts, sweeps, mechanical)
        coexistence = root / COEXISTENCE
        original = coexistence.read_bytes()
        coexistence.write_bytes(original.replace(b",1.0", b",5.0"))
        _seal(root, release, parts, sweeps, mechanical)
        if audit(root)["status"] == "pass":
            raise ValueError("Excessive coexistence desense passed RF audit")
        coexistence.write_bytes(original)
        _seal(root, release, parts, sweeps, mechanical)
        record = {
            "path": RELEASE.as_posix(),
            "sha256": _sha(root / RELEASE),
            "revision": "R1",
            "reviewed_by": "fixture reviewer",
            "disposition": "approved",
        }
        related = {
            "selected_bom": {
                "disposition": "approved",
                "sha256": release["selected_bom_sha256"],
            },
            "routed_pcb": {
                "disposition": "approved",
                "sha256": release["routed_pcb_sha256"],
            },
            "schematic_netlist": {
                "disposition": "approved",
                "sha256": release["netlist_sha256"],
                "bom_sha256": release["electrical_bom_sha256"],
            },
            "mechanical_release": {
                "disposition": "approved",
                "sha256": release["mechanical_assembly_sha256"],
                "manifest_sha256": release["mechanical_manifest_sha256"],
            },
            "firmware_boot": {
                "disposition": "approved",
                "sha256": release["firmware_bundle_sha256"],
            },
        }
        selection = {"status": "pass", "sha256": release["selected_bom_sha256"]}
        requirement = {"id": "rf_release", "stage": "design_release"}
        if (
            _evidence_result(root, requirement, record, selection, related)["status"]
            != "accepted"
        ):
            raise ValueError("Approved bound RF fixture was rejected")
        related["routed_pcb"]["sha256"] = "0" * 64
        if (
            _evidence_result(root, requirement, record, selection, related)["status"]
            == "accepted"
        ):
            raise ValueError("RF release accepted an unapproved board")
    print("PASS: RF part, feed, placement, band, and sweep faults checked")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
