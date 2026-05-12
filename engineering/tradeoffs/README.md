# Engineering Tradeoff Mapping

`engineering/tradeoffs/` contains first-pass tools for mapping how two engineering parameters interact under an explicit constraint. These tools vary two profile values in memory, evaluate the selected constraint at every grid point, and print readable pressure-region maps.

Tradeoff maps are screening tools, not optimizers. They do not rank designs, auto-solve dimensions, or modify source YAML profiles.

## Tools

- `tradeoff_map.py` generates one two-variable map from CLI ranges.
- `tradeoff_matrix.py` generates a default set of useful interaction maps.
- `tradeoff_summary.py` generates qualitative summaries from the default maps.

Generated reports are written under `reports/tradeoffs/`.

## Example

```bash
python engineering/tradeoffs/tradeoff_map.py \
  --profile configs/devices/slate-pocket-v1.yaml \
  --x geometry.thickness_mm 8 14 0.5 \
  --y compute.sustained_power_w 4 40 2 \
  --constraint thermal_risk_not_extreme
```

## Supported parameter paths

- `geometry.thickness_mm`
- `battery.capacity_mah`
- `compute.sustained_power_w`
- `compute.peak_power_w`
- `memory.capacity_gb`
- `storage.capacity_tb`
- `thermal.ambient_c`
- `runtime.context_tokens`
- `mass_targets.engineering_estimate_g` for the default battery-capacity-vs-mass screening map

## Supported constraints

The tradeoff mapper reuses the existing feasibility-boundary constraint checks:

- `zone_stackup_pass`
- `thermal_risk_not_extreme`
- `skin_temp_pass`
- `runtime_minimum`
- `mass_within_engineering_range`
- `memory_runtime_pass`

## Pressure classifications

Each grid point is classified as a transparent screening label:

- `PASS`: selected constraint passes with no active warnings or comfortable margin.
- `MODERATE`: selected constraint passes but warnings are active or margin is modest.
- `HIGH`: selected constraint passes with low margin, severe warnings, or multiple warnings.
- `EXTREME`: selected constraint passes but is near a modeled threshold.
- `FAIL`: selected explicit constraint fails.

These labels are not exact engineering standards. They are intentionally readable pressure regions for review and follow-up analysis.

## Default matrix

Run all default maps with:

```bash
python engineering/tradeoffs/tradeoff_matrix.py
```

Default maps cover:

1. thickness vs sustained power under `thermal_risk_not_extreme`;
2. battery capacity vs mass estimate under `mass_within_engineering_range`;
3. memory capacity vs thickness under `zone_stackup_pass`;
4. ambient temperature vs sustained power under `skin_temp_pass`;
5. memory capacity vs context length under `memory_runtime_pass`.

## Summary

Run qualitative summaries with:

```bash
python engineering/tradeoffs/tradeoff_summary.py
```

The summary report highlights model-dependent interaction effects and repeats the first-pass limitations: `PASS` does not mean manufacturable, and `FAIL` does not mean impossible forever.
