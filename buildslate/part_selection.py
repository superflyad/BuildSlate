"""Audit a released part set before it can count toward hardware readiness."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any

from buildslate.io import load_yaml

RELEASE = Path("engineering/hardware/released/selected-bom.json")
STRATEGY = Path("validation/evt0/bom-strategy.yaml")
CORE_ROLES = (
    "compute_platform",
    "memory",
    "storage",
    "battery_pack",
    "display_module",
)
MEMORY_FLOOR_BYTES = 128_000_000_000
MEMORY_PLACEMENTS = frozenset({"board", "on_package"})
STORAGE_FLOOR_BYTES = 1_000_000_000_000


def _text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _positive_number(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
        and value > 0
    )


def _document_error(root: Path, role: str, kind: str, record: Any) -> str | None:
    if not isinstance(record, dict) or not _text(record.get("path")):
        return f"{kind}: missing controlled source path"
    if not _text(record.get("sha256")):
        return f"{kind}: missing source SHA-256"
    allowed = (root / "engineering/hardware/released/parts" / role).resolve()
    target = (root / record["path"]).resolve()
    if not target.is_relative_to(allowed) or target == allowed:
        return f"{kind}: source is outside the released part directory"
    if target.suffix.lower() in {".md", ".yaml", ".yml", ".json"}:
        return f"{kind}: planning or status file is not supplier evidence"
    if not target.is_file():
        return f"{kind}: source file is missing"
    if hashlib.sha256(target.read_bytes()).hexdigest() != record["sha256"].lower():
        return f"{kind}: source hash mismatch"
    return None


def _memory_topology_errors(parts: dict[str, Any]) -> list[str]:
    """Bind a declared 128 GB configuration to exact parts and source bytes."""
    compute_part = parts["compute_platform"]
    memory_part = parts["memory"]
    compute = compute_part["capabilities"]
    memory = memory_part["capabilities"]
    topology = memory.get("qualified_topology")
    if not isinstance(topology, dict):
        return ["Missing supplier-qualified memory topology record"]
    errors: list[str] = []
    placement = memory.get("placement")
    if not isinstance(placement, str) or placement not in MEMORY_PLACEMENTS:
        errors.append("Memory placement must be board or on_package")
    if topology.get("placement") != placement:
        errors.append("Memory topology placement differs from selected memory")
    supported_placements = compute.get("supported_memory_placements")
    if (
        not isinstance(supported_placements, list)
        or placement not in supported_placements
    ):
        errors.append("Memory placement is not supported by selected compute SKU")
    for field in ("id", "controller_mpn", "memory_mpn"):
        if not _text(topology.get(field)):
            errors.append(f"Memory topology is missing {field}")
    if topology.get("controller_mpn") != compute_part.get("mpn"):
        errors.append(
            "Memory topology controller MPN differs from selected compute part"
        )
    if topology.get("memory_mpn") != memory_part.get("mpn"):
        errors.append("Memory topology memory MPN differs from selected memory part")
    if topology.get("package_count") != memory_part.get("quantity"):
        errors.append("Memory topology package count differs from selected quantity")
    if topology.get("capacity_bytes_per_package") != memory.get(
        "capacity_bytes_per_package"
    ):
        errors.append("Memory topology package capacity differs from selected part")
    package_count = topology.get("package_count")
    package_capacity = topology.get("capacity_bytes_per_package")
    total = (
        package_count * package_capacity
        if isinstance(package_count, int)
        and not isinstance(package_count, bool)
        and _positive_number(package_capacity)
        else 0
    )
    if total < MEMORY_FLOOR_BYTES or topology.get("total_capacity_bytes") != total:
        errors.append("Memory topology does not establish the 128 GB floor")
    if not _positive_number(compute.get("max_memory_bytes")) or total > compute.get(
        "max_memory_bytes", 0
    ):
        errors.append("Memory topology exceeds the selected controller limit")
    if placement == "on_package":
        if (
            compute.get("configured_memory_bytes") != total
            or memory.get("included_in_compute_sku") is not True
        ):
            errors.append(
                "On-package memory does not match the orderable compute SKU configuration"
            )
    elif placement == "board":
        if memory.get("included_in_compute_sku") is True:
            errors.append("Board memory cannot be declared included in compute SKU")
        if compute.get("configured_memory_bytes") not in (None, 0):
            errors.append("Board-only map cannot use a memory-on-package compute SKU")
    for field, role, kind in (
        ("controller_support_sha256", "memory", "controller_support"),
        ("reference_design_sha256", "compute_platform", "reference_design"),
    ):
        evidence = parts[role].get("evidence")
        source = evidence.get(kind) if isinstance(evidence, dict) else None
        expected = source.get("sha256") if isinstance(source, dict) else None
        if not _text(topology.get(field)) or topology[field] != expected:
            errors.append(f"Memory topology {field} is not bound to selected source")
    return errors


def audit(root: Path, strategy: dict[str, Any] | None = None) -> dict[str, Any]:
    """Require exact MPNs, controlled sources, and basic interface compatibility."""
    root = root.resolve()
    strategy = strategy or load_yaml(root / STRATEGY)
    path = root / RELEASE
    cellular_required = strategy["roles"]["cellular"]["status"] == "selected"
    roles = (*CORE_ROLES, "cellular") if cellular_required else CORE_ROLES
    if not path.is_file():
        return {
            "status": "missing",
            "source": RELEASE.as_posix(),
            "errors": ["No released selected BOM"],
            "roles": [
                {"id": role, "selected": False, "reasons": ["No released selected BOM"]}
                for role in roles
            ],
        }
    try:
        release = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return {
            "status": "blocked",
            "source": RELEASE.as_posix(),
            "errors": [f"Cannot read released selected BOM: {exc}"],
            "roles": [
                {"id": role, "selected": False, "reasons": ["Invalid selected BOM"]}
                for role in roles
            ],
        }
    errors: list[str] = []
    if not isinstance(release, dict) or release.get("schema_version") != 1:
        errors.append("Selected BOM must use schema_version 1")
        release = {}
    if release.get("device") != "slate-pocket-v1r":
        errors.append("Selected BOM device identity is incorrect")
    if not _text(release.get("revision")) or not _text(release.get("reviewed_by")):
        errors.append("Selected BOM needs a revision and named engineering reviewer")
    parts = release.get("parts")
    if not isinstance(parts, dict):
        parts = {}
        errors.append("Selected BOM parts must be a mapping")
    if set(parts) != set(roles):
        errors.append(
            "Selected BOM role coverage does not match the released configuration"
        )
    if strategy["metadata"].get("selected_parts") != len(roles):
        errors.append("Strategy selected_parts must equal released BOM role count")
    results: list[dict[str, Any]] = []
    for role in roles:
        part = parts.get(role)
        role_errors: list[str] = []
        source = strategy["roles"][role]
        if not isinstance(part, dict):
            results.append(
                {
                    "id": role,
                    "selected": False,
                    "reasons": ["Role absent from released BOM"],
                }
            )
            continue
        for field in ("manufacturer", "mpn", "revision"):
            if not _text(part.get(field)):
                role_errors.append(f"Missing {field}")
        if source.get("status") != "selected" or part.get("mpn") != source.get(
            "selected_candidate"
        ):
            role_errors.append(
                "Strategy selection does not match the exact released MPN"
            )
        on_package_memory = (
            role == "memory"
            and isinstance(part.get("capabilities"), dict)
            and part["capabilities"].get("placement") == "on_package"
        )
        required_availability = (
            "included_in_compute_sku" if on_package_memory else "purchasable"
        )
        if (
            part.get("availability") != required_availability
            or part.get("lifecycle") != "active"
        ):
            role_errors.append(
                "On-package DRAM must be included in an orderable compute SKU and active"
                if on_package_memory
                else "Part must be purchasable and active"
            )
        quantity = part.get("quantity")
        if not isinstance(quantity, int) or isinstance(quantity, bool) or quantity <= 0:
            role_errors.append("Quantity must be a positive integer")
        if (
            isinstance(source.get("quantity_per_unit"), int)
            and quantity != source["quantity_per_unit"]
        ):
            role_errors.append("Quantity differs from the approved strategy")
        evidence = part.get("evidence")
        if not isinstance(evidence, dict):
            evidence = {}
        required = source.get("required_evidence", [])
        if not required:
            role_errors.append("Strategy has no required evidence types for this role")
        for kind in required:
            problem = _document_error(root, role, kind, evidence.get(kind))
            if problem:
                role_errors.append(problem)
        if not isinstance(part.get("capabilities"), dict):
            role_errors.append("Missing machine-readable capabilities")
        results.append(
            {
                "id": role,
                "selected": not role_errors,
                "reasons": role_errors,
                "mpn": part.get("mpn") if _text(part.get("mpn")) else None,
            }
        )

    def incompatible(role: str, reason: str) -> None:
        target = next(item for item in results if item["id"] == role)
        target["selected"] = False
        target["reasons"].append(reason)

    if all(
        isinstance(parts.get(role), dict)
        and isinstance(parts[role].get("capabilities"), dict)
        for role in CORE_ROLES
    ):
        compute = parts["compute_platform"]["capabilities"]
        memory = parts["memory"]["capabilities"]
        storage = parts["storage"]["capabilities"]
        battery = parts["battery_pack"]["capabilities"]
        display = parts["display_module"]["capabilities"]
        total_memory = (
            memory.get("capacity_bytes_per_package", 0)
            * parts["memory"].get("quantity", 0)
            if _positive_number(memory.get("capacity_bytes_per_package"))
            and isinstance(parts["memory"].get("quantity"), int)
            else 0
        )
        if not _positive_number(compute.get("max_memory_bytes")) or not (
            MEMORY_FLOOR_BYTES <= total_memory <= compute["max_memory_bytes"]
        ):
            incompatible(
                "memory", "128 GB memory topology exceeds or misses host capacity"
            )
        if not _text(memory.get("interface")) or memory.get("interface") != compute.get(
            "memory_interface"
        ):
            incompatible(
                "memory", "Memory interface is not supported by the compute platform"
            )
        for problem in _memory_topology_errors(parts):
            incompatible("memory", problem)
        if (
            not _positive_number(storage.get("capacity_bytes"))
            or storage["capacity_bytes"] < STORAGE_FLOOR_BYTES
        ):
            incompatible(
                "storage", "Storage capacity is below the 1 TB EVT0 configuration"
            )
        storage_interfaces = compute.get("storage_interfaces")
        if (
            not isinstance(storage_interfaces, list)
            or not _text(storage.get("interface"))
            or storage["interface"] not in storage_interfaces
        ):
            incompatible(
                "storage", "Storage interface is not supported by the compute platform"
            )
        if (
            not _positive_number(display.get("diagonal_in"))
            or not 7 <= display["diagonal_in"] <= 8.4
        ):
            incompatible(
                "display_module", "Display diagonal is outside the approved fallback"
            )
        display_interfaces = compute.get("display_interfaces")
        if (
            not isinstance(display_interfaces, list)
            or not _text(display.get("interface"))
            or display["interface"] not in display_interfaces
        ):
            incompatible(
                "display_module",
                "Display interface is not supported by the compute platform",
            )
        if not _positive_number(battery.get("energy_wh")) or not _positive_number(
            battery.get("maximum_validated_charge_w")
        ):
            incompatible(
                "battery_pack", "Battery energy or validated charge limit is missing"
            )
        if cellular_required:
            cellular_part = parts.get("cellular")
            cellular = (
                cellular_part.get("capabilities")
                if isinstance(cellular_part, dict)
                else None
            )
            cellular_interfaces = compute.get("cellular_interfaces")
            if (
                not isinstance(cellular, dict)
                or not isinstance(cellular_interfaces, list)
                or not _text(cellular.get("interface"))
                or cellular["interface"] not in cellular_interfaces
            ):
                incompatible(
                    "cellular",
                    "Cellular interface is not supported by the compute platform",
                )
    elif parts:
        errors.append(
            "Cross-part compatibility cannot be checked without all core capabilities"
        )
    errors.extend(
        f"{item['id']}: {reason}" for item in results for reason in item["reasons"]
    )
    return {
        "status": "pass" if not errors else "blocked",
        "source": RELEASE.as_posix(),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "revision": release.get("revision"),
        "reviewed_by": release.get("reviewed_by"),
        "errors": errors,
        "roles": results,
    }
