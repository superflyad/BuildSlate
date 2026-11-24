"""EVT0 evidence-bundle validation, metrics, correlation, ingestion, and gates."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

from .io import dump_yaml, load_yaml
from .memory_probe import (
    DEFAULT_ALLOCATION,
    DEFAULT_MIN_TOTAL,
    PAGE,
    PATTERN_ALGORITHM,
    PATTERN_REGION,
)

HASH_LENGTH = 64
INTERFACE_COUNTERS = (
    "display_frames",
    "touch_events",
    "camera_frames",
    "audio_playback_samples",
    "audio_capture_samples",
    "usb_bytes_tx",
    "usb_bytes_rx",
)
REQUIRED_MANIFEST_FIELDS = {
    "schema_version",
    "campaign_id",
    "unit_id",
    "build_id",
    "run_id",
    "test_id",
    "start_time_utc",
    "configuration",
    "workload",
    "instrumentation",
    "environment",
}
REQUIRED_RESULT_FIELDS = {
    "schema_version",
    "manifest_path",
    "raw_data",
    "time_range_utc",
    "required_channel_status",
    "metrics",
    "hard_stop_events",
    "validity",
    "disposition",
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _datetime(value: Any, field: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be an ISO-8601 timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field} must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"{field} must include a timezone")
    return parsed


def _valid_hash(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == HASH_LENGTH
        and all(character in "0123456789abcdefABCDEF" for character in value)
    )


def _coherent_coverage(
    items: list[dict[str, Any]], required: set[str]
) -> tuple[dict[str, str] | None, set[str], list[dict[str, Any]]]:
    """Credit tests only within one campaign, unit, build, and configuration."""
    groups: dict[tuple[str, str, str, str], set[str]] = {}
    for item in items:
        if item.get("objective_disposition") != "VALID_PASS":
            continue
        fields = (
            item.get("campaign_id"),
            item.get("unit_id"),
            item.get("build_id"),
            item.get("configuration_sha256"),
        )
        if not all(isinstance(field, str) and field for field in fields):
            continue
        groups.setdefault(fields, set()).add(item["test_id"])
    ordered = sorted(
        groups.items(), key=lambda entry: (-len(entry[1] & required), entry[0])
    )
    summaries = [
        {
            "campaign_id": key[0],
            "unit_id": key[1],
            "build_id": key[2],
            "configuration_sha256": key[3],
            "passing_required_tests": sorted(tests & required),
        }
        for key, tests in ordered
    ]
    if not ordered:
        return None, set(), summaries
    return (
        {
            key: value
            for key, value in zip(
                ("campaign_id", "unit_id", "build_id", "configuration_sha256"),
                ordered[0][0],
                strict=True,
            )
        },
        ordered[0][1] & required,
        summaries,
    )


class EVT0CampaignRepository:
    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root.resolve()
        self.evt_root = self.repo_root / "validation" / "evt0"
        self.campaign_root = self.evt_root / "campaigns"
        self.matrix = load_yaml(self.evt_root / "test-matrix.yaml")
        self.instrumentation = load_yaml(self.evt_root / "instrumentation.yaml")
        self.metric_definitions = load_yaml(self.evt_root / "metric-definitions.yaml")
        self.test_ids = {entry["id"] for entry in self.matrix["sequence"]}
        self.objective_measurements = self.matrix["objective_measurements"]
        if set(self.objective_measurements) != set(
            self.matrix["required_for_evt0_evidence_gate"]
        ):
            raise ValueError(
                "Every required EVT0 test needs an objective measurement contract"
            )
        schemas = {
            name: load_yaml(self.evt_root / "schemas" / f"{name}.schema.yaml")
            for name in ("run-manifest", "test-result", "calibration", "deviation")
        }
        registry = Registry()
        for schema in schemas.values():
            Draft202012Validator.check_schema(schema)
            registry = registry.with_resource(
                schema["$id"], Resource.from_contents(schema)
            )
        self.validators = {
            name: Draft202012Validator(
                schema, registry=registry, format_checker=FormatChecker()
            )
            for name, schema in schemas.items()
        }

    def _schema_errors(self, name: str, data: object) -> list[str]:
        return [
            f"{name} schema: {'/'.join(str(part) for part in error.absolute_path) or '<root>'}: {error.message}"
            for error in sorted(
                self.validators[name].iter_errors(data),
                key=lambda item: (
                    tuple(str(part) for part in item.absolute_path),
                    item.message,
                ),
            )
        ]

    def required_channels(self, test_id: str) -> tuple[str, ...]:
        groups = self.matrix.get("channel_requirements", {}).get(test_id, [])
        channels: set[str] = set()
        for group in groups:
            definition = self.instrumentation["channel_groups"].get(group)
            if not isinstance(definition, dict):
                raise ValueError(
                    f"unknown instrumentation channel group for {test_id}: {group}"
                )
            channels.update(definition.get("required", []))
        return tuple(sorted(channels))

    def _bundle_path(self, bundle: Path, relative: Any, field: str) -> Path:
        if not isinstance(relative, str) or not relative:
            raise ValueError(f"{field} must be a relative path")
        path = (bundle / relative).resolve()
        try:
            path.relative_to(bundle.resolve())
        except ValueError as exc:
            raise ValueError(f"{field} escapes the bundle: {relative}") from exc
        return path

    def _load_bundle(self, bundle: Path) -> tuple[dict[str, Any], dict[str, Any]]:
        return load_yaml(bundle / "manifest.yaml"), load_yaml(bundle / "result.yaml")

    def _validate_structure(
        self, manifest: dict[str, Any], result: dict[str, Any]
    ) -> list[str]:
        errors = self._schema_errors("run-manifest", manifest) + self._schema_errors(
            "test-result", result
        )
        if errors:
            return errors
        missing_manifest = sorted(REQUIRED_MANIFEST_FIELDS - set(manifest))
        missing_result = sorted(REQUIRED_RESULT_FIELDS - set(result))
        if missing_manifest:
            errors.append(f"manifest missing fields: {', '.join(missing_manifest)}")
        if missing_result:
            errors.append(f"result missing fields: {', '.join(missing_result)}")
        if errors:
            return errors
        if manifest["schema_version"] != 1 or result["schema_version"] != 1:
            errors.append("manifest and result schema_version must be 1")
        for field in ("campaign_id", "unit_id", "build_id", "run_id", "test_id"):
            if not isinstance(manifest[field], str) or not manifest[field].strip():
                errors.append(f"manifest.{field} must be a non-empty string")
        if manifest.get("test_id") not in self.test_ids:
            errors.append(f"unknown EVT0 test_id: {manifest.get('test_id')}")
        try:
            start = _datetime(manifest["start_time_utc"], "manifest.start_time_utc")
            result_start = _datetime(
                result["time_range_utc"]["start"], "result.time_range_utc.start"
            )
            result_end = _datetime(
                result["time_range_utc"]["end"], "result.time_range_utc.end"
            )
            if result_start < start or result_end <= result_start:
                errors.append(
                    "result time range must begin at/after manifest start and end later"
                )
        except (KeyError, TypeError, ValueError) as exc:
            errors.append(str(exc))
        configuration = manifest.get("configuration")
        if not isinstance(configuration, dict):
            errors.append("manifest.configuration must be a mapping")
        else:
            for field in (
                "bom_revision",
                "board_revision",
                "enclosure_revision",
                "thermal_stack_revision",
                "firmware_hash",
            ):
                if field not in configuration:
                    errors.append(f"manifest.configuration missing {field}")
            if (
                "firmware_hash" in configuration
                and len(str(configuration["firmware_hash"])) < 16
            ):
                errors.append("manifest.configuration.firmware_hash is too short")
        workload = manifest.get("workload")
        if (
            not isinstance(workload, dict)
            or not isinstance(workload.get("artifact_hashes"), list)
            or not workload["artifact_hashes"]
        ):
            errors.append("manifest.workload.artifact_hashes must be a non-empty list")
        elif any(len(str(value)) < 16 for value in workload["artifact_hashes"]):
            errors.append("manifest.workload contains an invalid artifact hash")
        instrumentation = manifest.get("instrumentation")
        if (
            not isinstance(instrumentation, dict)
            or not isinstance(instrumentation.get("calibration_ids"), list)
            or not instrumentation["calibration_ids"]
        ):
            errors.append(
                "manifest.instrumentation.calibration_ids must be a non-empty list"
            )
        if result.get("manifest_path") != "manifest.yaml":
            errors.append(
                "result.manifest_path must be manifest.yaml inside the preserved bundle"
            )
        if result.get("validity") not in {"valid", "invalid", "aborted"}:
            errors.append("result.validity has an invalid value")
        if result.get("disposition") not in {
            "pass",
            "fail",
            "blocked",
            "review_required",
        }:
            errors.append("result.disposition has an invalid value")
        if result.get("disposition") == "pass" and (
            not isinstance(result.get("reviewers"), list)
            or not result["reviewers"]
            or any(
                not isinstance(item, str) or not item.strip()
                for item in result["reviewers"]
            )
        ):
            errors.append("passing result requires named engineering reviewers")
        test = next(
            (
                entry
                for entry in self.matrix["sequence"]
                if entry["id"] == manifest.get("test_id")
            ),
            None,
        )
        if test and test["state"].startswith("prohibited"):
            errors.append(f"{test['id']} remains prohibited by the EVT0 plan")
        if (
            test
            and isinstance(manifest.get("workload"), dict)
            and manifest["workload"].get("workload_id") != test["workload"]
        ):
            errors.append(f"{test['id']} workload does not match the test matrix")
        if not isinstance(result.get("raw_data"), list) or not result["raw_data"]:
            errors.append("result.raw_data must be a non-empty list")
        if (
            not isinstance(result.get("required_channel_status"), dict)
            or not result["required_channel_status"]
        ):
            errors.append("result.required_channel_status must be a non-empty mapping")
        elif manifest.get("test_id") in self.test_ids:
            missing_channels = sorted(
                set(self.required_channels(manifest["test_id"]))
                - set(result["required_channel_status"])
            )
            if missing_channels:
                errors.append(
                    "required_channel_status missing channels: "
                    + ", ".join(missing_channels)
                )
        return errors

    def _verify_artifacts(
        self, bundle: Path, result: dict[str, Any]
    ) -> tuple[list[str], list[Path]]:
        errors: list[str] = []
        csv_paths: list[Path] = []
        for index, artifact in enumerate(result.get("raw_data", [])):
            if not isinstance(artifact, dict) or not {
                "path",
                "sha256",
                "format",
                "source",
            }.issubset(artifact):
                errors.append(f"raw_data[{index}] is structurally incomplete")
                continue
            try:
                path = self._bundle_path(
                    bundle, artifact["path"], f"raw_data[{index}].path"
                )
            except ValueError as exc:
                errors.append(str(exc))
                continue
            if not path.is_file():
                errors.append(f"raw artifact is missing: {artifact['path']}")
            elif (
                not _valid_hash(artifact["sha256"])
                or _sha256(path).lower() != artifact["sha256"].lower()
            ):
                errors.append(f"raw artifact hash mismatch: {artifact['path']}")
            elif str(artifact["format"]).lower() == "csv":
                csv_paths.append(path)
        for index, artifact in enumerate(result.get("analysis_artifacts", [])):
            if not isinstance(artifact, dict) or not {"path", "sha256"}.issubset(
                artifact
            ):
                errors.append(f"analysis_artifacts[{index}] is structurally incomplete")
                continue
            try:
                path = self._bundle_path(
                    bundle, artifact["path"], f"analysis_artifacts[{index}].path"
                )
            except ValueError as exc:
                errors.append(str(exc))
                continue
            if (
                not path.is_file()
                or not _valid_hash(artifact["sha256"])
                or _sha256(path).lower() != artifact["sha256"].lower()
            ):
                errors.append(
                    f"analysis artifact hash mismatch or missing: {artifact['path']}"
                )
        return errors, csv_paths

    def _verify_calibrations(self, bundle: Path, manifest: dict[str, Any]) -> list[str]:
        errors: list[str] = []
        try:
            run_start = _datetime(manifest["start_time_utc"], "manifest.start_time_utc")
        except (KeyError, ValueError):
            return ["calibration validity cannot be checked without a valid run start"]
        ids = manifest.get("instrumentation", {}).get("calibration_ids", [])
        covered_channels: set[str] = set()
        for calibration_id in ids:
            record_path = bundle / "calibrations" / f"{calibration_id}.yaml"
            try:
                record = load_yaml(record_path)
                schema_errors = self._schema_errors("calibration", record)
                if schema_errors:
                    errors.extend(schema_errors)
                    continue
                if (
                    record.get("schema_version") != 1
                    or record.get("calibration_id") != calibration_id
                ):
                    errors.append(f"calibration identity mismatch: {calibration_id}")
                    continue
                valid_from = _datetime(
                    record["valid_from_utc"],
                    f"calibration {calibration_id} valid_from_utc",
                )
                valid_until = _datetime(
                    record["valid_until_utc"],
                    f"calibration {calibration_id} valid_until_utc",
                )
                if not valid_from <= run_start <= valid_until:
                    errors.append(
                        f"calibration is not current at run start: {calibration_id}"
                    )
                if not isinstance(record.get("channels"), list):
                    errors.append(f"calibration channels are missing: {calibration_id}")
                else:
                    covered_channels.update(record["channels"])
                certificate = record["certificate"]
                certificate_path = self._bundle_path(
                    bundle,
                    certificate["path"],
                    f"calibration {calibration_id} certificate",
                )
                if (
                    not certificate_path.is_file()
                    or not _valid_hash(certificate["sha256"])
                    or _sha256(certificate_path).lower()
                    != certificate["sha256"].lower()
                ):
                    errors.append(
                        f"calibration certificate hash mismatch or missing: {calibration_id}"
                    )
            except (OSError, KeyError, TypeError, ValueError) as exc:
                errors.append(f"invalid calibration {calibration_id}: {exc}")
        required = set(self.required_channels(manifest.get("test_id", "")))
        uncovered = sorted(required - covered_channels)
        if uncovered:
            errors.append(
                "required channels lack calibration coverage: " + ", ".join(uncovered)
            )
        return errors

    def _read_rows(
        self, csv_paths: list[Path]
    ) -> tuple[list[list[dict[str, float]]], list[str]]:
        tables: list[list[dict[str, float]]] = []
        errors: list[str] = []
        for path in csv_paths:
            try:
                rows: list[dict[str, float]] = []
                with path.open("r", encoding="utf-8-sig", newline="") as stream:
                    reader = csv.DictReader(stream)
                    if not reader.fieldnames or len(reader.fieldnames) != len(
                        set(reader.fieldnames)
                    ):
                        raise ValueError("missing or duplicate CSV header")
                    for row in reader:
                        if None in row:
                            raise ValueError("CSV row has more fields than its header")
                        converted: dict[str, float] = {}
                        for key, value in row.items():
                            if key and value not in (None, ""):
                                number = float(value)
                                if not math.isfinite(number):
                                    raise ValueError(f"non-finite value in {key}")
                                converted[key] = number
                        rows.append(converted)
                tables.append(rows)
            except (OSError, UnicodeError, ValueError) as exc:
                errors.append(f"cannot parse raw CSV {path.name}: {exc}")
        return tables, errors

    def _objective_rows(
        self, test_id: str, tables: list[list[dict[str, float]]], result: dict[str, Any]
    ) -> tuple[list[dict[str, float]], list[str]]:
        """Evaluate required activity in one hash-verified CSV time series."""
        contract = self.objective_measurements.get(test_id)
        if contract is None:
            return (tables[0] if tables else []), []
        columns = contract["required_columns"]
        matches = [
            table
            for table in tables
            if len(table) >= 2
            and all(all(column in row for column in columns) for row in table)
        ]
        if len(matches) != 1:
            return [], [
                f"{test_id} requires exactly one CSV with all required columns: {', '.join(columns)}"
            ]
        rows = matches[0]
        errors: list[str] = []
        times = [row["elapsed_s"] for row in rows]
        if any(right <= left for left, right in zip(times, times[1:], strict=False)):
            errors.append(f"{test_id} raw elapsed_s must increase strictly")
        duration = times[-1] - times[0]
        if duration < contract.get("minimum_duration_s", 0):
            errors.append(f"{test_id} raw duration is below the test minimum")
        try:
            time_range = result["time_range_utc"]
            declared_duration = (
                _datetime(time_range["end"], "result end")
                - _datetime(time_range["start"], "result start")
            ).total_seconds()
            if abs(duration - declared_duration) > 1:
                errors.append(f"{test_id} raw duration differs from result time range")
        except (KeyError, TypeError, ValueError):
            errors.append(f"{test_id} result time range cannot be verified")
        for column in contract.get("positive_columns", []):
            if any(row[column] <= 0 for row in rows):
                errors.append(f"{test_id} requires positive {column} samples")
        for column in contract.get("positive_deltas", []):
            if rows[-1][column] <= rows[0][column]:
                errors.append(f"{test_id} requires positive raw activity: {column}")
        for column in contract.get("negative_deltas", []):
            if rows[-1][column] >= rows[0][column]:
                errors.append(f"{test_id} requires decreasing raw activity: {column}")
        for column in contract.get("zero_columns", []):
            if any(row[column] != 0 for row in rows):
                errors.append(f"{test_id} requires zero {column} events")
        for column in contract.get("one_columns", []):
            if rows[-1][column] != 1:
                errors.append(f"{test_id} requires confirmed {column}")
        for column in contract.get("observed_one_columns", []):
            if not any(row[column] == 1 for row in rows):
                errors.append(f"{test_id} requires observed {column}")
        for column, floor in contract.get("minimum_final", {}).items():
            if rows[-1][column] < floor:
                errors.append(f"{test_id} {column} is below the required configuration")
        for lower, upper in contract.get("final_order", []):
            if rows[-1][lower] > rows[-1][upper]:
                errors.append(f"{test_id} {lower} exceeds {upper}")
        for column, floor in contract.get("minimum_columns", {}).items():
            if any(row[column] < floor for row in rows):
                errors.append(f"{test_id} {column} is below the test condition")
        for column, ceiling in contract.get("maximum_columns", {}).items():
            if any(row[column] > ceiling for row in rows):
                errors.append(f"{test_id} {column} exceeds the test condition")
        if "maximum_input_power_w" in contract and any(
            row["input_voltage_v"] * row["input_current_a"]
            > contract["maximum_input_power_w"]
            for row in rows
        ):
            errors.append(f"{test_id} measured input power exceeds the EVT cap")
        if len(result.get("analysis_artifacts", [])) < contract.get(
            "analysis_artifacts_min", 0
        ):
            errors.append(f"{test_id} needs hash-verified analysis artifacts")
        return rows, errors

    def _verify_memory_probe(
        self,
        bundle: Path,
        manifest: dict[str, Any],
        result: dict[str, Any],
        rows: list[dict[str, float]],
    ) -> list[str]:
        if manifest.get("test_id") != "M20":
            return []
        artifacts = [
            item
            for item in result.get("analysis_artifacts", [])
            if isinstance(item, dict)
            and item.get("path") == "analysis/memory-probe.json"
        ]
        if len(artifacts) != 1:
            return ["M20 needs exactly one analysis/memory-probe.json artifact"]
        artifact = artifacts[0]
        try:
            path = self._bundle_path(bundle, artifact["path"], "M20 memory probe")
            if (
                not path.is_file()
                or path.stat().st_size > 100_000
                or _sha256(path).lower() != artifact["sha256"].lower()
            ):
                raise ValueError(
                    "M20 memory probe file is missing, oversized, or stale"
                )
            probe = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(probe, dict):
                raise ValueError("M20 memory probe must be a JSON object")
        except (KeyError, TypeError, ValueError, OSError, UnicodeError) as exc:
            return [f"M20 memory probe is invalid: {exc}"]
        errors: list[str] = []
        if (
            probe.get("status") != "pass"
            or probe.get("unit_id") != manifest.get("unit_id")
            or probe.get("build_id") != manifest.get("build_id")
        ):
            errors.append("M20 memory probe status or build identity differs")
        if (
            probe.get("pattern_algorithm") != PATTERN_ALGORITHM
            or probe.get("pattern_region_bytes") != PATTERN_REGION
        ):
            errors.append("M20 memory probe lacks full-allocation pattern proof")
        for field, floor in (
            ("os_total_physical_bytes", DEFAULT_MIN_TOTAL),
            ("allocated_bytes", DEFAULT_ALLOCATION),
            ("resident_delta_bytes", DEFAULT_ALLOCATION * 99 // 100),
            ("verified_pages", DEFAULT_ALLOCATION // PAGE),
            ("verified_bytes", DEFAULT_ALLOCATION),
        ):
            value = probe.get(field)
            if not isinstance(value, int) or isinstance(value, bool) or value < floor:
                errors.append(f"M20 memory probe {field} is below proof minimum")
        if probe.get("memory_errors") != 0:
            errors.append("M20 memory probe memory_errors must be zero")
        if probe.get("swap_used_delta_bytes") != 0 and not (
            probe.get("os_name") == "Windows"
            and probe.get("swap_used_delta_bytes") is None
        ):
            errors.append(
                "M20 memory probe swap use must be zero or unavailable on Windows"
            )
        allocation = probe.get("allocated_bytes")
        if isinstance(allocation, int) and allocation >= DEFAULT_ALLOCATION:
            resident = probe.get("resident_delta_bytes")
            pages = probe.get("verified_pages")
            verified = probe.get("verified_bytes")
            if not isinstance(resident, int) or resident < allocation * 99 // 100:
                errors.append("M20 resident memory is below 99 percent of allocation")
            if not isinstance(pages, int) or pages < (allocation + PAGE - 1) // PAGE:
                errors.append("M20 page verification does not cover allocation")
            if not isinstance(verified, int) or verified != allocation:
                errors.append("M20 byte verification does not cover allocation")
        if rows and len(errors) == 0:
            final = rows[-1]
            total = probe["os_total_physical_bytes"]
            if final["installed_bytes"] < total:
                errors.append("M20 reported installed memory is below OS capacity")
            if abs(final["usable_bytes"] - total) > 1_000_000_000:
                errors.append("M20 usable memory differs from the OS probe")
            if final["allocated_bytes"] != probe["allocated_bytes"]:
                errors.append("M20 allocated memory differs from the resident probe")
            if final["work_units_completed"] < probe["verified_pages"]:
                errors.append("M20 workload counter omits verified pages")
        return errors

    def calculate_metrics(
        self, rows: list[dict[str, float]]
    ) -> dict[str, dict[str, Any]]:
        metrics: dict[str, dict[str, Any]] = {}
        for metric_id, definition in self.metric_definitions["metrics"].items():
            columns = definition["columns"]
            available = bool(rows) and all(
                any(column in row for row in rows) for column in columns
            )
            if not available:
                metrics[metric_id] = {
                    "value": None,
                    "unit": definition["unit"],
                    "method": definition["method"],
                    "confidence": "unavailable",
                }
                continue
            method = definition["method"]
            if method == "mean":
                values = [row[columns[0]] for row in rows if columns[0] in row]
                value = sum(values) / len(values)
            elif method == "maximum":
                value = max(row[columns[0]] for row in rows if columns[0] in row)
            elif method == "maximum_across":
                value = max(
                    row[column] for row in rows for column in columns if column in row
                )
            elif method == "last_minus_first":
                values = [row[columns[0]] for row in rows if columns[0] in row]
                value = values[-1] - values[0]
            elif method == "trapezoidal_integral_divide_3600":
                points = [
                    (row[columns[0]], row[columns[1]])
                    for row in rows
                    if all(column in row for column in columns)
                ]
                value = (
                    sum(
                        (right[0] - left[0]) * (right[1] + left[1]) / 2
                        for left, right in zip(points, points[1:], strict=False)
                    )
                    / 3600
                )
            elif method in {"delta_over_duration", "throughput_divide_mean_power"}:
                time_values = [row[columns[0]] for row in rows if columns[0] in row]
                work_values = [row[columns[1]] for row in rows if columns[1] in row]
                throughput = (work_values[-1] - work_values[0]) / (
                    time_values[-1] - time_values[0]
                )
                if method == "delta_over_duration":
                    value = throughput
                else:
                    power_values = [
                        row[columns[2]] for row in rows if columns[2] in row
                    ]
                    value = throughput / (sum(power_values) / len(power_values))
            else:
                raise ValueError(f"unsupported metric method: {method}")
            metrics[metric_id] = {
                "value": round(value, 6),
                "unit": definition["unit"],
                "method": method,
                "confidence": "derived",
            }
        return metrics

    def review_bundle(self, bundle: Path) -> dict[str, Any]:
        bundle = bundle.resolve()
        errors: list[str] = []
        try:
            manifest, result = self._load_bundle(bundle)
        except (OSError, ValueError) as exc:
            return {
                "integrity_errors": [str(exc)],
                "objective_disposition": "REJECTED_INVALID_EVIDENCE",
            }
        errors.extend(self._validate_structure(manifest, result))
        if errors:
            return {
                "campaign_id": manifest.get("campaign_id"),
                "run_id": manifest.get("run_id"),
                "test_id": manifest.get("test_id"),
                "unit_id": manifest.get("unit_id"),
                "build_id": manifest.get("build_id"),
                "integrity_errors": errors,
                "objective_disposition": "REJECTED_INVALID_EVIDENCE",
                "evidence_effect": "invalid run structure; no requirement verification",
            }
        artifact_errors, csv_paths = self._verify_artifacts(bundle, result)
        errors.extend(artifact_errors)
        errors.extend(self._verify_calibrations(bundle, manifest))
        tables, csv_errors = self._read_rows(csv_paths)
        errors.extend(csv_errors)
        rows, measurement_errors = self._objective_rows(
            manifest.get("test_id"), tables, result
        )
        errors.extend(measurement_errors)
        errors.extend(self._verify_memory_probe(bundle, manifest, result, rows))
        interface_activity: dict[str, float | None] = {}
        if manifest.get("test_id") == "I20":
            for counter in INTERFACE_COUNTERS:
                values = [row[counter] for row in rows if counter in row]
                delta = values[-1] - values[0] if len(values) >= 2 else None
                interface_activity[counter] = delta
        try:
            calculated_metrics = self.calculate_metrics(rows) if not csv_errors else {}
        except (ValueError, ZeroDivisionError) as exc:
            errors.append(f"metric calculation failed: {exc}")
            calculated_metrics = {}

        correlations: list[dict[str, Any]] = []
        for correlation in result.get("model_correlations", []):
            try:
                residual = correlation["measured"] - correlation["predicted"]
                passed = abs(residual) <= correlation["tolerance_absolute"]
                correlations.append(
                    {**correlation, "residual": round(residual, 6), "passed": passed}
                )
            except (KeyError, TypeError) as exc:
                errors.append(f"invalid model correlation: {exc}")
        required_correlations = self.objective_measurements.get(
            manifest.get("test_id"), {}
        ).get("correlations_min", 0)
        if len(correlations) < required_correlations:
            errors.append(
                f"{manifest.get('test_id')} needs at least {required_correlations} model correlations"
            )
        deviations = result.get("deviations", [])
        required_deviation_fields = {
            "deviation_id",
            "requirement",
            "observed_evidence",
            "root_cause_status",
            "affected_artifacts",
            "disposition",
        }
        for index, deviation in enumerate(deviations):
            if not isinstance(
                deviation, dict
            ) or not required_deviation_fields.issubset(deviation):
                errors.append(f"deviations[{index}] is structurally incomplete")
            elif deviation["disposition"] not in {
                "open",
                "accepted",
                "rejected",
                "superseded",
            }:
                errors.append(f"deviations[{index}] has an invalid disposition")
        open_deviations = [
            item
            for item in deviations
            if isinstance(item, dict) and item.get("disposition") == "open"
        ]
        channel_failures = sorted(
            key
            for key, value in result.get("required_channel_status", {}).items()
            if value is not True
        )
        hard_stops = result.get("hard_stop_events", [])
        max_skin = calculated_metrics.get("maximum_skin_c", {}).get("value")
        max_battery = calculated_metrics.get("maximum_battery_temperature_c", {}).get(
            "value"
        )
        limit_events: list[str] = []
        if (
            isinstance(max_skin, (int, float))
            and max_skin
            >= self.matrix["global_pass_fail"]["hard_stops"]["maximum_skin_c"]
        ):
            limit_events.append("maximum_skin_c")
        if isinstance(max_battery, (int, float)) and max_battery >= 40.0:
            limit_events.append("pre_supplier_battery_abort_c")
        objective_failure = bool(
            hard_stops
            or limit_events
            or channel_failures
            or any(not item["passed"] for item in correlations)
        )
        if errors:
            disposition = "REJECTED_INVALID_EVIDENCE"
        elif (
            result.get("validity") in {"invalid", "aborted"}
            or hard_stops
            or limit_events
        ):
            disposition = "ABORTED_OR_HARD_STOP"
        elif channel_failures:
            disposition = "BLOCKED_EVIDENCE_QUALITY"
        elif (
            any(not item["passed"] for item in correlations)
            or open_deviations
            or result.get("disposition") == "review_required"
        ):
            disposition = "ENGINEERING_REVIEW_REQUIRED"
        elif result.get("disposition") == "fail" or objective_failure:
            disposition = "VALID_FAIL"
        elif result.get("disposition") == "pass":
            disposition = "VALID_PASS"
        else:
            disposition = "BLOCKED"
        if objective_failure and result.get("disposition") == "pass":
            errors.append(
                "reported pass contradicts objective hard-stop, channel, or correlation evidence"
            )
            disposition = "REJECTED_INVALID_EVIDENCE"
        return {
            "campaign_id": manifest.get("campaign_id"),
            "run_id": manifest.get("run_id"),
            "test_id": manifest.get("test_id"),
            "unit_id": manifest.get("unit_id"),
            "build_id": manifest.get("build_id"),
            "configuration_sha256": hashlib.sha256(
                json.dumps(
                    manifest.get("configuration"), sort_keys=True, default=str
                ).encode()
            ).hexdigest(),
            "integrity_errors": errors,
            "calculated_metrics": calculated_metrics,
            "interface_activity": interface_activity,
            "model_correlations": correlations,
            "deviation_count": len(deviations),
            "open_deviation_count": len(open_deviations),
            "required_channel_failures": channel_failures,
            "hard_stop_event_count": len(hard_stops),
            "calculated_limit_events": limit_events,
            "reported_validity": result.get("validity"),
            "reported_disposition": result.get("disposition"),
            "objective_disposition": disposition,
            "evidence_effect": "run evidence under review; no automatic requirement verification",
        }

    def ingest(
        self, bundle: Path, received_at: str, received_by: str
    ) -> tuple[Path, dict[str, Any]]:
        review = self.review_bundle(bundle)
        if review["integrity_errors"]:
            raise ValueError(
                "EVT0 bundle rejected: " + "; ".join(review["integrity_errors"])
            )
        _datetime(received_at, "received_at")
        if not received_by.strip():
            raise ValueError("received_by must not be empty")
        campaign_id = review["campaign_id"]
        run_id = review["run_id"]
        if not all(
            isinstance(value, str)
            and value
            and value.replace("-", "").replace("_", "").isalnum()
            for value in (campaign_id, run_id)
        ):
            raise ValueError("campaign_id and run_id must be path-safe identifiers")
        destination = self.campaign_root / campaign_id / run_id
        if destination.exists():
            raise ValueError(
                f"EVT0 campaign run already exists: {campaign_id}/{run_id}"
            )
        shutil.copytree(bundle, destination)
        file_hashes = {
            path.relative_to(destination).as_posix(): _sha256(path)
            for path in sorted(destination.rglob("*"))
            if path.is_file()
        }
        receipt = {
            "receipt_version": 1,
            "campaign_id": campaign_id,
            "run_id": run_id,
            "received_at": received_at,
            "received_by": received_by,
            "file_hashes": file_hashes,
            "review": review,
            "authority_boundary": "ingested_run_evidence_not_automatic_verification",
        }
        receipt_path = destination / "receipt.yaml"
        receipt_path.write_text(dump_yaml(receipt), encoding="utf-8", newline="\n")
        return receipt_path, review

    def build_campaign_report(self) -> dict[str, Any]:
        items: list[dict[str, Any]] = []
        for receipt_path in sorted(self.campaign_root.glob("*/*/receipt.yaml")):
            bundle = receipt_path.parent
            receipt = load_yaml(receipt_path)
            integrity_errors: list[str] = []
            for relative, expected in receipt.get("file_hashes", {}).items():
                path = self._bundle_path(bundle, relative, "receipt.file_hashes")
                if not path.is_file() or _sha256(path) != expected:
                    integrity_errors.append(f"receipt hash mismatch: {relative}")
            review = self.review_bundle(bundle)
            review["integrity_errors"] = integrity_errors + review["integrity_errors"]
            if integrity_errors:
                review["objective_disposition"] = "REJECTED_INVALID_EVIDENCE"
            items.append(review)
        required = set(self.matrix["required_for_evt0_evidence_gate"])
        selected_group, passing, groups = _coherent_coverage(items, required)
        missing = sorted(required - passing)
        if not items:
            gate = "EMPTY_CAMPAIGN"
        elif any(
            item["objective_disposition"] == "REJECTED_INVALID_EVIDENCE"
            for item in items
        ):
            gate = "BLOCKED_INVALID_EVIDENCE"
        elif missing:
            gate = "CAMPAIGN_INCOMPLETE"
        else:
            gate = "OBJECTIVE_EVIDENCE_REVIEW_READY"
        return {
            "EVT0_CAMPAIGN_GATE": gate,
            "summary": {
                "ingested_run_count": len(items),
                "required_test_count": len(required),
                "passing_required_test_count": len(required) - len(missing),
            },
            "missing_or_nonpassing_required_tests": missing,
            "coherent_evidence_group": selected_group,
            "evidence_groups": groups,
            "runs": items,
            "next_actions": [
                "Satisfy supplier, Phase 2, safety, calibration, and authorization prerequisites before physical work.",
                "Ingest only hash-verifiable run bundles; resolve invalid evidence and open deviations.",
                "Complete every required test and model-correlation review before an EVT0 evidence gate decision.",
            ],
            "caveat": "An objective evidence review queue does not claim prototype readiness, safety validation, certification, or product verification.",
        }

    def generate_campaign_report(self) -> Path:
        destination = self.repo_root / "reports" / "program" / "evt0-campaign.yaml"
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(
            dump_yaml(self.build_campaign_report()), encoding="utf-8", newline="\n"
        )
        return destination
