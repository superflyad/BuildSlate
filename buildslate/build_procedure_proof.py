"""Check controlled EVT0 assembly and first-power procedures.

These checks bind instructions and bench limits to one design revision. They
cannot establish that a physical unit was assembled or energized safely.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

from buildslate.firmware_proof import RELEASE as FIRMWARE
from buildslate.interconnect_proof import RELEASE as INTERCONNECT
from buildslate.mechanical_proof import ASSEMBLY as MECHANICAL
from buildslate.part_selection import RELEASE as SELECTED_BOM
from buildslate.power_safety_proof import RELEASE as POWER
from buildslate.thermal_proof import RELEASE as THERMAL

BOARD = Path("engineering/hardware/released/board.kicad_pcb")
BENCH_RELEASE = Path("engineering/hardware/released/assembly/bench-safety.json")
ASSEMBLY_RELEASE = Path(
    "engineering/hardware/released/assembly/assembly-procedure.json"
)
BENCH_SOURCES = {
    "selected_bom_sha256": SELECTED_BOM,
    "routed_pcb_sha256": BOARD,
    "power_safety_sha256": POWER,
    "firmware_bundle_sha256": FIRMWARE,
}
ASSEMBLY_SOURCES = {
    **BENCH_SOURCES,
    "mechanical_assembly_sha256": MECHANICAL,
    "interconnect_sha256": INTERCONNECT,
    "thermal_release_sha256": THERMAL,
    "bench_safety_sha256": BENCH_RELEASE,
}
STOP_KEYS = {
    "overvoltage_v",
    "overcurrent_a",
    "overtemperature_c",
    "telemetry_loss_s",
    "smoke_or_swelling",
}
STAGES = {
    "incoming_inspection": {"part_identity", "lot_traceability"},
    "pcba_inspection": {"shorts_and_polarity"},
    "first_power": {"supply_limits", "rail_sequence"},
    "isolated_programming": {"flash_readback"},
    "thermal_installation": {"interface_bondline"},
    "pack_fit_isolated": {"pack_insulation", "no_compression"},
    "interconnect_installation": {"pinout_and_retention"},
    "enclosure_closure": {"clearance_and_seal"},
    "integrated_power_check": {"supply_limits", "boot_and_radio_kill"},
    "final_inspection": {"configuration_hash", "defect_disposition"},
}
RECORD_FIELDS = {"operator_id", "time_utc", "measured_values", "disposition"}


def _text(value: object) -> bool:
    return (
        isinstance(value, str)
        and bool(value.strip())
        and value.strip().lower() not in {"tbd", "unknown", "placeholder", "none"}
    )


def _number(value: object) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _start(
    root: Path, release_path: Path, sources: dict[str, Path]
) -> tuple[dict | None, list[str]]:
    path = root / release_path
    if not path.is_file():
        return None, [f"No controlled release: {release_path.as_posix()}"]
    try:
        release = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        return None, [f"Release unreadable: {error}"]
    if not isinstance(release, dict):
        return None, ["Release must be a JSON object"]
    errors = []
    if (
        release.get("schema_version") != 1
        or release.get("device") != "slate-pocket-v1r"
    ):
        errors.append("Unknown release schema or device")
    for field in ("revision", "reviewed_by"):
        if not _text(release.get(field)):
            errors.append(f"Missing release {field}")
    for field, source in sources.items():
        path = root / source
        if not path.is_file():
            errors.append(f"Missing upstream file: {field}")
        elif release.get(field) != _sha(path):
            errors.append(f"Release is not bound to {field}")
    return release, errors


def audit_bench(root: Path) -> dict:
    """Check deenergized-pack first-power limits against the released power design."""
    if not (root / BENCH_RELEASE).is_file():
        return {"status": "missing", "errors": ["No released bench safety procedure"]}
    release, errors = _start(root, BENCH_RELEASE, BENCH_SOURCES)
    if release is None:
        return {"status": "fail", "errors": errors}
    power_path = root / POWER
    try:
        power = json.loads(power_path.read_text(encoding="utf-8"))
        limits = power["limits"]
    except (OSError, UnicodeError, json.JSONDecodeError, KeyError, TypeError) as error:
        return {
            "status": "fail",
            "errors": errors + [f"Power limits unreadable: {error}"],
        }
    required_limits = (
        "operating_min_v",
        "normal_charge_termination_v",
        "continuous_discharge_limit_a",
        "battery_overtemperature_trip_c",
    )
    if not isinstance(limits, dict) or any(
        not _number(limits.get(field)) for field in required_limits
    ):
        return {
            "status": "fail",
            "errors": errors + ["Released power limits incomplete"],
        }
    rails = power.get("rails") if isinstance(power, dict) else None
    sequence = power.get("rail_sequence") if isinstance(power, dict) else None
    if (
        not isinstance(rails, list)
        or not rails
        or not all(
            isinstance(item, dict)
            and _text(item.get("id"))
            and _number(item.get("voltage_v"))
            and item["voltage_v"] > 0
            for item in rails
        )
        or not isinstance(sequence, list)
        or len(sequence) != len(rails)
        or not all(_text(item) for item in sequence)
        or len(set(sequence)) != len(sequence)
        or set(sequence) != {item["id"] for item in rails}
    ):
        return {
            "status": "fail",
            "errors": errors + ["Released rail sequence incomplete"],
        }
    if release.get("rail_sequence") != sequence:
        errors.append("Bench rail sequence differs from the released power design")
    measurements = release.get("rail_measurements")
    if not isinstance(measurements, dict) or set(measurements) != set(sequence):
        errors.append("First-power rail measurements are incomplete")
    else:
        for rail in rails:
            item = measurements[rail["id"]]
            if (
                not isinstance(item, dict)
                or any(
                    not _number(item.get(field))
                    for field in ("min_v", "max_v", "settle_timeout_ms")
                )
                or not 0 < item["min_v"] <= rail["voltage_v"] <= item["max_v"]
                or item["settle_timeout_ms"] <= 0
            ):
                errors.append(f"Rail {rail['id']} has no valid measurement window")
    supply = release.get("supply")
    if not isinstance(supply, dict):
        return {
            "status": "fail",
            "errors": errors + ["Isolated supply contract missing"],
        }
    if (
        supply.get("mode") != "isolated_battery_emulator"
        or supply.get("pack_connected") is not False
        or supply.get("charging_enabled") is not False
        or supply.get("radio_enabled") is not False
        or supply.get("wireless_enabled") is not False
    ):
        errors.append("First power must isolate the pack, charge path, and radios")
    numeric_supply = (
        "min_voltage_v",
        "max_voltage_v",
        "current_limit_a",
        "overtemperature_stop_c",
    )
    if any(not _number(supply.get(field)) for field in numeric_supply):
        errors.append("Supply voltage, current, or temperature limits missing")
    elif not (
        limits["operating_min_v"]
        <= supply["min_voltage_v"]
        < supply["max_voltage_v"]
        <= limits["normal_charge_termination_v"]
        and 0 < supply["current_limit_a"] <= limits["continuous_discharge_limit_a"]
        and 0
        < supply["overtemperature_stop_c"]
        <= limits["battery_overtemperature_trip_c"]
    ):
        errors.append("Bench supply exceeds the approved power limits")
    stops = release.get("hard_stops")
    if not isinstance(stops, dict) or set(stops) != STOP_KEYS:
        errors.append("First-power hard stops are incomplete")
    elif (
        any(
            not _number(stops.get(field)) for field in STOP_KEYS - {"smoke_or_swelling"}
        )
        or stops["smoke_or_swelling"] is not True
    ):
        errors.append("First-power hard stops have invalid thresholds")
    elif all(_number(supply.get(field)) for field in numeric_supply) and not (
        0 < stops["overvoltage_v"] <= supply["max_voltage_v"]
        and 0 < stops["overcurrent_a"] <= supply["current_limit_a"]
        and 0 < stops["overtemperature_c"] <= supply["overtemperature_stop_c"]
        and 0 < stops["telemetry_loss_s"] <= 5
    ):
        errors.append("Hard-stop thresholds exceed bench supply limits")
    instruments = release.get("instrumentation")
    if not isinstance(instruments, dict) or set(instruments) != {
        "voltage",
        "current",
        "temperature",
    }:
        errors.append("Voltage, current, and temperature instruments are required")
    else:
        for role, instrument in instruments.items():
            if (
                not isinstance(instrument, dict)
                or not _text(instrument.get("model"))
                or not _text(instrument.get("calibration_id"))
                or not _number(instrument.get("sample_period_s"))
                or instrument["sample_period_s"] <= 0
            ):
                errors.append(f"{role} instrumentation is incomplete")
    emergency = release.get("emergency")
    if (
        not isinstance(emergency, dict)
        or any(
            not _text(emergency.get(field))
            for field in ("disconnect_method", "quarantine_location", "operator_role")
        )
        or emergency.get("witness_required") is not True
        or not _number(emergency.get("response_time_s"))
        or not 0 < emergency["response_time_s"] <= 5
    ):
        errors.append("Emergency disconnect and quarantine procedure incomplete")
    return {
        "status": "pass" if not errors else "fail",
        "errors": errors,
        "revision": release.get("revision"),
        "reviewed_by": release.get("reviewed_by"),
        **{key: release.get(key) for key in BENCH_SOURCES},
        "supply": supply,
        "hard_stops": stops,
        "rail_sequence": release.get("rail_sequence"),
        "rails_checked": len(rails),
        "caveat": "Limit and instrument records require engineering review and physical fault testing.",
    }


def audit_assembly(root: Path) -> dict:
    """Check ordered instructions, inspection criteria, and exact design bindings."""
    if not (root / ASSEMBLY_RELEASE).is_file():
        return {"status": "missing", "errors": ["No released assembly procedure"]}
    release, errors = _start(root, ASSEMBLY_RELEASE, ASSEMBLY_SOURCES)
    if release is None:
        return {"status": "fail", "errors": errors}
    bench = audit_bench(root)
    if bench["status"] != "pass":
        errors.append("Assembly first-power step lacks a passing bench safety proof")
    operations = release.get("operations")
    if not isinstance(operations, list) or [
        item.get("id") if isinstance(item, dict) else None for item in operations
    ] != list(STAGES):
        errors.append("Assembly stages must be complete, unique, and in build order")
        operations = []
    for operation in operations:
        stage = operation["id"]
        if (
            not _text(operation.get("instruction"))
            or not _text(operation.get("operator_role"))
            or operation.get("hold_on_failure") is not True
            or not isinstance(operation.get("tools"), list)
            or not operation["tools"]
            or not all(_text(item) for item in operation["tools"])
            or not isinstance(operation.get("record_fields"), list)
            or not all(_text(item) for item in operation["record_fields"])
            or not RECORD_FIELDS.issubset(operation["record_fields"])
        ):
            errors.append(
                f"{stage}: instruction, tools, hold, or record fields missing"
            )
        inspections = operation.get("inspections")
        if not isinstance(inspections, list) or not all(
            isinstance(item, dict) for item in inspections
        ):
            errors.append(f"{stage}: inspections missing")
            continue
        names = [item.get("id") for item in inspections]
        evidence_fields = [item.get("evidence_field") for item in inspections]
        if (
            not all(_text(name) for name in names)
            or len(names) != len(set(name for name in names if _text(name)))
            or not STAGES[stage].issubset(names)
            or not all(_text(name) for name in evidence_fields)
            or len(evidence_fields) != len(set(evidence_fields))
        ):
            errors.append(f"{stage}: required inspection coverage missing")
        for inspection in inspections:
            acceptance = inspection.get("acceptance")
            if (
                not _text(inspection.get("id"))
                or not _text(inspection.get("method"))
                or not _text(inspection.get("evidence_field"))
                or not isinstance(acceptance, dict)
            ):
                errors.append(f"{stage}: inspection lacks a measurable record")
                continue
            if acceptance.get("kind") == "range":
                if (
                    not _text(acceptance.get("unit"))
                    or not _number(acceptance.get("min"))
                    or not _number(acceptance.get("max"))
                    or acceptance["min"] >= acceptance["max"]
                ):
                    errors.append(f"{stage}: invalid numeric acceptance range")
            elif acceptance.get("kind") == "binary":
                if acceptance.get("expected") is not True:
                    errors.append(f"{stage}: binary acceptance must require a pass")
            else:
                errors.append(f"{stage}: unknown acceptance method")
        if (
            stage in {"first_power", "integrated_power_check"}
            and bench["status"] == "pass"
        ):
            current = next(
                (item for item in inspections if item.get("id") == "supply_limits"),
                None,
            )
            acceptance = current.get("acceptance") if current else None
            if (
                not isinstance(acceptance, dict)
                or acceptance.get("kind") != "range"
                or acceptance.get("unit") != "A"
                or not _number(acceptance.get("min"))
                or not _number(acceptance.get("max"))
                or acceptance["min"] < 0
                or acceptance["max"] <= 0
                or acceptance["max"] > bench["supply"]["current_limit_a"]
            ):
                errors.append("First-power current acceptance exceeds bench limit")
    return {
        "status": "pass" if not errors else "fail",
        "errors": errors,
        "revision": release.get("revision"),
        "reviewed_by": release.get("reviewed_by"),
        **{key: release.get(key) for key in ASSEMBLY_SOURCES},
        "stages": [item.get("id") for item in operations],
        "caveat": "Procedure completeness does not prove tooling, workmanship, or a built unit.",
    }
