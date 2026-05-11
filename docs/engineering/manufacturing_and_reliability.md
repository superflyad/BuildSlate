# Manufacturing and Reliability Screening

BuildSlate treats manufacturability as a physical constraint, not a late-stage production detail. Thin AI-device architectures concentrate batteries, compute packages, thermal spreaders, antennas, cameras, bonded glass, and structural rails into a small z-height budget. These screens are intentionally first-order: they expose likely pressure points before CAD, supplier drawings, tolerance distributions, fixtures, process capability data, and reliability testing exist.

## What the models cover

The scripts in `engineering/manufacturing_models/` estimate manufacturing and reliability pressure from several independent constraints:

- **Tolerance stackup**: stacked components accumulate dimensional uncertainty. Worst-case linear addition is conservative, while RSS gives a less severe reference estimate when independent distributions are plausible.
- **Thermal expansion mismatch**: bonded materials with different coefficients of thermal expansion can build stress across long interfaces during heating and cooling.
- **Battery swelling allowance**: pouch or pack growth must be accommodated without consuming nominal clearances or pressing into displays, covers, frames, or thermal layers.
- **Assembly complexity**: high component count, PCB layer count, camera count, antenna windows, and thermal-stack layers increase inspection, alignment, fixture, and process-control pressure.
- **Reliability hotspots**: recurring high-risk regions often emerge where heat, structural discontinuities, battery pressure, connectors, and camera islands overlap.
- **Repairability pressure**: thinness, adhesives, bonded glass, stacked thermal assemblies, and low battery removability can conflict with safe service access.
- **Yield risk indicators**: dense packaging, high layer counts, thin z-height, complex thermal stacks, antenna breaks, and camera modules raise manufacturing sensitivity.

## Why thin devices amplify tolerance sensitivity

A small global thickness target leaves little room for accumulated part tolerance, adhesive thickness variation, compression pads, seal height, screw bosses, frame flatness, and local package height. A stack that passes nominal arithmetic can still fail once worst-case dimensional contributors are applied. The tolerance model therefore reports both linear worst-case accumulation and RSS accumulation so reviews can separate conservative clearance risk from statistical assumptions.

## Battery swelling must be accommodated

Battery thickness is not a fixed geometric constant over product life. Swelling allowance must be reserved in the mechanical stack so cell growth does not preload the display, rear housing, frame, wireless charging stack, or local thermal layers. The battery swelling model is not a safety certification model; it is a clearance screen that makes the allowance visible.

## Thermal expansion mismatch over bonded surfaces

Long bonded interfaces can experience differential expansion when materials with different CTE values are constrained together. The thermal expansion model uses typical CTE constants from `engineering/constants/materials.yaml` and reports mismatch across common material pairs. Adhesive compliance, geometry, creep, local ribs, slots, and cycling profiles are not modeled, so high mismatch should trigger deeper mechanical review rather than a pass/fail feasibility claim.

## Assembly complexity affects yield pressure

More components, denser PCBs, more antenna windows, stacked thermal layers, and multi-camera modules increase the number of alignment, handling, bonding, inspection, and rework-sensitive operations. The assembly and yield models report pressure indicators rather than factory yield percentages. They are intended to flag escalation risk before detailed process design.

## Repairability tradeoffs

Repairability often conflicts with thinness and thermal performance. Adhesives, bonded glass, compressed stacks, large heat spreaders, and buried batteries can improve packaging or thermal paths while making service access destructive or high risk. The repairability model therefore treats low battery removability, high screen-removal risk, and high internal layer complexity as blockers that should be visible in architecture reviews.

## Reliability hotspots

Reliability hotspots emerge from concentration. Compute power creates thermal gradients; camera islands and antenna windows interrupt structure; batteries require swelling space; connectors and flexes concentrate repeated stress; wireless charging can heat the rear stack. The hotspot model prints categorized regions for review and does not claim durability, qualification, or product lifetime.

## Interpretation limits

These models are conservative screening tools only. They do not replace CAD, tolerance analysis, FEA, thermal simulation, drop testing, HALT/HASS, supplier process capability, teardown validation, or factory yield data. No output should be read as a manufacturing feasibility claim.
