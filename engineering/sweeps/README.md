# Scenario Sweeps

Scenario sweeps vary one device-profile parameter at a time and run lightweight engineering checks against each mutated in-memory profile.

These tools are sensitivity-analysis utilities, not optimizers:

- They do **not** solve constraints automatically.
- They do **not** choose a best design.
- They do **not** modify the source YAML profile.
- They provide conservative first-pass screening information for engineering review.

## Tools

### `sweep_runner.py`

Run a one-parameter sweep and write a readable report to `reports/sweeps/sweep-report.txt` by default.

```bash
python engineering/sweeps/sweep_runner.py \
  --profile configs/devices/slate-pocket-v1.yaml \
  --parameter geometry.thickness_mm \
  --values 8.8 9.5 10.5 12.0
```

Optional output path:

```bash
python engineering/sweeps/sweep_runner.py \
  --profile configs/devices/slate-pocket-v1.yaml \
  --parameter compute.sustained_power_w \
  --values 8 12 18 28 \
  --output reports/sweeps/power-sweep.txt
```

Supported dot-path examples include:

- `geometry.thickness_mm`
- `geometry.length_mm`
- `geometry.width_mm`
- `battery.capacity_mah`
- `compute.sustained_power_w`
- `compute.peak_power_w`
- `memory.capacity_gb`
- `memory.gb_per_package`
- `storage.capacity_tb`
- `thermal.sustained_w`
- `thermal.ambient_c`
- `runtime.model_params_billions`
- `runtime.context_tokens`
- `environment.condition`
- `environment.brightness_mode`

Mapped sweep groups compute first-pass outputs for thickness/volume/stackup, sustained power, memory packaging and runtime budget, battery energy/volume/mass/runtime, and ambient skin-temperature margin. Unmapped parameters still receive basic profile validation and are labeled `not_mapped`.

## Warning Labels

Each row includes compact warning labels such as:

- `stackup_fail`
- `high_thermal_risk`
- `runtime_low`
- `memory_pressure`
- `mass_pressure`
- `throttle_pressure`
- `not_mapped`

Warnings are engineering information for follow-up review. They are not automatic blockers, optimization targets, or certification results.

### `sensitivity_summary.py`

Generate a conservative summary from default useful sweeps:

```bash
python engineering/sweeps/sensitivity_summary.py
```

The summary reports which parameters most affect thermal risk, runtime, and stackup within the default first-pass sweep set. It intentionally avoids optimization claims.
