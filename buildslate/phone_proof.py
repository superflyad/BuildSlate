"""Check the identity and raw measurements of an integrated phone test bundle."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

TESTS = (
    "network_registration",
    "outgoing_call",
    "incoming_call",
    "packet_data",
    "radio_kill",
    "emergency_lab_simulator",
)
MEASURED_FIELDS = {
    "network_registration": ("elapsed_s", "registered", "sim_ready"),
    "outgoing_call": (
        "elapsed_s",
        "connected",
        "uplink_audio_samples",
        "downlink_audio_samples",
        "dropped",
    ),
    "incoming_call": (
        "elapsed_s",
        "connected",
        "uplink_audio_samples",
        "downlink_audio_samples",
        "dropped",
    ),
    "packet_data": ("elapsed_s", "bytes_tx", "bytes_rx"),
    "radio_kill": ("elapsed_s", "radio_disabled", "registered"),
    "emergency_lab_simulator": ("elapsed_s", "emergency_route_pass"),
}
IDENTITY = ("campaign_id", "unit_id", "build_id", "configuration_sha256")
FIELDS = {key: (*IDENTITY, *values) for key, values in MEASURED_FIELDS.items()}


def _text(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _digest(value: object) -> bool:
    return (
        _text(value)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _number(row: dict, key: str) -> float:
    value = float(row[key])
    if not 0 <= value < float("inf"):
        raise ValueError(f"Invalid {key}")
    return value


def _measure(test_id: str, rows: list[dict]) -> list[str]:
    errors = []
    if len(rows) < 2:
        return ["At least two timestamped rows are required"]
    try:
        elapsed = [_number(row, "elapsed_s") for row in rows]
        if elapsed[0] != 0 or any(
            second <= first for first, second in zip(elapsed, elapsed[1:], strict=False)
        ):
            errors.append("Elapsed time must start at zero and increase")
        if test_id == "network_registration":
            if (
                _number(rows[0], "registered") != 0
                or _number(rows[0], "sim_ready") != 0
                or _number(rows[-1], "registered") != 1
                or _number(rows[-1], "sim_ready") != 1
            ):
                errors.append("Network registration and SIM-ready transition missing")
        elif test_id in {"outgoing_call", "incoming_call"}:
            connected = [
                index
                for index, row in enumerate(rows)
                if _number(row, "connected") == 1
            ]
            if (
                len(connected) < 2
                or elapsed[connected[-1]] - elapsed[connected[0]] < 30
                or _number(rows[-1], "uplink_audio_samples")
                <= _number(rows[0], "uplink_audio_samples")
                or _number(rows[-1], "downlink_audio_samples")
                <= _number(rows[0], "downlink_audio_samples")
                or any(_number(row, "dropped") != 0 for row in rows)
            ):
                errors.append(
                    "Call lacks 30 s connected, advancing audio, or drop-free log"
                )
        elif test_id == "packet_data":
            if _number(rows[-1], "bytes_tx") <= _number(rows[0], "bytes_tx") or _number(
                rows[-1], "bytes_rx"
            ) <= _number(rows[0], "bytes_rx"):
                errors.append("Cellular transmit and receive bytes did not increase")
        elif test_id == "radio_kill":
            if (
                _number(rows[0], "radio_disabled") != 0
                or _number(rows[0], "registered") != 1
                or _number(rows[-1], "radio_disabled") != 1
                or _number(rows[-1], "registered") != 0
            ):
                errors.append("Radio kill did not clear an established registration")
        elif test_id == "emergency_lab_simulator":
            if (
                _number(rows[0], "emergency_route_pass") != 0
                or _number(rows[-1], "emergency_route_pass") != 1
            ):
                errors.append("Lab simulator did not show emergency route")
    except (KeyError, TypeError, ValueError) as error:
        errors.append(f"Unusable measurement: {error}")
    return errors


def audit(path: Path, root: Path) -> dict:
    """Validate controlled JSON and each raw CSV without claiming physical authenticity."""
    errors: list[str] = []
    try:
        bundle = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        return {"status": "fail", "errors": [f"Phone bundle unreadable: {error}"]}
    if not isinstance(bundle, dict):
        return {"status": "fail", "errors": ["Phone bundle must be an object"]}
    if bundle.get("schema_version") != 1 or bundle.get("device") != "slate-pocket-v1r":
        errors.append("Unknown phone bundle schema or device")
    for key in (*IDENTITY, "cellular_mpn", "modem_firmware_version", "carrier"):
        if not _text(bundle.get(key)):
            errors.append(f"Missing {key}")
    for key in (
        "configuration_sha256",
        "selected_bom_sha256",
        "cellular_design_sha256",
        "telephony_software_sha256",
    ):
        if not _digest(bundle.get(key)):
            errors.append(f"Invalid {key}")
    cases = bundle.get("tests")
    if (
        not isinstance(cases, list)
        or not all(isinstance(item, dict) for item in cases)
        or [item.get("id") for item in cases] != list(TESTS)
    ):
        errors.append("Phone tests must cover each required case once in order")
        cases = []
    controlled = (root / "validation/phone/test-results").resolve()
    seen_raw_paths = set()
    for case in cases:
        test_id = case["id"]
        if case.get("disposition") != "pass":
            errors.append(f"{test_id}: review disposition is not pass")
        if not _text(case.get("raw_path")) or not _digest(case.get("raw_sha256")):
            errors.append(f"{test_id}: missing raw path or SHA-256")
            continue
        raw = (root / case["raw_path"]).resolve()
        if raw in seen_raw_paths:
            errors.append(f"{test_id}: raw CSV was reused for another case")
            continue
        seen_raw_paths.add(raw)
        if not raw.is_relative_to(controlled) or raw.suffix.lower() != ".csv":
            errors.append(f"{test_id}: raw CSV is outside controlled test results")
            continue
        if (
            not raw.is_file()
            or hashlib.sha256(raw.read_bytes()).hexdigest() != case["raw_sha256"]
        ):
            errors.append(f"{test_id}: raw CSV missing or hash mismatch")
            continue
        try:
            with raw.open(encoding="utf-8-sig", newline="") as stream:
                reader = csv.DictReader(stream)
                if not set(FIELDS[test_id]).issubset(reader.fieldnames or []):
                    errors.append(f"{test_id}: required measurement columns missing")
                    continue
                rows = list(reader)
        except (OSError, UnicodeError, csv.Error) as error:
            errors.append(f"{test_id}: CSV unreadable: {error}")
            continue
        if any(row.get(key) != bundle.get(key) for row in rows for key in IDENTITY):
            errors.append(f"{test_id}: raw unit, build, or configuration differs")
            continue
        errors.extend(f"{test_id}: {item}" for item in _measure(test_id, rows))
    if bundle.get("emergency_method") != "authorized_lab_simulator":
        errors.append("Emergency behavior must use an authorized lab simulator")
    if not _text(bundle.get("emergency_lab_approval")):
        errors.append("Emergency simulator approval reference is missing")
    if not _text(bundle.get("regulatory_review_reference")):
        errors.append("Applicable regulatory review reference is missing")
    return {
        "status": "pass" if not errors else "fail",
        "errors": errors,
        "identity": {key: bundle.get(key) for key in IDENTITY},
        "cellular_mpn": bundle.get("cellular_mpn"),
        "selected_bom_sha256": bundle.get("selected_bom_sha256"),
        "cellular_design_sha256": bundle.get("cellular_design_sha256"),
        "telephony_software_sha256": bundle.get("telephony_software_sha256"),
        "tested_cases": [case["id"] for case in cases],
        "caveat": "CSV consistency and hashes do not authenticate a physical unit, carrier service, emergency handling, or regulatory approval; independent engineering review remains required.",
    }
