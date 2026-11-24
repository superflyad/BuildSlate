"""Audit an exported KiCad XML netlist against an electrical handoff contract."""

from __future__ import annotations

import argparse
import csv
import json
import xml.etree.ElementTree as ET
from pathlib import Path

from buildslate.io import load_yaml

REQUIRED_CONNECTIONS = (
    "battery_supply_to_power_path",
    "battery_return_to_power_path",
    "charger_system_to_pmic",
    "pmic_to_compute",
    "pmic_to_memory",
    "pmic_to_storage",
    "pmic_to_display",
    "usb_vbus_to_pd",
    "power_button_to_controller",
    "debug_to_controller",
)
REQUIRED_ISOLATIONS = ("battery_positive_from_return",)
ROLE_PAIRS = {
    "battery_supply_to_power_path": ("battery_pack", "power_path"),
    "battery_return_to_power_path": ("battery_pack", "power_path"),
    "charger_system_to_pmic": ("charger", "pmic"),
    "pmic_to_compute": ("pmic", "compute"),
    "pmic_to_memory": ("pmic", "memory"),
    "pmic_to_storage": ("pmic", "storage"),
    "pmic_to_display": ("pmic", "display"),
    "usb_vbus_to_pd": ("usb_connector", "pd_controller"),
    "power_button_to_controller": ("power_button", "controller"),
    "debug_to_controller": ("debug_connector", "controller"),
    "battery_positive_from_return": ("battery_pack", "battery_pack"),
}
PLACEHOLDER_WORDS = ("placeholder", "unknown", "tbd", "to_be_determined")


def _pair(data: dict) -> tuple[tuple[str, str], tuple[str, str]]:
    endpoints = data.get("endpoints")
    if not isinstance(endpoints, list) or len(endpoints) != 2:
        raise ValueError(f"{data.get('id')}: expected exactly two endpoints")
    try:
        pair = tuple((str(item["ref"]), str(item["pin"])) for item in endpoints)
    except (KeyError, TypeError) as error:
        raise ValueError(f"{data.get('id')}: invalid endpoint") from error
    if pair[0] == pair[1]:
        raise ValueError(f"{data['id']}: endpoints must be different pins")
    return pair


def _netlist(path: Path) -> tuple[dict, dict]:
    raw = path.read_bytes()
    if (
        len(raw) > 10_000_000
        or b"<!DOCTYPE" in raw.upper()
        or b"<!ENTITY" in raw.upper()
    ):
        raise ValueError("Netlist XML is oversized or contains entity declarations")
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as error:
        raise ValueError(f"Invalid KiCad XML netlist: {error}") from error
    if root.tag != "export":
        raise ValueError("Expected a KiCad XML netlist export")
    components: dict[str, dict] = {}
    for item in root.findall("./components/comp"):
        ref = item.get("ref", "")
        if not ref or ref in components:
            raise ValueError(f"Missing or duplicate component reference: {ref}")
        components[ref] = {
            "value": item.findtext("value", default=""),
            "footprint": item.findtext("footprint", default=""),
        }
    if not components:
        raise ValueError("Netlist has no components")
    pins: dict[tuple[str, str], str] = {}
    net_names: set[str] = set()
    net_codes: set[str] = set()
    for item in root.findall("./nets/net"):
        code = item.get("code", "").strip()
        name = item.get("name", "").strip()
        if not code or code in net_codes or (name and name in net_names):
            raise ValueError(f"Missing or duplicate net code/name: {code}/{name}")
        net_codes.add(code)
        if name:
            net_names.add(name)
        identity = name or f"#{code}"
        for node in item.findall("node"):
            ref, pin = node.get("ref", ""), node.get("pin", "")
            key = (ref, pin)
            if ref not in components or not pin or key in pins:
                raise ValueError(
                    f"Unknown or multiply assigned netlist pin: {ref}.{pin}"
                )
            pins[key] = identity
    if not pins:
        raise ValueError("Netlist has no connected pins")
    return components, pins


