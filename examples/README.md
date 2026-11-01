# Evidence workflow examples

Examples here describe bundle layouts and commands only. They intentionally contain no supplier claims, component selections, measurements, pilot units, approvals, or test results.

- Supplier fields and domain structure: `research/rfqs/*/response-template.yaml`
- EVT0 bundle layout and workflow: `docs/engineering/operator_workflows.md`
- Pilot bundle layout and workflow: `docs/engineering/operator_workflows.md`
- Machine-readable schemas: `engineering/program/supplier-schemas`, `validation/evt0/schemas`, and `manufacturing/schemas`
- Approved operational fallback decision contract: `engineering/program/configuration-change.schema.yaml`

Fallback examples are intentionally not stored as applied decisions. Use schema-valid placeholder data only in external staging, then reference a real controlled receipt and explicit approval when evidence exists.

