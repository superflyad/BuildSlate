# Compute Package and Memory Topology — Phase 1

Reviewed: 2026-11-24
Status: **Architecture narrowed; package topology not verified**

## Current architecture decision

Use Qualcomm Snapdragon X2 Elite Extreme as the first product-track RFQ because its public brief is the closest reviewed match to the locked 128 GB fallback and provides 228 GB/s memory bandwidth, an 80 TOPS INT8 NPU, dual PCIe 5.0, and UFS 4.0.

This is not a component selection. Snapdragon X2 is a client-PC platform, and the public brief does not provide the package drawing, PMIC/rail design, sustained power telemetry, board area, procurement path, or pocket-device thermal behavior required to select it.

## Memory topology findings

- Snapdragon 8 Elite Gen 5 and both Gen 6 mobile SKUs have integrated phone systems, but their public maximum memory is 24 GB. None can satisfy the approved 128 GB floor.
- Snapdragon X2 Elite documentation lists 128 GB or 128+ GB maximum capacity depending on SKU. This supports research at the locked 128 GB tier; it does not support 256 GB or 512 GB.
- Qualcomm's [X2 Plus brief](https://www.qualcomm.com/content/dam/qcomm-martech/dm-assets/documents/Snapdragon-X2-Plus-Product-Brief.pdf) lists a 128 GB maximum on a 128-bit LPDDR5X bus for both `X2P-64-100` (10-core) and `X2P-42-100` (6-core). [HP lists a 32 GB 10-core system](https://www.hp.com/us-en/shop/mdp/elitebook-6-series-14-inch-%28qualcomm%29-laptops-tab4-module4-elitebook6-14qualcomm); [Lenovo lists up to 32 GB soldered on its 6-core system](https://psref.lenovo.com/syspool/Sys/PDF/IdeaPad/IdeaPad_Slim_5_13Q8Y11/IdeaPad_Slim_5_13Q8Y11_Spec.PDF). These are parallel supplier questions, not selected lower-power or 128 GB configurations.
- [ASUS's Zenbook A16 specification](https://www.asus.com/laptops/for-home/zenbook/asus-zenbook-a16-ux3607/techspec/) lists X2 Elite Extreme configurations with 48 GB memory on package. [TechInsights' physical package analysis](https://www.techinsights.com/ja/node/61888) reports three 16 GB LPDDR5X packages co-packaged with the processor in a Zenbook A16. The observed 48 GB package does not establish an orderable 128 GB X2 option or external memory support. The separate memory boxes in the concept CAD are a hypothetical external placement screen, not the observed X2 package.
- Micron announced an 8–32 GB LPDDR5X range for 2026 flagship smartphones, and Samsung advertises a 32 GB LPDDR5X capacity. Micron's exact [`MT62F4G64DAFL-023 WT:C`](https://www.micron.com/products/obsolete/obsolete-lpddr5x/part-catalog/part-detail/mt62f4g64dafl-023-wt-c) is 32 GB in a 14 × 12.4 × 0.96 mm x64 package, but Micron marks it obsolete. It exceeds the present 14 × 10 mm planning sites, and four independent x64 connections need 256 data bits against the X2 Extreme's 192-bit bus. A current-production, X2-qualified four-package topology remains unavailable in the reviewed public sources.
- Micron's exact `MT62F2G64D8EK-023 WT:C` public listing is 128 Gb, or 16 GB, in a 14 × 14 × 1.1 mm package. An eight-package 128 GB arithmetic alternative would exceed the four memory planning sites and needs its own qualified channel topology and board design. See the [package fit screen](../../../docs/engineering/memory_package_fit.md).
- ADATA's [US LPDDR5X page](https://www.adata.com/us/embedded/lpddr5x/) labels `L5CG32D2023MCAS`/`L5EG32D4023MCAS` as 32GB/64GB, but its [UK page](https://www.adata.com/uk/embedded/lpddr5x/) labels the same parts 32Gb/64Gb. The US organization fields (1024M x32 and 2048M x32) calculate to 4GB and 8GB. Four parts therefore do not form 128GB; both 12.4 × 15 mm outlines also exceed the current 14 × 10 mm planning sites. The [computed unit screen](../../../docs/engineering/memory_package_fit.md) prevents the US label from promoting these parts into a 128GB build.
- The X2 Elite Extreme brief lists a 192-bit bus. Eight independent x64 connections for the Micron reference part would need 512 data bits. Shared-channel or another attachment may exist, but the reviewed public sources do not qualify one. The eight-package CAD is only an outline study.
- A 512 GB topology would imply sixteen 32 GB packages and exceeds the documented memory maximum of the reviewed Snapdragon platforms. It remains aspirational and is not a Phase 1 product configuration.

## Prototype strategy

Use an external 128 GB developer platform to characterize target models, runtimes, memory allocation, bandwidth, and thermal duty cycle while product-platform access is negotiated. AMD Ryzen AI Max and NVIDIA Jetson AGX Thor are valid lab references, not pocket integration candidates: their published power ranges begin at 45 W and 40 W respectively.

## Required Qualcomm RFQ/NDA package

- SoC package drawing, keepouts, mounting and thermal limits.
- Orderable 128 GB SKU and whether its memory is on package, off package, or mixed; supported topology, qualified memory parts, package count, placement, and routing guidance.
- PMIC, rail map, sequencing, transient load, and reference design.
- Sustained and peak power telemetry for defined NPU/GPU/CPU workloads.
- Supported precision, runtime/compiler coverage, benchmark disclosure, and long-duration throttle behavior.
- Development hardware, BSP/runtime access, commercial availability, lifecycle, price, and minimum order quantity.

## Primary sources

- [Qualcomm Snapdragon X2 Elite product brief](https://www.qualcomm.com/content/dam/qcomm-martech/dm-assets/documents/Snapdragon-X2-Elite-Product-Brief.pdf)
- [Qualcomm Snapdragon X2 Plus product brief](https://www.qualcomm.com/content/dam/qcomm-martech/dm-assets/documents/Snapdragon-X2-Plus-Product-Brief.pdf)
- [Qualcomm Snapdragon 8 Elite Gen 5 product brief](https://www.qualcomm.com/content/dam/qcomm-martech/dm-assets/documents/Snapdragon-8-Elite-Gen-5-product-brief.pdf)
- [Qualcomm Snapdragon 8 Elite Gen 6 product brief](https://www.qualcomm.com/content/dam/qcomm-martech/dm-assets/documents/Snapdragon-8-Elite-Gen-6-Product-Brief.pdf)
- [Qualcomm Snapdragon 8 Elite Extreme Gen 6 product brief](https://www.qualcomm.com/content/dam/qcomm-martech/dm-assets/documents/Snapdragon-8-Elite-Extreme-Gen-6-Product-Brief.pdf)
- [Micron 2026 flagship LPDDR5X package announcement](https://investors.micron.com/news/press-release/2025/Micron-Ships-Worlds-First-1-1-Gamma-Based-LPDDR5X-Enabling-Rich-Mobile-AI-Experiences-06-03-2025/default.aspx)
- [Samsung LPDDR5X product page](https://semiconductor.samsung.com/dram/lpddr/lpddr5x/)
- [AMD Ryzen AI Max product guide](https://www.amd.com/content/dam/amd/en/documents/partner-hub/ryzen/ryzen-consumer-master-quick-reference-competitive.pdf)
- [NVIDIA Jetson AGX Thor developer documentation](https://developer.nvidia.com/blog/introducing-nvidia-jetson-thor-the-ultimate-platform-for-physical-ai)
