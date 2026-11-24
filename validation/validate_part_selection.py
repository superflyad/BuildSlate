"""Check released part identity, source binding, and cross-part compatibility."""

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
from buildslate.io import load_yaml  # noqa: E402
from buildslate.part_selection import CORE_ROLES, RELEASE, audit  # noqa: E402


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
        strategy = load_yaml(ROOT / "validation/evt0/bom-strategy.yaml")
        strategy["metadata"]["selected_parts"] = len(CORE_ROLES)
        capabilities = {
            "compute_platform": {
                "memory_interface": "LPDDR5X",
                "max_memory_bytes": 128_000_000_000,
                "storage_interfaces": ["UFS4.1"],
                "display_interfaces": ["eDP1.5"],
            },
            "memory": {
                "interface": "LPDDR5X",
                "capacity_bytes_per_package": 32_000_000_000,
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
                document_path.write_bytes(f"synthetic {role} {kind}\n".encode())
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
        release_path = root / RELEASE
        release_path.parent.mkdir(parents=True, exist_ok=True)
        write_release(release_path, release)
        proof = audit(root, strategy)
        require(
            proof["status"] == "pass"
            and all(item["selected"] for item in proof["roles"]),
            "complete synthetic part set passes identity, source, and interface checks",
        )
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
        source_path.write_bytes(b"synthetic storage package_drawing\n")
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
            document_path.write_bytes(f"synthetic cellular {kind}\n".encode())
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
    print("PASS: part selection proof validation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
