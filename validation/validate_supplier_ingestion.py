#!/usr/bin/env python3
"""Validate controlled supplier-response ingestion and review behavior."""

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

from buildslate.io import dump_yaml, load_yaml
from buildslate.suppliers import SupplierResponseRepository


def passed(message: str) -> None:
    print(f"PASS: {message}")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)
    passed(message)


def set_path(document: dict[str, Any], dotted_path: str, value: Any) -> None:
    target = document
    parts = dotted_path.split(".")
    for part in parts[:-1]:
        target = target[part]
    target[parts[-1]] = value


def complete_battery_response() -> dict[str, Any]:
    response = load_yaml(REPO_ROOT / "research/rfqs/battery/response-template.yaml")
    values = {
        "supplier.legal_name": "Synthetic Validation Supplier",
        "supplier.response_date": "2026-11-01",
        "proposal.option_id": "VALIDATION-ONLY",
        "proposal.source_documents": ["synthetic-validation-datasheet-rev-a"],
        "electrical.energy_wh_min": 20.0,
        "mechanical.complete_pack_mm.length": 100.0,
        "mechanical.complete_pack_mm.width": 70.0,
        "mechanical.complete_pack_mm.thickness": 5.2,
        "mechanical.complete_pack_volume_mm3": 30000,
        "mechanical.mass_g": 95.0,
        "charge_discharge.maximum_validated_charge_w": 25.0,
        "thermal_safety.protection_requirements": "validation fixture value",
        "reliability_supply.sample_availability": "validation fixture value",
        "supplier_attestation.values_are_supplier_provided": True,
        "supplier_attestation.authorized_for_public_disclosure": False,
    }
    for path, value in values.items():
        set_path(response, path, value)
    return response


def main() -> int:
    repository = SupplierResponseRepository(REPO_ROOT)
    require(repository.domains == ("battery", "compute_memory", "dfm", "display", "storage"), "all five supplier domains are registered")

    expected_artifacts = [
        REPO_ROOT / "engineering/program/supplier_ingestion.yaml",
        REPO_ROOT / "reports/program/supplier-response-review.yaml",
        REPO_ROOT / "research/supplier-responses/raw/README.md",
        REPO_ROOT / "research/supplier-responses/receipts/README.md",
    ]
    expected_artifacts.extend(
        REPO_ROOT / f"engineering/program/supplier-schemas/{name}.schema.yaml"
        for name in ("battery", "compute-memory", "display", "storage", "dfm")
    )
    for path in expected_artifacts:
        require(path.is_file(), f"supplier ingestion artifact exists: {path.relative_to(REPO_ROOT)}")

    empty_queue = repository.build_review_queue()
    require(empty_queue["SUPPLIER_RESPONSE_GATE"] == "EMPTY_INBOX", "empty supplier inbox remains explicit")
    require(empty_queue["summary"]["receipt_count"] == 0, "no supplier response or receipt is invented")
    generated = load_yaml(REPO_ROOT / "reports/program/supplier-response-review.yaml")
    require(generated == empty_queue, "generated supplier review queue is deterministic and current")

    with tempfile.TemporaryDirectory() as temp_directory:
        temporary_root = Path(temp_directory)
        schema_target = temporary_root / "engineering/program/supplier-schemas"
        schema_target.parent.mkdir(parents=True)
        shutil.copytree(REPO_ROOT / "engineering/program/supplier-schemas", schema_target)
        shutil.copy2(REPO_ROOT / "engineering/program/supplier_ingestion.yaml", schema_target.parent / "supplier_ingestion.yaml")
        for source in (
            "configs/devices/slate-pocket-v1r.yaml",
            "research/evidence/battery/pack-envelope.yaml",
        ):
            destination = temporary_root / source
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(REPO_ROOT / source, destination)

        response_path = temporary_root / "synthetic-battery-response.yaml"
        response_bytes = dump_yaml(complete_battery_response()).encode("utf-8")
        response_path.write_bytes(response_bytes)

        temporary_repository = SupplierResponseRepository(temporary_root)
        review = temporary_repository.validate_response(response_path, "battery")
        require(not review.schema_errors, "complete synthetic fixture satisfies structural schema")
        require(review.completeness_percent == 100.0, "completeness scoring reaches 100 percent only when required fields are answered")
        require(review.disposition == "CONTRADICTION_REVIEW_REQUIRED", "target and fallback contradictions enter review instead of changing configuration")
        require(len(review.contradictions) == 3, "battery target, allocation, and EVT0 cap contradictions are detected")

        receipt_path, ingested_review = temporary_repository.ingest(
            response_path, "battery", "2026-11-01T12:00:00-05:00", "validation-operator"
        )
        receipt = load_yaml(receipt_path)
        raw_path = temporary_root / receipt["raw_path"]
        require(raw_path.read_bytes() == response_bytes, "ingestion preserves exact raw supplier bytes")
        require(receipt["sha256"] == hashlib.sha256(response_bytes).hexdigest(), "receipt hash matches raw response")
        require(receipt["authority_boundary"] == "ingested_not_verified_not_selected", "receipt preserves the evidence authority boundary")
        require(ingested_review.disposition == "CONTRADICTION_REVIEW_REQUIRED", "ingestion preserves review disposition")

        queue = temporary_repository.build_review_queue()
        require(queue["SUPPLIER_RESPONSE_GATE"] == "REVIEW_QUEUE_OPEN", "contradictory response opens the review queue")
        require(queue["items"][0]["integrity_errors"] == [], "review queue verifies raw-file integrity")

        raw_path.write_text("tampered: true\n", encoding="utf-8")
        tampered_queue = temporary_repository.build_review_queue()
        require(tampered_queue["SUPPLIER_RESPONSE_GATE"] == "BLOCKED_BY_INVALID_RESPONSE", "hash mismatch blocks the supplier gate")

        malformed_path = temporary_root / "malformed.yaml"
        malformed_path.write_text(yaml.safe_dump({"request": {"packet": "wrong"}}), encoding="utf-8")
        malformed_review = temporary_repository.validate_response(malformed_path, "battery")
        require(bool(malformed_review.schema_errors), "malformed response is rejected by structural schema")

    cli = subprocess.run(
        [sys.executable, "-m", "buildslate", "suppliers", "queue", "--format", "json"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    require(cli.returncode == 0 and '"SUPPLIER_RESPONSE_GATE": "EMPTY_INBOX"' in cli.stdout, "CLI exposes the supplier review queue")
    passed("supplier-response ingestion validation")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AssertionError, OSError, ValueError, KeyError, TypeError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)

