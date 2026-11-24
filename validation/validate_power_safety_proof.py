"""Exercise released power arithmetic and hardware evidence binding."""

from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from buildslate.hardware_readiness import _evidence_result  # noqa: E402
from buildslate.power_safety_proof import (  # noqa: E402
    BOARD,
    ELECTRICAL_BOM,
    FAULTS,
    PROFILE,
    RELEASE,
    SELECTED_BOM,
    audit,
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def _fixture(root: Path) -> dict:
    (root / PROFILE).parent.mkdir(parents=True)
    (root / PROFILE).write_bytes((ROOT / PROFILE).read_bytes())
    selected = root / SELECTED_BOM
    _write(
        selected,
        {
            "parts": {
                "battery_pack": {
                    "mpn": "FIXTURE-PACK",
                    "capabilities": {
                        "min_voltage_v": 3.0,
                        "max_voltage_v": 4.2,
                        "max_charge_current_a": 3.0,
                        "max_continuous_discharge_a": 40.0,
                        "max_peak_discharge_a": 80.0,
                        "charge_temperature_min_c": 0.0,
                        "charge_temperature_max_c": 45.0,
                        "maximum_operating_temperature_c": 60.0,
                        "maximum_validated_charge_w": 12.0,
                    },
                }
            }
        },
    )
    electrical = root / ELECTRICAL_BOM
    electrical.parent.mkdir(parents=True, exist_ok=True)
    electrical.write_text(
        "ref,manufacturer,mpn\nU1,Fixture,CHARGER\nU2,Fixture,PMIC\n"
        "U3,Fixture,PROTECTOR\nU4,Fixture,USB-PD\n",
        encoding="utf-8",
    )
    board = root / BOARD
    board.write_bytes(b"fixture routed board")
    roles = {
        "charger": ("U1", "CHARGER"),
        "pmic": ("U2", "PMIC"),
        "protection": ("U3", "PROTECTOR"),
        "usb_pd": ("U4", "USB-PD"),
    }
    return {
        "schema_version": 1,
        "device": "slate-pocket-v1r",
        "revision": "P1",
        "reviewed_by": "fixture reviewer",
        "selected_bom_sha256": _sha(selected),
        "electrical_bom_sha256": _sha(electrical),
        "routed_pcb_sha256": _sha(board),
        "battery_mpn": "FIXTURE-PACK",
        "power_components": {
            role: {"ref": ref, "mpn": mpn} for role, (ref, mpn) in roles.items()
        },
        "limits": {
            "operating_min_v": 3.2,
            "normal_charge_termination_v": 4.0,
            "charge_current_limit_a": 2.0,
            "continuous_discharge_limit_a": 40.0,
            "peak_discharge_limit_a": 80.0,
            "charge_temperature_min_c": 5.0,
            "charge_temperature_max_c": 40.0,
            "battery_overvoltage_trip_v": 4.1,
            "battery_undervoltage_trip_v": 3.1,
            "battery_overtemperature_trip_c": 50.0,
            "wired_input_cap_w": 30.0,
            "charge_path_efficiency": 0.85,
            "idle_system_w": 2.0,
            "wireless_enabled": False,
            "full_power_charge_ai_overlap": False,
        },
        "loads": [
            {"id": name, "continuous_w": sustained, "peak_w": peak}
            for name, sustained, peak in (
                ("compute_platform", 28.0, 45.0),
                ("memory_128gb", 12.0, 16.0),
                ("storage_1tb", 5.0, 7.0),
                ("display", 3.5, 6.0),
                ("radios", 2.0, 8.0),
                ("cameras", 0.0, 6.0),
                ("system_io_and_controls", 1.5, 5.0),
            )
        ],
        "rails": [
            {
                "id": "core",
                "voltage_v": 1.0,
                "efficiency": 0.9,
                "continuous_current_a": 35.0,
                "peak_current_a": 50.0,
                "load_ids": ["compute_platform"],
                "depends_on": [],
            },
            {
                "id": "aux",
                "voltage_v": 5.0,
                "efficiency": 0.9,
                "continuous_current_a": 10.0,
                "peak_current_a": 15.0,
                "load_ids": [
                    "memory_128gb",
                    "storage_1tb",
                    "display",
                    "radios",
                    "cameras",
                    "system_io_and_controls",
                ],
                "depends_on": ["core"],
            },
        ],
        "rail_sequence": ["core", "aux"],
        "fault_controls": {
            name: {
                "hardware_ref": "U3",
                "hardware_action": "fixture cutoff",
                "firmware_action": "fixture fault log",
            }
            for name in FAULTS
        },
    }


def main() -> int:
    if audit(ROOT)["status"] != "missing":
        raise ValueError("Public checkout must not imply a released power design")
    with TemporaryDirectory() as temp:
        root = Path(temp)
        baseline = _fixture(root)
        release = root / RELEASE
        _write(release, baseline)
        if audit(root)["status"] != "pass":
            raise ValueError(f"Valid power fixture was rejected: {audit(root)}")
        for name, mutate in (
            ("battery identity", lambda x: x.update(battery_mpn="wrong")),
            ("stale BOM", lambda x: x.update(electrical_bom_sha256="0" * 64)),
            ("charge current", lambda x: x["limits"].update(charge_current_limit_a=4)),
            ("input cap", lambda x: x["limits"].update(charge_path_efficiency=0.2)),
            ("compute floor", lambda x: x["loads"][0].update(peak_w=40)),
            ("rail capacity", lambda x: x["rails"][0].update(peak_current_a=40)),
            ("rail assignment", lambda x: x["rails"][1]["load_ids"].pop()),
            ("rail ordering", lambda x: x.update(rail_sequence=["aux", "core"])),
            ("fault action", lambda x: x["fault_controls"].pop(FAULTS[0])),
            (
                "fault reference",
                lambda x: x["fault_controls"][FAULTS[0]].update(hardware_ref="U9"),
            ),
            (
                "charge overlap",
                lambda x: x["limits"].update(full_power_charge_ai_overlap=True),
            ),
        ):
            changed = copy.deepcopy(baseline)
            mutate(changed)
            _write(release, changed)
            if audit(root)["status"] == "pass":
                raise ValueError(f"Invalid power fixture passed: {name}")
        _write(release, baseline)
        record = {
            "path": RELEASE.as_posix(),
            "sha256": _sha(release),
            "revision": "P1",
            "reviewed_by": "fixture reviewer",
            "disposition": "approved",
        }
        related = {
            "selected_bom": {
                "disposition": "approved",
                "sha256": baseline["selected_bom_sha256"],
            },
            "schematic_netlist": {
                "disposition": "approved",
                "bom_sha256": baseline["electrical_bom_sha256"],
            },
            "routed_pcb": {
                "disposition": "approved",
                "sha256": baseline["routed_pcb_sha256"],
            },
        }
        selection = {"status": "pass", "sha256": baseline["selected_bom_sha256"]}
        requirement = {"id": "power_safety", "stage": "design_release"}
        if (
            _evidence_result(root, requirement, record, selection, related)["status"]
            != "accepted"
        ):
            raise ValueError("Approved bound power fixture was rejected")
        related["routed_pcb"]["sha256"] = "0" * 64
        if (
            _evidence_result(root, requirement, record, selection, related)["status"]
            == "accepted"
        ):
            raise ValueError("Unbound board was accepted")
    print("PASS: power load, charge, fault, and release bindings checked")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
