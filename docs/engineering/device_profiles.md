# Configurable Device Profiles

BuildSlate device profiles are structured YAML inputs for evaluating different Slate hardware assumptions with the same math-backed model system.

Profiles are not optimized answers. They are scenario definitions: geometry, mass targets, battery, display, compute, memory, storage, thermal, materials, runtime, manufacturing, and environmental assumptions are written down explicitly so the existing engineering scripts can screen them consistently.

## Why profiles exist

A profile lets BuildSlate run the same model chain against different hardware assumptions without rewriting scripts or hiding tradeoffs. The core flow is:

```text
device profile YAML → engineering model inputs → feasibility report
```

This makes comparisons repeatable. For example, a canonical concept profile, an aggressive ambition profile, and a conservative screening profile can all be evaluated through the same validation and model commands.

## Profile interpretation

- Profiles are structured inputs, not claims that a device is buildable.
- Aggressive profiles are allowed when clearly labeled as aggressive or conceptual.
- Conservative profiles are allowed for grounded comparison, but they are not automatically final or feasible.
- Warnings are expected because the models are designed to expose mass, thermal, packaging, interconnect, runtime, and environmental pressure.
- Reported warnings and blockers are engineering information, not software defects.
- Profile reports do not prove manufacturability, safety, certification, supplier availability, or production yield.

## Running profiles

Validate all configured device profiles:

```bash
python validation/validate_device_profiles.py
```

Generate a report for the canonical Slate Pocket v1 profile:

```bash
python engineering/run_device_profile.py --profile configs/devices/slate-pocket-v1.yaml
```

The runner loads the YAML profile, validates required top-level sections, maps profile values to supported model CLI arguments, captures model output, scans warning/blocker lines, and writes a profile-specific report under `reports/`.
