# Engineering Calculation Core

`engineering/core/` contains the additive centralized calculation engine for BuildSlate engineering variables and formulas.

The core currently provides:

- `registry_loader.py` for shared YAML registry loading.
- `variable_registry.py` for variable metadata lookups.
- `formula_registry.py` for formula metadata and output lookups.
- `dependency_graph.py` for formula input and dependent relationships.
- `calculator.py` for dependency-aware recomputation from known inputs and defaults.
- `explanation_engine.py` for human-readable calculation traces.

The core is intentionally small and explainable. Existing engineering scripts remain intact and continue to own their current command-line workflows while this shared layer matures.
