"""Pilot evidence validation, genealogy, yield, defect, rework, and capability analytics."""

from __future__ import annotations

import csv
import hashlib
import math
import shutil
import statistics
from datetime import datetime
from pathlib import Path
from typing import Any

from .configuration import MISSING, value_at
from .io import dump_yaml, load_yaml


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _boolean(value: str) -> bool:
    normalized = value.strip().lower()
    if normalized not in {"true", "false"}:
        raise ValueError(f"expected true/false, got {value!r}")
    return normalized == "true"


def _timestamp(value: Any, field: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be an ISO-8601 timestamp")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError(f"{field} must include a timezone")
    return parsed


class ManufacturingAnalyticsRepository:
    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root.resolve()
        self.root = self.repo_root / "manufacturing"
        self.config = load_yaml(self.root / "pilot-analytics.yaml")
        self.plan = load_yaml(self.root / "pilot-build-plan.yaml")
        self.taxonomy = load_yaml(self.root / "defect-taxonomy.yaml")
        self.campaign_root = self.root / "pilot-results" / "campaigns"
        self._validate_config()

    def _validate_config(self) -> None:
        if self.config.get("metadata", {}).get("schema_version") != 1:
            raise ValueError("pilot analytics requires schema_version 1")
        source = self.config["capability_policy"]["target_cpk_source"]
        path_text, field = source.split("#", 1)
        source_value = value_at(load_yaml(self.repo_root / path_text), field)
        if source_value is MISSING or source_value != self.plan["provisional_yield_gates"]["critical_characteristic_capability"]["target_cpk"]:
            raise ValueError("pilot capability target source is missing or stale")

    def _bundle_path(self, bundle: Path, relative: Any) -> Path:
        if not isinstance(relative, str) or not relative:
            raise ValueError("bundle file path must be non-empty")
        path = (bundle / relative).resolve()
        try:
            path.relative_to(bundle.resolve())
        except ValueError as exc:
            raise ValueError(f"bundle file escapes root: {relative}") from exc
        return path

    def _read_table(self, path: Path, required: list[str]) -> tuple[list[dict[str, str]], list[str]]:
        errors: list[str] = []
        if not path.is_file():
            return [], [f"required pilot table is missing: {path.name}"]
        try:
            with path.open("r", encoding="utf-8-sig", newline="") as stream:
                reader = csv.DictReader(stream)
                fields = reader.fieldnames or []
                missing = sorted(set(required) - set(fields))
                if missing:
                    errors.append(f"{path.name} missing columns: {', '.join(missing)}")
                rows = list(reader)
        except (OSError, UnicodeError, csv.Error) as exc:
            return [], [f"cannot read {path.name}: {exc}"]
        return rows, errors

    def _wilson(self, successes: int, total: int) -> dict[str, float | int | str | None]:
        if total == 0:
            return {"count": successes, "denominator": total, "percent": None, "lower_95_percent": None, "upper_95_percent": None, "method": "wilson_score"}
        z = float(self.config["confidence_intervals"]["z"])
        p = successes / total
        denominator = 1 + z * z / total
        center = (p + z * z / (2 * total)) / denominator
        half = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / denominator
        return {
            "count": successes,
            "denominator": total,
            "percent": round(100 * p, 3),
            "lower_95_percent": round(100 * max(0, center - half), 3),
            "upper_95_percent": round(100 * min(1, center + half), 3),
            "method": "wilson_score",
        }

    def review_bundle(self, bundle: Path) -> dict[str, Any]:
        bundle = bundle.resolve()
        errors: list[str] = []
        try:
            manifest = load_yaml(bundle / self.config["bundle"]["manifest"])
        except (OSError, ValueError) as exc:
            return {"integrity_errors": [str(exc)], "PILOT_GATE": "REJECTED_INVALID_EVIDENCE"}
        required_manifest = {
            "schema_version", "campaign_id", "build_id", "start_time_utc", "end_time_utc", "authorization",
            "released_baseline", "input_unit_count", "source_files", "stop_events", "capability_scope",
        }
        missing_manifest = sorted(required_manifest - set(manifest))
        if missing_manifest:
            errors.append("pilot manifest missing fields: " + ", ".join(missing_manifest))
        if manifest.get("schema_version") != 1:
            errors.append("pilot manifest schema_version must be 1")
        if not isinstance(manifest.get("input_unit_count"), int) or manifest.get("input_unit_count", 0) < 1:
            errors.append("pilot input_unit_count must be a positive integer")
        try:
            if _timestamp(manifest["end_time_utc"], "end_time_utc") <= _timestamp(manifest["start_time_utc"], "start_time_utc"):
                errors.append("pilot end_time_utc must follow start_time_utc")
        except (KeyError, TypeError, ValueError) as exc:
            errors.append(str(exc))
        authorization = manifest.get("authorization", {})
        if not isinstance(authorization, dict) or authorization.get("authorized") is not True or not authorization.get("authorized_by") or not authorization.get("reference"):
            errors.append("pilot manifest requires explicit authorization identity and reference")
        baseline = manifest.get("released_baseline", {})
        for field in ("design_revision", "bom_revision", "process_revision", "control_plan_revision"):
            if not isinstance(baseline, dict) or not baseline.get(field):
                errors.append(f"released_baseline.{field} is required")

        declared_files: dict[str, str] = {}
        for item in manifest.get("source_files", []):
            if not isinstance(item, dict) or not {"path", "sha256"}.issubset(item):
                errors.append("source_files entry is structurally incomplete")
                continue
            try:
                path = self._bundle_path(bundle, item["path"])
                if not path.is_file() or _sha256(path).lower() != str(item["sha256"]).lower():
                    errors.append(f"pilot source hash mismatch or missing: {item['path']}")
                declared_files[item["path"]] = item["sha256"]
            except ValueError as exc:
                errors.append(str(exc))
        for filename in self.config["bundle"]["required_tables"]:
            if filename not in declared_files:
                errors.append(f"required pilot table is not declared: {filename}")

        tables: dict[str, list[dict[str, str]]] = {}
        for filename in self.config["bundle"]["required_tables"] + self.config["bundle"]["optional_tables"]:
            path = bundle / filename
            if filename in self.config["bundle"]["optional_tables"] and not path.exists():
                tables[filename] = []
                continue
            rows, table_errors = self._read_table(path, self.config["required_columns"][filename])
            tables[filename] = rows
            errors.extend(table_errors)

        units = tables.get("units.csv", [])
        defects = tables.get("defects.csv", [])
        reworks = tables.get("rework.csv", [])
        measurements = tables.get("measurements.csv", [])
        unit_ids = [row.get("unit_id", "") for row in units]
        unit_set = set(unit_ids)
        if len(unit_set) != len(unit_ids) or "" in unit_set:
            errors.append("unit identifiers must be non-empty and unique")
        if manifest.get("input_unit_count") != len(units):
            errors.append(f"input_unit_count {manifest.get('input_unit_count')} does not match unit rows {len(units)}")
        invalid_refs = sorted({row.get("unit_id", "") for row in defects + reworks + measurements} - unit_set)
        if invalid_refs:
            errors.append("records reference unknown units: " + ", ".join(invalid_refs))

        genealogy_fields = [
            "unit_id", "serial_number", "part_lots", "board_revision", "enclosure_revision", "firmware_hash", "configuration_hash"
        ]
        traceable = sum(1 for row in units if all(row.get(field, "").strip() for field in genealogy_fields))
        test_complete = 0
        first_pass_count = 0
        final_pass_count = 0
        for row in units:
            try:
                if not _boolean(row.get("entered_station1", "")):
                    errors.append(f"unit did not enter denominator station: {row.get('unit_id')}")
                first_pass_count += int(_boolean(row.get("first_pass", "")))
                test_complete += int(_boolean(row.get("required_test_complete", "")))
            except ValueError as exc:
                errors.append(f"unit {row.get('unit_id')}: {exc}")
            final_pass_count += int(row.get("final_disposition") == "pass")

        defect_codes = self.taxonomy["codes"]
        severities = self.taxonomy["severity"]
        origins = set(self.taxonomy["origins"])
        dispositions = set(self.taxonomy["dispositions"])
        critical_defects = 0
        unknown_or_ntf_units: set[str] = set()
        defect_pareto: dict[str, int] = {}
        for row in defects:
            code = row.get("defect_code")
            if code not in defect_codes:
                errors.append(f"unknown defect code: {code}")
            if row.get("severity") not in severities:
                errors.append(f"invalid defect severity: {row.get('severity')}")
            if row.get("suspected_origin") not in origins:
                errors.append(f"invalid defect origin: {row.get('suspected_origin')}")
            if row.get("disposition") not in dispositions:
                errors.append(f"invalid defect disposition: {row.get('disposition')}")
            critical_defects += int(row.get("severity") == "critical")
            if row.get("suspected_origin") == "unknown" or row.get("finding") == "no_trouble_found":
                unknown_or_ntf_units.add(row.get("unit_id", ""))
            defect_pareto[code or "<missing>"] = defect_pareto.get(code or "<missing>", 0) + 1

        rework_ids: set[str] = set()
        reworked_units: set[str] = set()
        for row in reworks:
            rework_id = row.get("rework_id", "")
            if not rework_id or rework_id in rework_ids:
                errors.append(f"rework identifiers must be non-empty and unique: {rework_id}")
            rework_ids.add(rework_id)
            reworked_units.add(row.get("unit_id", ""))
            if not row.get("approved_by", "").strip():
                errors.append(f"rework lacks approval: {rework_id}")

        denominator = len(units)
        metrics = {
            "first_pass_yield": self._wilson(first_pass_count, denominator),
            "final_yield": self._wilson(final_pass_count, denominator),
            "rework_rate": self._wilson(len(reworked_units), denominator),
            "unknown_or_no_trouble_found_rate": self._wilson(len(unknown_or_ntf_units), denominator),
            "traceability_completeness": self._wilson(traceable, denominator),
            "required_test_data_completeness": self._wilson(test_complete, denominator),
        }

        capability: list[dict[str, Any]] = []
        grouped: dict[str, list[dict[str, str]]] = {}
        for row in measurements:
            grouped.setdefault(row.get("characteristic_id", ""), []).append(row)
        minimum_n = int(self.config["capability_policy"]["minimum_observations"])
        for characteristic, rows in sorted(grouped.items()):
            item: dict[str, Any] = {"characteristic_id": characteristic, "observation_count": len(rows)}
            try:
                prerequisites = all(
                    all(_boolean(row[field]) for row in rows)
                    for field in self.config["capability_policy"]["required_prerequisites"]
                )
                values = [float(row["value"]) for row in rows]
                lowers = {float(row["lower_spec"]) for row in rows}
                uppers = {float(row["upper_spec"]) for row in rows}
                eligible = prerequisites and len(rows) >= minimum_n and len(lowers) == 1 and len(uppers) == 1 and len(values) >= 2
                if eligible:
                    sigma = statistics.stdev(values)
                    if sigma <= 0:
                        eligible = False
                if eligible:
                    mean = statistics.mean(values)
                    cpk = min((next(iter(uppers)) - mean) / (3 * sigma), (mean - next(iter(lowers))) / (3 * sigma))
                    item.update({"status": "calculated", "cpk": round(cpk, 4), "target": self.plan["provisional_yield_gates"]["critical_characteristic_capability"]["target_cpk"]})
                else:
                    item.update({"status": "prerequisites_not_met", "cpk": None})
            except (KeyError, ValueError, statistics.StatisticsError) as exc:
                errors.append(f"invalid capability data for {characteristic}: {exc}")
                item.update({"status": "invalid", "cpk": None})
            capability.append(item)

        gates = self.plan["provisional_yield_gates"]
        threshold_failures: list[str] = []
        comparisons = (
            ("first_pass_yield", ">=", gates["first_pass_yield_percent"]["minimum"]),
            ("final_yield", ">=", gates["final_yield_percent"]["minimum"]),
            ("rework_rate", "<=", gates["rework_rate_percent"]["maximum"]),
            ("unknown_or_no_trouble_found_rate", "<=", gates["unknown_or_no_trouble_found_rate_percent"]["maximum"]),
            ("traceability_completeness", ">=", gates["traceability_completeness_percent"]["minimum"]),
            ("required_test_data_completeness", ">=", gates["required_test_data_completeness_percent"]["minimum"]),
        )
        for metric_id, operator, threshold in comparisons:
            actual = metrics[metric_id]["percent"]
            if actual is None or (operator == ">=" and actual < threshold) or (operator == "<=" and actual > threshold):
                threshold_failures.append(f"{metric_id} {actual} does not meet {operator} {threshold}")
        stop_reasons = [f"manifest stop event: {item}" for item in manifest.get("stop_events", [])]
        if critical_defects:
            stop_reasons.append(f"critical defect count: {critical_defects}")
        capability_required = manifest.get("capability_scope", {}).get("critical_characteristics_required") is True
        capability_blocked = capability_required and (not capability or any(item["status"] != "calculated" for item in capability))
        capability_failures = [item["characteristic_id"] for item in capability if item.get("cpk") is not None and item["cpk"] < item["target"]]
        if errors:
            gate = "REJECTED_INVALID_EVIDENCE"
        elif stop_reasons:
            gate = "STOP_QUARANTINE_AND_REVIEW"
        elif threshold_failures or capability_failures:
            gate = "FAIL_OBJECTIVE_QUALITY_GATES"
        elif capability_blocked:
            gate = "BLOCKED_CAPABILITY_PREREQUISITES"
        else:
            gate = "PILOT_ANALYTICS_PASS_REVIEW_REQUIRED"
        return {
            "campaign_id": manifest.get("campaign_id"),
            "build_id": manifest.get("build_id"),
            "PILOT_GATE": gate,
            "integrity_errors": errors,
            "denominator": {"rule": self.plan["lot"]["yield_denominator_rule"], "input_units": denominator, "manifest_input_units": manifest.get("input_unit_count")},
            "metrics": metrics,
            "defects": {"count": len(defects), "critical_count": critical_defects, "pareto": dict(sorted(defect_pareto.items(), key=lambda item: (-item[1], item[0])))},
            "rework": {"record_count": len(reworks), "unit_count": len(reworked_units)},
            "capability": capability,
            "capability_scope": manifest.get("capability_scope"),
            "threshold_failures": threshold_failures,
            "capability_failures": capability_failures,
            "stop_reasons": stop_reasons,
            "caveat": "Pilot analytics do not prove long-term yield, capability, reliability, compliance, or production readiness.",
        }

    def ingest(self, bundle: Path, received_at: str, received_by: str) -> tuple[Path, dict[str, Any]]:
        review = self.review_bundle(bundle)
        if review["integrity_errors"]:
            raise ValueError("pilot bundle rejected: " + "; ".join(review["integrity_errors"]))
        _timestamp(received_at, "received_at")
        if not received_by.strip():
            raise ValueError("received_by must not be empty")
        campaign_id = review["campaign_id"]
        if not isinstance(campaign_id, str) or not campaign_id.replace("-", "").replace("_", "").isalnum():
            raise ValueError("pilot campaign_id must be path-safe")
        destination = self.campaign_root / campaign_id
        if destination.exists():
            raise ValueError(f"pilot campaign already exists: {campaign_id}")
        shutil.copytree(bundle, destination)
        hashes = {path.relative_to(destination).as_posix(): _sha256(path) for path in sorted(destination.rglob("*")) if path.is_file()}
        receipt = {
            "receipt_version": 1,
            "campaign_id": campaign_id,
            "received_at": received_at,
            "received_by": received_by,
            "file_hashes": hashes,
            "review": review,
            "authority_boundary": "pilot_evidence_under_quality_review_not_production_approval",
        }
        receipt_path = destination / "receipt.yaml"
        receipt_path.write_text(dump_yaml(receipt), encoding="utf-8")
        return receipt_path, review

    def build_report(self) -> dict[str, Any]:
        campaigns: list[dict[str, Any]] = []
        for receipt_path in sorted(self.campaign_root.glob("*/receipt.yaml")):
            receipt = load_yaml(receipt_path)
            hash_errors: list[str] = []
            for relative, expected in receipt.get("file_hashes", {}).items():
                path = self._bundle_path(receipt_path.parent, relative)
                if not path.is_file() or _sha256(path) != expected:
                    hash_errors.append(f"receipt hash mismatch: {relative}")
            review = self.review_bundle(receipt_path.parent)
            review["integrity_errors"] = hash_errors + review["integrity_errors"]
            if hash_errors:
                review["PILOT_GATE"] = "REJECTED_INVALID_EVIDENCE"
            campaigns.append(review)
        if not campaigns:
            gate = "EMPTY_PILOT_EVIDENCE"
        elif any(item["PILOT_GATE"] == "REJECTED_INVALID_EVIDENCE" for item in campaigns):
            gate = "BLOCKED_INVALID_PILOT_EVIDENCE"
        elif any(item["PILOT_GATE"] == "STOP_QUARANTINE_AND_REVIEW" for item in campaigns):
            gate = "STOP_QUARANTINE_AND_REVIEW"
        elif all(item["PILOT_GATE"] == "PILOT_ANALYTICS_PASS_REVIEW_REQUIRED" for item in campaigns):
            gate = "PILOT_QUALITY_REVIEW_READY"
        else:
            gate = "PILOT_GATE_NOT_MET"
        return {
            "MANUFACTURING_ANALYTICS_GATE": gate,
            "campaign_count": len(campaigns),
            "campaigns": campaigns,
            "next_actions": [
                "Do not execute a pilot until EVT0, DFM, release, process, safety, and authorization prerequisites are satisfied.",
                "Ingest every input unit and retain failures, rework, scrap, and unknown findings in the denominator.",
                "Review stop conditions, confidence intervals, capability prerequisites, and signed quality disposition.",
            ],
            "caveat": "No pilot evidence exists unless a hash-verified authorized campaign is ingested.",
        }

    def generate_report(self) -> Path:
        destination = self.repo_root / self.config["outputs"]["report"]
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(dump_yaml(self.build_report()), encoding="utf-8")
        return destination

