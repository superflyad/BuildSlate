# Slate Pocket v1R Manufacturing Quality Gate

Status: proposed, not approved. No supplier, EVT0, pilot, reliability, or compliance evidence exists.

## Gate sequence

### G0 — Design handoff ready

- Released requirements, CAD, drawings, BOM/AVL, schematic/layout, firmware/configuration, critical characteristics, and change control.
- Supplier packages and Phase 2/EVT0 evidence verified; unsupported targets are traded explicitly.
- Open risks, deviations, regulatory scope, safety ownership, and validation plan approved.

### G1 — Process and tooling ready

- Supplier DFM comments closed; process flow, PFMEA/control plan, work instructions, fixtures/gages, inspection, ESD, battery safety, materials, rework, and traceability approved.
- Measurement systems demonstrate acceptable resolution, repeatability/reproducibility, calibration, and data integrity for their intended decisions.
- Line dry run and safety/data interlocks pass without product units.

### G2 — Pilot execution acceptable

- All 100 proposed pilot inputs remain in the denominator with documented disposition.
- Zero critical safety/regulatory defects.
- FPY ≥90%, final yield ≥95%, rework ≤10%, unknown/no-trouble-found ≤2%.
- Required traceability and test-data completeness both 100%.
- Critical characteristics target Cpk ≥1.33 only where specification, stability, distribution, and measurement-system prerequisites are met.
- Failures have containment, root-cause status, corrective action, retest, and residual-risk disposition.

### G3 — Reliability and compliance-pretest acceptable

- Approved reliability matrix completed with traceable units and no unresolved safety-critical failure.
- Compliance pretests and accredited-lab plan cover every shipping configuration, market, accessory, and operating mode.
- Service operations are demonstrated repeatedly with restored safety/function and affected thermal/RF/seal controls.

### G4 — Production decision

- Supplier capacity, quality, lifecycle, change notification, cost, lead time, continuity, and field-support plans approved.
- Residual risks and deviations accepted by named owners.
- Required certifications/declarations/filings and production-release reviews complete.

## Decision states

- `BLOCKED`: required input/evidence missing.
- `FAIL`: valid evidence violates a gate.
- `CONDITIONAL`: bounded deviation has owner, containment, expiration, and closure plan.
- `PASS`: all criteria have traceable approved evidence.

No gate may pass on artifact existence, averages hiding critical defects, excluded failed units, unreviewed rework, missing raw data, or supplier verbal assurance. This document does not claim that any manufacturing gate currently passes.
