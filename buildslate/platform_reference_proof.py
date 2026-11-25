"""Audit the selected platform reference and its 128 GB channel map.

This checks identities, source bytes, and map consistency. It cannot establish
that a supplier approves the topology or that a routed board will boot.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from typing import Any

from buildslate.part_selection import MEMORY_PLACEMENTS
from buildslate.part_selection import RELEASE as SELECTED_BOM

RELEASE = Path("engineering/hardware/released/platform/platform-reference.json")
PMIC_ROOT = Path("engineering/hardware/released/platform/pmic")
ELECTRICAL_BOM = Path("engineering/hardware/released/board.bom.csv")
MEMORY_FLOOR_BYTES = 128_000_000_000
SOURCE_BINDINGS = {
    "compute_package_drawing": ("compute_platform", "package_drawing"),
    "compute_reference_design": ("compute_platform", "reference_design"),
    "compute_rail_map": ("compute_platform", "rail_map"),
    "memory_controller_support": ("memory", "controller_support"),
    "memory_package_drawings": ("memory", "package_drawings"),
    "memory_routing_rules": ("memory", "routing_rules"),
    "storage_host_support": ("storage", "host_support"),
    "storage_pin_map": ("storage", "pin_map"),
}
PMIC_DOCUMENTS = ("datasheet", "package_drawing", "reference_schematic")


def _text(value: Any) -> bool:
    return (
        isinstance(value, str)
        and bool(value.strip())
        and value.strip().lower()
        not in {
            "unknown",
            "placeholder",
            "tbd",
        }
    )


def _integer(value: Any, minimum: int = 1) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= minimum


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _pmic_document_error(root: Path, name: str, record: Any) -> str | None:
    if (
        not isinstance(record, dict)
        or not _text(record.get("path"))
        or not _text(record.get("sha256"))
    ):
        return f"PMIC {name} needs a controlled path and SHA-256"
    allowed = (root / PMIC_ROOT).resolve()
    target = (root / record["path"]).resolve()
    if not target.is_relative_to(allowed) or target == allowed:
        return f"PMIC {name} is outside the controlled PMIC directory"
    if target.suffix.lower() in {".md", ".yaml", ".yml", ".json"}:
        return f"PMIC {name} is a planning or status file"
    if not target.is_file() or _sha(target) != record["sha256"].lower():
        return f"PMIC {name} source is missing or changed"
    return None


def _electrical_parts(path: Path) -> dict[str, str]:
    with path.open("r", encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        if not reader.fieldnames or not {"ref", "mpn"}.issubset(reader.fieldnames):
            raise ValueError("Electrical BOM needs ref and mpn columns")
        parts: dict[str, str] = {}
        for row in reader:
            ref = (row.get("ref") or "").strip()
            mpn = (row.get("mpn") or "").strip()
            if not ref or ref in parts or not mpn:
                raise ValueError("Electrical BOM has blank or duplicate part identity")
            parts[ref] = mpn
        return parts


def _channel_errors(
    release: dict[str, Any], memory: dict[str, Any], compute: dict[str, Any]
) -> list[str]:
    errors: list[str] = []
    channels = release.get("memory_channels")
    packages = release.get("memory_packages")
    controller_width = compute.get("memory_bus_width_bits")
    package_width = memory.get("bus_width_bits")
    placement = release.get("memory_placement")
    if not isinstance(placement, str) or placement not in MEMORY_PLACEMENTS:
        return ["Memory package placement is missing or invalid"]
    if not _integer(controller_width) or not _integer(package_width):
        return ["Selected controller or memory package bus width is missing"]
    if not isinstance(channels, list) or not channels:
        return ["Memory channel map is missing"]
    if not isinstance(packages, list) or not packages:
        return ["Memory package map is missing"]
    widths: dict[str, int] = {}
    for item in channels:
        if (
            not isinstance(item, dict)
            or not _text(item.get("id"))
            or not _integer(item.get("width_bits"))
            or item["id"] in widths
        ):
            errors.append("Memory channel has invalid or duplicate identity and width")
            continue
        widths[item["id"]] = item["width_bits"]
    if sum(widths.values()) > controller_width:
        errors.append("Memory channels exceed the selected controller bus width")
    if len(packages) != release.get("memory_package_count"):
        errors.append("Memory package map count differs from release count")
    refs: set[str] = set()
    lanes: dict[tuple[str, int], set[int]] = {}
    ranks: dict[str, set[int]] = {}
    for item in packages:
        if not isinstance(item, dict):
            errors.append("Memory package map contains an invalid site")
            continue
        ref_key = "ref" if placement == "board" else "package_id"
        ref = item.get(ref_key)
        channel = item.get("channel")
        rank = item.get("rank")
        start = item.get("bit_start")
        if (
            not _text(ref)
            or ref in refs
            or ("package_id" in item if placement == "board" else "ref" in item)
        ):
            errors.append("Memory package has invalid or duplicate placement identity")
        else:
            refs.add(ref)
        if (
            not _text(channel)
            or channel not in widths
            or not _integer(rank, 0)
            or not _integer(start, 0)
        ):
            errors.append(f"{ref}: channel, rank, or lane start is invalid")
            continue
        occupied = set(range(start, start + package_width))
        if max(occupied) >= widths[channel]:
            errors.append(f"{ref}: package lanes exceed channel width")
        key = (channel, rank)
        if lanes.setdefault(key, set()) & occupied:
            errors.append(f"{ref}: memory lanes overlap another package on one rank")
        lanes[key].update(occupied)
        ranks.setdefault(channel, set()).add(rank)
    for channel, rank_set in ranks.items():
        if rank_set != set(range(max(rank_set) + 1)):
            errors.append(f"{channel}: rank numbering has a gap")
        for rank in rank_set:
            if lanes[(channel, rank)] != set(range(widths[channel])):
                errors.append(f"{channel} rank {rank}: data lanes are incomplete")
    if set(widths) != set(ranks):
        errors.append("Memory channel map includes an unused channel")
    return errors


def audit(root: Path) -> dict[str, Any]:
    """Require exact selected parts, source bindings, and complete lane maps."""
    root = root.resolve()
    path = root / RELEASE
    if not path.is_file():
        return {"status": "missing", "errors": ["No released platform reference"]}
    selected_path = root / SELECTED_BOM
    if not selected_path.is_file():
        return {"status": "blocked", "errors": ["Selected BOM is missing"]}
    electrical_path = root / ELECTRICAL_BOM
    if not electrical_path.is_file():
        return {"status": "blocked", "errors": ["Released electrical BOM is missing"]}
    try:
        release = json.loads(path.read_text(encoding="utf-8"))
        selected = json.loads(selected_path.read_text(encoding="utf-8"))
        electrical = _electrical_parts(electrical_path)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as error:
        return {"status": "blocked", "errors": [f"Platform input unreadable: {error}"]}
    if not isinstance(release, dict) or not isinstance(selected, dict):
        return {"status": "blocked", "errors": ["Platform and BOM must be objects"]}
    errors: list[str] = []
    if (
        release.get("schema_version") != 1
        or release.get("device") != "slate-pocket-v1r"
    ):
        errors.append("Unknown platform reference schema or device")
    for field in ("revision", "reviewed_by"):
        if not _text(release.get(field)):
            errors.append(f"Platform reference is missing {field}")
    if release.get("selected_bom_sha256") != _sha(selected_path):
        errors.append("Platform reference is not bound to selected BOM bytes")
    electrical_digest = _sha(electrical_path)
    if release.get("electrical_bom_sha256") != electrical_digest:
        errors.append("Platform reference is not bound to electrical BOM bytes")
    parts = selected.get("parts")
    if not isinstance(parts, dict) or any(
        not isinstance(parts.get(role), dict)
        for role in ("compute_platform", "memory", "storage")
    ):
        return {
            "status": "blocked",
            "errors": errors + ["Selected core parts are missing"],
        }
    compute_part = parts["compute_platform"]
    memory_part = parts["memory"]
    identity = release.get("selected_mpns")
    expected_mpns = {
        role: parts[role].get("mpn")
        for role in ("compute_platform", "memory", "storage")
    }
    if identity != expected_mpns or any(
        not _text(value) for value in expected_mpns.values()
    ):
        errors.append("Platform reference MPNs differ from selected BOM")
    memory = memory_part.get("capabilities")
    compute = compute_part.get("capabilities")
    topology = memory.get("qualified_topology") if isinstance(memory, dict) else None
    if (
        not isinstance(memory, dict)
        or not isinstance(compute, dict)
        or not isinstance(topology, dict)
    ):
        return {
            "status": "blocked",
            "errors": errors + ["Selected memory topology is missing"],
        }
    if not _text(topology.get("id")) or release.get("topology_id") != topology["id"]:
        errors.append("Platform topology ID differs from selected memory qualification")
    placement = memory.get("placement")
    if (
        not isinstance(placement, str)
        or placement not in MEMORY_PLACEMENTS
        or release.get("memory_placement") != placement
        or topology.get("placement") != placement
    ):
        errors.append("Platform memory placement differs from selected qualification")
    count = memory_part.get("quantity")
    capacity = memory.get("capacity_bytes_per_package")
    if (
        not _integer(count)
        or not _integer(capacity)
        or release.get("memory_package_count") != count
        or release.get("total_memory_bytes") != count * capacity
        or count * capacity < MEMORY_FLOOR_BYTES
    ):
        errors.append("Platform package count or capacity does not establish 128 GB")
    if placement == "on_package" and compute.get("configured_memory_bytes") != (
        count * capacity if _integer(count) and _integer(capacity) else None
    ):
        errors.append("On-package capacity differs from orderable compute SKU")
    if placement == "board" and compute.get("configured_memory_bytes") not in (
        None,
        0,
    ):
        errors.append("Board-only memory map uses a preconfigured compute package")
    supported_placements = compute.get("supported_memory_placements")
    if (
        not isinstance(supported_placements, list)
        or placement not in supported_placements
    ):
        errors.append("Selected compute SKU does not support memory placement")
    sources = release.get("source_bindings")
    if not isinstance(sources, dict) or set(sources) != set(SOURCE_BINDINGS):
        errors.append("Platform supplier source bindings are incomplete")
        sources = {}
    for label, (role, kind) in SOURCE_BINDINGS.items():
        evidence = parts[role].get("evidence")
        record = evidence.get(kind) if isinstance(evidence, dict) else None
        expected = record.get("sha256") if isinstance(record, dict) else None
        if not _text(expected) or sources.get(label) != expected:
            errors.append(f"Platform {label} differs from selected supplier source")
    pmic = release.get("pmic")
    if not isinstance(pmic, dict):
        errors.append("Platform PMIC selection is missing")
    else:
        for field in ("manufacturer", "mpn", "revision", "ref"):
            if not _text(pmic.get(field)):
                errors.append(f"Platform PMIC is missing {field}")
        if (
            pmic.get("availability") != "purchasable"
            or pmic.get("lifecycle") != "active"
        ):
            errors.append("Platform PMIC must be purchasable and active")
        documents = pmic.get("evidence")
        for name in PMIC_DOCUMENTS:
            record = documents.get(name) if isinstance(documents, dict) else None
            problem = _pmic_document_error(root, name, record)
            if problem:
                errors.append(problem)
    errors.extend(_channel_errors(release, memory, compute))
    board_refs = release.get("board_refs")
    memory_packages = release.get("memory_packages")
    if not isinstance(board_refs, dict) or set(board_refs) != {
        "compute_platform",
        "storage",
    }:
        errors.append("Platform compute and storage board references are missing")
        board_refs = {}
    mapped: dict[str, str] = {}
    for role in ("compute_platform", "storage"):
        ref = board_refs.get(role)
        if not _text(ref) or ref in mapped:
            errors.append(f"Platform {role} board reference is blank or duplicate")
        else:
            mapped[ref] = parts[role].get("mpn")
    if isinstance(pmic, dict) and _text(pmic.get("ref")):
        if pmic["ref"] in mapped:
            errors.append("PMIC board reference duplicates a selected part")
        mapped[pmic["ref"]] = pmic.get("mpn")
    if placement == "on_package" and memory_part.get("mpn") in electrical.values():
        errors.append("On-package DRAM appears as a separate board BOM component")
    if placement == "board" and isinstance(memory_packages, list):
        for item in memory_packages:
            if isinstance(item, dict) and _text(item.get("ref")):
                if item["ref"] in mapped:
                    errors.append("Memory board reference duplicates another part")
                mapped[item["ref"]] = memory_part.get("mpn")
    for ref, mpn in mapped.items():
        if electrical.get(ref) != mpn:
            errors.append(f"{ref}: electrical BOM MPN differs from platform reference")
    return {
        "status": "pass" if not errors else "blocked",
        "errors": errors,
        "revision": release.get("revision"),
        "reviewed_by": release.get("reviewed_by"),
        "selected_bom_sha256": release.get("selected_bom_sha256"),
        "electrical_bom_sha256": release.get("electrical_bom_sha256"),
        "topology_id": release.get("topology_id"),
        "memory_package_count": release.get("memory_package_count"),
        "memory_placement": placement,
        "memory_channel_width_bits": sum(
            item["width_bits"]
            for item in (
                release.get("memory_channels")
                if isinstance(release.get("memory_channels"), list)
                else []
            )
            if isinstance(item, dict) and _integer(item.get("width_bits"))
        ),
        "pmic_mpn": pmic.get("mpn") if isinstance(pmic, dict) else None,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo-root", type=Path, default=Path(__file__).resolve().parents[1]
    )
    args = parser.parse_args()
    print(json.dumps(audit(args.repo_root), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
