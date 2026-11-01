# Compute and Memory Evidence Review — Phase 1

Reviewed: 2026-10-31  
Status: **Public evidence available; platform not verified**

## Decision

Advance Snapdragon X2 Elite Extreme to supplier/NDA review at the 128 GB memory fallback. Use 128 GB external developer systems for workload characterization. Do not carry 512 GB into CAD as a credible first-build configuration.

## Findings

- No reviewed platform meets the combined 512 GB memory, sustained 100 TOPS, and 28 W Slate target.
- Snapdragon X2 Elite is the closest documented product-track option: 80–85 TOPS depending on SKU, 128/128+ GB maximum memory, and 152–228 GB/s bandwidth. Public documentation does not establish its sustained power or pocket integration geometry.
- Snapdragon 8 Elite Gen 5 provides the best mobile integration posture but publicly supports only up to 24 GB.
- AMD Ryzen AI Max and NVIDIA Jetson AGX Thor expose useful 128 GB development environments but start above the Slate power target and are not physical candidates.
- Public 32 GB LPDDR5X packages make a four-package 128 GB hypothesis conceivable; controller support, placement, routing, power, thermals, and procurement remain unverified.

## Gate impact

The 512 GB risk remains blocked. The 100 TOPS headline remains aspirational. The 128 GB fallback is now the only reviewed memory tier with platform-level public support, but it cannot be marked verified until package, power, software, and supply evidence are obtained.

This review is a public-source architecture screen, not a benchmark, supplier approval, platform selection, or proof of sustained performance.
