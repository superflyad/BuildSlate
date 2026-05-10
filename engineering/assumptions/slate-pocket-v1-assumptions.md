# Slate Pocket v1 Assumption Registry

## Purpose

This registry makes Slate pocket v1 claims traceable to source intent, constants, equations, modeled estimates, explicit assumptions, or unresolved blockers. It is not proof that Slate pocket v1 is production-buildable today.

## Known values from Slate v1 PDF

The Slate v1 PDF is treated as source intent for product targets that need engineering validation before they become build claims. Current tracked targets include:

- Pocket-class Slate device concept.
- 6000mAh battery target.
- 512GB LPDDR6X memory target.
- 100 TOPS NPU target.
- 8.8mm chassis thickness target.
- 250g mass target.

## Modeled estimates

Modeled estimates are first-pass calculations using explicit constants and formulas in `engineering/constants/` and `engineering/models/`.

- Battery energy uses `Ah = mAh / 1000` and `Wh = Ah * nominal_voltage_v`.
- Usable energy and runtime are ranges because usable capacity depends on reserve limits, discharge rate, temperature, aging, and power-management policy.
- Model memory fit estimates parameter storage plus overhead; they do not prove runtime speed, memory bandwidth, or sustained thermal behavior.
- Surface area, volume, heat density, and heat flux use rectangular approximations until CAD replaces them.
- Mass budget is a placeholder allocation that must be replaced by component-level BOM and CAD-derived masses.

## Aggressive assumptions

Aggressive assumptions are preserved so targets can be explored, but they must remain clearly labeled and must not be presented as validated production claims.

- 100 TOPS NPU is treated as near-term/conditional, not guaranteed sustained performance.
- 6000mAh battery is plausible, but runtime under AI load is limited.
- 8.8mm chassis is a packaging risk because battery, PCB, display, cameras, speakers, antennas, shielding, thermal spreaders, structural margins, and adhesive stackups compete for the same volume.
- 250g target is a mass-budget risk because battery, thermal module, chassis stiffness, display module, and camera systems leave limited margin.
- Passive/hybrid cooling is the central feasibility constraint for sustained local AI workloads.

## Conceptual extrapolations

Conceptual extrapolations are physically motivated directions that are not yet validated in the required Slate pocket v1 form factor.

- 512GB LPDDR6X is treated as conceptual extrapolation until package availability, board layout, power, cost, thermals, and supply-chain evidence are validated.
- Sustained high-throughput local AI in a pocket chassis is conceptual until memory bandwidth, NPU efficiency, workload duty cycle, and skin-temperature measurements are proven.

## Research blockers

The repo must not claim the device is production-buildable without CAD, BOM, thermal, and component validation. Required blockers include:

- CAD packaging study for display stack, battery, PCB, cameras, speakers, antennas, buttons, seals, fasteners, and service constraints.
- Component BOM with available parts, dimensions, masses, power envelopes, thermal limits, vendor status, and lifecycle risk.
- Thermal simulation and measurement plan for sustained workloads, ambient variation, user contact, orientation, charging, and degraded conditions.
- Battery safety validation for swelling, puncture, charge/discharge limits, cycle aging, and enclosure tolerance.
- Memory and compute validation for package availability, power draw, bandwidth, sustained throughput, firmware support, and software runtime behavior.

## Review standard

Every claim should be classed as measured fact, industry reference, modeled estimate, conceptual extrapolation, or unresolved research blocker. If math contradicts a target, preserve the contradiction and flag it rather than smoothing it away.
