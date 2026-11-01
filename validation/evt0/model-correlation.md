# Slate Pocket v1R EVT0 Model Correlation

Status: workflow only; no measured EVT0 data or correlated model exists.

## Evidence chain

Each comparison must trace from a schema-valid run manifest and raw data through a pinned analysis artifact to a named model input/output revision. The comparison records units, coordinate/sensor mapping, time window, filtering, uncertainty, residual, disposition, and any calibration change.

## Correlation domains

- Mechanical: external dimensions, mass, critical clearances, component/source locations, thermal-interface bondlines, and interference findings.
- Electrical: idle/sustained/peak load, conversion efficiency, battery current, rail DC drop, transient droop/recovery, protection behavior, and charger losses.
- Thermal: sensor-by-sensor steady state, hotspot location, transient time constants, time to 40 °C skin caution, throttle onset, and energy balance.
- Runtime: installed/usable/peak memory, workload throughput/latency, energy per work unit, storage behavior, clocks, throttle time, and errors.
- RF development: modular-radio conducted/OTA observations and coexistence deltas; never relabel these as certification results.

## Initial correlation gates

These are model-quality gates, not safety or product-performance limits:

- exterior steady-state temperature residual: within ±2 °C at every mapped sensor;
- controlled internal temperature residual: within ±3 °C;
- time to cross 40 °C skin caution: within ±15%;
- electrical steady-state power/current residual: within ±5% after instrument uncertainty is included;
- rail transient peak/time residual: threshold set from selected regulator/load-step requirements before test;
- dimensions and mass: within released drawing/tolerance and metrology uncertainty;
- runtime arithmetic: measured configuration and allocation must reconcile with logged capacity and workload inputs;
- validation cases remain separate from calibration cases.

Average agreement cannot mask a failing hotspot, unsafe transient, missing channel, or wrong source location.

## Workflow

1. Freeze model, build, instrumentation, firmware, and workload revisions before opening the campaign.
2. Validate manifests, calibrations, raw-data hashes, time synchronization, and hard-stop/event logs.
3. Compare without tuning and publish residuals for every required channel.
4. Classify mismatches as geometry, property, boundary, source/load, control, instrumentation, or implementation uncertainty.
5. Tune only traceable uncertain inputs within approved ranges using designated calibration cases.
6. Rerun independent validation cases without retuning.
7. Record model change, reason, prior/new value, evidence, sensitivity, reviewer, and affected predictions.
8. Convert target failures into a baseline change request or retained blocker—never an undocumented model adjustment.

## Gate result states

- `BLOCKED`: prerequisite result or evidence quality is missing.
- `FAIL`: valid evidence violates a safety, design, or correlation gate.
- `CONDITIONAL`: correlation passes only in a bounded configuration/use case recorded in the requirement set.
- `PASS`: all required cases and domain gates pass with reviewed evidence.

This document does not claim that an EVT0 unit exists, models are correlated, targets pass, or the design is ready for manufacture.
