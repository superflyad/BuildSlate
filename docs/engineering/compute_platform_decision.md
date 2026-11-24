# 128 GB compute path

The product decision is to retain **128 GB** as Slate Pocket v1R's minimum memory configuration. The [public platform screen](../../buildslate/platform_fit.py) compares that floor with manufacturer specifications and appears in the [Hardware view](https://superflyad.github.io/BuildSlate/?tab=hardware). It is a source screen, not a selected BOM or a measured Slate device.

## What is established

| Platform | Public 128 GB evidence | Phone integration | Slate disposition |
| --- | --- | --- | --- |
| Snapdragon X2 Elite Extreme | Qualcomm's [product brief](https://www.qualcomm.com/content/dam/qcomm-martech/dm-assets/documents/Snapdragon-X2-Elite-Product-Brief.pdf) lists a 128+ GB controller maximum; the example is configured at 48 GB | Separate modem system is supported in the brief; Slate RF, power, firmware, and antenna integration is not designed | First product-track supplier request, not selected |
| Snapdragon 8 Elite Gen 5 | [Product brief](https://www.qualcomm.com/content/dam/qcomm-martech/dm-assets/documents/Snapdragon-8-Elite-Gen-5-SM8850-5-AC-Product-Brief.pdf) lists 24 GB maximum | Integrated cellular | Below Slate memory floor |
| Snapdragon 8 Elite Gen 6 and Extreme Gen 6 | Both [Gen 6](https://www.qualcomm.com/content/dam/qcomm-martech/dm-assets/documents/Snapdragon-8-Elite-Gen-6-Product-Brief.pdf) and [Extreme](https://www.qualcomm.com/content/dam/qcomm-martech/dm-assets/documents/Snapdragon-8-Elite-Extreme-Gen-6-Product-Brief.pdf) briefs list 24 GB maximum | Integrated cellular | Below Slate memory floor |
| AMD Ryzen AI Halo developer platform | AMD [lists a 128 GB configured developer system](https://www.amd.com/en/products/processors/desktops/ryzen/ryzen-ai-halo/ryzen-ai-max-plus-395.html) | No integrated phone path established | External workload reference |
| NVIDIA Jetson AGX Thor developer kit | NVIDIA [lists 128 GB](https://www.nvidia.com/en-us/autonomous-machines/embedded-systems/jetson-thor/) and a 40–130 W module range | No integrated phone path established | External workload reference; published minimum power exceeds the 28 W Slate screen |

The inference from these public specifications is narrow: a 128 GB *controller maximum* exists in the preferred X2 family, and separate 128 GB development systems exist. No reviewed source proves a qualified 128 GB X2 board that fits the 180 × 95 × 9.5 mm Slate envelope, sustains its workload within the thermal limit, and operates as a phone. The [candidate data](../../research/evidence/compute/platform-comparison.yaml) records each source and the unresolved limits.

The [package screen](memory_package_fit.md) tests the board's four assumed 32 GB sites against an exact public 16 GB Micron LPDDR5X package. That alternative requires eight packages and does not fit the present rectangles. It does not change the 128 GB decision or select memory.

## Proof required for Slate

1. Obtain the exact X2 SKU, supplier supported 128 GB LPDDR5X topology, qualified memory MPNs, package count, pin and routing rules, package drawings, and complete reference design. A four by 32 GB calculation alone is not controller or board qualification.
2. Release the selected BOM, rail and PMIC design, schematic, routed board, stackup, interconnect, thermal assembly, boot chain, and modem integration against those exact part revisions. The [hardware gate](build_to_function.md) must accept the controlled design package.
3. Build a serialized unit and record installed and usable memory from the booted target. Run the guarded [resident memory probe](../../buildslate/memory_probe.py) on that unit, then submit its JSON with the required [M20 EVT0 test](../../validation/evt0/test-matrix.yaml). Reproduce long-duration workloads with measured power and temperature. Keep raw logs, source hashes, calibration, and reviewer disposition.
4. Integrate and measure cellular calling and data before calling the result a phone. The present EVT0 configuration defers cellular; it cannot satisfy phone function by itself.

The next outside dependency is the X2 supplier design package and access to a qualified 128 GB configuration. Until it exists, the selected BOM and design release remain blocked. Public maximum capacity must not be reported as measured Slate memory.

## Resident memory exercise

On an authorized, booted target with the matching unit and build IDs, run:

```bash
python -m buildslate.memory_probe --execute --unit-id UNIT-ID --build-id BUILD-ID --output analysis/memory-probe.json
```

The command refuses to run without `--execute`. Before allocation, it requires at least 120 billion bytes of OS-visible physical memory and enough available physical memory for a 96 GiB allocation plus an 8 GiB reserve. It holds the allocation concurrently, writes a distinct marker on every memory page, verifies every marker, and checks that at least 99% of the allocation remains in the process working set. Linux also rejects observed swap growth. The result records the unit/build IDs, OS counters, verified page count, error count, and resident delta. Windows does not independently report swap growth; its working-set requirement still applies.

The M20 evidence reviewer requires a hash-bound `analysis/memory-probe.json` from this tool and reconciles it with raw M20 capacity and activity columns. The probe does not authenticate supplier DRAM identity or test every bit on every chip. A 128 GB **Slate** claim also needs the selected part topology, reviewed board, calibrated physical build record, and engineering signoff. The repository currently has none of those physical records. The [32 MiB smoke validator](../../validation/validate_memory_probe.py) checks the tool, not a 128 GB device.
