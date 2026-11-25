"""Audit released connector maps against the exported electrical netlist."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from buildslate.netlist_proof import _netlist

RELEASE = Path("engineering/hardware/released/interconnect/interconnect.json")
NETLIST = Path("engineering/hardware/released/board.xml")
ELECTRICAL_BOM = Path("engineering/hardware/released/board.bom.csv")
BOARD = Path("engineering/hardware/released/board.kicad_pcb")
ASSEMBLY = Path("engineering/hardware/released/mechanical/assembly.step")
SELECTED_BOM = Path("engineering/hardware/released/selected-bom.json")
REQUIRED_INTERFACES = frozenset(
    {
        "display",
        "touch",
        "rear_camera",
        "front_camera",
        "usb",
        "battery",
        "antenna_main",
        "antenna_diversity",
        "audio_output",
        "audio_input",
        "haptic",
        "power_button",
        "service_debug",
    }
)
DOCUMENT_ROOT = Path("engineering/hardware/released/interconnect/sources")
MEDIA = frozenset({"board", "flex", "coax", "harness"})


def _text(value: Any) -> bool:
    return (
        isinstance(value, str)
        and bool(value.strip())
        and value.strip().lower() not in {"unknown", "placeholder", "tbd"}
    )


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audit(root: Path) -> dict[str, Any]:
    """Check documented pin continuity and byte identity, not physical function."""
    root = root.resolve()
    path = root / RELEASE
    if not path.is_file():
        return {"status": "missing", "errors": ["No released interconnect map"]}
    try:
        release = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        return {
            "status": "blocked",
            "errors": [f"Interconnect map unreadable: {error}"],
        }
    if not isinstance(release, dict):
        return {"status": "blocked", "errors": ["Interconnect map must be an object"]}
    errors: list[str] = []
    if (
        release.get("schema_version") != 1
        or release.get("device") != "slate-pocket-v1r"
    ):
        errors.append("Unknown interconnect schema or device")
    for field in ("revision", "reviewed_by"):
        if not _text(release.get(field)):
            errors.append(f"Interconnect release is missing {field}")
    for field, source in (
        ("selected_bom_sha256", SELECTED_BOM),
        ("netlist_sha256", NETLIST),
        ("electrical_bom_sha256", ELECTRICAL_BOM),
        ("routed_pcb_sha256", BOARD),
        ("mechanical_assembly_sha256", ASSEMBLY),
    ):
        target = root / source
        if not target.is_file() or release.get(field) != _sha(target):
            errors.append(
                f"Interconnect {field} is missing or differs from released bytes"
            )
    if not (root / NETLIST).is_file():
        return {"status": "blocked", "errors": errors}
    try:
        components, pins = _netlist(root / NETLIST)
    except (OSError, UnicodeError, ValueError) as error:
        return {
            "status": "blocked",
            "errors": errors + [f"Netlist unreadable: {error}"],
        }
    interfaces = release.get("interfaces")
    if not isinstance(interfaces, list) or any(
        not isinstance(item, dict) for item in interfaces
    ):
        return {
            "status": "blocked",
            "errors": errors + ["Interconnect interfaces must be a list of objects"],
        }
    ids = [item.get("id") for item in interfaces]
    if any(not _text(identifier) for identifier in ids) or len(ids) != len(set(ids)):
        errors.append("Interconnect path IDs must be unique and nonblank")
    checks: list[dict[str, Any]] = []
    mapped_endpoints: set[tuple[str, str]] = set()
    mapped_roles: set[str] = set()
    for item in interfaces:
        identifier = item.get("id")
        if not _text(identifier):
            errors.append("Interconnect interface has no identity")
            continue
        medium = item.get("medium")
        if not _text(medium) or medium not in MEDIA:
            errors.append(f"{identifier}: unsupported connection medium")
            continue
        first_ref = item.get("board_ref")
        second_ref = item.get("device_ref")
        if (
            not _text(first_ref)
            or not _text(second_ref)
            or first_ref == second_ref
            or first_ref not in components
            or second_ref not in components
        ):
            errors.append(f"{identifier}: connector or endpoint refs are invalid")
            continue
        contacts = item.get("contacts")
        if (
            not isinstance(contacts, list)
            or not contacts
            or any(not isinstance(contact, dict) for contact in contacts)
        ):
            errors.append(f"{identifier}: contact map is missing")
            continue
        used_first: set[str] = set()
        used_second: set[str] = set()
        for contact in contacts:
            role = contact.get("role")
            if not _text(role) or role not in REQUIRED_INTERFACES:
                errors.append(f"{identifier}: contact has no required functional role")
                continue
            first_pin = contact.get("board_pin")
            second_pin = contact.get("device_pin")
            first_net = pins.get((first_ref, first_pin)) if _text(first_pin) else None
            second_net = (
                pins.get((second_ref, second_pin)) if _text(second_pin) else None
            )
            passed = (
                bool(first_net)
                and first_net == second_net
                and first_pin not in used_first
                and second_pin not in used_second
                and (first_ref, first_pin) not in mapped_endpoints
                and (second_ref, second_pin) not in mapped_endpoints
            )
            checks.append(
                {
                    "interface": identifier,
                    "role": role,
                    "board": f"{first_ref}.{first_pin}",
                    "device": f"{second_ref}.{second_pin}",
                    "net": first_net,
                    "passed": bool(passed),
                }
            )
            if not passed:
                errors.append(
                    f"{identifier}: crossed, repeated, or unconnected contact"
                )
            else:
                mapped_roles.add(role)
            if _text(first_pin):
                used_first.add(first_pin)
                mapped_endpoints.add((first_ref, first_pin))
            if _text(second_pin):
                used_second.add(second_pin)
                mapped_endpoints.add((second_ref, second_pin))
        if medium != "board":
            expected_first = {pin for ref, pin in pins if ref == first_ref}
            expected_second = {pin for ref, pin in pins if ref == second_ref}
            if used_first != expected_first or used_second != expected_second:
                errors.append(
                    f"{identifier}: mating connector pin coverage is incomplete"
                )
            document = item.get("drawing")
            if not isinstance(document, dict) or not _text(document.get("path")):
                errors.append(f"{identifier}: controlled cable drawing is missing")
            else:
                allowed = (root / DOCUMENT_ROOT).resolve()
                target = (root / document["path"]).resolve()
                if (
                    not target.is_relative_to(allowed)
                    or target == allowed
                    or target.suffix.lower() in {".md", ".yaml", ".yml", ".json"}
                    or not target.is_file()
                    or document.get("sha256") != _sha(target)
                ):
                    errors.append(
                        f"{identifier}: drawing is missing, stale, or uncontrolled"
                    )
    if mapped_roles != REQUIRED_INTERFACES:
        errors.append("Interconnect contacts do not cover every required function")
    return {
        "status": "pass" if not errors else "blocked",
        "errors": errors,
        "revision": release.get("revision"),
        "reviewed_by": release.get("reviewed_by"),
        "selected_bom_sha256": release.get("selected_bom_sha256"),
        "netlist_sha256": release.get("netlist_sha256"),
        "electrical_bom_sha256": release.get("electrical_bom_sha256"),
        "routed_pcb_sha256": release.get("routed_pcb_sha256"),
        "mechanical_assembly_sha256": release.get("mechanical_assembly_sha256"),
        "contact_checks": checks,
        "caveat": (
            "This checks declared connector pin continuity, complete mapped mating "
            "pins, drawing hashes, and released design identity. It does not prove "
            "voltage/current ratings, signal integrity, flex fit, or physical operation."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    args = parser.parse_args()
    report = audit(args.repo_root)
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
