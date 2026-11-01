# Compute Package and Memory Topology — Phase 1

Reviewed: 2026-10-31  
Status: **Architecture narrowed; package topology not verified**

## Current architecture decision

Use Qualcomm Snapdragon X2 Elite Extreme as the first product-track RFQ because its public brief is the closest reviewed match to the locked 128 GB fallback and provides 228 GB/s memory bandwidth, an 80 TOPS INT8 NPU, dual PCIe 5.0, and UFS 4.0.

This is not a component selection. Snapdragon X2 is a client-PC platform, and the public brief does not provide the package drawing, PMIC/rail design, sustained power telemetry, board area, procurement path, or pocket-device thermal behavior required to select it.

## Memory topology findings

- Snapdragon 8 Elite Gen 5 is the stronger integration reference for a pocket device, but its public maximum memory is 24 GB. It cannot satisfy the 128 GB fallback.
- Snapdragon X2 Elite documentation lists 128 GB or 128+ GB maximum capacity depending on SKU. This supports research at the locked 128 GB tier; it does not support 256 GB or 512 GB.
- Micron publicly describes 8–32 GB LPDDR5X packages for 2026 flagship smartphones, and Samsung advertises a 32 GB LPDDR5X capacity. A 128 GB topology therefore implies four 32 GB packages before controller, routing, package-height, power, thermal, and availability constraints.
- A 512 GB topology would imply sixteen 32 GB packages and exceeds the documented memory maximum of the reviewed Snapdragon platforms. It remains aspirational and is not a Phase 1 product configuration.

## Prototype strategy

Use an external 128 GB developer platform to characterize target models, runtimes, memory allocation, bandwidth, and thermal duty cycle while product-platform access is negotiated. AMD Ryzen AI Max and NVIDIA Jetson AGX Thor are valid lab references, not pocket integration candidates: their published power ranges begin at 45 W and 40 W respectively.

## Required Qualcomm RFQ/NDA package

- SoC package drawing, keepouts, mounting and thermal limits.
- Supported 128 GB memory topology, qualified memory parts, package count, placement, and routing guidance.
- PMIC, rail map, sequencing, transient load, and reference design.
- Sustained and peak power telemetry for defined NPU/GPU/CPU workloads.
- Supported precision, runtime/compiler coverage, benchmark disclosure, and long-duration throttle behavior.
- Development hardware, BSP/runtime access, commercial availability, lifecycle, price, and minimum order quantity.

## Primary sources

- [Qualcomm Snapdragon X2 Elite product brief](https://www.qualcomm.com/content/dam/qcomm-martech/dm-assets/documents/Snapdragon-X2-Elite-Product-Brief.pdf)
- [Qualcomm Snapdragon 8 Elite Gen 5 product brief](https://www.qualcomm.com/content/dam/qcomm-martech/dm-assets/documents/Snapdragon-8-Elite-Gen-5-product-brief.pdf)
- [Micron 2026 flagship LPDDR5X package announcement](https://investors.micron.com/news/press-release/2025/Micron-Ships-Worlds-First-1-1-Gamma-Based-LPDDR5X-Enabling-Rich-Mobile-AI-Experiences-06-03-2025/default.aspx)
- [Samsung LPDDR5X product page](https://semiconductor.samsung.com/dram/lpddr/lpddr5x/)
- [AMD Ryzen AI Max product guide](https://www.amd.com/content/dam/amd/en/documents/partner-hub/ryzen/ryzen-consumer-master-quick-reference-competitive.pdf)
- [NVIDIA Jetson AGX Thor developer documentation](https://developer.nvidia.com/blog/introducing-nvidia-jetson-thor-the-ultimate-platform-for-physical-ai)
