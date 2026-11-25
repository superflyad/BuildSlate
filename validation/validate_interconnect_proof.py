"""Exercise interconnect release checks with synthetic crossed-pin faults."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from buildslate.hardware_readiness import _evidence_result  # noqa: E402
from buildslate.interconnect_proof import (  # noqa: E402
    ASSEMBLY,
    BOARD,
    ELECTRICAL_BOM,
    NETLIST,
    RELEASE,
    REQUIRED_INTERFACES,
    SELECTED_BOM,
    audit,
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write(root: Path, relative: Path, data: bytes) -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


def _fixture(root: Path) -> tuple[dict, dict, dict]:
    for path in (SELECTED_BOM, ELECTRICAL_BOM, BOARD, ASSEMBLY):
        _write(root, path, f"synthetic {path.name}".encode())
    exported = ET.Element("export")
    components = ET.SubElement(exported, "components")
    nets = ET.SubElement(exported, "nets")
    interfaces = []
    for index, identifier in enumerate(sorted(REQUIRED_INTERFACES)):
        board_ref, device_ref = f"J{index + 1}", f"P{index + 1}"
        for ref in (board_ref, device_ref):
            ET.SubElement(components, "comp", ref=ref)
        for pin in ("1", "2"):
            net = ET.SubElement(
                nets, "net", code=str(index * 2 + int(pin)), name=f"{identifier}_{pin}"
            )
            for ref in (board_ref, device_ref):
                ET.SubElement(net, "node", ref=ref, pin=pin)
        drawing = Path(
            f"engineering/hardware/released/interconnect/sources/{identifier}.pdf"
        )
        _write(root, drawing, f"synthetic drawing for {identifier}".encode())
        interfaces.append(
            {
                "id": identifier,
                "medium": "flex" if identifier != "usb" else "board",
                "board_ref": board_ref,
                "device_ref": device_ref,
                "contacts": [
                    {"role": identifier, "board_pin": pin, "device_pin": pin}
                    for pin in ("1", "2")
                ],
                "drawing": {"path": drawing.as_posix(), "sha256": _sha(root / drawing)},
            }
        )
    _write(root, NETLIST, ET.tostring(exported, encoding="utf-8"))
    release = {
        "schema_version": 1,
        "device": "slate-pocket-v1r",
        "revision": "A",
        "reviewed_by": "fixture reviewer",
        "selected_bom_sha256": _sha(root / SELECTED_BOM),
        "netlist_sha256": _sha(root / NETLIST),
        "electrical_bom_sha256": _sha(root / ELECTRICAL_BOM),
        "routed_pcb_sha256": _sha(root / BOARD),
        "mechanical_assembly_sha256": _sha(root / ASSEMBLY),
        "interfaces": interfaces,
    }
    _write(root, RELEASE, (json.dumps(release) + "\n").encode())
    evidence = {
        "path": RELEASE.as_posix(),
        "sha256": _sha(root / RELEASE),
        "revision": "A",
        "reviewed_by": "fixture reviewer",
        "disposition": "approved",
    }
    related = {
        identifier: {"disposition": "approved", field: digest}
        for identifier, field, digest in (
            ("selected_bom", "sha256", release["selected_bom_sha256"]),
            ("schematic_netlist", "sha256", release["netlist_sha256"]),
            ("routed_pcb", "sha256", release["routed_pcb_sha256"]),
            ("mechanical_release", "sha256", release["mechanical_assembly_sha256"]),
        )
    }
    related["schematic_netlist"]["bom_sha256"] = release["electrical_bom_sha256"]
    return release, evidence, related


def _require_blocked(root: Path, label: str) -> None:
    if audit(root)["status"] == "pass":
        raise ValueError(f"Interconnect fault passed: {label}")


def main() -> int:
    with TemporaryDirectory() as temporary:
        root = Path(temporary)
        release, evidence, related = _fixture(root)
        selection = {"status": "pass", "sha256": release["selected_bom_sha256"]}
        if audit(root)["status"] != "pass":
            raise ValueError("Valid synthetic connector map failed")
        requirement = {"id": "interconnect", "stage": "design_release"}
        accepted = _evidence_result(root, requirement, evidence, selection, related)
        if accepted["status"] != "accepted":
            raise ValueError(f"Valid interconnect release was rejected: {accepted}")
        if (
            _evidence_result(
                root,
                requirement,
                evidence,
                selection,
                {
                    **related,
                    "routed_pcb": {"disposition": "approved", "sha256": "0" * 64},
                },
            )["status"]
            == "accepted"
        ):
            raise ValueError("Interconnect accepted a different approved board")
        original = (root / RELEASE).read_bytes()
        shared = json.loads(original)
        display = next(item for item in shared["interfaces"] if item["id"] == "display")
        touch = next(item for item in shared["interfaces"] if item["id"] == "touch")
        display["contacts"][1]["role"] = "touch"
        shared["interfaces"].remove(touch)
        (root / RELEASE).write_text(json.dumps(shared), encoding="utf-8")
        if audit(root)["status"] != "pass":
            raise ValueError("One physical path cannot cover two functional roles")
        (root / RELEASE).write_bytes(original)
        release["interfaces"][0]["contacts"][0]["device_pin"] = "2"
        (root / RELEASE).write_text(json.dumps(release), encoding="utf-8")
        _require_blocked(root, "crossed contact")
        (root / RELEASE).write_bytes(original)
        release["interfaces"][0]["contacts"].pop()
        (root / RELEASE).write_text(json.dumps(release), encoding="utf-8")
        _require_blocked(root, "omitted mating pin")
        (root / RELEASE).write_bytes(original)
        release["interfaces"][1]["contacts"][0]["role"] = "display"
        release["interfaces"][1]["contacts"][1]["role"] = "display"
        (root / RELEASE).write_text(json.dumps(release), encoding="utf-8")
        _require_blocked(root, "missing functional role")
        (root / RELEASE).write_bytes(original)
        drawing = root / release["interfaces"][0]["drawing"]["path"]
        drawing.write_bytes(b"changed drawing")
        _require_blocked(root, "stale cable drawing")
        _fixture(root)
        (root / BOARD).write_bytes(b"changed board")
        _require_blocked(root, "stale routed board")
    print("PASS: interconnect pins, sources, and release bindings fail closed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
