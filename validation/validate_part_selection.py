"""Check released part identity, source binding, and cross-part compatibility."""

from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from buildslate.hardware_readiness import _evidence_result  # noqa: E402
from buildslate.io import load_yaml  # noqa: E402
from buildslate.part_selection import CORE_ROLES, RELEASE, audit  # noqa: E402
from buildslate.supplier_source import source_format_error  # noqa: E402
from validation.source_fixtures import pdf_source  # noqa: E402


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)
    print(f"PASS: {message}")


def write_release(path: Path, release: dict) -> None:
    path.write_text(
        json.dumps(release, indent=2) + "\n", encoding="utf-8", newline="\n"
    )


def main() -> int:
    current = audit(ROOT)
    require(
        current["status"] in {"missing", "pass"}
        and (
            current["status"] != "pass"
            or all(item["selected"] for item in current["roles"])
        ),
        "current part release is either absent or fully auditable",
    )
    with TemporaryDirectory() as temporary:
        root = Path(temporary)
        step_path = root / "supplier-outline.step"
        step_path.write_bytes(
            b"ISO-10303-21;\nHEADER;\nENDSEC;\nDATA;\nENDSEC;\nEND-ISO-10303-21;\n"
        )
        archive_path = root / "reference-design.zip"
        with ZipFile(archive_path, "w") as archive:
            archive.writestr("readme.txt", "synthetic reference design")
        require(
            source_format_error(step_path) is None
            and source_format_error(archive_path) is None,
            "STEP and intact ZIP supplier containers pass format screening",
        )
        archive_path.write_bytes(b"renamed text")
        require(
            source_format_error(archive_path) is not None,
            "renamed text cannot pass as a ZIP supplier container",
        )
        strategy = load_yaml(ROOT / "validation/evt0/bom-strategy.yaml")
        strategy["metadata"]["selected_parts"] = len(CORE_ROLES)
        capabilities = {
            "compute_platform": {
                "memory_interface": "LPDDR5X",
                "max_memory_bytes": 128_000_000_000,
                "supported_memory_placements": ["board", "on_package"],
                "storage_interfaces": ["UFS4.1"],
                "display_interfaces": ["eDP1.5"],
            },
            "memory": {
                "interface": "LPDDR5X",
                "capacity_bytes_per_package": 32_000_000_000,
                "placement": "board",
            },
            "storage": {"interface": "UFS4.1", "capacity_bytes": 1_000_000_000_000},
            "battery_pack": {"energy_wh": 20, "maximum_validated_charge_w": 25},
            "display_module": {"interface": "eDP1.5", "diagonal_in": 7.5},
        }
        release = {
            "schema_version": 1,
            "device": "slate-pocket-v1r",
            "revision": "SYNTHETIC-A",
            "reviewed_by": "validation fixture",
            "parts": {},
        }
        for role in CORE_ROLES:
            strategy["roles"][role]["status"] = "selected"
            strategy["roles"][role]["selected_candidate"] = f"FIXTURE-{role}"
            documents = {}
            for kind in strategy["roles"][role]["required_evidence"]:
                document_path = (
                    root / f"engineering/hardware/released/parts/{role}/{kind}.pdf"
                )
                document_path.parent.mkdir(parents=True, exist_ok=True)
                document_path.write_bytes(pdf_source(f"{role} {kind}"))
                documents[kind] = {
                    "path": document_path.relative_to(root).as_posix(),
                    "sha256": hashlib.sha256(document_path.read_bytes()).hexdigest(),
                }
            release["parts"][role] = {
                "manufacturer": "Fixture manufacturer",
                "mpn": f"FIXTURE-{role}",
                "revision": "A",
                "availability": "purchasable",
                "lifecycle": "active",
                "quantity": 4 if role == "memory" else 1,
                "evidence": documents,
                "capabilities": capabilities[role],
            }
        release["parts"]["memory"]["capabilities"]["qualified_topology"] = {
            "id": "FIXTURE-128GB",
            "controller_mpn": "FIXTURE-compute_platform",
            "memory_mpn": "FIXTURE-memory",
            "package_count": 4,
            "capacity_bytes_per_package": 32_000_000_000,
            "total_capacity_bytes": 128_000_000_000,
            "placement": "board",
            "controller_support_sha256": release["parts"]["memory"]["evidence"][
                "controller_support"
            ]["sha256"],
            "reference_design_sha256": release["parts"]["compute_platform"]["evidence"][
                "reference_design"
            ]["sha256"],
        }
        release_path = root / RELEASE
        release_path.parent.mkdir(parents=True, exist_ok=True)
        write_release(release_path, release)
        proof = audit(root, strategy)
        require(
            proof["status"] == "pass"
            and all(item["selected"] for item in proof["roles"]),
            "complete synthetic part set passes identity, source, and interface checks",
        )
        for role in CORE_ROLES:
            invalid = copy.deepcopy(release)
            del invalid["parts"][role]["evidence"]["lifecycle"]
            write_release(release_path, invalid)
            result = audit(root, strategy)
            require(
                result["status"] == "blocked"
                and any(
                    "lifecycle: missing controlled source path" in reason
                    for reason in result["errors"]
                ),
                f"{role} selection requires lifecycle source evidence",
            )
        write_release(release_path, release)
        on_package = copy.deepcopy(release)
        on_package["parts"]["compute_platform"]["capabilities"][
            "configured_memory_bytes"
        ] = 128_000_000_000
        on_package["parts"]["memory"]["availability"] = "included_in_compute_sku"
        on_package["parts"]["memory"]["capabilities"]["placement"] = "on_package"
        on_package["parts"]["memory"]["capabilities"]["included_in_compute_sku"] = True
        on_package["parts"]["memory"]["capabilities"]["qualified_topology"][
            "placement"
        ] = "on_package"
        write_release(release_path, on_package)
        require(
            audit(root, strategy)["status"] == "pass",
            "supplier-backed on-package topology can be represented",
        )
        invalid = copy.deepcopy(on_package)
        invalid["parts"]["compute_platform"]["capabilities"][
            "configured_memory_bytes"
        ] = 48_000_000_000
        write_release(release_path, invalid)
        require(
            audit(root, strategy)["status"] == "blocked",
            "48 GB compute SKU cannot claim 128 GB on-package memory",
        )
        invalid = copy.deepcopy(on_package)
        invalid["parts"]["memory"]["availability"] = "purchasable"
        write_release(release_path, invalid)
        require(
            audit(root, strategy)["status"] == "blocked",
            "on-package DRAM cannot masquerade as separate purchased packages",
        )
        invalid = copy.deepcopy(release)
        invalid["parts"]["compute_platform"]["capabilities"][
            "configured_memory_bytes"
        ] = 48_000_000_000
        write_release(release_path, invalid)
        require(
            audit(root, strategy)["status"] == "blocked",
            "board-only map cannot inherit a 48 GB on-package compute SKU",
        )
        write_release(release_path, release)
        record = {
            "path": RELEASE.as_posix(),
            "sha256": hashlib.sha256(release_path.read_bytes()).hexdigest(),
            "revision": "SYNTHETIC-A",
            "reviewed_by": "validation fixture",
            "disposition": "approved",
        }
        requirement = {"id": "selected_bom", "stage": "design_release"}
        require(
            _evidence_result(root, requirement, record, proof)["status"] == "accepted",
            "released BOM evidence binds to the exact audited bytes",
        )
        require(
            _evidence_result(root, requirement, {**record, "revision": "WRONG"}, proof)[
                "status"
            ]
            == "rejected",
            "selected BOM evidence cannot misstate the released revision",
        )
        source_record = release["parts"]["storage"]["evidence"]["package_drawing"]
        source_path = root / source_record["path"]
        source_path.write_bytes(b"tampered supplier drawing")
        require(
            audit(root, strategy)["status"] == "blocked",
            "changed source drawing invalidates part selection",
        )
        source_path.write_bytes(pdf_source("storage package_drawing"))
        invalid = copy.deepcopy(release)
        source_path.write_bytes(b"supplier-looking text with a .pdf filename\n")
        invalid["parts"]["storage"]["evidence"]["package_drawing"]["sha256"] = (
            hashlib.sha256(source_path.read_bytes()).hexdigest()
        )
        write_release(release_path, invalid)
        result = audit(root, strategy)
        require(
            result["status"] == "blocked"
            and any(
                "PDF signature or trailer" in reason for reason in result["errors"]
            ),
            "matching hash cannot make renamed text into supplier PDF evidence",
        )
        source_path.write_bytes(b"%PDF-1.4\nnot a PDF\nstartxref\n0\n%%EOF\n")
        invalid["parts"]["storage"]["evidence"]["package_drawing"]["sha256"] = (
            hashlib.sha256(source_path.read_bytes()).hexdigest()
        )
        write_release(release_path, invalid)
        result = audit(root, strategy)
        require(
            result["status"] == "blocked"
            and any("PDF cannot be parsed" in reason for reason in result["errors"]),
            "PDF markers without a readable document cannot pass part selection",
        )
        source_path.write_bytes(pdf_source("storage package_drawing"))
        write_release(release_path, release)
        for role, mutation, expected in (
            ("memory", {"capacity_bytes_per_package": 16_000_000_000}, "128 GB"),
            ("storage", {"interface": "unsupported"}, "interface"),
            ("display_module", {"diagonal_in": 9.0}, "diagonal"),
            ("battery_pack", {"maximum_validated_charge_w": 0}, "charge"),
        ):
            invalid = copy.deepcopy(release)
            invalid["parts"][role]["capabilities"].update(mutation)
            write_release(release_path, invalid)
            result = audit(root, strategy)
            require(
                result["status"] == "blocked"
                and any(expected in reason for reason in result["errors"]),
                f"{role} incompatibility blocks selected BOM proof",
            )
        write_release(release_path, release)
        for mutation, expected in (
            ({"package_count": 8}, "package count"),
            ({"controller_mpn": "OTHER-HOST"}, "controller MPN"),
            ({"controller_support_sha256": "stale"}, "controller_support_sha256"),
            ({"total_capacity_bytes": 64_000_000_000}, "128 GB"),
        ):
            invalid = copy.deepcopy(release)
            invalid["parts"]["memory"]["capabilities"]["qualified_topology"].update(
                mutation
            )
            write_release(release_path, invalid)
            result = audit(root, strategy)
            require(
                result["status"] == "blocked"
                and any(expected in reason for reason in result["errors"]),
                "unqualified or stale memory topology blocks selected BOM proof",
            )
        write_release(release_path, release)
        strategy["roles"]["cellular"]["status"] = "selected"
        strategy["roles"]["cellular"]["selected_candidate"] = "FIXTURE-cellular"
        strategy["metadata"]["selected_parts"] += 1
        require(
            audit(root, strategy)["status"] == "blocked",
            "cellular cannot be added by status flag without its own released part",
        )
        strategy["roles"]["cellular"]["quantity_per_unit"] = 1
        documents = {}
        for kind in strategy["roles"]["cellular"]["required_evidence"]:
            document_path = (
                root / f"engineering/hardware/released/parts/cellular/{kind}.pdf"
            )
            document_path.parent.mkdir(parents=True, exist_ok=True)
            document_path.write_bytes(pdf_source(f"cellular {kind}"))
            documents[kind] = {
                "path": document_path.relative_to(root).as_posix(),
                "sha256": hashlib.sha256(document_path.read_bytes()).hexdigest(),
            }
        release["parts"]["compute_platform"]["capabilities"]["cellular_interfaces"] = [
            "PCIe"
        ]
        release["parts"]["cellular"] = {
            "manufacturer": "Fixture manufacturer",
            "mpn": "FIXTURE-cellular",
            "revision": "A",
            "availability": "purchasable",
            "lifecycle": "active",
            "quantity": 1,
            "evidence": documents,
            "capabilities": {"interface": "PCIe"},
        }
        write_release(release_path, release)
        require(
            audit(root, strategy)["status"] == "pass",
            "cellular selection needs its own source files and host interface",
        )
        invalid = copy.deepcopy(release)
        del invalid["parts"]["cellular"]["evidence"]["lifecycle"]
        write_release(release_path, invalid)
        result = audit(root, strategy)
        require(
            result["status"] == "blocked"
            and any(
                "lifecycle: missing controlled source path" in reason
                for reason in result["errors"]
            ),
            "cellular selection requires lifecycle source evidence",
        )
    print("PASS: part selection proof validation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
