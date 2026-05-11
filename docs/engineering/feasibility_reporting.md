# Feasibility Reporting

BuildSlate's feasibility report generator exists to provide one readable engineering review artifact for Slate Pocket v1. The repository now contains many first-pass models and validation scripts, and reviewing them independently can hide cross-domain risks. A single report keeps validation state, mass, energy, thermal, stackup, packaging, interconnect, runtime memory, manufacturing, environmental, and provenance outputs visible in one place.

The report runner executes selected existing scripts, captures their stdout and stderr, and groups the results by engineering review area. It does not optimize the design, choose parts, create device profiles, or replace the individual models. Instead, it preserves the model outputs so reviewers can see which checks passed, which checks failed, and which assumptions still need evidence.

## Engineering blockers from warnings

The generator scans captured output for simple warning and risk keywords such as `WARNING`, `risk:`, `over target`, `FAIL`, `exceeds`, and `blocker`. Matching lines are collected into the `Top Engineering Blockers` section. This is intentionally simple: the goal is to surface likely review items, not to reinterpret every model's domain-specific output.

A warning in the blocker section does not automatically mean the design is impossible. It means the issue should remain visible until it is resolved, justified, measured, or accepted as a known early-stage risk.

## Skipped checks during early development

Some model areas are still evolving, so the report runner allows optional scripts to be absent. Missing optional checks are reported as skipped rather than failed. This keeps the unified report useful while the model suite is incomplete, while still making coverage gaps explicit.

Required validation scripts are different: they must pass for the report command to exit successfully. Validation failures indicate that the inputs or provenance records are not trustworthy enough for a clean feasibility snapshot.

## Future configurations

Future work can allow product profiles, configuration files, or device variants to select model inputs and report sections. Until then, the runner is fixed to the Slate Pocket v1 first-pass screening workflow and should be treated as a consolidated review command rather than a configuration system.
