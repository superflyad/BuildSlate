# BuildSlate

BuildSlate is a hardware digital-twin repository for a tablet-class Slate v1 concept. The repository is organized around machine-readable specifications, CAD blocking models, bill-of-materials data, simulation scripts, and validation checks.

## Repository areas

- `specs/` — source-of-truth device specifications. `specs/slate-v1.yaml` is JSON-compatible YAML so it can be parsed without non-standard Python dependencies.
- `specs/components/` — component-level specification files and interface notes.
- `cad/slate-v1/` — mechanical CAD workspace for Slate v1 enclosure, thermal stack, and PCB placeholder models.
- `bom/` — structured bill-of-materials files with component categories, quantities, placeholder parts, and engineering notes.
- `simulations/thermal/` — thermal models, assumptions, and future solver inputs.
- `simulations/power/` — battery and workload runtime estimates.
- `simulations/model-fit/` — memory-fit estimates for local model parameter counts and quantization levels.
- `diagrams/` — system diagrams, mechanical stack diagrams, and architecture sketches.
- `validation/` — scripts that verify specs and other digital-twin inputs are complete enough for downstream tooling.
- `docs/` — design notes, decisions, and methodology documentation.
- `scripts/` — repository automation and utility scripts.

## Current checks

Run the baseline validation and simulation scripts from the repository root:

```bash
python validation/validate_specs.py
python simulations/model-fit/model_fit.py 7B 4
python simulations/power/power_budget.py
```

These scripts are first-order engineering tools. They are intended to keep assumptions explicit and machine-checkable while the CAD, BOM, and simulation models mature.
