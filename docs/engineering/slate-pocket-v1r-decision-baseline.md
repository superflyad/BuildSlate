# Slate Pocket v1R Decision Baseline

Status: **Approved and locked for Phase 1**  
Approved: **2026-10-31**  
Decision owner: **BuildSlate product owner**  
Baseline profile: `configs/devices/slate-pocket-v1r.yaml`  
Evidence package: `requirements_baseline`

## Decision purpose

This document separates the product outcome from the current numerical implementation targets. It prevents component research, CAD, and simulation from silently treating every source-intent number as equally mandatory.

This baseline approves the requirement classes and fallback rules used to begin Phase 1 supplier evidence work. It does not claim that the targets are feasible; unsupported targets must move to their approved fallback rather than remaining hidden assumptions.

## Product outcomes to preserve

These are proposed as the stable intent of Slate Pocket:

- A pocket-class, AI-native workstation rather than a conventional phone profile.
- A roughly 7.5-inch, 16:10 primary display suitable for local creation and analysis workflows.
- Useful local inference with offline operation, encrypted model/data storage, and verifiable radio isolation.
- Sustained workloads governed by explicit power and temperature policies rather than peak-only marketing claims.
- A design that can be assembled, serviced, and validated without hiding conflicts in generic volume factors.

## Proposed requirement classes

| Requirement | Current v1R value | Proposed class | Evidence needed to retain it | Proposed fallback or trade rule | Decision state |
| --- | ---: | --- | --- | --- | --- |
| Device identity | Pocket AI workstation | Must-have outcome | Integrated workflow and ergonomic review | Re-scope workload set before changing device class | Locked |
| Display format | 7.5 in, 16:10 | Must-have outcome | Panel outline, flex, power, availability, and enclosure fit | Permit small diagonal/refresh/resolution changes that preserve the workspace intent | Locked |
| Offline/security posture | Local inference, encrypted storage, radio isolation | Must-have outcome | Hardware root of trust, firmware controls, threat model, and verification plan | Reduce performance or radios before weakening the security posture | Locked |
| Thickness | 9.5 mm | Target | Supplier-backed stackup, local-zone CAD, tolerances, sealing, and ergonomics | Evaluate 10.2 mm first; reduce features only after coupled CAD review | Locked |
| Battery capacity | 6000 mAh at 3.85 V | Target | Complete pack CAD, supplier energy/capacity data, swelling, charge/discharge, and cycle-life evidence | Use candidate-backed capacity; the current same-density recovery estimate is about 4236 mAh | Locked |
| Memory | 512 GB | Aspirational target | Supported SoC topology, package count/height, bandwidth, power, thermal, sourcing, and software need | Compare 256 GB and 128 GB against explicit model/workload tiers | Locked |
| Storage | 4 TB | Target | Package drawing, interface support, power, sustained-write thermal data, sourcing, and workload need | Use 2 TB baseline with modular/external storage strategy if integration evidence fails | Locked |
| NPU capability | 100 TOPS | Aspirational target | Supported precision, compiler/runtime coverage, benchmark disclosure, sustained telemetry, and efficiency | Select for measured workload performance per watt; do not require sustained headline TOPS | Locked |
| Compute power | 28 W sustained / 45 W peak | Constraint to validate | Workload definition, SoC telemetry, power tree, thermal model, and throttle policy | Set the power envelope from measured skin-temperature and runtime limits | Locked |
| Skin temperature | 43 °C maximum target | Safety/comfort boundary | Requirement mapping, sensor map, ambient/use cases, and prototype chamber data | Throttle workload; do not relax the boundary without safety and human-factors review | Locked |
| Mass | 250 g aspirational; 290–350 g accepted engineering range | Target | Supplier-backed mass rollup and prototype weigh-in | Use the current 290–350 g range until a mass budget proves a lower target | Locked |
| Wired charging | 100 W | Target | Cell/charger limits, charge curve, cable/connector, thermal map, and cycle-life impact | Reduce charge power to the highest validated level that meets the charging-time requirement | Locked |
| Wireless charging | 50 W | Negotiable feature | Coil/ferrite/shield stack, efficiency, alignment, RF coexistence, heat, and certification | Reduce power or remove wireless charging if it blocks thickness, RF, or thermal gates | Locked |
| Camera architecture | 48 MP lateral rear; under-display front | Negotiable feature set | Module drawings, image-quality goal, optical keepout, flex, ISP support, and thermal placement | Simplify module count/optics before compromising core compute, battery safety, or RF space | Locked |
| Ingress protection | IP68 intent | Target | Seal architecture, openings, assembly process, and validation plan | Select the highest testable rating consistent with serviceability and thermal design | Locked |

## Locked Phase 0 decisions

The product owner approved the following rules:

1. The proposed product outcomes define Slate Pocket's stable identity.
2. The working envelope is 9.5 mm, with 10.2 mm as the first thickness fallback.
3. The 512 GB memory target is aspirational; 256 GB and 128 GB are approved evidence-driven tiers.
4. The 6000 mAh battery target may fall to the best supplier-validated capacity that fits the complete pack envelope; 4236 mAh is the current same-density reference point, not a selected capacity.
5. The 4 TB internal-storage target may fall to 2 TB with a modular or external storage strategy.
6. Measured workload performance per watt governs platform selection; sustained headline TOPS is not required.
7. Wireless charging, charging power, camera complexity, ingress rating, and material choices may be traded to preserve the core product outcomes and safety boundaries.

## Change-control rule

Once approved, any change to this baseline must record:

- the changed requirement and reason;
- the approving decision owner;
- affected specs, profiles, assumptions, risks, models, and evidence packages;
- new acceptance criteria and validation method;
- whether existing reports must be regenerated.

## Phase 0 verification checklist

- [x] Requirement classes are approved.
- [x] Every retained target has an approved fallback.
- [x] Every target has a named decision owner.
- [x] Every target has a verification method.
- [x] The 9.5 mm v1R envelope is accepted.
- [x] Approved decisions are reflected in the v1R profile and evidence registry.

Phase 0 is verified. Phase 1 supplier evidence work is now unblocked; the broader program remains `BLOCKED_ON_FOUNDATIONAL_EVIDENCE` until the critical Phase 1 and Phase 2 packages are verified.
