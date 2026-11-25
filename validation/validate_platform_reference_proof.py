"""Exercise the platform reference gate with a complete synthetic release."""

from __future__ import annotations

import copy
import hashlib
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from buildslate.hardware_readiness import _evidence_result  # noqa: E402
from buildslate.platform_reference_proof import (  # noqa: E402
    ELECTRICAL_BOM,
    ELECTRICAL_NETLIST,
    PMIC_DOCUMENTS,
    PMIC_ROOT,
    RELEASE,
    SELECTED_BOM,
    SOURCE_BINDINGS,
    audit,
)
from validation.source_fixtures import pdf_source  # noqa: E402


def _write(path: Path, data: dict) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8", newline="\n")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _source(root: Path, path: Path, content: bytes) -> dict[str, str]:
    absolute = root / path
    absolute.parent.mkdir(parents=True, exist_ok=True)
    absolute.write_bytes(content)
    return {"path": path.as_posix(), "sha256": hashlib.sha256(content).hexdigest()}


def _netlist_fixture(root: Path, *, on_package: bool = False) -> str:
    export = ET.Element("export")
    components = ET.SubElement(export, "components")
    refs = ["U10", "U20", "U30"] + ([] if on_package else [f"U{i}" for i in range(4)])
    for ref in refs:
        ET.SubElement(components, "comp", ref=ref)
    nets = ET.SubElement(export, "nets")
    if on_package:
        net = ET.SubElement(nets, "net", code="1", name="PWR")
        ET.SubElement(net, "node", ref="U10", pin="P0")
        ET.SubElement(net, "node", ref="U20", pin="P0")
    else:
        for bit in range(128):
            net = ET.SubElement(nets, "net", code=str(bit + 1), name=f"DQ{bit}")
            ET.SubElement(net, "node", ref="U10", pin=f"H{bit}")
            ET.SubElement(net, "node", ref=f"U{bit // 32}", pin=f"D{bit % 32}")
    path = root / ELECTRICAL_NETLIST
    path.parent.mkdir(parents=True, exist_ok=True)
    ET.ElementTree(export).write(path, encoding="utf-8", xml_declaration=True)
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _fixture(root: Path) -> tuple[dict, dict, str]:
    selected = {
        "parts": {
            "compute_platform": {
                "mpn": "FIXTURE-HOST",
                "capabilities": {
                    "memory_bus_width_bits": 128,
                    "supported_memory_placements": ["board", "on_package"],
                },
                "evidence": {},
            },
            "memory": {
                "mpn": "FIXTURE-DRAM",
                "quantity": 4,
                "capabilities": {
                    "capacity_bytes_per_package": 32_000_000_000,
                    "bus_width_bits": 32,
                    "placement": "board",
                    "qualified_topology": {"id": "FIXTURE-4X32", "placement": "board"},
                },
                "evidence": {},
            },
            "storage": {"mpn": "FIXTURE-UFS", "evidence": {}},
        }
    }
    source_bindings = {}
    for label, (role, kind) in SOURCE_BINDINGS.items():
        path = Path(f"engineering/hardware/released/parts/{role}/{kind}.pdf")
        record = _source(root, path, pdf_source(label))
        selected["parts"][role]["evidence"][kind] = record
        source_bindings[label] = record["sha256"]
    selected_digest = _write(root / SELECTED_BOM, selected)
    electrical_path = root / ELECTRICAL_BOM
    electrical_path.parent.mkdir(parents=True, exist_ok=True)
    electrical_path.write_text(
        "ref,manufacturer,mpn\n"
        "U0,Fixture,FIXTURE-DRAM\n"
        "U1,Fixture,FIXTURE-DRAM\n"
        "U2,Fixture,FIXTURE-DRAM\n"
        "U3,Fixture,FIXTURE-DRAM\n"
        "U10,Fixture,FIXTURE-HOST\n"
        "U20,Fixture,FIXTURE-PMIC\n"
        "U30,Fixture,FIXTURE-UFS\n",
        encoding="utf-8",
        newline="\n",
    )
    electrical_digest = hashlib.sha256(electrical_path.read_bytes()).hexdigest()
    netlist_digest = _netlist_fixture(root)
    pmic_evidence = {}
    for kind in PMIC_DOCUMENTS:
        pmic_evidence[kind] = _source(
            root, PMIC_ROOT / f"{kind}.pdf", pdf_source(f"PMIC {kind}")
        )
    release = {
        "schema_version": 1,
        "device": "slate-pocket-v1r",
        "revision": "FIXTURE-A",
        "reviewed_by": "validation fixture",
        "selected_bom_sha256": selected_digest,
        "electrical_bom_sha256": electrical_digest,
        "electrical_netlist_sha256": netlist_digest,
        "board_refs": {"compute_platform": "U10", "storage": "U30"},
        "selected_mpns": {
            "compute_platform": "FIXTURE-HOST",
            "memory": "FIXTURE-DRAM",
            "storage": "FIXTURE-UFS",
        },
        "topology_id": "FIXTURE-4X32",
        "memory_placement": "board",
        "memory_package_count": 4,
        "total_memory_bytes": 128_000_000_000,
        "source_bindings": source_bindings,
        "pmic": {
            "manufacturer": "Fixture supplier",
            "mpn": "FIXTURE-PMIC",
            "revision": "A",
            "ref": "U20",
            "availability": "purchasable",
            "lifecycle": "active",
            "evidence": pmic_evidence,
        },
        "memory_channels": [
            {"id": f"CH{index}", "width_bits": 32} for index in range(4)
        ],
        "memory_packages": [
            {"ref": f"U{index}", "channel": f"CH{index}", "rank": 0, "bit_start": 0}
            for index in range(4)
        ],
        "memory_data_lanes": [
            {
                "ref": f"U{bit // 32}",
                "channel": f"CH{bit // 32}",
                "rank": 0,
                "bit": bit % 32,
                "controller_pin": f"H{bit}",
                "package_pin": f"D{bit % 32}",
            }
            for bit in range(128)
        ],
    }
    return selected, release, selected_digest


