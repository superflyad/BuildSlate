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

The campaign gate credits required passes only within one campaign, serialized unit, build, and configuration. The required `I20` integrated-interface run needs positive deltas in raw CSV columns `display_frames`, `touch_events`, `camera_frames`, `audio_playback_samples`, `audio_capture_samples`, `usb_bytes_tx`, and `usb_bytes_rx`. Capture logs and physical observations alongside these counters for engineering review; generated counters alone cannot establish correct user-visible behavior.

Every required test has an `objective_measurements` contract in `test-matrix.yaml`. A passing run needs one hash-verified CSV containing its complete column set, strictly increasing elapsed time, a duration consistent with the result manifest, named reviewers, and the specified activity, limits, or analysis files. The B50 contract enforces the 30 W EVT input cap. M20 checks installed and OS-usable memory, requires at least 96 GiB of resident allocation with full-byte pattern verification and a timed full-allocation stream copy, and binds the raw CSV to `analysis/memory-probe.json` from the [guarded probe](../../buildslate/memory_probe.py). The copy rate is not an isolated DRAM bandwidth or stability certification. These are minimum evidence checks. Supplier-approved electrical and thermal limits, device behavior, and test authenticity still require engineering review and physical observation.

The B00 incoming inspection checks measured mass and external length, width, and thickness against the active [v1R profile](../../configs/devices/slate-pocket-v1r.yaml). Its current upper bounds are 350 g and 180 × 95 × 9.5 mm. The campaign reader refuses a test matrix whose B00 bounds differ from that profile. The 10.2 mm fallback cannot be credited by changing a test result; it requires an approved profile change and matching test contract before a run is accepted.
