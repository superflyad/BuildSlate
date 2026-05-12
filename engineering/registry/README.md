# Engineering Registry

`engineering/registry/` stores centralized YAML registries used by the calculation core.

- `variables.yaml` defines reusable variables, units, categories, source types, defaults, confidence, and dependency hints.
- `formulas.yaml` defines reusable formulas, outputs, inputs, limitations, confidence, and output units.
- `units.yaml` defines normalized unit labels used by the registries.

These files are additive scaffolding for future UI, API, audit, and model integration work. They do not replace the existing model scripts yet.
