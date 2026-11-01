#!/usr/bin/env python3
"""Validate pilot genealogy, yield, rework, defects, confidence, capability, and gates."""

from __future__ import annotations

import hashlib
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from buildslate.io import dump_yaml, load_yaml
from buildslate.manufacturing import ManufacturingAnalyticsRepository


def passed(message: str) -> None:
    print(f"PASS: {message}")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)
    passed(message)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def create_bundle(root: Path, *, critical_defect: bool = False, capability_required: bool = False, unit_count: int = 10) -> Path:
    bundle = root / ("synthetic-critical" if critical_defect else "synthetic-pilot")
    bundle.mkdir()
    units = bundle / "units.csv"
    units.write_text(
        "unit_id,serial_number,entered_station1,part_lots,board_revision,enclosure_revision,firmware_hash,configuration_hash,first_pass,final_disposition,required_test_complete\n"
        + "".join(
            f"U{index:03d},S{index:03d},true,LOT-A,BRD-A,ENC-A,{'a'*64},{'b'*64},{'false' if index == 1 else 'true'},pass,true\n"
            for index in range(1, unit_count + 1)
        ),
        encoding="utf-8",
    )
    defects = bundle / "defects.csv"
    defects.write_text(
        "defect_id,unit_id,defect_code,severity,suspected_origin,discovery_station,finding,disposition\n"
        + ("D001,U001,BAT,critical,battery,EOL,defect,quarantine\n" if critical_defect else ""),
        encoding="utf-8",
    )
    rework = bundle / "rework.csv"
    rework.write_text(
        "rework_id,unit_id,action,outcome,approved_by\nR001,U001,synthetic_rework,pass,validation-quality\n",
        encoding="utf-8",
    )
    measurements = bundle / "measurements.csv"
    measurements.write_text(
        "characteristic_id,unit_id,value,lower_spec,upper_spec,measurement_system_approved,process_stable,distribution_reviewed\n"
        + "".join(f"THICKNESS,U{index:03d},{9.5 + ((index % 5) - 2) * 0.005},9.3,9.7,true,true,true\n" for index in range(1, unit_count + 1)),
        encoding="utf-8",
    )
    source_files = [
        {"path": path.name, "sha256": sha256(path)} for path in (units, defects, rework, measurements)
    ]
    manifest = {
        "schema_version": 1,
        "campaign_id": "SYNTHETIC-CRITICAL" if critical_defect else "SYNTHETIC-PILOT",
        "build_id": "SYNTHETIC-BUILD",
        "start_time_utc": "2026-06-01T00:00:00Z",
        "end_time_utc": "2026-06-02T00:00:00Z",
        "authorization": {"authorized": True, "authorized_by": "validation-fixture", "reference": "synthetic-test-only"},
        "released_baseline": {"design_revision": "synthetic", "bom_revision": "synthetic", "process_revision": "synthetic", "control_plan_revision": "synthetic"},
        "input_unit_count": unit_count,
        "source_files": source_files,
        "stop_events": [],
        "capability_scope": {"critical_characteristics_required": capability_required, "rationale": "synthetic validator fixture only"},
    }
    (bundle / "pilot-manifest.yaml").write_text(dump_yaml(manifest), encoding="utf-8")
    return bundle


def copy_engine_inputs(destination: Path) -> None:
    root = destination / "manufacturing"
    root.mkdir(parents=True)
    for name in ("pilot-analytics.yaml", "pilot-build-plan.yaml", "defect-taxonomy.yaml"):
        shutil.copy2(REPO_ROOT / "manufacturing" / name, root / name)
    (root / "pilot-results/campaigns").mkdir(parents=True)