def _bom(path: Path, components: dict) -> list[str]:
    errors: list[str] = []
    with path.open("r", encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        if not reader.fieldnames or not {"ref", "manufacturer", "mpn"}.issubset(
            reader.fieldnames
        ):
            raise ValueError("Electrical BOM needs ref, manufacturer, and mpn columns")
        seen: set[str] = set()
        for row in reader:
            ref = row["ref"].strip()
            if not ref or ref in seen:
                errors.append(f"Missing or duplicate BOM reference: {ref}")
            seen.add(ref)
            if ref not in components:
                errors.append(f"BOM reference absent from netlist: {ref}")
            for field in ("manufacturer", "mpn"):
                value = (row.get(field) or "").strip().lower()
                if not value or any(word in value for word in PLACEHOLDER_WORDS):
                    errors.append(f"{ref}: {field} is not a selected part identity")
        missing = set(components) - seen
        errors.extend(
            f"Netlist component absent from BOM: {ref}" for ref in sorted(missing)
        )
    return errors


def audit(netlist: Path, contract: Path, bom: Path) -> dict:
    """Verify actual connectivity and BOM identity, without claiming circuit function."""
    components, pins = _netlist(netlist)
    specification = load_yaml(contract)
    if (
        specification.get("schema_version") != 1
        or specification.get("device") != "slate-pocket-v1r"
    ):
        raise ValueError("Unknown electrical handoff contract")
    errors = _bom(bom, components)
    roles = specification.get("roles")
    if not isinstance(roles, dict) or set(roles) != {
        role for pair in ROLE_PAIRS.values() for role in pair
    }:
        raise ValueError("Electrical contract has incomplete component roles")
    for role, refs in roles.items():
        if (
            not isinstance(refs, list)
            or not refs
            or any(not isinstance(ref, str) or ref not in components for ref in refs)
        ):
            raise ValueError(f"{role}: unknown or empty component reference mapping")
    checks: list[dict] = []
    for key, required, should_connect in (
        ("connections", REQUIRED_CONNECTIONS, True),
        ("isolations", REQUIRED_ISOLATIONS, False),
    ):
        entries = specification.get(key)
        if (
            not isinstance(entries, list)
            or {item["id"] for item in entries} != set(required)
            or len(entries) != len(required)
        ):
            raise ValueError(f"Electrical contract has incomplete {key}")
        for item in entries:
            first, second = _pair(item)
            first_role, second_role = ROLE_PAIRS[item["id"]]
            first_net, second_net = pins.get(first), pins.get(second)
            passed = (
                bool(first_net and second_net)
                and ((first_net == second_net) == should_connect)
                and first[0] in roles[first_role]
                and second[0] in roles[second_role]
            )
            checks.append(
                {
                    "id": item["id"],
                    "kind": "connection" if should_connect else "isolation",
                    "endpoints": [f"{ref}.{pin}" for ref, pin in (first, second)],
                    "nets": [first_net, second_net],
                    "passed": passed,
                }
            )
            if not passed:
                errors.append(
                    f"{item['id']}: endpoint connectivity or role mapping does not match contract"
                )
    return {
        "status": "pass" if not errors else "fail",
        "component_count": len(components),
        "net_count": len(set(pins.values())),
        "checks": checks,
        "errors": errors,
        "caveat": (
            "This checks exported pin connectivity and selected BOM identities. "
            "It does not run KiCad ERC or PCB DRC, establish voltage compatibility, "
            "simulate power integrity, or prove physical operation."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("netlist", type=Path, help="KiCad XML netlist export")
    parser.add_argument("contract", type=Path, help="reviewed endpoint contract YAML")
    parser.add_argument("bom", type=Path, help="one selected part identity per ref")
    args = parser.parse_args()
    report = audit(args.netlist, args.contract, args.bom)
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
