# BuildSlate execution-platform architecture

## Authority layers

1. **Protected engineering inputs** — the v1R profile, evidence/assumption/risk/blocker registries, RFQ packets, integration models, EVT0 definitions, and manufacturing plans retain their existing authority and classifications.
2. **Controlled evidence stores** — supplier responses, EVT0 run bundles, and pilot bundles preserve source bytes and SHA-256 receipts. Ingestion never changes requirements or evidence status.
3. **Resolution and contracts** — configuration authority classifies targets, fallbacks, references, rejections, selections, and unresolved decisions. Phase 2 contracts reject cross-domain drift.
4. **Deterministic generation** — the regeneration DAG hashes inputs/outputs and runs whitelisted commands in dependency order.
5. **Decision views** — program snapshot, gates, migration audit, and dashboard are generated views. They are not independent evidence authorities.

## Core flow

```text
raw supplier / EVT0 / pilot evidence
              |
              v
schema + provenance + hash review
              |
              v
review queues and objective analytics
              |
              v
configuration authority + Phase 2 contracts
              |
              v
dependency-aware regeneration
              |
              v
gates + unified graph + dashboard
```

No arrow automatically promotes evidence. Supplier claims require engineering review; selected components require a matching review-ready receipt; test/pilot evidence remains subject to deviations, correlations, stop rules, and named approvals.

## Controlled fallback transaction

An ingested contradiction does not mutate configuration. A separate approved decision must reference the intact receipt and an executable contradiction rule. The transaction changes only an `operational_fallback` authority, updates every bound profile and cross-domain propagation target, preserves prior values and hashes in `engineering/program/configuration-decisions`, and regenerates the affected DAG. Locked targets remain unchanged and continue to show the product aspiration. Non-executable fallback language remains a review action, never an automatic edit.

## Failure behavior

- Malformed or hash-inconsistent evidence is rejected before ingestion.
- Valid failed/aborted evidence is preserved and blocks or opens review; it is not discarded.
- Unsupported configuration bound to a model returns a nonzero result.
- Cross-domain contradictions stop regeneration before downstream reports refresh.
- A fallback approval, supplier hash, value, target, or downstream generation failure rolls the entire configuration transaction back.
- Missing or changed generator inputs/outputs become hash-stale.
- Regeneration hashes canonicalize UTF-8 text line endings to LF so Windows and Linux evaluate the same content identically; binary evidence remains byte-exact.
- Critical pilot defects trigger stop/quarantine regardless of average yield.
- Dashboard currency never implies physical or commercial readiness.

