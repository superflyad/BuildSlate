"""Exercise firmware bundle integrity and hardware-gate binding with faults."""

from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from buildslate.firmware_proof import DRIVER_ROLES, RELEASE, audit  # noqa: E402
from buildslate.hardware_readiness import _evidence_result  # noqa: E402


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> int:
    if audit(ROOT / RELEASE)["status"] != "missing":
        raise ValueError("Public checkout must not imply a released firmware bundle")
    with TemporaryDirectory() as temp:
        root = Path(temp)
        path = root / RELEASE
        path.parent.mkdir(parents=True)
        images = []
        for kind in ("bootloader", "kernel", "rootfs", "recovery"):
            data = f"synthetic {kind} image".encode()
            (path.parent / f"{kind}.bin").write_bytes(data)
            images.append(
                {
                    "id": kind,
                    "kind": kind,
                    "path": f"{kind}.bin",
                    "sha256": _sha(data),
                    "size_bytes": len(data),
                    "version": "fixture-1",
                    "target_partition": kind,
                    "license": "synthetic fixture",
                }
            )
        device_data = b"synthetic camera device firmware"
        (path.parent / "camera.bin").write_bytes(device_data)
        images.append(
            {
                "id": "camera_firmware",
                "kind": "device_firmware",
                "path": "camera.bin",
                "sha256": _sha(device_data),
                "size_bytes": len(device_data),
                "version": "fixture-1",
                "target_partition": "camera",
                "license": "synthetic fixture",
            }
        )
        bom_hash = _sha(b"selected BOM fixture")
        board_hash = _sha(b"routed PCB fixture")
        tool_data = b"synthetic flash tool"
        (path.parent / "flasher.bin").write_bytes(tool_data)
        bundle = {
            "schema_version": 1,
            "device": "slate-pocket-v1r",
            "revision": "F1",
            "board_revision": "B1",
            "build_id": "fixture-build",
            "reviewed_by": "fixture reviewer",
            "selected_bom_sha256": bom_hash,
            "routed_pcb_sha256": board_hash,
            "images": images,
            "boot_order": ["bootloader", "kernel", "rootfs"],
            "drivers": [
                {
                    "role": role,
                    "image_id": "camera_firmware"
                    if role == "front_camera_module"
                    else "kernel",
                    "driver": f"fixture_{role}",
                    "device_identifier": f"fixture:{role}",
                    "probe_command": f"probe {role}",
                }
                for role in DRIVER_ROLES
            ],
            "flash": {
                "tool": "fixture flash tool",
                "tool_version": "1",
                "tool_path": "flasher.bin",
                "tool_sha256": _sha(tool_data),
                "readback_command": "fixture readback",
                "power_loss_response": "stop and recover",
                "steps": [
                    {"image_id": kind, "verify_readback": True}
                    for kind in (
                        "bootloader",
                        "kernel",
                        "rootfs",
                        "camera_firmware",
                        "recovery",
                    )
                ],
            },
            "recovery": {
                "image_id": "recovery",
                "entry": "fixture recovery entry",
                "verify_command": "fixture recovery verify",
            },
        }

        def check(value: dict, expected: str) -> None:
            path.write_text(json.dumps(value), encoding="utf-8")
            result = audit(path)
            if result["status"] != expected:
                raise ValueError(f"Firmware fixture {expected} expected: {result}")

        check(bundle, "pass")
        (path.parent / "kernel.bin").write_bytes(b"altered kernel")
        check(bundle, "fail")
        (path.parent / "kernel.bin").write_bytes(b"synthetic kernel image")
        (path.parent / "flasher.bin").write_bytes(b"altered flash tool")
        check(bundle, "fail")
        (path.parent / "flasher.bin").write_bytes(tool_data)
        for mutation in (
            lambda item: item["images"][0].update(sha256="0" * 64),
            lambda item: item["images"][0].update(path="../../escape.bin"),
            lambda item: item["images"][0].update(size_bytes=1),
            lambda item: item["images"][0].update(target_partition="kernel"),
            lambda item: item["boot_order"].pop(),
            lambda item: item["drivers"].pop(),
            lambda item: item["flash"]["steps"].pop(3),
            lambda item: item["flash"].update(tool_sha256="0" * 64),
            lambda item: item["drivers"][0].update(image_id="recovery"),
            lambda item: item["flash"]["steps"][0].update(verify_readback=False),
            lambda item: item["recovery"].update(image_id="kernel"),
        ):
            bad = copy.deepcopy(bundle)
            mutation(bad)
            check(bad, "fail")
        check(bundle, "pass")
        record = {
            "path": RELEASE.as_posix(),
            "sha256": _sha(path.read_bytes()),
            "revision": "F1",
            "reviewed_by": "fixture reviewer",
            "disposition": "approved",
        }
        related = {
            "selected_bom": {"disposition": "approved", "sha256": bom_hash},
            "routed_pcb": {
                "disposition": "approved",
                "sha256": board_hash,
                "revision": "B1",
            },
        }
        selection = {"status": "pass", "sha256": bom_hash}
        requirement = {"id": "firmware_boot", "stage": "design_release"}
        accepted = _evidence_result(root, requirement, record, selection, related)
        if accepted["status"] != "accepted":
            raise ValueError(f"Bound firmware fixture was rejected: {accepted}")
        for bad_record, bad_selection, bad_related in (
            ({**record, "revision": "F2"}, selection, related),
            (record, {"status": "blocked", "sha256": bom_hash}, related),
            (record, selection, {**related, "routed_pcb": {"sha256": board_hash}}),
            (
                record,
                selection,
                {**related, "routed_pcb": {**related["routed_pcb"], "revision": "B2"}},
            ),
        ):
            if (
                _evidence_result(
                    root, requirement, bad_record, bad_selection, bad_related
                )["status"]
                == "accepted"
            ):
                raise ValueError("Firmware release escaped upstream binding")
    print("PASS: firmware bundle and hardware-gate fault fixtures")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
