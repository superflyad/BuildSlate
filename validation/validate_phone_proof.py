"""Exercise phone-test evidence binding and objective failure cases."""

from __future__ import annotations

import copy
import csv
import hashlib
import json
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from buildslate.hardware_readiness import _evidence_result  # noqa: E402
from buildslate.phone_proof import TESTS, audit  # noqa: E402

HASH = "a" * 64


def _rows(test_id: str) -> list[dict]:
    first = {
        "network_registration": {"elapsed_s": 0, "registered": 0, "sim_ready": 0},
        "outgoing_call": {
            "elapsed_s": 0,
            "connected": 1,
            "uplink_audio_samples": 0,
            "downlink_audio_samples": 0,
            "dropped": 0,
        },
        "incoming_call": {
            "elapsed_s": 0,
            "connected": 1,
            "uplink_audio_samples": 0,
            "downlink_audio_samples": 0,
            "dropped": 0,
        },
        "packet_data": {"elapsed_s": 0, "bytes_tx": 0, "bytes_rx": 0},
        "radio_kill": {"elapsed_s": 0, "radio_disabled": 0, "registered": 1},
        "emergency_lab_simulator": {"elapsed_s": 0, "emergency_route_pass": 0},
    }
    second = {
        "network_registration": {"elapsed_s": 30, "registered": 1, "sim_ready": 1},
        "outgoing_call": {
            "elapsed_s": 30,
            "connected": 1,
            "uplink_audio_samples": 240000,
            "downlink_audio_samples": 240000,
            "dropped": 0,
        },
        "incoming_call": {
            "elapsed_s": 30,
            "connected": 1,
            "uplink_audio_samples": 240000,
            "downlink_audio_samples": 240000,
            "dropped": 0,
        },
        "packet_data": {"elapsed_s": 30, "bytes_tx": 1024, "bytes_rx": 2048},
        "radio_kill": {"elapsed_s": 30, "radio_disabled": 1, "registered": 0},
        "emergency_lab_simulator": {"elapsed_s": 30, "emergency_route_pass": 1},
    }
    identity = {
        "campaign_id": "fixture-campaign",
        "unit_id": "fixture-unit",
        "build_id": "fixture-build",
        "configuration_sha256": HASH,
    }
    return [{**identity, **first[test_id]}, {**identity, **second[test_id]}]


def _write_case(path: Path, rows: list[dict]) -> str:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_bundle(path: Path, bundle: dict) -> str:
    path.write_text(json.dumps(bundle, indent=2) + "\n", encoding="utf-8")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    with TemporaryDirectory() as temporary:
        root = Path(temporary)
        controlled = root / "validation/phone/test-results"
        controlled.mkdir(parents=True)
        cases = []
        for test_id in TESTS:
            raw = controlled / f"{test_id}.csv"
            cases.append(
                {
                    "id": test_id,
                    "raw_path": raw.relative_to(root).as_posix(),
                    "raw_sha256": _write_case(raw, _rows(test_id)),
                    "disposition": "pass",
                }
            )
        bundle = {
            "schema_version": 1,
            "device": "slate-pocket-v1r",
            "campaign_id": "fixture-campaign",
            "unit_id": "fixture-unit",
            "build_id": "fixture-build",
            "configuration_sha256": HASH,
            "cellular_mpn": "fixture-voice-module",
            "modem_firmware_version": "fixture-fw",
            "carrier": "fixture-network",
            "selected_bom_sha256": "b" * 64,
            "cellular_design_sha256": "c" * 64,
            "telephony_software_sha256": "d" * 64,
            "emergency_method": "authorized_lab_simulator",
            "emergency_lab_approval": "fixture-only",
            "regulatory_review_reference": "fixture-only",
            "tests": cases,
        }
        path = controlled / "phone-evidence.json"
        digest = _write_bundle(path, bundle)
        if audit(path, root)["status"] != "pass":
            raise ValueError("Complete synthetic phone test bundle was rejected")
        record = {
            "path": path.relative_to(root).as_posix(),
            "sha256": digest,
            "revision": "fixture",
            "reviewed_by": "fixture reviewer",
            "disposition": "approved",
        }
        requirement = {"id": "phone_validation", "stage": "phone_function"}
        related = {
            identifier: {"sha256": bundle[field], "disposition": "approved"}
            for identifier, field in (
                ("selected_bom", "selected_bom_sha256"),
                ("cellular_design", "cellular_design_sha256"),
                ("telephony_software", "telephony_software_sha256"),
            )
        }
        if (
            _evidence_result(root, requirement, record, related_records=related)[
                "status"
            ]
            != "accepted"
        ):
            raise ValueError("Complete bound fixture was rejected by phone gate")
        bad_related = copy.deepcopy(related)
        bad_related["cellular_design"]["sha256"] = HASH
        if (
            _evidence_result(root, requirement, record, related_records=bad_related)[
                "status"
            ]
            == "accepted"
        ):
            raise ValueError("Unbound cellular design was accepted")
        call = controlled / "outgoing_call.csv"
        call.write_text("tampered\n", encoding="utf-8")
        if (
            _evidence_result(root, requirement, record, related_records=related)[
                "status"
            ]
            == "accepted"
        ):
            raise ValueError("Tampered call CSV was accepted")
        cases[1]["raw_sha256"] = _write_case(
            call,
            [
                _rows("outgoing_call")[0],
                {**_rows("outgoing_call")[1], "downlink_audio_samples": 0},
            ],
        )
        record["sha256"] = _write_bundle(path, bundle)
        if audit(path, root)["status"] != "fail":
            raise ValueError("Call with no received audio was accepted")
        cases[1]["raw_sha256"] = _write_case(call, _rows("outgoing_call"))
        registration = controlled / "network_registration.csv"
        other_unit = [
            {**row, "unit_id": "different-physical-unit"}
            for row in _rows("network_registration")
        ]
        cases[0]["raw_sha256"] = _write_case(registration, other_unit)
        _write_bundle(path, bundle)
        if audit(path, root)["status"] != "fail":
            raise ValueError("Raw log from another physical unit was accepted")
        design_record = {
            **record,
            "path": "validation/phone/test-results/phone-evidence.json",
        }
        if (
            _evidence_result(
                root,
                {"id": "cellular_design", "stage": "phone_function"},
                design_record,
            )["status"]
            == "accepted"
        ):
            raise ValueError("Phone design release was accepted from a test directory")
    print("PASS: phone evidence identity, raw logs, and gate fault fixtures")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
