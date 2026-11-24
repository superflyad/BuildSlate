#!/usr/bin/env python3
"""Validate EVT0 evidence ingestion, metrics, correlations, and objective gates."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from buildslate.evt0 import EVT0CampaignRepository, _coherent_coverage
from buildslate.io import dump_yaml, load_yaml


def passed(message: str) -> None:
    print(f"PASS: {message}")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)
    passed(message)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def create_bundle(root: Path, maximum_skin_c: float = 40.0) -> Path:
    bundle = root / "synthetic-validation-bundle"
    (bundle / "raw").mkdir(parents=True)
    (bundle / "calibrations").mkdir()
    raw_path = bundle / "raw" / "telemetry.csv"
    raw_path.write_text(
        "elapsed_s,system_power_w,work_units_completed,compute_rail_voltage_v,compute_rail_current_a,TC_REAR_SOC,TC_FRONT_SOC,TC_FRONT_CENTER,TC_REAR_CHARGER,TC_EDGE_LEFT,TC_EDGE_RIGHT,TC_REAR_BATTERY,unexpected_resets,protection_faults\n"
        f"0,10,0,1,1,30,30,30,30,29,29,28,0,0\n3600,20,100,1,1,{maximum_skin_c},39,38,37,36,35,35,0,0\n",
        encoding="utf-8",
        newline="\n",
    )
    certificate_path = bundle / "calibrations" / "CAL-VALIDATION.txt"
    certificate_path.write_text(
        "synthetic calibration certificate for validator only\n",
        encoding="utf-8",
        newline="\n",
    )
    required_channels = EVT0CampaignRepository(REPO_ROOT).required_channels("P10")
    calibration = {
        "schema_version": 1,
        "calibration_id": "CAL-VALIDATION",
        "instrument_id": "SYNTHETIC-INSTRUMENT",
        "valid_from_utc": "2026-01-01T00:00:00Z",
        "valid_until_utc": "2027-01-01T00:00:00Z",
        "channels": list(required_channels),
        "certificate": {
            "path": "calibrations/CAL-VALIDATION.txt",
            "sha256": sha256(certificate_path),
        },
        "uncertainty_note": "synthetic validator fixture; not engineering evidence",
    }
    (bundle / "calibrations" / "CAL-VALIDATION.yaml").write_text(
        dump_yaml(calibration), encoding="utf-8", newline="\n"
    )
    manifest: dict[str, Any] = {
        "schema_version": 1,
        "campaign_id": "SYNTHETIC-VALIDATION",
        "unit_id": "UNIT-VALIDATION",
        "build_id": "BUILD-VALIDATION",
        "run_id": "RUN-P10",
        "test_id": "P10",
        "start_time_utc": "2026-06-01T12:00:00Z",
        "operator_ids": ["validator"],
        "configuration": {
            "bom_revision": "synthetic",
            "board_revision": "synthetic",
            "enclosure_revision": "synthetic",
            "thermal_stack_revision": "synthetic",
            "firmware_hash": "0" * 64,
            "configuration_hash": "1" * 64,
        },
        "workload": {
            "workload_id": "W10_ai_reference_70b_4bit",
            "definition_revision": "synthetic",
            "artifact_hashes": ["2" * 64],
            "command_line": "synthetic-validator-command",
            "random_seeds": [1],
        },
        "instrumentation": {
            "channel_map_revision": "synthetic",
            "calibration_ids": ["CAL-VALIDATION"],
            "synchronization_method": "synthetic common clock",
        },
        "environment": {
            "ambient_c": 25.0,
            "humidity_percent": 50.0,
            "condition": "open_air",
            "orientation": "flat",
        },
        "approved_limits_revision": "synthetic-validator-only",
        "notes": "This temporary fixture is not a physical measurement.",
    }
    result = {
        "schema_version": 1,
        "manifest_path": "manifest.yaml",
        "raw_data": [
            {
                "path": "raw/telemetry.csv",
                "sha256": sha256(raw_path),
                "format": "csv",
                "source": "synthetic validator",
            }
        ],
        "time_range_utc": {
            "start": "2026-06-01T12:00:00Z",
            "end": "2026-06-01T13:00:00Z",
        },
        "required_channel_status": {channel: True for channel in required_channels},
        "metrics": {},
        "hard_stop_events": [],
        "validity": "valid",
        "disposition": "pass",
        "invalidation_reasons": [],
        "requirement_trades": [],
        "analysis_artifacts": [],
        "deviations": [],
        "model_correlations": [
            {
                "model_id": "synthetic-power-model",
                "metric_id": "mean_system_power_w",
                "predicted": 14.0,
                "measured": 15.0,
                "unit": "W",
                "tolerance_absolute": 2.0,
            }
        ],
        "reviewers": ["validator"],
        "notes": "Temporary synthetic fixture only.",
    }
    (bundle / "manifest.yaml").write_text(
        dump_yaml(manifest), encoding="utf-8", newline="\n"
    )
    (bundle / "result.yaml").write_text(
        dump_yaml(result), encoding="utf-8", newline="\n"
    )
    return bundle


def copy_engine_inputs(destination_root: Path) -> None:
    evt_destination = destination_root / "validation/evt0"
    evt_destination.mkdir(parents=True)
    for name in ("test-matrix.yaml", "instrumentation.yaml", "metric-definitions.yaml"):
        shutil.copy2(REPO_ROOT / "validation/evt0" / name, evt_destination / name)
    shutil.copytree(REPO_ROOT / "validation/evt0/schemas", evt_destination / "schemas")
    (evt_destination / "campaigns").mkdir()


def main() -> int:
    repository = EVT0CampaignRepository(REPO_ROOT)
    current = repository.build_campaign_report()
    require(
        current["summary"]["ingested_run_count"]
        == len(list(repository.campaign_root.glob("*/*/receipt.yaml"))),
        "campaign run count matches preserved receipts",
    )
    require(
        current["EVT0_CAMPAIGN_GATE"] != "EMPTY_CAMPAIGN"
        or current["summary"]["passing_required_test_count"] == 0,
        "empty campaign cannot claim passing measurements",
    )
    require(
        load_yaml(REPO_ROOT / "reports/program/evt0-campaign.yaml") == current,
        "generated EVT0 campaign report is deterministic and current",
    )
    required = set(repository.matrix["required_for_evt0_evidence_gate"])
    split_units = [
        {
            "campaign_id": "C1",
            "unit_id": f"U{index}",
            "build_id": "B1",
            "configuration_sha256": "a" * 64,
            "test_id": test_id,
            "objective_disposition": "VALID_PASS",
        }
        for index, test_id in enumerate(sorted(required))
    ]
    _, credited, groups = _coherent_coverage(split_units, required)
    require(
        len(credited) == 1 and len(groups) == len(required),
        "passing tests on different physical units cannot complete EVT0",
    )
    coherent = [{**item, "unit_id": "U1"} for item in split_units]
    selected, credited, _ = _coherent_coverage(coherent, required)
    require(
        credited == required and selected["unit_id"] == "U1",
        "one serialized unit can cover the full required test set",
    )
    mixed_build = [
        {**item, "build_id": "B2" if index % 2 else "B1"}
        for index, item in enumerate(coherent)
    ]
    _, credited, _ = _coherent_coverage(mixed_build, required)
    require(
        len(credited) < len(required),
        "tests across build revisions cannot be pooled",
    )
    mixed_configuration = [
        {**item, "configuration_sha256": "b" * 64 if index % 2 else "a" * 64}
        for index, item in enumerate(coherent)
    ]
    _, credited, _ = _coherent_coverage(mixed_configuration, required)
    require(
        len(credited) < len(required),
        "tests across configuration revisions cannot be pooled",
    )
    require(
        set(repository.objective_measurements) == required,
        "every required EVT0 test has an objective measurement contract",
    )
    for name in ("calibration.schema.yaml", "deviation.schema.yaml"):
        require(
            (REPO_ROOT / "validation/evt0/schemas" / name).is_file(),
            f"EVT0 schema exists: {name}",
        )

    with tempfile.TemporaryDirectory() as temp_directory:
        temporary = Path(temp_directory)
        bundle = create_bundle(temporary)
        review = repository.review_bundle(bundle)
        require(
            review["integrity_errors"] == [],
            "synthetic fixture passes structural, hash, and calibration checks",
        )
        require(
            review["objective_disposition"] == "VALID_PASS",
            "objective disposition preserves a valid synthetic pass",
        )
        require(
            review["calculated_metrics"]["energy_consumed_wh"]["value"] == 15.0,
            "energy metric is calculated from raw CSV",
        )
        require(
            review["calculated_metrics"]["performance_per_watt"]["value"] == 0.001852,
            "performance-per-watt is calculated from raw CSV",
        )
        require(
            review["model_correlations"][0]["residual"] == 1.0
            and review["model_correlations"][0]["passed"],
            "model residual and tolerance decision are calculated",
        )

        invalid_result = load_yaml(bundle / "result.yaml")
        invalid_result["reviewers"] = []
        (bundle / "result.yaml").write_text(
            dump_yaml(invalid_result), encoding="utf-8", newline="\n"
        )
        require(
            repository.review_bundle(bundle)["objective_disposition"]
            == "REJECTED_INVALID_EVIDENCE",
            "unreviewed passing result is rejected",
        )
        invalid_result["reviewers"] = ["validator"]
        invalid_result["time_range_utc"]["end"] = "2026-06-01T12:00:10Z"
        (bundle / "result.yaml").write_text(
            dump_yaml(invalid_result), encoding="utf-8", newline="\n"
        )
        require(
            any(
                "raw duration differs" in error
                for error in repository.review_bundle(bundle)["integrity_errors"]
            ),
            "declared result duration cannot hide a short raw capture",
        )
        invalid_result["time_range_utc"]["end"] = "2026-06-01T13:00:00Z"
        invalid_result["unreviewed_extra_field"] = "not allowed"
        (bundle / "result.yaml").write_text(
            dump_yaml(invalid_result), encoding="utf-8", newline="\n"
        )
        require(
            any(
                "test-result schema" in error
                for error in repository.review_bundle(bundle)["integrity_errors"]
            ),
            "result schema rejects unrecognized evidence fields",
        )
        invalid_result.pop("unreviewed_extra_field")
        invalid_result["deviations"] = [{"deviation_id": "INCOMPLETE"}]
        (bundle / "result.yaml").write_text(
            dump_yaml(invalid_result), encoding="utf-8", newline="\n"
        )
        require(
            any(
                "deviations" in error and "test-result schema" in error
                for error in repository.review_bundle(bundle)["integrity_errors"]
            ),
            "local deviation schema is enforced during bundle review",
        )
        invalid_result["deviations"] = []
        (bundle / "result.yaml").write_text(
            dump_yaml(invalid_result), encoding="utf-8", newline="\n"
        )
        calibration_path = bundle / "calibrations/CAL-VALIDATION.yaml"
        calibration = load_yaml(calibration_path)
        calibration["unexpected_field"] = True
        calibration_path.write_text(
            dump_yaml(calibration), encoding="utf-8", newline="\n"
        )
        require(
            any(
                "calibration schema" in error
                for error in repository.review_bundle(bundle)["integrity_errors"]
            ),
            "calibration schema rejects unreviewed fields",
        )
        calibration.pop("unexpected_field")
        calibration_path.write_text(
            dump_yaml(calibration), encoding="utf-8", newline="\n"
        )

        temp_repo = temporary / "repo"
        copy_engine_inputs(temp_repo)
        temp_repository = EVT0CampaignRepository(temp_repo)
        receipt, _ = temp_repository.ingest(
            bundle, "2026-06-02T12:00:00Z", "validation-operator"
        )
        require(receipt.is_file(), "valid EVT0 bundle is preserved with a receipt")
        report = temp_repository.build_campaign_report()
        require(
            report["EVT0_CAMPAIGN_GATE"] == "CAMPAIGN_INCOMPLETE",
            "one passing run cannot satisfy the campaign gate",
        )
        require(
            "P10" not in report["missing_or_nonpassing_required_tests"],
            "passing test is credited without claiming campaign completion",
        )
        require(
            report["coherent_evidence_group"]["unit_id"] == "UNIT-VALIDATION",
            "campaign report identifies the physical unit behind credited tests",
        )

        preserved_raw = receipt.parent / "raw/telemetry.csv"
        preserved_raw.write_text("tampered\n", encoding="utf-8", newline="\n")
        require(
            temp_repository.build_campaign_report()["EVT0_CAMPAIGN_GATE"]
            == "BLOCKED_INVALID_EVIDENCE",
            "post-ingestion hash tampering blocks the campaign",
        )

    with tempfile.TemporaryDirectory() as temp_directory:
        hot_bundle = create_bundle(Path(temp_directory), maximum_skin_c=44.0)
        hot_review = repository.review_bundle(hot_bundle)
        require(
            hot_review["objective_disposition"] == "REJECTED_INVALID_EVIDENCE",
            "reported pass cannot override calculated skin hard stop",
        )
        require(
            "maximum_skin_c" in hot_review["calculated_limit_events"],
            "calculated hard-stop cause is explicit",
        )

    with tempfile.TemporaryDirectory() as temp_directory:
        root = Path(temp_directory)
        for test_id in sorted(required - {"P10", "I20"}):
            bundle = create_bundle(root / test_id)
            manifest_path = bundle / "manifest.yaml"
            manifest = load_yaml(manifest_path)
            manifest["test_id"] = test_id
            manifest["workload"]["workload_id"] = next(
                item["workload"]
                for item in repository.matrix["sequence"]
                if item["id"] == test_id
            )
            manifest_path.write_text(
                dump_yaml(manifest), encoding="utf-8", newline="\n"
            )
            review = repository.review_bundle(bundle)
            require(
                review["objective_disposition"] == "REJECTED_INVALID_EVIDENCE"
                and any(
                    "required columns" in error or "hash-verified analysis" in error
                    for error in review["integrity_errors"]
                ),
                f"{test_id} cannot reuse unrelated P10 telemetry as a pass",
            )

    with tempfile.TemporaryDirectory() as temp_directory:
        interface_bundle = create_bundle(Path(temp_directory))
        manifest_path = interface_bundle / "manifest.yaml"
        manifest = load_yaml(manifest_path)
        manifest["test_id"] = "I20"
        manifest["run_id"] = "RUN-I20"
        manifest["workload"]["workload_id"] = "none"
        manifest_path.write_text(dump_yaml(manifest), encoding="utf-8", newline="\n")
        result_path = interface_bundle / "result.yaml"
        result = load_yaml(result_path)
        result["time_range_utc"]["end"] = "2026-06-01T12:00:10Z"
        for channel in repository.required_channels("I20"):
            result["required_channel_status"][channel] = True
        result_path.write_text(dump_yaml(result), encoding="utf-8", newline="\n")
        review = repository.review_bundle(interface_bundle)
        require(
            review["objective_disposition"] == "REJECTED_INVALID_EVIDENCE"
            and any("display_frames" in error for error in review["integrity_errors"]),
            "interface test cannot pass without raw activity counters",
        )
        raw_path = interface_bundle / "raw/telemetry.csv"
        counter_names = (
            "display_frames",
            "touch_events",
            "camera_frames",
            "audio_playback_samples",
            "audio_capture_samples",
            "usb_bytes_tx",
            "usb_bytes_rx",
        )
        raw_path.write_text(
            "elapsed_s,"
            + ",".join(counter_names)
            + "\n"
            + "0,"
            + ",".join("0" for _ in counter_names)
            + "\n"
            + "10,"
            + ",".join("10" for _ in counter_names)
            + "\n",
            encoding="utf-8",
            newline="\n",
        )
        result["raw_data"][0]["sha256"] = sha256(raw_path)
        result_path.write_text(dump_yaml(result), encoding="utf-8", newline="\n")
        calibration_path = interface_bundle / "calibrations/CAL-VALIDATION.yaml"
        calibration = load_yaml(calibration_path)
        calibration["channels"] = sorted(
            set(calibration["channels"]) | set(repository.required_channels("I20"))
        )
        calibration_path.write_text(
            dump_yaml(calibration), encoding="utf-8", newline="\n"
        )
        review = repository.review_bundle(interface_bundle)
        require(
            review["objective_disposition"] == "VALID_PASS"
            and all(value == 10 for value in review["interface_activity"].values()),
            "interface activity is calculated from hash-verified raw CSV",
        )

    with tempfile.TemporaryDirectory() as temp_directory:
        charge_bundle = create_bundle(Path(temp_directory))
        manifest_path = charge_bundle / "manifest.yaml"
        manifest = load_yaml(manifest_path)
        manifest["test_id"] = "B50"
        manifest["workload"]["workload_id"] = "W00_idle_baseline"
        manifest_path.write_text(dump_yaml(manifest), encoding="utf-8", newline="\n")
        raw_path = charge_bundle / "raw/telemetry.csv"
        raw_path.write_text(
            "elapsed_s,state_of_charge_percent,input_voltage_v,input_current_a,TC_REAR_BATTERY,charge_faults\n"
            "0,20,20,1,28,0\n600,40,20,1,32,0\n",
            encoding="utf-8",
            newline="\n",
        )
        result_path = charge_bundle / "result.yaml"
        result = load_yaml(result_path)
        result["time_range_utc"]["end"] = "2026-06-01T12:10:00Z"
        result["raw_data"][0]["sha256"] = sha256(raw_path)
        result_path.write_text(dump_yaml(result), encoding="utf-8", newline="\n")
        require(
            repository.review_bundle(charge_bundle)["objective_disposition"]
            == "VALID_PASS",
            "hash-verified charging trace within the 30 W EVT cap is reviewable",
        )
        raw_path.write_text(
            "elapsed_s,state_of_charge_percent,input_voltage_v,input_current_a,TC_REAR_BATTERY,charge_faults\n"
            "0,20,20,2,28,0\n600,40,20,2,32,0\n",
            encoding="utf-8",
            newline="\n",
        )
        result["raw_data"][0]["sha256"] = sha256(raw_path)
        result_path.write_text(dump_yaml(result), encoding="utf-8", newline="\n")
        require(
            any(
                "exceeds the EVT cap" in error
                for error in repository.review_bundle(charge_bundle)["integrity_errors"]
            ),
            "charging above the 30 W EVT cap cannot be reported as pass",
        )

    with tempfile.TemporaryDirectory() as temp_directory:
        memory_bundle = create_bundle(Path(temp_directory))
        manifest_path = memory_bundle / "manifest.yaml"
        manifest = load_yaml(manifest_path)
        manifest["test_id"] = "M20"
        manifest["workload"]["workload_id"] = "W20_memory_capacity_and_bandwidth"
        manifest_path.write_text(dump_yaml(manifest), encoding="utf-8", newline="\n")
        raw_path = memory_bundle / "raw/telemetry.csv"
        raw_path.write_text(
            "elapsed_s,installed_bytes,usable_bytes,allocated_bytes,memory_errors,work_units_completed\n"
            "0,128000000000,120000000000,1000000000,0,0\n"
            "10,128000000000,120000000000,103079215104,0,25165824\n",
            encoding="utf-8",
            newline="\n",
        )
        probe_path = memory_bundle / "analysis/memory-probe.json"
        probe_path.parent.mkdir(parents=True, exist_ok=True)
        probe = {
            "status": "pass",
            "unit_id": "UNIT-VALIDATION",
            "build_id": "BUILD-VALIDATION",
            "os_name": "Linux",
            "os_total_physical_bytes": 120000000000,
            "allocated_bytes": 103079215104,
            "resident_delta_bytes": 103079215104,
            "verified_pages": 25165824,
            "memory_errors": 0,
            "swap_used_delta_bytes": 0,
        }
        probe_path.write_text(json.dumps(probe), encoding="utf-8")
        result_path = memory_bundle / "result.yaml"
        result = load_yaml(result_path)
        result["time_range_utc"]["end"] = "2026-06-01T12:00:10Z"
        result["raw_data"][0]["sha256"] = sha256(raw_path)
        result["analysis_artifacts"] = [
            {"path": "analysis/memory-probe.json", "sha256": sha256(probe_path)}
        ]
        result_path.write_text(dump_yaml(result), encoding="utf-8", newline="\n")
        require(
            repository.review_bundle(memory_bundle)["objective_disposition"]
            == "VALID_PASS",
            "128 GB memory fixture binds resident page exercise to M20 telemetry",
        )
        probe["resident_delta_bytes"] = 1
        probe_path.write_text(json.dumps(probe), encoding="utf-8")
        result["analysis_artifacts"][0]["sha256"] = sha256(probe_path)
        result_path.write_text(dump_yaml(result), encoding="utf-8", newline="\n")
        require(
            any(
                "resident memory is below" in error
                for error in repository.review_bundle(memory_bundle)["integrity_errors"]
            ),
            "reported allocation without resident pages cannot pass M20",
        )
        probe["resident_delta_bytes"] = 103079215104
        probe_path.write_text(json.dumps(probe), encoding="utf-8")
        result["analysis_artifacts"][0]["sha256"] = sha256(probe_path)
        result_path.write_text(dump_yaml(result), encoding="utf-8", newline="\n")
        raw_path.write_text(
            "elapsed_s,installed_bytes,usable_bytes,allocated_bytes,memory_errors,work_units_completed\n"
            "0,128000000000,120000000000,1000000000,0,0\n"
            "10,128000000000,120000000000,1000000000,0,25165824\n",
            encoding="utf-8",
            newline="\n",
        )
        result["raw_data"][0]["sha256"] = sha256(raw_path)
        result_path.write_text(dump_yaml(result), encoding="utf-8", newline="\n")
        require(
            any(
                "allocated_bytes is below" in error
                for error in repository.review_bundle(memory_bundle)["integrity_errors"]
            ),
            "nominal installed memory cannot mask inadequate usable allocation",
        )

    cli = subprocess.run(
        [sys.executable, "-m", "buildslate", "evt0", "report", "--format", "json"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    require(
        cli.returncode == 0
        and f'"EVT0_CAMPAIGN_GATE": "{current["EVT0_CAMPAIGN_GATE"]}"' in cli.stdout,
        "CLI exposes the EVT0 campaign gate",
    )
    passed("EVT0 campaign tooling validation")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (
        AssertionError,
        OSError,
        ValueError,
        KeyError,
        TypeError,
        ZeroDivisionError,
    ) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
