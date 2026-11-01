# Slate Pocket v1R RF, EMC, and Wireless-Power Validation Plan

Status: planned pre-module/pre-antenna; exact bands, standards editions, and limits remain unset.

## Release prerequisites

- Approved SKU and market matrix, including whether cellular and UWB ship.
- Selected radio modules/chipsets, reference designs, antennas, cables/connectors, and certified-module grant conditions.
- Released mechanical/ECAD geometry with chassis materials, coatings, display, battery, thermal spreaders, speakers, cameras, ports, seals, and accessories.
- Regulatory lab scoping for FCC, EU RED, other target markets, SAR/RF exposure, EMC, PTCRB/operator work if cellular, and WPC work if wireless charging returns.

## Simulation plan

1. Build the full-device EM model with housing, frame breaks, ground, display, battery, board copper, shields, thermal materials, cables, and user/accessory phantoms.
2. Sweep each antenna candidate across its selected operating bands and record efficiency, total radiated power/sensitivity proxies, impedance, coupling, current distribution, and sensitivity to tolerances.
3. Evaluate MIMO correlation/isolation and simultaneous-radio cases after antenna count and band scope are known.
4. Model detuning from hands, body, table, case, USB cable, display states, and production material variation.
5. Add wireless-power coil/ferrite/shield and misalignment only if its mechanical gate reopens; simulate magnetic leakage, eddy-current heating, and radio desense.

No numeric RF pass limits are set before the selected radio/antenna supplier requirements and lab plan exist.

## Chamber and bench sequence

- Conducted bring-up: output power, sensitivity, error rate, spectrum, harmonics/spurious, receiver blocking, and coexistence controls.
- Antenna prototypes: impedance/current scans, tuning-range study, cable/fixture de-embedding, and material/tolerance variants.
- OTA: radiated performance by orientation, MIMO behavior, hand/body/accessory effects, and unit-to-unit variation.
- Coexistence: simultaneous Wi-Fi/Bluetooth/UWB/cellular combinations, display/memory/storage traffic, USB, charging, and compute workloads.
- EMC pre-compliance: radiated/conducted emissions and immunity, ESD, EFT/surge where applicable, charger/cable/accessory variants, and clock/power-state sweeps.
- RF exposure/SAR: accredited-lab evaluation for the final configuration and supported use positions; do not rely solely on module approval.
- Cellular, if retained: PTCRB and target-operator scope followed by field/network testing.

## Wireless-power branch

Wireless charging is not an EVT0 test item. Re-entry requires a selected WPC profile/receiver, mechanically passing coil stack, safe charge curve, foreign-object and alignment controls, thermal loss map, and an authorized-lab plan. Then test efficiency, control communication, authentication if applicable, interoperability, misalignment, foreign objects, emissions, immunity, radio desense, and skin/battery temperatures.

## Configuration and failure control

Every result records hardware/antenna/firmware revision, calibration, chamber/fixture, module settings, region, channel/band, power state, thermal state, battery/charger state, accessory, orientation, and raw data. Failures create tracked changes to geometry, tuning, shielding, clocks, firmware, or requirements; they cannot be closed by changing an undocumented test condition.

## Exit criteria

- All shipping radio functions and market variants have reviewed requirements and traceable results.
- Production-intent geometry meets supplier, system, coexistence, EMC, and accredited-lab gates with margin across declared use cases and tolerances.
- Radio-kill and security behavior is verified across boot, fault, update, and suspend/resume states.
- Wireless-power certification exists before any Qi/Qi2 claim or logo use, if the feature returns.
- RF, regulatory, electrical, mechanical, thermal, firmware, security, manufacturing, and quality owners sign the release package.

This plan does not claim an antenna design, passing simulation, chamber result, certification, or regulatory approval.
