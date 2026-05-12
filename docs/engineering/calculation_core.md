# Centralized Calculation Core

BuildSlate now includes an additive centralized calculation core for reusable engineering variables, formulas, dependencies, units, and explanations.

## Centralized variables

Variable metadata lives in `engineering/registry/variables.yaml`. Each variable has a stable id, name, units, category, description, source type, default value, confidence, declared inputs, and declared dependents. This gives existing and future models a shared vocabulary without forcing an immediate rewrite of older scripts.

## Formula registry

Formula metadata lives in `engineering/registry/formulas.yaml`. Each formula declares one output variable, its arithmetic expression, input variables, units, description, limitations, and confidence. The initial formula set covers battery energy, usable energy, runtime, battery mass, geometry volume and surface area, heat density, model memory, and KV cache estimates.

## Dependency graph

`engineering/core/dependency_graph.py` builds a simple graph from formula inputs and outputs. It supports:

- finding the inputs required to compute a variable;
- finding variables that depend on a given input;
- finding the formula that produces a variable.

This graph is intentionally explicit and traceable rather than an optimizer or auto-design solver.

## Calculator

`engineering/core/calculator.py` computes requested variables from CLI inputs, registry defaults, and formula dependencies. For example:

```bash
python engineering/core/calculator.py \
  --set battery.capacity_mah=6000 \
  --set battery.nominal_voltage_v=3.85 \
  --compute battery.energy_wh
```

Expected output:

```text
battery.energy_wh = 23.1 Wh
```

## Explanation engine

`engineering/core/explanation_engine.py` shows how a value was computed by printing the formula, a substituted expression, and the result. For example:

```bash
python engineering/core/explanation_engine.py --compute battery.energy_wh
```

Expected output:

```text
battery.energy_wh
= (battery.capacity_mah / 1000) * battery.nominal_voltage_v
= (6000 / 1000) * 3.85
= 23.1 Wh
```

## First Model Integration

`engineering/models/battery_energy.py` is the first legacy engineering model routed through the centralized calculation core. The script keeps its existing CLI inputs, assumptions, conservative/nominal/aggressive output structure, and text-oriented report format while using registered core formulas for shared battery energy arithmetic.

Existing scripts are being migrated gradually. Model behavior should remain stable during migration, with arithmetic moving toward centralized formulas, variable ids, units, and explanation output where that provides clearer reuse and auditability.

## Future extensibility

The calculation core is structured so future work can add:

- registry validation;
- richer unit conversion;
- UI/API access to variables and formulas;
- model-script migration onto shared formulas;
- audit views that explain where every derived number came from;
- scenario and profile integration using the same stable variable ids.

## Existing scripts still coexist

This engine is additive. Existing engineering models, sweeps, constraints, tradeoff maps, audits, and validation scripts continue to run as before. The centralized core introduces shared infrastructure first, without removing or rewriting current model scripts.
