# Firmware release bundle proof

No Slate Pocket firmware release exists. The [hardware gate](build_to_function.md) now requires a controlled, machine-readable bundle for `firmware_boot`; a reviewed PDF or a filename alone cannot satisfy that record.

## Bundle contract

Place `firmware-release.json` and its image files under `engineering/hardware/released/firmware/`. The manifest must identify schema version 1, `slate-pocket-v1r`, firmware and board revisions, build ID, reviewer, and SHA-256 values for the approved selected BOM and routed PCB. The `firmware_boot` evidence record binds the manifest's exact bytes, revision, and reviewer. The gate also requires matching approved BOM and PCB evidence records, a passing selected-part proof, and the same board revision.

The manifest's `images` array contains exactly one each of `bootloader`, `kernel`, `rootfs`, and `recovery`; extra `device_firmware` images are allowed. Every image has a unique ID and target partition, version, license, relative file path, size, and SHA-256. The auditor rejects empty, missing, altered, duplicate, or out-of-directory files. `boot_order` names the bootloader, kernel, and rootfs in sequence. `flash.steps` names those images, any separate device firmware, then recovery, and requires readback verification at each step. The flash tool's file path and SHA-256, tool/version, readback command, and power-loss response must be recorded. The recovery procedure names its image, entry method, and verification command.

The `drivers` inventory must cover storage, display, touch, both cameras, speakers, microphones, USB, and antenna modules. Each role identifies a driver, device identifier, probe command, and the kernel or device-firmware image carrying it. These fields form a review checklist and test handoff; the auditor does not execute the commands.

```bash
python -m buildslate.firmware_proof engineering/hardware/released/firmware/firmware-release.json
python validation/validate_firmware_proof.py
buildslate hardware --require-design-release
```

The [fault fixture](../../validation/validate_firmware_proof.py) checks altered image bytes, path escape, size and partition mismatch, missing drivers, broken boot order, omitted readback, recovery mismatch, and stale BOM/board bindings. It uses synthetic bytes and is not firmware for the device.

This proof establishes file integrity and declared release coverage. It does not verify image signatures, secure boot policy, driver compatibility, boot success, flash safety, or recovery on physical hardware. Those need a selected platform design, supplier review, secure provisioning analysis, and serialized EVT0 measurements. The public [Hardware view](https://superflyad.github.io/BuildSlate/?tab=hardware) reports the bundle as missing until real release files exist.
