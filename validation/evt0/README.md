# Slate Pocket v1R EVT0 Integration Mule

Status: `planned_not_authorized`. This package prepares a controlled engineering build and test program; it does not authorize purchasing, assembly, energized testing, supplier disclosure, or physical work.

EVT0 is an integration mule intended to reproduce the v1R external envelope, major component topology, heat-source locations, power paths, and radio reservations closely enough to correlate the engineering models. It is not a cosmetic, ingress-rated, certified, reliability-qualified, or production-representative unit.

The package contains:

- `evt0-spec.yaml` — authoritative configuration, prerequisites, variants, and gate rules;
- `bom-strategy.yaml` — selection/qualification evidence required for every build role;
- `instrumentation.yaml` — synchronized electrical, thermal, performance, and configuration channels;
- `workloads.yaml` — version-locked workload definitions and invalidation rules;
- `test-matrix.yaml` — sequenced build, functional, power, thermal, runtime, and fault tests;
- `build-traveler.md` — controlled assembly and inspection record;
- `schemas/` — machine-readable run manifest and result validation schemas;
- `test-results/README.md` — rules for storing real raw and derived evidence;
- `model-correlation.md` — model-to-measurement workflow and thresholds.

No test result exists until a schema-valid result package references raw data, unit/build identity, calibration, workload hashes, and reviewer disposition. Empty folders, templates, and generated readiness reports are not measurements.
