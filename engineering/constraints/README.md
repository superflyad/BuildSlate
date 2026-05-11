# Constraint Boundary Analysis

Constraint boundary tools sweep one numeric device-profile parameter over an explicit range, evaluate one pass/fail constraint at each scan point, and report where the scan first crosses into feasibility.

These tools are screening utilities, not optimizers:

- They do **not** redesign Slate automatically.
- They do **not** choose a best architecture.
- They do **not** modify source YAML profiles.
- They do **not** certify production feasibility.
- They classify explicit model-dependent constraints as a screening result, not production validation.

## Tools

### `feasibility_boundary.py`

Run one boundary scan:

```bash
python engineering/constraints/feasibility_boundary.py \
  --profile configs/devices/slate-pocket-v1.yaml \
  --vary geometry.thickness_mm \
  --min 8.0 \
  --max 14.0 \
  --step 0.25 \
  --constraint zone_stackup_pass
```

Required arguments:

- `--profile`: device profile YAML path.
- `--vary`: dot-path parameter to mutate in memory.
- `--min`: minimum numeric scan value.
- `--max`: maximum numeric scan value.
- `--step`: positive numeric scan step.
- `--constraint`: explicit pass/fail constraint.

Optional argument:

- `--target-runtime-h`: runtime target for `runtime_minimum`; default is `1.0` hour.

Supported constraints:

- `zone_stackup_pass`: passes when worst zone margin is at least `0` mm.
- `thermal_risk_not_extreme`: passes when thermal risk is not `EXTREME`.
- `skin_temp_pass`: passes when estimated skin temperature is less than or equal to max skin temperature.
- `runtime_minimum`: passes when estimated runtime is at least `--target-runtime-h`.
- `mass_within_engineering_range`: passes when estimated mass is within `mass_targets.acceptable_range_g.max` when available.
- `memory_runtime_pass`: passes when runtime memory budget is less than or equal to available memory.

The report includes the parameter varied, tested range, constraint evaluated, first passing value, last failing value before pass, best passing value in scan order, fail/pass sequence, evaluated rows, and warnings.

### `constraint_runner.py`

Run the default Slate Pocket v1 boundary set and write `reports/constraints/boundary-report.txt`:

```bash
python engineering/constraints/constraint_runner.py
```

Default checks cover minimum thickness, maximum sustained power before extreme thermal risk, maximum ambient temperature before skin-temperature failure, minimum battery capacity for one hour runtime, and memory capacity runtime budget.

### `constraint_summary.py`

Summarize the default boundary findings in plain language and write `reports/constraints/constraint-summary.txt`:

```bash
python engineering/constraints/constraint_summary.py
```

The summary is intended for review conversations. It repeats that results are screening results, not production validation, and lists model limitations.
