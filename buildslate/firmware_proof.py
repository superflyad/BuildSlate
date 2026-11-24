"""Audit the integrity and interface coverage of a controlled firmware bundle.

This checks release consistency. It cannot prove that an image boots on hardware.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

RELEASE = Path("engineering/hardware/released/firmware/firmware-release.json")
IMAGE_KINDS = {"bootloader", "kernel", "rootfs", "recovery", "device_firmware"}
BOOT_KINDS = ("bootloader", "kernel", "rootfs")
DRIVER_ROLES = (
    "storage_package",
    "display_module",
    "touch_digitizer",
    "front_camera_module",
    "rear_camera_module",
    "speakers",
    "microphones",
    "usb_c_port",
    "antenna_modules",
)


def _text(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _digest(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _contained_file(root: Path, relative: object) -> Path | None:
    if not _text(relative):
        return None
    path = Path(relative)
    if path.is_absolute() or ".." in path.parts or path.as_posix() != relative:
        return None
    resolved = (root / path).resolve()
    if not resolved.is_relative_to(root.resolve()) or not resolved.is_file():
        return None
    return resolved


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def audit(path: Path) -> dict:
    """Check a versioned bundle without executing untrusted firmware or tools."""
    if not path.is_file():
        return {"status": "missing", "errors": ["No released firmware manifest"]}
    if path.stat().st_size > 2_000_000:
        return {"status": "fail", "errors": ["Firmware manifest exceeds 2 MB"]}
    try:
        release = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        return {"status": "fail", "errors": [f"Invalid firmware manifest: {error}"]}
    if not isinstance(release, dict):
        return {"status": "fail", "errors": ["Firmware manifest must be an object"]}
    errors: list[str] = []
    if (
        release.get("schema_version") != 1
        or release.get("device") != "slate-pocket-v1r"
    ):
        errors.append("Unknown firmware manifest schema or device")
    for field in ("revision", "board_revision", "build_id", "reviewed_by"):
        if not _text(release.get(field)):
            errors.append(f"Missing firmware {field}")
    for field in ("selected_bom_sha256", "routed_pcb_sha256"):
        if not _digest(release.get(field)):
            errors.append(f"Missing or malformed {field}")
    images = release.get("images")
    if not isinstance(images, list) or not images:
        images = []
        errors.append("Firmware bundle has no images")
    image_by_id: dict[str, dict] = {}
    kinds: dict[str, list[str]] = {}
    paths: set[str] = set()
    resolved_paths: set[Path] = set()
    for image in images:
        if not isinstance(image, dict):
            errors.append("Firmware image record must be an object")
            continue
        identifier = image.get("id")
        kind = image.get("kind")
        if not _text(identifier) or identifier in image_by_id:
            errors.append(f"Missing or duplicate firmware image ID: {identifier}")
            continue
        image_by_id[identifier] = image
        if not _text(kind) or kind not in IMAGE_KINDS:
            errors.append(f"{identifier}: unknown image kind")
        else:
            kinds.setdefault(kind, []).append(identifier)
        for field in ("version", "target_partition", "license"):
            if not _text(image.get(field)):
                errors.append(f"{identifier}: missing {field}")
        relative = image.get("path")
        if _text(relative) and relative in paths:
            errors.append(f"{identifier}: duplicate image path")
        elif _text(relative):
            paths.add(relative)
        target = _contained_file(path.parent, relative)
        if target is None:
            errors.append(
                f"{identifier}: image is missing or outside release directory"
            )
        elif target in resolved_paths:
            errors.append(f"{identifier}: duplicate image file")
        elif target == path.resolve() or target.stat().st_size == 0:
            errors.append(f"{identifier}: image is empty or names the manifest")
        elif not _digest(image.get("sha256")) or _sha256(target) != image["sha256"]:
            errors.append(f"{identifier}: image hash mismatch")
        if target is not None:
            resolved_paths.add(target)
        if (
            not isinstance(image.get("size_bytes"), int)
            or isinstance(image.get("size_bytes"), bool)
            or image["size_bytes"] <= 0
        ):
            errors.append(f"{identifier}: invalid image size")
        elif target is not None and target.stat().st_size != image["size_bytes"]:
            errors.append(f"{identifier}: image size mismatch")
    for kind in (*BOOT_KINDS, "recovery"):
        if len(kinds.get(kind, [])) != 1:
            errors.append(f"Firmware bundle needs exactly one {kind} image")
    partitions = [
        image.get("target_partition")
        for image in image_by_id.values()
        if _text(image.get("target_partition"))
    ]
    if len(partitions) != len(set(partitions)):
        errors.append("Firmware images claim duplicate target partitions")
    order = release.get("boot_order")
    if (
        not isinstance(order, list)
        or any(not _text(identifier) for identifier in order)
        or len(order) != len(set(order))
        or any(identifier not in image_by_id for identifier in order)
        or [image_by_id[identifier].get("kind") for identifier in order]
        != list(BOOT_KINDS)
    ):
        errors.append("Boot order must name bootloader, kernel, and rootfs images")
        order = []
    drivers = release.get("drivers")
    if not isinstance(drivers, list):
        drivers = []
        errors.append("Firmware driver inventory is missing")
    roles: set[str] = set()
    for driver in drivers:
        if not isinstance(driver, dict):
            errors.append("Driver record must be an object")
            continue
        role = driver.get("role")
        if not _text(role) or role not in DRIVER_ROLES or role in roles:
            errors.append(f"Missing, unknown, or duplicate driver role: {role}")
            continue
        roles.add(role)
        if not _text(driver.get("image_id")) or driver["image_id"] not in image_by_id:
            errors.append(f"{role}: driver image is absent")
        elif image_by_id[driver["image_id"]].get("kind") not in {
            "kernel",
            "device_firmware",
        }:
            errors.append(f"{role}: driver must reside in kernel or device firmware")
        for field in ("driver", "device_identifier", "probe_command"):
            if not _text(driver.get(field)):
                errors.append(f"{role}: missing {field}")
    if roles != set(DRIVER_ROLES):
        errors.append("Firmware driver inventory does not cover required interfaces")
    flash = release.get("flash")
    if not isinstance(flash, dict):
        flash = {}
        errors.append("Flash plan is missing")
    for field in ("tool", "tool_version", "readback_command", "power_loss_response"):
        if not _text(flash.get(field)):
            errors.append(f"Flash plan needs {field}")
    tool = _contained_file(path.parent, flash.get("tool_path"))
    if tool is None or tool == path.resolve() or tool.stat().st_size == 0:
        errors.append("Flash tool file is missing, empty, or outside release directory")
    elif not _digest(flash.get("tool_sha256")) or _sha256(tool) != flash["tool_sha256"]:
        errors.append("Flash tool hash mismatch")
    steps = flash.get("steps")
    if (
        not isinstance(steps, list)
        or [step.get("image_id") for step in steps if isinstance(step, dict)]
        != [identifier for identifier in order if identifier in image_by_id]
        + kinds.get("device_firmware", [])
        + kinds.get("recovery", [])
        or len(steps)
        != len(order)
        + len(kinds.get("device_firmware", []))
        + len(kinds.get("recovery", []))
        or any(
            not isinstance(step, dict) or step.get("verify_readback") is not True
            for step in steps
        )
    ):
        errors.append("Flash steps must cover boot order and recovery with readback")
    recovery = release.get("recovery")
    if (
        not isinstance(recovery, dict)
        or recovery.get("image_id") not in kinds.get("recovery", [])
        or any(not _text(recovery.get(field)) for field in ("entry", "verify_command"))
    ):
        errors.append("Recovery procedure does not bind the recovery image")
    return {
        "status": "pass" if not errors else "fail",
        "source": RELEASE.as_posix(),
        "revision": release.get("revision"),
        "board_revision": release.get("board_revision"),
        "selected_bom_sha256": release.get("selected_bom_sha256"),
        "routed_pcb_sha256": release.get("routed_pcb_sha256"),
        "reviewed_by": release.get("reviewed_by"),
        "image_count": len(image_by_id),
        "driver_roles_checked": len(roles),
        "errors": errors,
        "caveat": "Bundle integrity and declared driver coverage do not establish boot, signature trust, device compatibility, or recovery on hardware.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path, nargs="?", default=RELEASE)
    args = parser.parse_args()
    report = audit(args.manifest)
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
