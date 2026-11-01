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
- **Contract contradiction:** resolve the upstream domain inputs; do not edit the generated contract report.
- **Stale output:** use `regenerate`; do not hand-edit generated reports or the hash state.
- **Unexpected gate pass:** stop, preserve the state, and inspect the underlying evidence and decision rule before further work.

