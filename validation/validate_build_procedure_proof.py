"""Exercise the assembly and first-power release gates with fault fixtures."""

from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from buildslate.build_procedure_proof import (  # noqa: E402
    ASSEMBLY_RELEASE,
    ASSEMBLY_SOURCES,
    BENCH_RELEASE,
    BENCH_SOURCES,
    RECORD_FIELDS,
    STAGES,
    audit_assembly,
    audit_bench,
)
from buildslate.hardware_readiness import _evidence_result  # noqa: E402


def _write(path: Path, value: object) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _release(root: Path, source: dict[str, Path]) -> dict:
    return {
        "schema_version": 1,
        "device": "slate-pocket-v1r",
        "revision": "EVT0-A",
        "reviewed_by": "fixture engineering reviewer",
        **{
            field: hashlib.sha256((root / path).read_bytes()).hexdigest()
            for field, path in source.items()
        },
    }


def _fixtures(root: Path) -> tuple[dict, dict]:
    for path in set(ASSEMBLY_SOURCES.values()) - {BENCH_RELEASE}:
        value: object = {"revision": "EVT0-A"}
        if path == BENCH_SOURCES["power_safety_sha256"]:
            value = {
                "limits": {
                    "operating_min_v": 3.0,
                    "normal_charge_termination_v": 4.2,
                    "continuous_discharge_limit_a": 5.0,
                    "battery_overtemperature_trip_c": 60.0,
                },
                "rails": [
                    {"id": "system", "voltage_v": 3.3},
                    {"id": "logic", "voltage_v": 1.8},
                ],
                "rail_sequence": ["system", "logic"],
            }
        _write(root / path, value)
    bench = {
        **_release(root, BENCH_SOURCES),
        "supply": {
            "mode": "isolated_battery_emulator",
            "pack_connected": False,
            "charging_enabled": False,
            "radio_enabled": False,
            "wireless_enabled": False,
            "min_voltage_v": 3.2,
            "max_voltage_v": 4.1,
            "current_limit_a": 2.0,
            "overtemperature_stop_c": 50.0,
        },
        "hard_stops": {
            "overvoltage_v": 4.0,
            "overcurrent_a": 1.8,
            "overtemperature_c": 45.0,
            "telemetry_loss_s": 2.0,
            "smoke_or_swelling": True,
        },
        "rail_sequence": ["system", "logic"],
        "rail_measurements": {
            "system": {"min_v": 3.2, "max_v": 3.4, "settle_timeout_ms": 100.0},
            "logic": {"min_v": 1.75, "max_v": 1.85, "settle_timeout_ms": 100.0},
        },
        "instrumentation": {
            role: {
                "model": f"fixture {role} instrument",
                "calibration_id": f"CAL-{role}",
                "sample_period_s": 0.1,
            }
            for role in ("voltage", "current", "temperature")
        },
        "emergency": {
            "disconnect_method": "Isolate bench output using accessible emergency switch",
            "quarantine_location": "Designated fire-safe bench quarantine area",
            "operator_role": "trained EVT0 operator",
            "witness_required": True,
            "response_time_s": 2.0,
        },
    }
    _write(root / BENCH_RELEASE, bench)
    assembly = {
        **_release(root, ASSEMBLY_SOURCES),
        "operations": [],
    }
    for stage, required in STAGES.items():
        inspections = [
            {
                "id": identifier,
                "method": f"Record and review {identifier}",
                "evidence_field": f"{stage}.{identifier}",
                "acceptance": {"kind": "binary", "expected": True},
            }
            for identifier in sorted(required)
        ]
        if stage in {"first_power", "integrated_power_check"}:
            next(item for item in inspections if item["id"] == "supply_limits")[
                "acceptance"
            ] = {"kind": "range", "unit": "A", "min": 0.0, "max": 1.8}
        if stage == "thermal_installation":
            inspections[0]["acceptance"] = {
                "kind": "range",
                "unit": "mm",
                "min": 0.05,
                "max": 0.2,
            }
        assembly["operations"].append(
            {
                "id": stage,
                "instruction": f"Controlled {stage} work instruction at EVT0-A",
                "operator_role": "trained EVT0 operator",
                "tools": [f"fixture tool for {stage}"],
                "record_fields": sorted(RECORD_FIELDS),
                "hold_on_failure": True,
                "inspections": inspections,
            }
        )
    _write(root / ASSEMBLY_RELEASE, assembly)
    return bench, assembly


def _record(root: Path, path: Path) -> dict:
    return {
        "path": path.as_posix(),
        "sha256": hashlib.sha256((root / path).read_bytes()).hexdigest(),
        "revision": "EVT0-A",
        "reviewed_by": "fixture engineering reviewer",
        "disposition": "approved",
    }