def main() -> int:
    repository = ManufacturingAnalyticsRepository(REPO_ROOT)
    report = repository.build_report()
    require(report["MANUFACTURING_ANALYTICS_GATE"] == "EMPTY_PILOT_EVIDENCE", "committed pilot evidence store remains empty")
    require(report["campaign_count"] == 0, "no pilot units, yields, or capability are invented")
    require(load_yaml(REPO_ROOT / "reports/program/manufacturing-pilot-analytics.yaml") == report, "manufacturing analytics report is deterministic and current")
    require((REPO_ROOT / "manufacturing/schemas/pilot-manifest.schema.yaml").is_file(), "pilot manifest schema exists")

    with tempfile.TemporaryDirectory() as temp_directory:
        temporary = Path(temp_directory)
        bundle = create_bundle(temporary)
        review = repository.review_bundle(bundle)
        require(review["integrity_errors"] == [], "synthetic pilot bundle passes structure, hash, genealogy, and taxonomy checks")
        require(review["denominator"]["input_units"] == 10, "yield denominator retains every input unit")
        require(review["metrics"]["first_pass_yield"]["percent"] == 90.0, "first-pass yield is calculated from unit rows")
        require(review["metrics"]["final_yield"]["percent"] == 100.0, "final yield is calculated from unit rows")
        require(review["metrics"]["rework_rate"]["percent"] == 10.0, "rework rate is calculated from unique reworked units")
        require(review["metrics"]["first_pass_yield"]["lower_95_percent"] < 90.0, "Wilson confidence interval exposes finite-sample uncertainty")
        require(review["PILOT_GATE"] == "PILOT_ANALYTICS_PASS_REVIEW_REQUIRED", "point gates pass without claiming production readiness")

        temp_repo = temporary / "repo"
        copy_engine_inputs(temp_repo)
        temp_repository = ManufacturingAnalyticsRepository(temp_repo)
        receipt, _ = temp_repository.ingest(bundle, "2026-06-03T00:00:00Z", "validation-operator")
        require(receipt.is_file(), "valid authorized pilot bundle is preserved with receipt")
        require(temp_repository.build_report()["MANUFACTURING_ANALYTICS_GATE"] == "PILOT_QUALITY_REVIEW_READY", "valid campaign reaches quality review, not production approval")
        (receipt.parent / "units.csv").write_text("tampered\n", encoding="utf-8")
        require(temp_repository.build_report()["MANUFACTURING_ANALYTICS_GATE"] == "BLOCKED_INVALID_PILOT_EVIDENCE", "post-ingestion genealogy tampering blocks the gate")

    with tempfile.TemporaryDirectory() as temp_directory:
        critical = create_bundle(Path(temp_directory), critical_defect=True)
        critical_review = repository.review_bundle(critical)
        require(critical_review["PILOT_GATE"] == "STOP_QUARANTINE_AND_REVIEW", "critical defect triggers the stop rule")
        require(critical_review["defects"]["critical_count"] == 1, "critical defect remains visible in analytics")

    with tempfile.TemporaryDirectory() as temp_directory:
        capability = create_bundle(Path(temp_directory), capability_required=True)
        capability_review = repository.review_bundle(capability)
        require(capability_review["PILOT_GATE"] == "BLOCKED_CAPABILITY_PREREQUISITES", "Cpk is blocked when minimum sample prerequisite is unmet")
        require(capability_review["capability"][0]["cpk"] is None, "unsupported Cpk is not calculated")

    with tempfile.TemporaryDirectory() as temp_directory:
        capable = create_bundle(Path(temp_directory), capability_required=True, unit_count=30)
        capable_review = repository.review_bundle(capable)
        require(capable_review["capability"][0]["status"] == "calculated", "Cpk is calculated after every prerequisite is met")
        require(capable_review["capability"][0]["cpk"] >= 1.33, "calculated Cpk is compared with the authoritative target")

    cli = subprocess.run(
        [sys.executable, "-m", "buildslate", "manufacturing", "report", "--format", "json"],
        cwd=REPO_ROOT, capture_output=True, text=True, check=False,
    )
    require(cli.returncode == 0 and '"MANUFACTURING_ANALYTICS_GATE": "EMPTY_PILOT_EVIDENCE"' in cli.stdout, "CLI exposes manufacturing analytics gate")
    passed("manufacturing analytics validation")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AssertionError, OSError, ValueError, KeyError, TypeError, ZeroDivisionError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)

