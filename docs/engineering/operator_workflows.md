# BuildSlate operator workflows

Run every command from the repository root. Do not manually edit files inside a controlled evidence campaign after ingestion.

## Daily local gate

```bash
python -m buildslate dashboard
python -m buildslate stale
python -m buildslate validate --all
```

If `stale` lists nodes, preview and execute the controlled order:

```bash
python -m buildslate regenerate --stale --dry-run
python -m buildslate regenerate --stale
python -m buildslate stale
```

## Supplier response

1. Preserve the supplier-authored YAML and source-document references unchanged.
2. Run `python -m buildslate suppliers validate --domain <domain> --response <file>`.
3. Resolve schema errors. Do not fill supplier fields with BuildSlate estimates.
4. Ingest with explicit receipt time/operator.
5. Regenerate and review contradictions/completeness in the dashboard.
6. Use configuration change control separately; ingestion does not select a part.

### Approved operational fallback

Only use this workflow when the review queue reports an active contradiction and that contradiction rule declares a machine-executable `configuration_effect`. Other contradictions require a separate engineering/product decision and cannot be forced through this command.

1. Create a decision document matching `engineering/program/configuration-change.schema.yaml` outside the controlled decision store.
2. Reference the exact supplier receipt and contradiction rule. Record the current authority value, supplier-backed new value, named approver, timezone-qualified approval time, and rationale.
3. Validate without writing:

   ```bash
   python -m buildslate configuration fallback validate --decision <staged-decision.yaml>
   ```

4. Review every target in the plan. Locked targets are never targets of this workflow.
5. Apply the transaction:

   ```bash
   python -m buildslate configuration fallback apply --decision <staged-decision.yaml>
   ```

The apply command verifies the preserved raw hash, confirms the contradiction is still active, changes the operational authority and all declared propagation targets, records prior values and provenance, updates the contradiction threshold, regenerates every impacted node, and rolls back if any step fails. It does not verify the supplier claim or select a component.

## EVT0 run bundle

Bundle layout:

```text
manifest.yaml
result.yaml
raw/<hash-referenced files>
calibrations/<calibration-id>.yaml
calibrations/<hash-referenced certificates>
```

Validate first, then ingest. A failed or aborted run with intact evidence should be ingested; never rewrite it into a pass. Resolve deviations through their recorded dispositions. Complete correlation is required before the objective evidence gate can become review-ready.

## Pilot bundle

Bundle layout:

```text
pilot-manifest.yaml
units.csv
defects.csv
rework.csv
measurements.csv  # optional unless capability scope requires it
```

Every station-1 input belongs in `units.csv`, including scrap and failed/reworked units. Summary percentages are not accepted as source evidence. Critical defects stop and quarantine. Do not calculate or report Cpk when the analytics engine marks prerequisites unmet.

## Recovery from an error

- **Schema/hash failure:** correct the external staging bundle, never the ingested store; validate again.
- **Receipt hash failure:** quarantine the campaign directory and restore from the preserved source. Do not update the receipt to match unexplained changes.
- **Configuration mismatch:** update the authority registry and profile together through reviewed change control, then regenerate.
- **Fallback transaction failure:** retain the staged decision and inspect the reported cause. The command restores authoritative inputs and generated outputs; do not partially apply its edits by hand.
- **Contract contradiction:** resolve the upstream domain inputs; do not edit the generated contract report.
- **Stale output:** use `regenerate`; do not hand-edit generated reports or the hash state.
- **Unexpected gate pass:** stop, preserve the state, and inspect the underlying evidence and decision rule before further work.

