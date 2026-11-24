"""Exercise KiCad netlist and selected-BOM proof against synthetic faults."""

from __future__ import annotations

import csv
import hashlib
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from tempfile import TemporaryDirectory

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from buildslate.hardware_readiness import _evidence_result  # noqa: E402
from buildslate.netlist_proof import (  # noqa: E402
    REQUIRED_CONNECTIONS,
    ROLE_PAIRS,
    audit,
)


def _write_fixture(directory: Path) -> tuple[Path, Path, Path, dict]:
    netlist = directory / "board.xml"
    contract = directory / "board.contract.yaml"
    bom = directory / "board.bom.csv"
    root = ET.Element("export", version="D")
    components = ET.SubElement(root, "components")
    nets = ET.SubElement(root, "nets")
    connections = []
    refs = []
    roles = {role: [] for pair in ROLE_PAIRS.values() for role in pair}
    for index, identifier in enumerate(REQUIRED_CONNECTIONS, start=1):
        first, second = f"J{index}", f"U{index}"
        refs.extend((first, second))
        for ref in (first, second):
            item = ET.SubElement(components, "comp", ref=ref)
            ET.SubElement(item, "value").text = "fixture"
        net = ET.SubElement(nets, "net", code=str(index), name=f"N{index}")
        for ref in (first, second):
            ET.SubElement(net, "node", ref=ref, pin="1")
        connections.append(
            {
                "id": identifier,
                "endpoints": [
                    {"ref": first, "pin": "1"},
                    {"ref": second, "pin": "1"},
                ],
            }
        )
        left_role, right_role = ROLE_PAIRS[identifier]
        roles[left_role].append(first)
        roles[right_role].append(second)
    ET.ElementTree(root).write(netlist, encoding="utf-8", xml_declaration=True)
    specification = {
        "schema_version": 1,
        "device": "slate-pocket-v1r",
        "roles": roles,
        "connections": connections,
        "isolations": [
            {
                "id": "battery_positive_from_return",
                "endpoints": [
                    {"ref": "J1", "pin": "1"},
                    {"ref": "J2", "pin": "1"},
                ],
            }
        ],
    }
    contract.write_text(
        yaml.safe_dump(specification, sort_keys=False), encoding="utf-8"
    )
    with bom.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=("ref", "manufacturer", "mpn"))
        writer.writeheader()
        for ref in refs:
            writer.writerow(
                {"ref": ref, "manufacturer": "fixture vendor", "mpn": f"P-{ref}"}
            )
    return netlist, contract, bom, specification


def main() -> int:
    with TemporaryDirectory() as temp:
        root = Path(temp)
        directory = root / "engineering/hardware/released"
        directory.mkdir(parents=True)
        netlist, contract, bom, specification = _write_fixture(directory)
        result = audit(netlist, contract, bom)
        if result["status"] != "pass" or len(result["checks"]) != 11:
            raise ValueError("Complete synthetic netlist was not proven")
        record = {
            "path": "engineering/hardware/released/board.xml",
            "sha256": hashlib.sha256(netlist.read_bytes()).hexdigest(),
            "contract_sha256": hashlib.sha256(contract.read_bytes()).hexdigest(),
            "bom_sha256": hashlib.sha256(bom.read_bytes()).hexdigest(),
            "revision": "fixture-A",
            "reviewed_by": "fixture reviewer",
            "disposition": "approved",
        }
        requirement = {"id": "schematic_netlist", "stage": "design_release"}
        if _evidence_result(root, requirement, record)["status"] != "accepted":
            raise ValueError("Valid electrical evidence fixture was rejected")
        changed = {**record, "bom_sha256": "0" * 64}
        if _evidence_result(root, requirement, changed)["status"] != "rejected":
            raise ValueError("Unbound BOM bytes passed")
        original_bom = bom.read_bytes()
        bom.write_bytes(original_bom.replace(b"P-J1", b"PLACEHOLDER"))
        if audit(netlist, contract, bom)["status"] != "fail":
            raise ValueError("Placeholder part identity passed")
        bom.write_bytes(original_bom)
        original_netlist = netlist.read_bytes()
        tree = ET.parse(netlist)
        second_net = tree.getroot().findall("./nets/net")[1]
        ET.SubElement(second_net, "node", ref="J1", pin="1")
        tree.write(netlist, encoding="utf-8", xml_declaration=True)
        try:
            audit(netlist, contract, bom)
        except ValueError:
            pass
        else:
            raise ValueError("Multiply assigned pin passed")
        netlist.write_bytes(original_netlist)
        original_compute = specification["roles"]["compute"]
        specification["roles"]["compute"] = ["U5"]
        contract.write_text(
            yaml.safe_dump(specification, sort_keys=False), encoding="utf-8"
        )
        if audit(netlist, contract, bom)["status"] != "fail":
            raise ValueError("Unrelated component role passed")
        specification["roles"]["compute"] = original_compute
        specification["connections"][3]["endpoints"][1]["ref"] = "U4"
        specification["connections"][3]["endpoints"][1]["pin"] = "9"
        contract.write_text(
            yaml.safe_dump(specification, sort_keys=False), encoding="utf-8"
        )
        if audit(netlist, contract, bom)["status"] != "fail":
            raise ValueError("Missing critical endpoint passed")
        changed = {
            **record,
            "contract_sha256": hashlib.sha256(contract.read_bytes()).hexdigest(),
        }
        if _evidence_result(root, requirement, changed)["status"] != "rejected":
            raise ValueError("Failed technical proof passed evidence gate")
        contract.write_text(
            yaml.safe_dump({**specification, "connections": []}), encoding="utf-8"
        )
        try:
            audit(netlist, contract, bom)
        except ValueError:
            pass
        else:
            raise ValueError("Incomplete electrical contract passed")
        if not result["caveat"]:
            raise ValueError("Electrical proof limits are missing")
    print("PASS: netlist topology, BOM, hash binding, and fault fixtures")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
