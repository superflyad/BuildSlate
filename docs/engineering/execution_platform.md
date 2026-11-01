# BuildSlate Engineering Execution Platform

BuildSlate now has a read-only program integration layer above the existing authoritative registries. The first platform revision does not migrate or rewrite engineering evidence. It indexes the protected v1R baseline, evidence packages, assumptions, risks, blockers, supplier candidates, component roles, EVT0 tests, defect codes, artifacts, and gate decisions into one deterministic graph.

## Authority model

`engineering/program/program_model.yaml` declares the authoritative source for each entity kind and the generated snapshot location. The graph preserves each source status exactly. A present file becomes an `artifact` with status `present`; it never upgrades the evidence package that expects it.

The generated snapshot is `reports/program/buildslate-program-snapshot.yaml`. It is a reproducible index, not a new engineering source of truth.

## CLI

Run from the repository root:

```bash
python -m buildslate validate
python -m buildslate validate --all
python -m buildslate status
python -m buildslate status --format json
python -m buildslate blockers
python -m buildslate blockers --id supplier_responses
python -m buildslate compare --left configs/devices/slate-pocket-v1.yaml --right configs/devices/slate-pocket-v1r.yaml
python -m buildslate generate
python -m buildslate suppliers validate --domain battery --response path/to/response.yaml
python -m buildslate suppliers ingest --domain battery --response path/to/response.yaml --received-at 2026-11-01T12:00:00-05:00 --received-by operator@example.com
python -m buildslate suppliers queue --generate
```

## Supplier-response ingestion

The supplier workflow supports battery, compute/memory, display, storage, and DFM responses. Each domain schema identifies required structure, completeness fields, provenance anchors, and contradictions against a locked target, operational fallback, or integration allocation.

`suppliers validate` is read-only. `suppliers ingest` accepts only structurally valid YAML, preserves the original bytes under a hash-addressed raw path, and creates an explicit receipt. `suppliers queue --generate` verifies receipt hashes and rebuilds the review queue. A `READY_FOR_ENGINEERING_REVIEW` disposition is not verified evidence and does not select a component. Configuration changes require the separate controlled resolver workflow.

The inbox is intentionally empty until authorized supplier-authored evidence is received. Do not copy RFQ templates into the raw store as if they were responses.

Structured output is available as JSON or YAML where applicable. Exit code `0` means the requested operation completed; validation/input errors return `2`; `validate --all` propagates the repository validation exit code.

## Current boundary

This checkpoint provides the program model, traceability graph, status/blocker inspection, configuration comparison, and CLI validation/generation foundation. Supplier ingestion, configuration resolution, dependency-aware regeneration, campaign analytics, and dashboard workflows will build on this layer in later commits.
