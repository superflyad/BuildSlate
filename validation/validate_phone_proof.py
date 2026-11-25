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
from buildslate.phone_proof import CALL_SETUP_FIELDS, TESTS, audit  # noqa: E402

HASH = "a" * 64


def _rows(test_id: str) -> list[dict]:
    first = {
        "network_registration": {"elapsed_s": 0, "registered": 0, "sim_ready": 0},
        "packet_data": {"elapsed_s": 0, "bytes_tx": 0, "bytes_rx": 0},
        "radio_kill": {"elapsed_s": 0, "radio_disabled": 0, "registered": 1},
        "emergency_lab_simulator": {"elapsed_s": 0, "emergency_route_pass": 0},
    }
    second = {
        "network_registration": {"elapsed_s": 30, "registered": 1, "sim_ready": 1},
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
    if test_id in CALL_SETUP_FIELDS:
        first_event, second_event = CALL_SETUP_FIELDS[test_id]
        return [
            {
                **identity,
                "elapsed_s": second,
                first_event: int(second >= 1),
                second_event: int(second >= 2),
                "connected": int(second >= 3),
                "uplink_audio_samples": max(0, second - 2) * 8000,
                "downlink_audio_samples": max(0, second - 2) * 8000,
                "dropped": 0,
            }
            for second in range(34)
        ]
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

        def reject_call(
            test_id: str, rows: list[dict], expected_error: str, reason: str
        ) -> None:
            index = TESTS.index(test_id)
            raw = controlled / f"{test_id}.csv"
            cases[index]["raw_sha256"] = _write_case(raw, rows)
            _write_bundle(path, bundle)
            review = audit(path, root)
            if review["status"] != "fail" or not any(
                expected_error in error for error in review["errors"]
            ):
                raise ValueError(reason)

        no_downlink = _rows("outgoing_call")
        for row in no_downlink:
            row["downlink_audio_samples"] = 0
        reject_call(
            "outgoing_call",
            no_downlink,
            "advancing downlink_audio_samples",
            "Call without downlink audio passed",
        )
        interrupted = _rows("outgoing_call")
        interrupted[18]["connected"] = 0
        reject_call(
            "outgoing_call",
            interrupted,
            "continuous 30 s connected telemetry",
            "Disconnected call interval passed",
        )
        sparse = [
            row
            for index, row in enumerate(_rows("outgoing_call"))
            if not 15 <= index < 24
        ]
        reject_call(
            "outgoing_call",
            sparse,
            "continuous 30 s connected telemetry",
            "Sparse connected call log passed",
        )
        stalled_audio = _rows("outgoing_call")
        stalled_audio[18]["uplink_audio_samples"] = stalled_audio[17][
            "uplink_audio_samples"
        ]
        reject_call(
            "outgoing_call",
            stalled_audio,
            "advancing uplink_audio_samples",
            "Stalled uplink audio passed",
        )
        no_dial = _rows("outgoing_call")
        for row in no_dial:
            row["dial_request_seen"] = 0
        reject_call(
            "outgoing_call",
            no_dial,
            "latched dial_request_seen",
            "Call without dial event passed",
        )
        reversed_setup = _rows("outgoing_call")
        for row in reversed_setup:
            row["dial_request_seen"] = int(row["elapsed_s"] >= 2)
            row["peer_answer_seen"] = int(row["elapsed_s"] >= 1)
        reject_call(
            "outgoing_call",
            reversed_setup,
            "setup events do not precede connection",
            "Out-of-order call setup passed",
        )
        no_answer = _rows("incoming_call")
        for row in no_answer:
            row["local_answer_seen"] = 0
        reject_call(
            "incoming_call",
            no_answer,
            "latched local_answer_seen",
            "Call without answer event passed",
        )
        cases[1]["raw_sha256"] = _write_case(call, _rows("outgoing_call"))
        cases[2]["raw_sha256"] = _write_case(
            controlled / "incoming_call.csv", _rows("incoming_call")
        )
        lines = call.read_text(encoding="utf-8").splitlines()
        call.write_text(
            "\n".join([lines[0] + ",connected", *(line + ",1" for line in lines[1:])])
            + "\n",
            encoding="utf-8",
        )
        cases[1]["raw_sha256"] = hashlib.sha256(call.read_bytes()).hexdigest()
        _write_bundle(path, bundle)
        if not any(
            "duplicate or missing CSV header" in error
            for error in audit(path, root)["errors"]
        ):
            raise ValueError("Duplicate call-state column was accepted")
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
