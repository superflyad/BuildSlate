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

Assumptions must also stay traceable:

- Every major assumption should eventually map to `engineering/assumptions/source_registry.yaml`.
- Low-confidence assumptions are allowed, but they must be labeled.
- "Unknown" is acceptable; hidden unknowns are not.

## Constants Provenance

Every major constant should map to an entry in `engineering/provenance/constants_provenance.yaml`. Low-confidence constants are allowed when explicitly labeled, and uncited constants are allowed temporarily when `source_notes.citation_status` marks the citation gap.

Future work should replace screening values with:

- vendor datasheets;
- peer-reviewed references;
- standards documents;
- measured prototype data.

BuildSlate must never hide assumed values inside code. If a constant or target affects feasibility, runtime, mass, thermal, manufacturing, reliability, or interconnect conclusions, it needs visible provenance that states category, confidence, units, rationale, limitations, and the path to replacement data.
