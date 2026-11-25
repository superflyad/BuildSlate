# 128 GB compute path

The product decision is to retain **128 GB** as Slate Pocket v1R's minimum memory configuration. The [public platform screen](../../buildslate/platform_fit.py) compares that floor with manufacturer specifications and appears in the [Hardware view](https://superflyad.github.io/BuildSlate/?tab=hardware). It is a source screen, not a selected BOM or a measured Slate device.

## What is established

| Platform | Public 128 GB evidence | Phone integration | Slate disposition |
| --- | --- | --- | --- |
| Snapdragon X2 Elite Extreme | Qualcomm's [product brief](https://www.qualcomm.com/content/dam/qcomm-martech/dm-assets/documents/Snapdragon-X2-Elite-Product-Brief.pdf) lists a 128+ GB controller maximum; [ASUS specifies 48 GB memory on package](https://www.asus.com/laptops/for-home/zenbook/asus-zenbook-a16-ux3607/techspec/) in its X2 Zenbook A16. [TechInsights' physical analysis](https://www.techinsights.com/ja/node/61888) reports three co-packaged 16 GB DRAM packages. No 128 GB orderable configuration is established. | Separate modem system is supported in the brief; Slate RF, power, firmware, and antenna integration is not designed | First product-track supplier request, not selected |
| Snapdragon X2 Plus, 10-core `X2P-64-100` and 6-core `X2P-42-100` | Qualcomm's [X2 Plus brief](https://www.qualcomm.com/content/dam/qcomm-martech/dm-assets/documents/Snapdragon-X2-Plus-Product-Brief.pdf) lists a 128 GB maximum on a 128-bit LPDDR5X bus for both SKUs. No reviewed 128 GB configured or orderable system, qualified package topology, or measured Slate power is established. | External X75 modem path is supported, but Slate phone integration is not designed | Parallel supplier question; neither SKU is selected |
| Snapdragon 8 Elite Gen 5 | [Product brief](https://www.qualcomm.com/content/dam/qcomm-martech/dm-assets/documents/Snapdragon-8-Elite-Gen-5-SM8850-5-AC-Product-Brief.pdf) lists 24 GB maximum | Integrated cellular | Below Slate memory floor |
| Snapdragon 8 Elite Gen 6 and Extreme Gen 6 | Both [Gen 6](https://www.qualcomm.com/content/dam/qcomm-martech/dm-assets/documents/Snapdragon-8-Elite-Gen-6-Product-Brief.pdf) and [Extreme](https://www.qualcomm.com/content/dam/qcomm-martech/dm-assets/documents/Snapdragon-8-Elite-Extreme-Gen-6-Product-Brief.pdf) briefs list 24 GB maximum | Integrated cellular | Below Slate memory floor |
| AMD Ryzen AI Halo developer platform | AMD [lists a 128 GB configured developer system](https://www.amd.com/en/products/processors/desktops/ryzen/ryzen-ai-halo/ryzen-ai-max-plus-395.html) | No integrated phone path established | External workload reference |
| NVIDIA Jetson T5000 module | NVIDIA [lists a configured 128 GB module](https://www.nvidia.com/en-us/autonomous-machines/embedded-systems/jetson-thor/) with a 100 × 87 mm face and 40–130 W modes | No integrated phone path established | The bare module face fits the body rectangle, but its minimum published mode is 12 W above Slate's 28 W sustained screen. Height, carrier, cooling, and integration remain unproven. |
| congatec conga-HPC/cRX1-X199-128G | congatec [lists exact part 053700](https://www.congatec.com/en/products/com-hpc/conga-hpccrx1/) with 128 GB onboard LPDDR5X and a 160 × 120 mm module | No integrated phone path established | Its 120 mm short side exceeds Slate's 95 mm body width by 25 mm; its lowest published 45 W TDP is 17 W above Slate's sustained screen. Bench reference only. |

The inference from these public specifications is narrow: 128 GB is real in other cataloged and configured modules, and a 128 GB *controller maximum* exists in the X2 Elite and Plus families. The reviewed commercial X2 configuration has 48 GB on package. No reviewed source proves an orderable 128 GB X2 package or a board that fits the 180 × 95 × 9.5 mm Slate envelope, sustains its workload within the thermal limit, and operates as a phone. Fewer X2 Plus cores do not establish lower sustained power. Published power modes are not measured power draw. The [candidate data](../../research/evidence/compute/platform-comparison.yaml) and [computed screen](../../buildslate/platform_fit.py) keep these distinctions explicit.

The [package screen](memory_package_fit.md) tests the board's four assumed 32 GB sites against exact public Micron LPDDR5X packages. Its 32 GB reference is obsolete, does not fit the sites, and four independent x64 connections would exceed the X2 Extreme's 192-bit bus. The 16 GB alternative needs eight packages and also does not fit those four rectangles; eight independent x64 connections would need 512 bits. It also reconciles a unit conflict on ADATA's US and UK pages: two parts labeled 32GB/64GB in the US are 32Gb/64Gb, or 4GB/8GB, by their published organization. A supplier-supported shared-channel or other topology remains unverified. None of these references selects memory.

The eight off-package memory boxes in the concept CAD do **not** depict the reviewed X2 Extreme 48 GB system-in-package. An X2 128 GB design needs a supplier-confirmed package option or a documented, supported external attachment before those boxes can become component placements.

## Proof required for Slate

1. Obtain the exact orderable X2 128 GB SKU and determine whether memory is on package, off package, or mixed. Require a supplier supported 128 GB LPDDR5X topology, qualified memory MPNs, package count, pin and routing rules, package drawings, and complete reference design. A four by 32 GB calculation alone is not controller or board qualification.
2. Release the selected BOM, rail and PMIC design, schematic, routed board, stackup, interconnect, thermal assembly, boot chain, and modem integration against those exact part revisions. The [hardware gate](build_to_function.md) must accept the controlled design package.
3. Build a serialized unit and record installed and usable memory from the booted target. Run the guarded [resident memory probe](../../buildslate/memory_probe.py) on that unit, then submit its JSON with the required [M20 EVT0 test](../../validation/evt0/test-matrix.yaml). Reproduce long-duration workloads with measured power and temperature. Keep raw logs, source hashes, calibration, and reviewer disposition.
4. Integrate and measure cellular calling and data before calling the result a phone. The present EVT0 configuration defers cellular; it cannot satisfy phone function by itself.

The next outside dependency is the X2 supplier design package and access to a qualified 128 GB configuration. Until it exists, the selected BOM and design release remain blocked. Public maximum capacity must not be reported as measured Slate memory.

## Resident memory exercise

On an authorized, booted target with the matching unit and build IDs, run:

```bash
python -m buildslate.memory_probe --execute --unit-id UNIT-ID --build-id BUILD-ID --output analysis/memory-probe.json
```

The command refuses to run without `--execute`. Before allocation, it requires at least 120 billion bytes of OS-visible physical memory and enough available physical memory for a 96 GiB allocation plus an 8 GiB reserve. It holds the allocation concurrently, fills every allocated byte with address-specific SHAKE256 data in 1 MiB regions, verifies every byte against regenerated data, and checks that at least 99% of the allocation remains in the process working set. Linux also rejects observed swap growth. The result records the unit/build IDs, OS counters, verified byte and page counts, mismatched region count, pattern version, and resident delta. Windows does not independently report swap growth; its working-set requirement still applies.

The M20 evidence reviewer requires a hash-bound `analysis/memory-probe.json` from this tool, rejects the earlier page-marker format, and reconciles it with raw M20 capacity and activity columns. The probe does not authenticate supplier DRAM identity or cover memory outside its 96 GiB allocation. A 128 GB **Slate** claim also needs the selected part topology, reviewed board, calibrated physical build record, and engineering signoff. The repository currently has none of those physical records. The [32 MiB smoke validator](../../validation/validate_memory_probe.py) checks the tool, not a 128 GB device.
