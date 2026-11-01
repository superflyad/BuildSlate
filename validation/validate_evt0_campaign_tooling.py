#!/usr/bin/env python3
"""Validate EVT0 evidence ingestion, metrics, correlations, and objective gates."""

from __future__ import annotations

import hashlib
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from buildslate.evt0 import EVT0CampaignRepository
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
        "elapsed_s,system_power_w,work_units_completed,TC_REAR_SOC,TC_FRONT_SOC,TC_FRONT_CENTER,TC_REAR_CHARGER,TC_EDGE_LEFT,TC_EDGE_RIGHT,TC_REAR_BATTERY\n"
        f"0,10,0,30,30,30,30,29,29,28\n10,20,100,{maximum_skin_c},39,38,37,36,35,35\n",
        encoding="utf-8",
    )
    certificate_path = bundle / "calibrations" / "CAL-VALIDATION.txt"
    certificate_path.write_text("synthetic calibration certificate for validator only\n", encoding="utf-8")
    required_channels = EVT0CampaignRepository(REPO_ROOT).required_channels("P10")
    calibration = {
        "schema_version": 1,
        "calibration_id": "CAL-VALIDATION",
        "instrument_id": "SYNTHETIC-INSTRUMENT",
        "valid_from_utc": "2026-01-01T00:00:00Z",
        "valid_until_utc": "2027-01-01T00:00:00Z",
        "channels": list(required_channels),
        "certificate": {"path": "calibrations/CAL-VALIDATION.txt", "sha256": sha256(certificate_path)},
        "uncertainty_note": "synthetic validator fixture; not engineering evidence",
    }
    (bundle / "calibrations" / "CAL-VALIDATION.yaml").write_text(dump_yaml(calibration), encoding="utf-8")
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
            "bom_revision": "synthetic", "board_revision": "synthetic", "enclosure_revision": "synthetic",
            "thermal_stack_revision": "synthetic", "firmware_hash": "0" * 64, "configuration_hash": "1" * 64,
        },
        "workload": {
            "workload_id": "W10_ai_reference_70b_4bit", "definition_revision": "synthetic",
            "artifact_hashes": ["2" * 64], "command_line": "synthetic-validator-command", "random_seeds": [1],
        },
        "instrumentation": {
            "channel_map_revision": "synthetic", "calibration_ids": ["CAL-VALIDATION"],
            "synchronization_method": "synthetic common clock",
        },
        "environment": {"ambient_c": 25.0, "humidity_percent": 50.0, "condition": "open_air", "orientation": "flat"},
        "approved_limits_revision": "synthetic-validator-only",
        "notes": "This temporary fixture is not a physical measurement.",
    }
    result = {
        "schema_version": 1,
        "manifest_path": "manifest.yaml",
        "raw_data": [{"path": "raw/telemetry.csv", "sha256": sha256(raw_path), "format": "csv", "source": "synthetic validator"}],
        "time_range_utc": {"start": "2026-06-01T12:00:00Z", "end": "2026-06-01T12:00:10Z"},
        "required_channel_status": {channel: True for channel in required_channels},
        "metrics": {},
        "hard_stop_events": [],
        "validity": "valid",
        "disposition": "pass",
        "invalidation_reasons": [],
        "requirement_trades": [],
        "analysis_artifacts": [],
        "deviations": [],
        "model_correlations": [{"model_id": "synthetic-power-model", "metric_id": "mean_system_power_w", "predicted": 14.0, "measured": 15.0, "unit": "W", "tolerance_absolute": 2.0}],
        "reviewers": ["validator"],
        "notes": "Temporary synthetic fixture only.",
    }
    (bundle / "manifest.yaml").write_text(dump_yaml(manifest), encoding="utf-8")
    (bundle / "result.yaml").write_text(dump_yaml(result), encoding="utf-8")
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
    empty = repository.build_campaign_report()
    require(empty["EVT0_CAMPAIGN_GATE"] == "EMPTY_CAMPAIGN", "committed EVT0 campaign store remains empty")
    require(empty["summary"]["ingested_run_count"] == 0, "no measurement or prototype run is invented")
    require(load_yaml(REPO_ROOT / "reports/program/evt0-campaign.yaml") == empty, "generated EVT0 campaign report is deterministic and current")
    for name in ("calibration.schema.yaml", "deviation.schema.yaml"):
        require((REPO_ROOT / "validation/evt0/schemas" / name).is_file(), f"EVT0 schema exists: {name}")

    with tempfile.TemporaryDirectory() as temp_directory:
        temporary = Path(temp_directory)
        bundle = create_bundle(temporary)
        review = repository.review_bundle(bundle)
        require(review["integrity_errors"] == [], "synthetic fixture passes structural, hash, and calibration checks")
        require(review["objective_disposition"] == "VALID_PASS", "objective disposition preserves a valid synthetic pass")
        require(review["calculated_metrics"]["energy_consumed_wh"]["value"] == 0.041667, "energy metric is calculated from raw CSV")
        require(review["calculated_metrics"]["performance_per_watt"]["value"] == 0.666667, "performance-per-watt is calculated from raw CSV")
        require(review["model_correlations"][0]["residual"] == 1.0 and review["model_correlations"][0]["passed"], "model residual and tolerance decision are calculated")

        temp_repo = temporary / "repo"
        copy_engine_inputs(temp_repo)
        temp_repository = EVT0CampaignRepository(temp_repo)
        receipt, _ = temp_repository.ingest(bundle, "2026-06-02T12:00:00Z", "validation-operator")
        require(receipt.is_file(), "valid EVT0 bundle is preserved with a receipt")
        report = temp_repository.build_campaign_report()
        require(report["EVT0_CAMPAIGN_GATE"] == "CAMPAIGN_INCOMPLETE", "one passing run cannot satisfy the campaign gate")
        require("P10" not in report["missing_or_nonpassing_required_tests"], "passing test is credited without claiming campaign completion")

        preserved_raw = receipt.parent / "raw/telemetry.csv"
        preserved_raw.write_text("tampered\n", encoding="utf-8")
        require(temp_repository.build_campaign_report()["EVT0_CAMPAIGN_GATE"] == "BLOCKED_INVALID_EVIDENCE", "post-ingestion hash tampering blocks the campaign")

    with tempfile.TemporaryDirectory() as temp_directory:
        hot_bundle = create_bundle(Path(temp_directory), maximum_skin_c=44.0)
        hot_review = repository.review_bundle(hot_bundle)
        require(hot_review["objective_disposition"] == "REJECTED_INVALID_EVIDENCE", "reported pass cannot override calculated skin hard stop")
        require("maximum_skin_c" in hot_review["calculated_limit_events"], "calculated hard-stop cause is explicit")

    cli = subprocess.run(
        [sys.executable, "-m", "buildslate", "evt0", "report", "--format", "json"],
        cwd=REPO_ROOT, capture_output=True, text=True, check=False,
    )
    require(cli.returncode == 0 and '"EVT0_CAMPAIGN_GATE": "EMPTY_CAMPAIGN"' in cli.stdout, "CLI exposes the EVT0 campaign gate")
    passed("EVT0 campaign tooling validation")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AssertionError, OSError, ValueError, KeyError, TypeError, ZeroDivisionError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)

