# Engineering Coverage Audit

This directory contains BuildSlate's formal engineering coverage map and model maturity audit tooling.

The audit exists because having a first-pass model is not the same as having validated engineering evidence. Each domain in `coverage_registry.yaml` is classified by coverage status, maturity level, assumptions, known gaps, required next evidence, and review priority.

## Files

- `coverage_registry.yaml` records the current domain-by-domain coverage and evidence status.
- `model_maturity_audit.py` validates and summarizes the registry from the command line.
- `coverage_gap_report.py` generates `reports/audit/coverage-gap-report.md` for review and planning.

## Maturity levels

- `screening`: useful for early tradeoff visibility, but not proof of feasibility.
- `first_order`: includes explicit equations and structured inputs, but is not calibrated to measured hardware.
- `calibrated`: adjusted against measured data, supplier data, or accepted references.
- `validated`: supported by measured prototype data or authoritative references for the intended design envelope.

## Coverage statuses

- `covered`: BuildSlate has a visible model or registry entry with explicit assumptions.
- `partial`: BuildSlate covers part of the domain, but important operating regimes or interfaces remain unresolved.
- `weak`: BuildSlate only has coarse screening coverage or low-confidence constants.
- `missing`: BuildSlate lacks a domain-specific model or evidence path beyond high-level acknowledgement.

No current registry verdict should be interpreted as production validation, certification, or proof that the backend is externally review ready.