def main() -> int:
    if audit(ROOT)["status"] != "missing":
        raise ValueError("Public platform reference must remain missing")
    with TemporaryDirectory() as temporary:
        root = Path(temporary)
        _, release, selected_digest = _fixture(root)
        release_path = root / RELEASE
        digest = _write(release_path, release)
        proof = audit(root)
        if (
            proof["status"] != "pass"
            or proof["memory_channel_width_bits"] != 128
            or proof["memory_data_lane_count"] != 128
        ):
            raise ValueError(f"Complete synthetic platform reference failed: {proof}")
        on_package_selected = copy.deepcopy(_fixture(root)[0])
        on_package_release = copy.deepcopy(release)
        on_package_selected["parts"]["compute_platform"]["capabilities"][
            "configured_memory_bytes"
        ] = 128_000_000_000
        on_package_selected["parts"]["memory"]["capabilities"]["placement"] = (
            "on_package"
        )
        on_package_selected["parts"]["memory"]["capabilities"]["qualified_topology"][
            "placement"
        ] = "on_package"
        on_package_release["memory_placement"] = "on_package"
        on_package_release["memory_data_lanes"] = []
        for item in on_package_release["memory_packages"]:
            item["package_id"] = item.pop("ref")
        on_package_release["selected_bom_sha256"] = _write(
            root / SELECTED_BOM, on_package_selected
        )
        electrical_path = root / ELECTRICAL_BOM
        electrical_path.write_text(
            "ref,manufacturer,mpn\n"
            "U10,Fixture,FIXTURE-HOST\n"
            "U20,Fixture,FIXTURE-PMIC\n"
            "U30,Fixture,FIXTURE-UFS\n",
            encoding="utf-8",
            newline="\n",
        )
        on_package_release["electrical_bom_sha256"] = hashlib.sha256(
            electrical_path.read_bytes()
        ).hexdigest()
        on_package_release["electrical_netlist_sha256"] = _netlist_fixture(
            root, on_package=True
        )
        _write(release_path, on_package_release)
        on_package_proof = audit(root)
        if (
            on_package_proof["status"] != "pass"
            or on_package_proof["memory_placement"] != "on_package"
        ):
            raise ValueError(f"On-package platform map failed: {on_package_proof}")
        invalid_on_package = copy.deepcopy(on_package_release)
        invalid_on_package["memory_packages"][0]["ref"] = "U0"
        _write(release_path, invalid_on_package)
        if audit(root)["status"] != "blocked":
            raise ValueError("On-package DRAM was accepted as a board component")
        _write(release_path, on_package_release)
        electrical_path.write_text(
            electrical_path.read_text(encoding="utf-8") + "U0,Fixture,FIXTURE-DRAM\n",
            encoding="utf-8",
            newline="\n",
        )
        on_package_release["electrical_bom_sha256"] = hashlib.sha256(
            electrical_path.read_bytes()
        ).hexdigest()
        _write(release_path, on_package_release)
        if audit(root)["status"] != "blocked":
            raise ValueError("On-package DRAM appeared as separate electrical part")
        electrical_path.write_text(
            "ref,manufacturer,mpn\n"
            "U10,Fixture,FIXTURE-HOST\n"
            "U20,Fixture,FIXTURE-PMIC\n"
            "U30,Fixture,FIXTURE-UFS\n",
            encoding="utf-8",
            newline="\n",
        )
        on_package_release["electrical_bom_sha256"] = hashlib.sha256(
            electrical_path.read_bytes()
        ).hexdigest()
        on_package_selected["parts"]["compute_platform"]["capabilities"][
            "configured_memory_bytes"
        ] = 48_000_000_000
        on_package_release["selected_bom_sha256"] = _write(
            root / SELECTED_BOM, on_package_selected
        )
        _write(release_path, on_package_release)
        if audit(root)["status"] != "blocked":
            raise ValueError("48 GB compute package passed a 128 GB map")
        selected, release, selected_digest = _fixture(root)
        digest = _write(release_path, release)
        selected_record = {
            "disposition": "approved",
            "sha256": selected_digest,
        }
        electrical_record = {
            "disposition": "approved",
            "sha256": release["electrical_netlist_sha256"],
            "bom_sha256": release["electrical_bom_sha256"],
        }
        record = {
            "path": RELEASE.as_posix(),
            "sha256": digest,
            "revision": "FIXTURE-A",
            "reviewed_by": "validation fixture",
            "disposition": "approved",
        }
        result = _evidence_result(
            root,
            {"id": "platform_reference", "stage": "design_release"},
            record,
            {"status": "pass", "sha256": selected_digest},
            {"selected_bom": selected_record, "schematic_netlist": electrical_record},
        )
        if result["status"] != "accepted":
            raise ValueError(f"Approved platform fixture was rejected: {result}")
        if (
            _evidence_result(
                root,
                {"id": "platform_reference", "stage": "design_release"},
                record,
                {"status": "blocked", "sha256": selected_digest},
                {
                    "selected_bom": selected_record,
                    "schematic_netlist": electrical_record,
                },
            )["status"]
            != "rejected"
        ):
            raise ValueError("Unproven selected BOM was accepted for platform release")
        if (
            _evidence_result(
                root,
                {"id": "platform_reference", "stage": "design_release"},
                record,
                {"status": "pass", "sha256": selected_digest},
                {"selected_bom": selected_record},
            )["status"]
            != "rejected"
        ):
            raise ValueError("Platform release accepted an unapproved electrical BOM")
        if (
            _evidence_result(
                root,
                {"id": "platform_reference", "stage": "design_release"},
                record,
                {"status": "pass", "sha256": selected_digest},
                {
                    "selected_bom": selected_record,
                    "schematic_netlist": {**electrical_record, "sha256": "stale"},
                },
            )["status"]
            != "rejected"
        ):
            raise ValueError("Platform release accepted an unapproved netlist")
        for mutation, expected in (
            ({"topology_id": "OTHER"}, "topology ID"),
            ({"memory_package_count": 8}, "package count"),
            ({"total_memory_bytes": 64_000_000_000}, "128 GB"),
            ({"selected_bom_sha256": "stale"}, "BOM bytes"),
            ({"electrical_bom_sha256": "stale"}, "electrical BOM bytes"),
            ({"electrical_netlist_sha256": "stale"}, "electrical netlist bytes"),
            ({"memory_channels": None}, "channel map"),
        ):
            invalid = copy.deepcopy(release)
            invalid.update(mutation)
            _write(release_path, invalid)
            result = audit(root)
            if result["status"] != "blocked" or not any(
                expected in error for error in result["errors"]
            ):
                raise ValueError(f"Invalid platform identity was accepted: {mutation}")
        for index, mutation in (
            (1, {"channel": "CH0"}),
            (1, {"ref": "U0"}),
            (1, {"rank": 1}),
        ):
            invalid = copy.deepcopy(release)
            invalid["memory_packages"][index].update(mutation)
            _write(release_path, invalid)
            if audit(root)["status"] != "blocked":
                raise ValueError(f"Invalid lane or rank map was accepted: {mutation}")
        for index, mutation in (
            (0, {"package_pin": "NOT_CONNECTED"}),
            (1, {"controller_pin": "H0"}),
            (1, {"ref": "U1"}),
        ):
            invalid = copy.deepcopy(release)
            invalid["memory_data_lanes"][index].update(mutation)
            _write(release_path, invalid)
            if audit(root)["status"] != "blocked":
                raise ValueError(f"Invalid data wiring was accepted: {mutation}")
        invalid = copy.deepcopy(release)
        invalid["memory_data_lanes"].pop()
        _write(release_path, invalid)
        if audit(root)["status"] != "blocked":
            raise ValueError("Incomplete board DRAM data wiring was accepted")
        netlist_path = root / ELECTRICAL_NETLIST
        valid_netlist = netlist_path.read_bytes()
        netlist_path.write_bytes(valid_netlist.replace(b'pin="D0"', b'pin="BROKEN"', 1))
        invalid = copy.deepcopy(release)
        invalid["electrical_netlist_sha256"] = hashlib.sha256(
            netlist_path.read_bytes()
        ).hexdigest()
        _write(release_path, invalid)
        result = audit(root)
        if result["status"] != "blocked" or not any(
            "host/DRAM netlist pins differ" in error for error in result["errors"]
        ):
            raise ValueError("Hash-matched miswired netlist passed platform proof")
        netlist_path.write_bytes(valid_netlist)
        invalid = copy.deepcopy(release)
        invalid["source_bindings"]["memory_controller_support"] = "stale"
        _write(release_path, invalid)
        if audit(root)["status"] != "blocked":
            raise ValueError("Changed supplier source binding was accepted")
        _write(release_path, release)
        source_path = (
            root
            / "engineering/hardware/released/parts/compute_platform/package_drawing.pdf"
        )
        source_path.write_bytes(b"renamed text, not a supplier PDF\n")
        invalid_selected = copy.deepcopy(selected)
        invalid_selected["parts"]["compute_platform"]["evidence"]["package_drawing"][
            "sha256"
        ] = hashlib.sha256(source_path.read_bytes()).hexdigest()
        invalid = copy.deepcopy(release)
        invalid["selected_bom_sha256"] = _write(root / SELECTED_BOM, invalid_selected)
        invalid["source_bindings"]["compute_package_drawing"] = invalid_selected[
            "parts"
        ]["compute_platform"]["evidence"]["package_drawing"]["sha256"]
        _write(release_path, invalid)
        result = audit(root)
        if result["status"] != "blocked" or not any(
            "PDF signature or trailer" in error for error in result["errors"]
        ):
            raise ValueError("Matched source digests accepted a renamed text file")
        source_path.write_bytes(pdf_source("compute_package_drawing"))
        _write(root / SELECTED_BOM, selected)
        _write(release_path, release)
        electrical_path = root / ELECTRICAL_BOM
        electrical_path.write_text(
            electrical_path.read_text(encoding="utf-8").replace(
                "U2,Fixture,FIXTURE-DRAM", "U2,Fixture,OTHER-DRAM"
            ),
            encoding="utf-8",
            newline="\n",
        )
        if audit(root)["status"] != "blocked":
            raise ValueError("Electrical BOM part substitution was accepted")
        electrical_path.write_text(
            electrical_path.read_text(encoding="utf-8").replace(
                "U2,Fixture,OTHER-DRAM", "U2,Fixture,FIXTURE-DRAM"
            ),
            encoding="utf-8",
            newline="\n",
        )
        pmic_path = root / PMIC_ROOT / "datasheet.pdf"
        pmic_path.write_bytes(b"changed PMIC source")
        if audit(root)["status"] != "blocked":
            raise ValueError("Changed PMIC document was accepted")
    print("PASS: platform reference identity, source, and memory lane proof")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
