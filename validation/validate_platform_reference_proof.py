"""Exercise the platform reference gate with a complete synthetic release."""

from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from buildslate.hardware_readiness import _evidence_result  # noqa: E402
from buildslate.platform_reference_proof import (  # noqa: E402
    ELECTRICAL_BOM,
    PMIC_DOCUMENTS,
    PMIC_ROOT,
    RELEASE,
    SELECTED_BOM,
    SOURCE_BINDINGS,
    audit,
)


def _write(path: Path, data: dict) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8", newline="\n")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _source(root: Path, path: Path, content: bytes) -> dict[str, str]:
    absolute = root / path
    absolute.parent.mkdir(parents=True, exist_ok=True)
    absolute.write_bytes(content)
    return {"path": path.as_posix(), "sha256": hashlib.sha256(content).hexdigest()}


def _fixture(root: Path) -> tuple[dict, dict, str]:
    selected = {
        "parts": {
            "compute_platform": {
                "mpn": "FIXTURE-HOST",
                "capabilities": {"memory_bus_width_bits": 128},
                "evidence": {},
            },
            "memory": {
                "mpn": "FIXTURE-DRAM",
                "quantity": 4,
                "capabilities": {
                    "capacity_bytes_per_package": 32_000_000_000,
                    "bus_width_bits": 32,
                    "qualified_topology": {"id": "FIXTURE-4X32"},
                },
                "evidence": {},
            },
            "storage": {"mpn": "FIXTURE-UFS", "evidence": {}},
        }
    }
    source_bindings = {}
    for label, (role, kind) in SOURCE_BINDINGS.items():
        path = Path(f"engineering/hardware/released/parts/{role}/{kind}.pdf")
        record = _source(root, path, f"synthetic {label}\n".encode())
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
    pmic_evidence = {}
    for kind in PMIC_DOCUMENTS:
        pmic_evidence[kind] = _source(
            root, PMIC_ROOT / f"{kind}.pdf", f"synthetic PMIC {kind}\n".encode()
        )
    release = {
        "schema_version": 1,
        "device": "slate-pocket-v1r",
        "revision": "FIXTURE-A",
        "reviewed_by": "validation fixture",
        "selected_bom_sha256": selected_digest,
        "electrical_bom_sha256": electrical_digest,
        "board_refs": {"compute_platform": "U10", "storage": "U30"},
        "selected_mpns": {
            "compute_platform": "FIXTURE-HOST",
            "memory": "FIXTURE-DRAM",
            "storage": "FIXTURE-UFS",
        },
        "topology_id": "FIXTURE-4X32",
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
        if proof["status"] != "pass" or proof["memory_channel_width_bits"] != 128:
            raise ValueError(f"Complete synthetic platform reference failed: {proof}")
        selected_record = {
            "disposition": "approved",
            "sha256": selected_digest,
        }
        electrical_record = {
            "disposition": "approved",
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
        for mutation, expected in (
            ({"topology_id": "OTHER"}, "topology ID"),
            ({"memory_package_count": 8}, "package count"),
            ({"total_memory_bytes": 64_000_000_000}, "128 GB"),
            ({"selected_bom_sha256": "stale"}, "BOM bytes"),
            ({"electrical_bom_sha256": "stale"}, "electrical BOM bytes"),
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
        invalid = copy.deepcopy(release)
        invalid["source_bindings"]["memory_controller_support"] = "stale"
        _write(release_path, invalid)
        if audit(root)["status"] != "blocked":
            raise ValueError("Changed supplier source binding was accepted")
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
