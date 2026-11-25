# Compute and Memory Evidence Review — Phase 1

Reviewed: 2026-11-24
Status: **Public evidence available; platform not verified**

## Decision

Keep the approved 128 GB floor. Advance Snapdragon X2 Elite Extreme to supplier/NDA review for an actual qualified 128 GB memory configuration and pocket integration package. Use 128 GB external developer systems for workload characterization. Do not carry 512 GB into CAD as a credible first-build configuration.

## Findings

- No reviewed platform meets the combined 512 GB memory, sustained 100 TOPS, and 28 W Slate target.
- Snapdragon X2 Elite is the closest documented product-track option: 80–85 TOPS depending on SKU, 128/128+ GB maximum memory, and 152–228 GB/s bandwidth. Public documentation does not establish its sustained power or pocket integration geometry.
- Snapdragon 8 Elite Gen 5 and both 2026 Gen 6 mobile SKUs publicly support only up to 24 GB. They cannot satisfy the approved 128 GB floor.
- The X2 Elite Extreme public brief states a 128+ GB controller maximum, but its example configuration is 48 GB. [ASUS lists a 48 GB memory-on-package X2 Zenbook A16](https://www.asus.com/laptops/for-home/zenbook/asus-zenbook-a16-ux3607/techspec/), and [TechInsights reports three co-packaged 16 GB DRAM packages](https://www.techinsights.com/ja/node/61888) in physical analysis. That establishes a real 48 GB configuration, not a shipped or qualified 128 GB X2 package or board.
- NVIDIA's Jetson AGX Thor developer kit and AMD's Ryzen AI Halo developer platform publicly list 128 GB configurations. They prove that external 128 GB development hardware exists, not that Slate's enclosure, power target, or phone functions are achievable.
- AMD Ryzen AI Max and NVIDIA Jetson AGX Thor expose useful 128 GB development environments but start above the Slate power target and are not physical candidates.
- An exact public 32 GB Micron LPDDR5X MPN exists, but Micron marks it obsolete. It does not fit the four planning sites or an independent x64-per-package connection to the X2 Extreme's 192-bit bus. Current-production package selection, controller topology, placement, routing, power, thermals, and procurement remain unverified.

## Gate impact

The 512 GB risk remains blocked. The 100 TOPS headline remains aspirational. The 128 GB fallback has platform-level public capacity support and external development systems, but no verified Slate topology. Supplier package, power, software, modem, and supply evidence must precede selection. The [platform fit screen](../../../docs/engineering/compute_platform_decision.md) keeps these proof levels separate.

This review is a public-source architecture screen, not a benchmark, supplier approval, platform selection, or proof of sustained performance.
