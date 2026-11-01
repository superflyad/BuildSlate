# Slate Pocket v1R Provisional Envelope Model

This directory defines a machine-readable mechanical blocking model for work that can proceed before supplier CAD arrives. It is a provisional integration contract, not production CAD or evidence that the parts fit.

- `envelope.yaml` defines the external body, conservative internal boundary, and reference component placements.
- `keepouts.yaml` defines perimeter RF, connector/service, camera, and acoustic exclusion zones.
- `zone-stackups.yaml` defines local z-height stacks instead of incorrectly summing every component into one global stack.

Every dimension carries an evidence class. `public_supplier` values come from public manufacturer material; `estimate`, `placeholder`, and `inferred` values must be replaced before the evidence package can become verified.

Generate the current screen with:

```bash
python engineering/cad_envelope/generate_v1r_cad_budget.py
```

The output is `reports/slate-pocket-v1r-cad-budget.txt`.
