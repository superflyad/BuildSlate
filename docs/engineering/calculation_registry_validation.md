# Calculation Registry Validation

The calculation registries are source-of-truth infrastructure for BuildSlate's centralized engineering core. `engineering/registry/variables.yaml` defines normalized variables, `engineering/registry/formulas.yaml` defines derived calculations, and `engineering/registry/units.yaml` defines the unit vocabulary those variables and formulas may use.

Because downstream models, explanations, profile checks, and feasibility reports can consume the same registered calculations, registry changes need validation before they are treated as safe engineering infrastructure.

## What the registry validation checks

Run the registry validator from the repository root:

```bash
python validation/validate_calculation_registry.py
```

The validator fails on missing registry files, missing required fields, duplicate variable or formula IDs, unknown formula outputs or inputs, unknown units, unsafe formula expressions, and dependency cycles. These checks prevent silent formula drift: a renamed variable, stale unit, accidental duplicate, or changed dependency must fail loudly instead of changing calculation behavior invisibly.

## Deterministic formula regression tests

Run the deterministic formula checks from the repository root:

```bash
python validation/validate_core_formula_outputs.py
```

These tests pin known outputs for battery energy, geometry volume, geometry surface area, heat density, model memory, and KV cache memory. They are intentionally simple regression checks. If someone changes arithmetic, defaults, or formula wiring, the expected values change only after an explicit engineering review.

## Formula safety

Formulas are evaluated dynamically by the centralized calculator, so expression safety is part of the registry contract. Formula text may only use arithmetic operators, parentheses, numbers, and declared variable IDs. The registry validator rejects unsupported names, functions, imports, undeclared variables, and unsafe tokens before those expressions can be used by the calculator.

Keeping formula expressions constrained makes registry data auditable and reduces the risk that a data-only registry edit can execute arbitrary Python or silently call unsupported behavior.

## Recommended checks

For full calculation-core coverage, run:

```bash
python validation/validate_calculation_registry.py
python validation/validate_core_formula_outputs.py
python validation/validate_core_formula_migration.py
```

These checks validate the registries, assert deterministic arithmetic outputs, and confirm the migrated model scripts still use the centralized core as expected.
