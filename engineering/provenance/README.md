# Engineering Constants Provenance

This directory tracks provenance for BuildSlate engineering constants and assumptions.

- `constants_provenance.yaml` is the detailed registry for important constants, concept targets, model parameters, and unresolved assumptions.
- `provenance_report.py` prints a human-readable summary of category counts, confidence counts, missing-citation work, conceptual extrapolations, unresolved research blockers, and high-risk assumptions.
- `../../validation/validate_provenance.py` validates the registry schema.

The registry is intentionally allowed to include low-confidence and uncited values when they are clearly labeled. It should distinguish measured facts, industry references, modeled estimates, conceptual extrapolations, and unresolved research blockers so reviewers can see what is known, estimated, or blocked.

Do not invent precise citations. Use `source_notes.citation_status` to mark whether external citation, vendor datasheets, standards documents, peer-reviewed references, or measured prototype data are still needed.
