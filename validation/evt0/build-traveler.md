# Slate Pocket v1R EVT0 Build Traveler

Status: template only; no build is authorized or recorded.

## Header

- Unit ID:
- Build ID / traveler revision:
- Date / location:
- Authorized build owner:
- Approved BOM revision:
- Board / enclosure / thermal stack / firmware revisions:
- Deviations approved before build:
- Safety review and emergency procedure references:

## Incoming inspection

Record supplier/part/lot/serial identity, documentation revision, quantity, visible condition, dimensions/mass where required, storage/handling state, and acceptance disposition for every controlled item. Quarantine mismatches; do not substitute them during assembly.

## Pre-assembly gates

- [ ] Purchase/build authorization recorded.
- [ ] Supplier limits and safety documents reviewed.
- [ ] Released drawings, schematic, BOM, and assembly instructions match the traveler.
- [ ] ESD, battery, electrical, thermal, chemical, and mechanical hazards reviewed.
- [ ] Fixtures, torque tools, metrology, instrumentation, and emergency controls in calibration/inspection.
- [ ] Battery remains isolated until the approved energization step.

## Assembly record

For each operation record operator, start/end time, work instruction, part/lot/serials consumed, material batch, equipment/fixture ID, measured value, acceptance range, pass/fail, rework, and witness where required.

Required controlled stages:

1. Enclosure/frame dimensional inspection and datum verification.
2. Board inspection, programming fixture check, and current-limited bench bring-up before enclosure assembly.
3. Thermal-interface material identity, bondline/application, contact feature, and sensor placement.
4. Battery protection/identity inspection and isolated mechanical fit check—no compression outside supplier limits.
5. Display, camera, speaker, radio, antenna, flex, connector, seal, fastener, and strain-relief installation as applicable.
6. Clearance/interference, connector retention, insulation, grounding/bonding, and foreign-material inspection.
7. Controlled first power with current limit, thermal observation, fault log, and emergency disconnect ready.
8. Firmware/configuration checksum, telemetry sanity, radio-kill check, and safe shutdown.

## Final build inspection

- External dimensions and mass:
- Critical internal clearances / evidence links:
- Thermal and electrical sensor locations / photo links:
- Fastener/adhesive/connector inspection:
- Battery condition and isolation/protection result:
- Configuration checksum:
- Open deviations / nonconformances:
- Disposition: `hold`, `rework`, `safe_for_limited_test`, or `scrap/quarantine`.

## Handoff

The build owner and test owner sign only after the exact allowed tests, power/charge limits, fixtures, hard stops, and emergency actions are attached. A traveler signature does not authorize tests outside that scope.
