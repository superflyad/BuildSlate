# Compute and Memory Platform RFI/NDA Data Request

Status: **Prepared, not sent**  
Initial target: **Qualcomm Snapdragon X2 Elite platform team**

## Purpose

Determine whether a Snapdragon X2-family platform can support the Slate Pocket v1R 128 GB fallback with defensible package, power, performance, software, lifecycle, and supply evidence.

## Locked decision boundary

- Preferred RFQ memory tier: 128 GB unified/system memory.
- 512 GB remains aspirational and must not influence CAD without a documented controller and package topology.
- Platform selection is governed by measured workload performance per watt, not headline TOPS.
- Screening envelope: 28 W sustained and 45 W peak are hypotheses, not accepted platform limits.
- Device envelope: 180 × 95 × 9.5 mm; passive spreading is the current concept.

## Workload disclosure requested

Please identify supported precision, runtime, memory use, bandwidth, sustained power, throttling, and performance for representative on-device workloads such as 13B/30B dense language models, Mixtral 8x7B-class mixtures, Whisper, CLIP, and a 70B INT4 fit experiment. Vendor-standard equivalent workloads are acceptable when conditions are fully disclosed.

## Required engineering data

- Orderable platform/SKU, package drawing, height, keepouts, mounting, and thermal-interface requirements.
- Supported 128 GB topology: qualified memory parts, package count/capacity, bus width, placement, routing, termination, and bandwidth.
- Memory-controller maximums and any 256/512 GB roadmap support, clearly separated from production support.
- PMIC/rail map, sequencing, reference schematic, average/peak/transient current, regulator losses, and reference decoupling.
- Sustained/peak CPU, GPU, NPU, memory, and total platform power under defined workloads and temperatures.
- NPU precision, compiler/runtime/kernel coverage, concurrency, model limits, benchmark methodology, and throttling behavior.
- Boot/storage/display/camera/high-speed I/O capabilities and reference-layout constraints.
- Security features needed for measured boot, secure storage, memory protection, attestation, and radio isolation.
- Evaluation hardware, BSP/SDK/toolchain access, license terms, supported OSes, debug capability, and update policy.
- Sample and production availability, qualification status, lifecycle, PCN/EOL policy, MOQ, lead time, pricing basis, and geographic restrictions.

## Decision thresholds

- A 128 GB topology must be supplier-supported, not inferred from package multiplication.
- Peak TOPS without workload, precision, power, duration, and thermal conditions is insufficient.
- Public claims may open the review; package/power/software evidence is required to verify it.
- Alternatives below 128 GB should state the best supported workload tier and product impact.

## Requested deliverables

- Completed YAML response template.
- Product brief plus NDA package/reference-design material.
- Supported memory topology and qualified-vendor list.
- Power/performance workbook or telemetry with test conditions.
- Development-access and commercial-lifecycle proposal.

This request is exploratory and does not constitute a purchase commitment or platform selection.
