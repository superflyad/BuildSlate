# Slate Pocket Execution Roadmap

## Objective

Move Slate Pocket v1R from a screening recovery profile to an evidence-backed prototype decision without allowing generated reports to imply more maturity than the underlying evidence supports.

The current baseline is `slate-pocket-v1r`: 9.5 mm thick, 6000 mAh, 512 GB memory, 4 TB storage, 28 W sustained compute, and 45 W peak compute. The profile has a conditional physical pass, but every headline target remains subject to supplier, CAD, electrical, thermal, RF, manufacturing, and prototype evidence.

## Operating rules

1. Treat v1R as the working hypothesis, not a frozen product claim.
2. Preserve explicit fallback targets for every high-pressure requirement.
3. Do not mark evidence verified merely because a document exists; review it against the package acceptance criteria.
4. Make target changes in the specs, assumptions, risks, and evidence registry together.
5. Prefer early disproof of a fragile requirement over late optimization around an impossible package.

## Phase 0 — Freeze the decision frame

Goal: create a stable decision baseline before paying for detailed research or CAD.

Actions:

- Classify battery capacity, memory, storage, compute, charging, thickness, mass, and skin temperature as must-have, target, or negotiable.
- Define one approved fallback for every retained headline target.
- Assign a decision owner and verification method to each target.
- Confirm v1R as the working baseline or publish a replacement profile.

Exit gate: `requirements_baseline` is verified.

## Phase 1 — Replace placeholders with supplier-backed candidates

Goal: determine whether the critical component set exists in a mutually compatible form.

Parallel workstreams:

- Battery cell and complete pack envelope.
- SoC/NPU, memory topology, measured or supported sustained performance, and software access.
- Display module and storage package.

Exit gate: critical component packages have reviewed mechanical, electrical, power, thermal, availability, and lifecycle evidence. Unsupported requirements are traded before CAD begins.

## Phase 2 — Prove integration on paper

Goal: replace bounding boxes and generic factors with coupled mechanical, electrical, thermal, and RF designs.

Workstreams:

- Mechanical CAD and zone-by-zone tolerance stack.
- PCB placement, routing escape, stackup, power tree, and PDN plan.
- Geometry-specific thermal model and prototype correlation plan.
- RF, antenna, chassis-material, and wireless-charging architecture.

Exit gate: all foundational critical evidence packages in phases 0-2 are verified. The evidence engine then returns `READY_FOR_PROTOTYPE_GATE`.

## Phase 3 — Build EVT-0 and measure reality

Goal: correlate the digital twin with an integration mule.

Measure:

- Sustained and peak workload power, clocks, performance, and throttling.
- Runtime memory allocation and bandwidth pressure.
- Battery runtime, discharge rate, charging overlap, and rail transients.
- Internal and exterior temperature maps across ambient and handling cases.
- Model error against mechanical, power, and thermal predictions.

Exit gate: measured data is stored, model deltas are understood, and failed targets result in explicit trades.

## Phase 4 — DFM and pilot readiness

Goal: determine whether the verified prototype architecture can become a repeatable build.

Actions:

- Supplier DFM review, assembly flow, datum and tolerance ownership, adhesives, fixtures, and rework.
- Reliability and compliance-pretest plans.
- Pilot build sample plan, inspection points, defect taxonomy, and yield threshold.
- Serviceability and repair strategy.

Exit gate: all evidence packages are verified and the evidence engine returns `EVIDENCE_GATE_COMPLETE`.

## Immediate attack order

1. Complete and verify `requirements_baseline`.
2. Run battery, compute/memory, and display/storage research in parallel.
3. Trade unsupported headline targets immediately; do not hide them behind generic package assumptions.
4. Start mechanical CAD only after candidate package geometry is credible.
5. Develop PCB/power, thermal, and RF work as one coupled integration loop.
6. Build EVT-0 only after the phase 2 evidence gate opens.

The machine-readable source of truth for this roadmap is `engineering/evidence/evidence_registry.yaml`. Generate the current status with:

```bash
python engineering/evidence/generate_evidence_readiness_report.py
```
