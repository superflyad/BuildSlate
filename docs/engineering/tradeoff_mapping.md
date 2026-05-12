# Tradeoff Mapping

BuildSlate tradeoff mapping shows how engineering pressure changes when two profile parameters vary together. The goal is interaction analysis, not optimization or automatic design solving.

## Why interaction effects matter

Single-parameter sweeps are useful, but hardware constraints often interact. A chassis that looks acceptable at one sustained power level may move into a higher thermal-pressure region when thickness falls. A memory capacity that helps runtime may increase package count and stackup pressure. A hot ambient environment can consume skin-temperature margin before compute load is increased.

Tradeoff maps make these coupled effects visible by varying parameter A and parameter B together, evaluating an explicit constraint at every grid point, and labeling the resulting engineering-pressure region.

## Nonlinear and model-dependent behavior

Engineering constraints can interact nonlinearly because geometry, thermal density, battery mass, memory package count, runtime demand, and ambient conditions are not independent. The current maps use simple first-pass formulas from the BuildSlate screening models. They are useful for review, but the pressure regions are model-dependent and should be revisited whenever equations, constants, assumptions, or source data change.

## What maps show

A tradeoff map shows regions:

- `PASS`
- `MODERATE`
- `HIGH`
- `EXTREME`
- `FAIL`

These are screening classifications. They are not exact engineering standards, certifications, or manufacturing sign-offs. The point is to identify where engineering pressure begins to rise and where follow-up analysis should focus.

## What maps do not do

Tradeoff maps do not optimize designs, choose final dimensions, rank architectures, or automatically repair failing points. They mutate profile values only in memory and leave source YAML profiles unchanged.

## Interpreting PASS and FAIL

`PASS` does not mean manufacturable. It only means the selected model and explicit constraint did not produce enough pressure to leave the pass region for that grid point. A passing point can still fail CAD, supplier packaging, thermal simulation, reliability, safety, cost, tolerance, or assembly review.

`FAIL` does not mean impossible forever. It means the current screening model violates the selected explicit constraint for that grid point. A different architecture, material, thermal path, supplier package, control policy, or validated assumption could move the boundary.

## Using the tools

Generate one map:

```bash
python engineering/tradeoffs/tradeoff_map.py \
  --profile configs/devices/slate-pocket-v1.yaml \
  --x geometry.thickness_mm 8 14 0.5 \
  --y compute.sustained_power_w 4 40 2 \
  --constraint thermal_risk_not_extreme
```

Generate the default matrix:

```bash
python engineering/tradeoffs/tradeoff_matrix.py
```

Generate qualitative summaries:

```bash
python engineering/tradeoffs/tradeoff_summary.py
```

Reports are written under `reports/tradeoffs/`.
