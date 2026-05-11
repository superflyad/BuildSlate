# Scenario Sweeps and Sensitivity Analysis

Scenario sweeps help BuildSlate reviewers understand how engineering pressure changes when one profile parameter changes at a time. They are useful after profile comparison because they isolate a single variable instead of comparing whole profile variants that may differ in many places.

## Why Sweeps Matter

A device profile can be feasible or risky for many coupled reasons: thickness, thermal load, battery energy, memory package count, runtime reserve, ambient temperature, and packaging assumptions. A one-parameter sweep gives a controlled view of direction and magnitude:

- Does extra thickness mostly improve stackup margin or thermal density?
- Does lower sustained power materially improve runtime and thermal risk?
- Does increasing RAM create package-count and board-area pressure?
- Does a larger battery improve runtime enough to justify mass and volume pressure?
- Does high ambient temperature erase skin-temperature margin?

These answers are screening signals for engineering discussion. They are not validated product predictions.

## Sweeps vs. Profile Comparison

Profile comparison reviews complete device profiles side by side. That is useful when comparing aggressive, canonical, and conservative concepts, but it can be hard to attribute a result to a single input.

Scenario sweeps keep the base profile fixed, mutate one dot-path parameter in memory, and recompute lightweight checks for each requested value. This makes sensitivity clearer while avoiding automatic solving or optimization.

## Examples

### Thickness Sweep

```bash
python engineering/sweeps/sweep_runner.py \
  --profile configs/devices/slate-pocket-v1.yaml \
  --parameter geometry.thickness_mm \
  --values 8.8 9.5 10.5 12.0
```

A thickness sweep reports first-pass stackup margin, volume change, thermal density/risk, and runtime context. This helps show whether a thicker enclosure relieves local z-height pressure.

### Sustained Power Sweep

```bash
python engineering/sweeps/sweep_runner.py \
  --profile configs/devices/slate-pocket-v1.yaml \
  --parameter compute.sustained_power_w \
  --values 8 12 18 28
```

A sustained-power sweep reports battery runtime, thermal risk, heat density, and charging-overlap risk. This is useful for observing the cost of laptop-class AI power in a pocket-sized chassis.

### Memory Sweep

```bash
python engineering/sweeps/sweep_runner.py \
  --profile configs/devices/slate-pocket-v1.yaml \
  --parameter memory.capacity_gb \
  --values 128 256 512
```

A memory sweep reports package count, package area pressure, active memory power, and runtime memory budget. This separates installed-memory capacity pressure from other profile differences.

### Battery Sweep

```bash
python engineering/sweeps/sweep_runner.py \
  --profile configs/devices/slate-pocket-v1.yaml \
  --parameter battery.capacity_mah \
  --values 5000 6000 7000
```

A battery sweep reports Wh, estimated battery mass, estimated battery volume, and runtime. This highlights the tradeoff between additional energy and physical packaging pressure.

### Ambient Temperature Sweep

```bash
python engineering/sweeps/sweep_runner.py \
  --profile configs/devices/slate-pocket-v1.yaml \
  --parameter thermal.ambient_c \
  --values 25 35 40
```

An ambient sweep reports estimated skin temperature, skin-temperature margin, and throttle-policy pressure. This is a first-pass way to see how hot-environment operation reduces thermal headroom.

## Summary Tool

```bash
python engineering/sweeps/sensitivity_summary.py
```

The summary tool runs the default useful sweep set and reports which parameters most affect mapped thermal risk, runtime, and stackup in that set. It does not choose a target or claim an optimum.

## Limitations

- Sweeps mutate one parameter at a time and do not capture full coupled design changes.
- Results use first-pass formulas and placeholder assumptions rather than CAD, CFD, supplier data, or prototypes.
- Warning labels are engineering information, not certification findings.
- Unmapped parameters are still validated but marked `not_mapped` until a model relationship is added.
- Source YAML profiles are never modified by sweep execution.
