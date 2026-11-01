# Slate Pocket v1R Provisional Stackup Review

Status: **Planned pre-supplier CAD work; not an evidence-backed fit claim**

## What changed

The v1R mechanical screen now uses local zones instead of adding display, battery, PCB, SoC, memory, storage, camera, thermal, and charging thicknesses as though they all occupy one vertical section.

The blocking model reserves separate battery, compute, camera, rear-overlay, thermal-overlay, and perimeter keepout regions. It uses the public Enovix AI1-M01 envelope only as a battery geometry reference; that published cell is not selected and is slightly larger than the current complete-pack volume allocation.

## Provisional conclusions

- A battery zone using the 5.44 mm public cell reference has positive screening margin only because pack overhead, swelling, structure, cover, adhesive, and tolerances remain placeholders.
- Adding the current 0.8 mm wireless-charging allowance to the battery zone is expected to exceed the 9.5 mm envelope. Wireless charging remains a negotiable feature.
- Compute and camera zones have nominal z-height room, but the package, board, shields, connectors, thermal interfaces, optics, and tolerance geometry are not supplier-backed.
- Perimeter RF, connector, acoustic, and service zones materially reduce the planform available to battery and PCB placement.
- The model cannot support a manufacturability or industrial-design claim until supplier drawings replace the placeholders.

## Exit conditions

Before `mechanical_cad_stackup` may become `available` or `verified`:

1. Phase 1 supplier packages must be verified.
2. Supplier package drawings must replace critical reference and placeholder geometry.
3. Battery tabs, protection, swelling, and restraint must be part of the pack body.
4. PCB placement must include shields, connectors, flexes, fasteners, test points, and service access.
5. RF and acoustic keepouts must be approved by their subsystem owners.
6. Zone section drawings and a tolerance stack must show positive margin.
7. A mass rollup must use selected or shortlisted components.

Until then, generated results are useful for finding conflicts and preparing CAD—not proving fit.
