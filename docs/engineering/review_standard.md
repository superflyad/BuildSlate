# Engineering Review Standard

BuildSlate should survive skeptical technical review. Professionals may challenge assumptions, but the project should not ignore first principles.

All claims should be classified as one of:

- measured fact
- industry reference
- modeled estimate
- conceptual extrapolation
- unresolved research blocker

Every model should print:

- inputs
- assumptions
- formulas
- outputs
- confidence: low / medium / high
- basis: measured / estimated / extrapolated
- primary blocker

Avoid fake precision. Prefer ranges over single-point claims. If math contradicts a target, preserve the contradiction and flag it.