def main() -> int:
    if audit_bench(ROOT)["status"] != "missing":
        raise ValueError("Public repository implies a released bench procedure")
    if audit_assembly(ROOT)["status"] != "missing":
        raise ValueError("Public repository implies a released assembly procedure")
    with TemporaryDirectory() as temp:
        root = Path(temp)
        bench, assembly = _fixtures(root)
        if audit_bench(root)["status"] != "pass":
            raise ValueError("Valid isolated first-power fixture was rejected")
        if audit_assembly(root)["status"] != "pass":
            raise ValueError("Valid ordered assembly fixture was rejected")
        upstream = {
            identifier: _record(root, path)
            for identifier, path in {
                "selected_bom": BENCH_SOURCES["selected_bom_sha256"],
                "routed_pcb": BENCH_SOURCES["routed_pcb_sha256"],
                "power_safety": BENCH_SOURCES["power_safety_sha256"],
                "firmware_boot": BENCH_SOURCES["firmware_bundle_sha256"],
                "mechanical_release": ASSEMBLY_SOURCES["mechanical_assembly_sha256"],
                "interconnect": ASSEMBLY_SOURCES["interconnect_sha256"],
                "thermal_release": ASSEMBLY_SOURCES["thermal_release_sha256"],
                "bench_safety": BENCH_RELEASE,
            }.items()
        }
        selection = {
            "status": "pass",
            "sha256": upstream["selected_bom"]["sha256"],
        }
        for identifier, path in (
            ("bench_safety", BENCH_RELEASE),
            ("assembly_release", ASSEMBLY_RELEASE),
        ):
            result = _evidence_result(
                root,
                {"id": identifier, "stage": "design_release"},
                _record(root, path),
                selection,
                upstream,
            )
            if result["status"] != "accepted":
                raise ValueError(f"Valid {identifier} evidence rejected: {result}")
        unapproved = copy.deepcopy(upstream)
        unapproved["power_safety"]["disposition"] = "draft"
        if (
            _evidence_result(
                root,
                {"id": "bench_safety", "stage": "design_release"},
                _record(root, BENCH_RELEASE),
                selection,
                unapproved,
            )["status"]
            != "rejected"
        ):
            raise ValueError("Bench procedure accepted an unapproved power design")
        unapproved = copy.deepcopy(upstream)
        unapproved["bench_safety"]["disposition"] = "draft"
        if (
            _evidence_result(
                root,
                {"id": "assembly_release", "stage": "design_release"},
                _record(root, ASSEMBLY_RELEASE),
                selection,
                unapproved,
            )["status"]
            != "rejected"
        ):
            raise ValueError(
                "Assembly procedure accepted an unapproved bench procedure"
            )
        arbitrary = ASSEMBLY_RELEASE.parent / "arbitrary.pdf"
        (root / arbitrary).write_bytes(b"unstructured document")
        if (
            _evidence_result(
                root,
                {"id": "assembly_release", "stage": "design_release"},
                _record(root, arbitrary),
                selection,
                upstream,
            )["status"]
            != "rejected"
        ):
            raise ValueError("Hash-matched arbitrary PDF cleared assembly release")
        for change in (
            lambda value: value["supply"].update({"pack_connected": True}),
            lambda value: value["supply"].update({"current_limit_a": 6.0}),
            lambda value: value["hard_stops"].update({"overcurrent_a": 5.0}),
            lambda value: value["instrumentation"].pop("temperature"),
            lambda value: value["rail_sequence"].reverse(),
            lambda value: value["rail_measurements"].pop("logic"),
        ):
            mutant = copy.deepcopy(bench)
            change(mutant)
            _write(root / BENCH_RELEASE, mutant)
            if audit_bench(root)["status"] != "fail":
                raise ValueError("Unsafe first-power procedure passed")
        _write(root / BENCH_RELEASE, bench)
        for change in (
            lambda value: value["operations"].reverse(),
            lambda value: value["operations"][0]["inspections"].clear(),
            lambda value: next(
                item for item in value["operations"] if item["id"] == "first_power"
            )["inspections"][1]["acceptance"].update({"max": 3.0}),
            lambda value: value.update({"routed_pcb_sha256": "0" * 64}),
        ):
            mutant = copy.deepcopy(assembly)
            change(mutant)
            _write(root / ASSEMBLY_RELEASE, mutant)
            if audit_assembly(root)["status"] != "fail":
                raise ValueError("Invalid assembly procedure passed")
    print("PASS: assembly order, first-power limits, hashes, and gate bindings")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
