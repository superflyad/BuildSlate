# Slate Pocket v1R Program Dashboard

**Dashboard gate:** `LOCAL_SYSTEM_CURRENT_EXTERNALLY_BLOCKED`

This is a generated evidence and action view. It does not approve suppliers, components, builds, tests, certification, or production.

## Evidence summary

| Class | Count | Meaning |
|---|---:|---|
| Verified | 1 | Acceptance criteria met in the evidence registry |
| Available, not verified | 3 | Reviewable evidence exists but is incomplete or unverified |
| Modeled, not verified | 4 | Phase 2 planning models exist without verified inputs/results |
| Rejected options | 3 | Explicitly prohibited or rejected configurations retained for traceability |
| Stale nodes | 0 | Generated outputs whose recorded hashes do not match |
| Contradictions | 0 | Authority, integrity, supplier, campaign, or cross-domain conflicts |
| External blockers | 8 | Work requiring authorization or external evidence |

## Gate status

- `configuration_gate`: `CONTROLLED_WITH_UNRESOLVED_EXTERNAL_DECISIONS` — `reports/program/configuration-resolution.yaml`
- `evidence_gate`: `BLOCKED_ON_FOUNDATIONAL_EVIDENCE` — `reports/slate-pocket-evidence-readiness.txt`
- `evt0_campaign_gate`: `EMPTY_CAMPAIGN` — `reports/program/evt0-campaign.yaml`
- `evt0_gate`: `BLOCKED_ON_SUPPLIER_PHASE2_VERIFICATION_BUILD_AUTHORIZATION_AND_RESULTS` — `reports/slate-pocket-v1r-evt0-gate.txt`
- `integration_contract_gate`: `CONTRACTS_CONSISTENT_NOT_RELEASED` — `reports/program/integration-contracts.yaml`
- `local_program_gate`: `SUPPLIER_READY_AND_PROTOTYPE_PLAN_READY_EXTERNALLY_BLOCKED` — `reports/slate-pocket-v1r-program-readiness.txt`
- `manufacturing_analytics_gate`: `EMPTY_PILOT_EVIDENCE` — `reports/program/manufacturing-pilot-analytics.yaml`
- `manufacturing_gate`: `BLOCKED_ON_VERIFIED_EVT0_SUPPLIER_DFM_RELEASED_PROCESS_AND_PILOT_EVIDENCE` — `reports/slate-pocket-v1r-manufacturing-readiness.txt`
- `supplier_response_gate`: `EMPTY_INBOX` — `reports/program/supplier-response-review.yaml`

## Rejected options

- `memory_first_build_rejection`: 512 GB — Unsupported as a first-build configuration; the headline target remains traceable.
- `storage_first_build_rejection`: 4 TB — Unsupported as an internal first-build configuration.
- `wireless_charging_evt0`: removed  — Removed from EVT0 after z-height and certification screening.

## Stale or contradictory local state

- None. All tracked generated nodes are current and no contradiction queue is open.

## Exact externally blocked next actions

1. **supplier_responses** (`supplier_and_nda`)
   - Missing: Completed supplier response templates, controlled drawings, limits, lifecycle/availability, sample terms, and attestations.
   - Action: Authorize supplier outreach using research/rfqs after contact and NDA review; request completed response schemas and source documents.
   - Authorization: `supplier_contact_and_any_NDA_acceptance`
   - Active fallback: Retain public candidates only as references; do not select components or release CAD.
2. **battery_pack_and_charge_limits** (`supplier_safety`)
   - Missing: Complete-pack CAD, swelling/tolerances, protection, charge/discharge curves, temperature/cycle limits, safety and shipping documentation.
   - Action: Request a supplier-proposed pack fitting the RFQ envelope and validated charger/system limits; do not prescribe unsupported capacity or charge rate.
   - Authorization: `supplier_contact_samples_and_purchases`
   - Active fallback: Use the best supplier-validated capacity fitting the envelope; cap wired charge below 30 W if required; wireless remains removed.
3. **platform_reference_design** (`supplier_confidential_engineering`)
   - Missing: Package/ball maps, qualified 128 GB topology, PMIC/rails, reference schematic, power/load steps, software access, and sustained workload telemetry.
   - Action: Obtain the selected platform's NDA-controlled design package and evaluation access for the 128 GB fallback.
   - Authorization: `supplier_contact_NDA_eval_hardware_and_licenses`
   - Active fallback: Use external 128 GB developer systems for workload characterization only; do not claim pocket integration.
4. **display_storage_drawings** (`supplier_engineering`)
   - Missing: Selected display module drawing/flex/power and selected storage package/host/power/thermal/lifecycle evidence.
   - Action: Run prepared display and storage RFIs; request EVT-available modules and complete response schemas.
   - Authorization: `supplier_contact_samples_and_purchases`
   - Active fallback: Allow supplier-available 7–8.4 inch display variation and modular/external storage; 4 TB internal stays rejected.
5. **released_integration_design** (`engineering_and_paid_tools`)
   - Missing: Released 3D CAD, tolerance/mass/interference review, schematic/netlist/routed ECAD, solver model, EM model, and peer signoff.
   - Action: After supplier packages are verified, authorize detailed CAD/ECAD/solver work and any required paid tools or contractors.
   - Authorization: `design_release_paid_tools_and_external_engineering_if_needed`
   - Active fallback: Preserve provisional blocking models and 10.2 mm first thickness fallback; do not release hardware.
6. **accredited_labs_and_compliance_scope** (`laboratory_and_regulatory`)
   - Missing: Market/SKU matrix, current lab scope, calibrated tests, accredited reports, certifications/declarations/filings.
   - Action: Select target markets/configurations and engage qualified labs/regulatory counsel after production-intent hardware exists.
   - Authorization: `market_decisions_lab_contracts_and_test_samples`
   - Active fallback: Defer cellular, remove wireless charging, limit claims/markets, and retain modular development radios.
7. **evt0_build_and_measurement** (`physical_work`)
   - Missing: Selected BOM, released designs, authorized build, calibrated setup, raw results, deviations, and correlated models.
   - Action: Authorize procurement/build/energized testing only after the EVT0 prerequisite and safety gates pass.
   - Authorization: `purchases_physical_build_and_energized_testing`
   - Active fallback: Continue workload characterization on external developer hardware without claiming integrated prototype performance.
8. **supplier_dfm_and_pilot** (`manufacturing_physical_work`)
   - Missing: Completed supplier DFM responses, released process/tooling, pilot authorization, 100-unit records, yield/capability, reliability, compliance, and service results.
   - Action: After verified EVT0, authorize supplier DFM and then the controlled pilot only when G0/G1 pass.
   - Authorization: `supplier_engagement_tooling_materials_pilot_and_labs`
   - Active fallback: Hold production claims and iterate EVT/design/process; do not shrink denominators or hide rework/failures.

> Artifact presence, current hashes, and consistent interfaces do not convert modeled or available evidence into verified evidence.
