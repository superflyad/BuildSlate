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
python -m buildslate configuration validate
python -m buildslate contracts validate
python -m buildslate evt0 validate --bundle path/to/run-bundle
python -m buildslate evt0 ingest --bundle path/to/run-bundle --received-at 2026-11-02T12:00:00-06:00 --received-by operator@example.com
python -m buildslate evt0 report --generate
python -m buildslate manufacturing validate --bundle path/to/pilot-bundle
python -m buildslate manufacturing ingest --bundle path/to/pilot-bundle --received-at 2026-11-03T12:00:00-06:00 --received-by operator@example.com
python -m buildslate manufacturing report --generate
python -m buildslate impact --changed configs/devices/slate-pocket-v1r.yaml
python -m buildslate regenerate --stale --dry-run
python -m buildslate regenerate --stale
```

## Supplier-response ingestion

The supplier workflow supports battery, compute/memory, display, storage, and DFM responses. Each domain schema identifies required structure, completeness fields, provenance anchors, and contradictions against a locked target, operational fallback, or integration allocation.

`suppliers validate` is read-only. `suppliers ingest` accepts only structurally valid YAML, preserves the original bytes under a hash-addressed raw path, and creates an explicit receipt. `suppliers queue --generate` verifies receipt hashes and rebuilds the review queue. A `READY_FOR_ENGINEERING_REVIEW` disposition is not verified evidence and does not select a component. Configuration changes require the separate controlled resolver workflow.

The inbox is intentionally empty until authorized supplier-authored evidence is received. Do not copy RFQ templates into the raw store as if they were responses.

## Configuration authority

`engineering/program/configuration_registry.yaml` is the classification layer between requirements/evidence and downstream model inputs. It keeps locked targets, operational fallbacks, modeled references, rejected options, selected components, and unresolved decisions distinct. Bindings assert that every controlled profile value matches its authority entry. An unresolved or prohibited value cannot be bound as a model input.

Selected-component entries require a non-null value, a review-ready ingestion receipt, a matching value in the hash-verified raw response, and an explicit value path; no such entry exists in the protected baseline. The generated `reports/program/configuration-resolution.yaml` currently preserves compute selection and cellular integration as externally unresolved while allowing only the documented v1R planning values into models.

## Dependency-aware regeneration

`engineering/program/regeneration.yaml` defines a generator DAG from supplier inputs and configuration through device profiles, CAD, PCB/power, thermal, RF, risks, handoff, and the program snapshot. `impact` answers what a proposed path change affects. `stale` compares current input/output SHA-256 hashes with the committed state. `regenerate` executes only whitelisted repository-local commands in dependency order and refreshes the state after every successful run.

The regeneration state proves only that generated files match repository inputs. It does not prove supplier claims, model accuracy, test results, or physical readiness.

## Phase 2 integration contracts

`engineering/program/integration_contracts.yaml` defines explicit input/output boundaries for mechanical, ECAD, power, thermal, RF, firmware, and manufacturing. Cross-domain checks bind the common envelope, board placement, memory tier, power loads, thermal sources, wireless disposition, EVT0 configuration, sensor inventory, and pilot denominator. A contradiction returns a nonzero CLI result and stops controlled regeneration before downstream reports are refreshed.

The current gate is `CONTRACTS_CONSISTENT_NOT_RELEASED`: all checked interfaces agree, but every domain remains provisional, planned, or not authorized. Interface consistency is not evidence of design release or physical validation.

## EVT0 campaign evidence

An EVT0 bundle contains `manifest.yaml`, `result.yaml`, referenced raw files, and calibration records/certificates. `evt0 validate` checks structure, test identity, time ranges, SHA-256 references, calibration validity at run start, required-channel status, hard stops, and deviations. It derives supported metrics directly from hash-verified CSV columns and calculates model-correlation residuals against declared tolerances.

`evt0 ingest` preserves the complete bundle and a receipt; failed or aborted tests may be valid evidence and are retained, while structurally invalid or hash-inconsistent bundles are rejected. `evt0 report` requires objective passes for all 16 gate tests. The committed campaign remains empty because no authorized physical campaign or measurements exist.

## Pilot manufacturing analytics

Pilot bundles contain an explicitly authorized manifest plus unit genealogy, defects, rework, and optional critical-characteristic measurements. The analytics engine keeps every station-1 input in the denominator, calculates FPY/final yield/rework/unknown rates and Wilson 95% intervals, validates defect codes and unit references, generates defect Pareto counts, and applies the existing stop rules and provisional quality thresholds.

Cpk is calculated only when the declared critical-characteristic scope requires it and every configured prerequisite is met, including at least 30 observations, approved measurement systems, process stability, reviewed distributions, consistent specifications, and nonzero sample variation. Passing point estimates produce `PILOT_ANALYTICS_PASS_REVIEW_REQUIRED`, never production approval. The committed pilot store remains empty.

Structured output is available as JSON or YAML where applicable. Exit code `0` means the requested operation completed; validation/input errors return `2`; `validate --all` propagates the repository validation exit code.

## Current boundary

This checkpoint provides the program model, traceability graph, status/blocker inspection, configuration comparison, and CLI validation/generation foundation. Supplier ingestion, configuration resolution, dependency-aware regeneration, campaign analytics, and dashboard workflows will build on this layer in later commits.
