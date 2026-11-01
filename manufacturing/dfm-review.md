# Slate Pocket v1R Supplier DFM Review Package

Status: prepared for review; no supplier DFM, tooling release, process qualification, or pilot authorization has occurred.

## Review basis

- Locked product/fallback baseline: `docs/engineering/slate-pocket-v1r-decision-baseline.md`
- Provisional mechanical model: `cad/slate-pocket-v1r/envelope-model/`
- Provisional ECAD/power package: `engineering/pcb/`
- Thermal and RF packages: `simulations/thermal/slate-pocket-v1r/` and `engineering/rf/`
- EVT0 build/test package: `validation/evt0/`

Every supplier must identify the document/revision reviewed, assumptions made, unresolved questions, required design changes, process capability evidence, tooling/fixture needs, lead times, and whether comments are public or NDA-controlled. A review response is advice, not automatic design approval.

## Known issues presented—not hidden

- The complete battery pack is unselected; the 6000 mAh target may fall to the best validated capacity fitting the envelope.
- The battery zone has only 0.46 mm nominal margin without wireless charging and lacks a tolerance stack.
- Wireless charging is removed from EVT0 because its planning overlay drives the local stack 0.34 mm over the 9.5 mm envelope.
- The provisional board has three-dimensional package, connector, shield, fastener, test, flex, and routing data missing.
- The 128 GB memory fallback is a four-site planning hypothesis, not a qualified topology; 512 GB is unsupported.
- One 1 TB embedded storage package is the planning baseline; 4 TB is unsupported.
- The planform model has unresolved speaker/RF and battery/board connector-zone conflicts.
- Material, adhesive, seal, fastener, thermal-interface, camera, antenna, acoustic, and surface-finish selections are open.

## Required supplier review

### Mechanical and enclosure

- Datum scheme, stack direction, locating strategy, tolerance ownership, inspection access, flatness/warpage, wall/rib/boss features, frame breaks, antenna windows, joints, cosmetic surfaces, and handling.
- Display/rear-cover bonding, adhesive land width, dispense/cure control, squeeze-out, rework, contamination, and shelf-life tracking.
- Fastener type, engagement, torque strategy, locking method, tool access, galvanic/grounding implications, and repair cycles.
- Battery cavity, puncture protection, swelling envelope, isolation, pull-tab/service path, and no-load transfer into display/rear cover.
- Flex bend radii, connector mate access, strain relief, camera alignment, acoustic seals/ports, environmental seals, and leak-test features.

### PCBA and electrical

- Fabricator-approved controlled-impedance stack, via structures, aspect ratios, annular rings, copper balance, warpage, panelization, coupons, surface finish, assembly clearances, shielding, rework, test access, and traceability.
- Component availability/MSL, paste aperture, placement/inspection limits, underfill/stiffener needs, thermal mass, voiding, BGA escape/yield, cleanability, and conformal/insulation requirements.
- Battery/charge protection, connector/cable current, isolation, grounding/bonding, ESD paths, programming, boundary scan where available, functional test, and safe firmware state.

### Thermal, RF, and final assembly

- TIM/graphite/vapor-chamber handling, bondline/contact-pressure control, compression stops, flatness, contamination, rework, and inspection.
- Antenna-window materials, conductive exclusions, ground/bond features, tuning access, unit variation, cases/cables, and line-test strategy.
- Assembly order, irreversible operations, cure queues, fixture interactions, sensor access, cleanliness, foreign-material control, and safe battery installation/energization.

## Provisional datum and tolerance ownership

- Datum A: internal midframe/display support plane controlling z-stack and flatness.
- Datum B: long-side internal locating edge controlling x placement.
- Datum C: short-side internal locating edge controlling y placement.

This scheme is a review proposal only. The enclosure supplier owns capability feedback; design engineering owns released dimensions/tolerances; manufacturing engineering owns process/fixture control; quality owns measurement-system approval and inspection plans. Supplier-requested changes require BuildSlate change control.

## Review exit

The package exits supplier DFM only when critical suppliers return dispositioned comments against released geometry/BOM/process assumptions, all critical-to-function characteristics have owners and measurable specifications, assembly/rework paths are demonstrated, and remaining risks are accepted or have funded closure plans.

This package does not prove manufacturability, supplier approval, process capability, tooling readiness, yield, reliability, serviceability, compliance, or production readiness.
