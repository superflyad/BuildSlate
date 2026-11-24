# Documentation

Use this index to move from a question to the authoritative source. The root [README](../README.md) gives a short operational path; the documents below explain the data contracts and engineering limits.

## Read by task

| Task | Start with | Then inspect |
| --- | --- | --- |
| Understand current readiness | [Build-to-function gate](engineering/build_to_function.md) | [Program dashboard](../reports/program/dashboard.md), [external blockers](engineering/slate-pocket-v1r-external-blockers.md), and the source registries linked by the dashboard |
| Change a profile or engineering input | [Repository standards](standards/repository.md) | [Program manifest](../engineering/program/program_model.yaml) and [regeneration manifest](../engineering/program/regeneration.yaml) |
| Review a calculated claim | [Engineering review standard](engineering/review_standard.md) | [Calculation core](engineering/calculation_core.md) and the cited input file |
| Inspect or extend the 3D model | [Assembly viewer](../viewer/README.md) | [CAD proofing](engineering/cad_proofing.md), [assembly contract](../engineering/assembly/README.md), and [architecture](../ARCHITECTURE.md) |
| Ingest supplier or test evidence | [Operator workflows](engineering/operator_workflows.md) | The applicable schema and source receipt |
| Contribute software or documentation | [Contributing](../CONTRIBUTING.md) | [Architecture](../ARCHITECTURE.md) and [design decisions](../DECISIONS.md) |

## Repository and review

| Document | Purpose |
| --- | --- |
| [Architecture](../ARCHITECTURE.md) | Authority layers, generation, and module boundaries |
| [Repository standards](standards/repository.md) | Directory ownership, file classes, names, and change rules |
| [Contributing](../CONTRIBUTING.md) | Development and validation workflow |
| [Support](../SUPPORT.md) | Issue routes and evidence boundaries |
| [Security policy](../SECURITY.md) | Private vulnerability reporting |
| [Design decisions](../DECISIONS.md) | Durable architecture choices |
| [Roadmap](../ROADMAP.md) | Delivered scope and missing inputs |
| [Changelog](../CHANGELOG.md) | Versioned software changes |
| [Release process](standards/releases.md) | Version, artifact, and publication rules |
| [Engineering review standard](engineering/review_standard.md) | Claim classes and model maturity |

## Program operation

| Document | Purpose |
| --- | --- |
| [Execution platform](engineering/execution_platform.md) | CLI and authority model |
| [Platform architecture](engineering/platform_architecture.md) | Evidence, configuration, and generation flow |
| [Operator workflows](engineering/operator_workflows.md) | Evidence intake and recovery procedures |
| [Platform handoff](engineering/platform_handoff.md) | Canonical commands and current boundary |
| [Execution roadmap](engineering/execution_roadmap.md) | Staged path from screening to prototype decisions |
| [Slate Pocket v1R baseline](engineering/slate-pocket-v1r-decision-baseline.md) | Protected device decisions and fallbacks |
| [External blockers](engineering/slate-pocket-v1r-external-blockers.md) | Evidence requests and external decisions |
| [Program dashboard](../reports/program/dashboard.md) | Generated gates and external blockers |

## Review and calculation methods

| Document | Purpose |
| --- | --- |
| [Engineering review standard](engineering/review_standard.md) | Claim classes and model maturity |
| [Feasibility methodology](engineering/feasibility_methodology.md) | Screening and validation method |
| [Feasibility reporting](engineering/feasibility_reporting.md) | Report structure and interpretation |
| [Calculation core](engineering/calculation_core.md) | Shared formulas and dependencies |
| [Calculation registry validation](engineering/calculation_registry_validation.md) | Formula registry checks |
| [Constraint boundary analysis](engineering/constraint_boundary_analysis.md) | Coupled design limits |
| [Scenario sweeps](engineering/scenario_sweeps.md) | Sensitivity analysis across assumptions |
| [Tradeoff mapping](engineering/tradeoff_mapping.md) | Comparison of competing constraints |

## Engineering models

| Document | Purpose |
| --- | --- |
| [Device profiles](engineering/device_profiles.md) | Profile data and comparisons |
| [Profile comparison](engineering/profile_comparison.md) | Cross-profile engineering tradeoffs |
| [Component modeling](engineering/component_modeling.md) | Component estimate structure |
| [Component physics models](engineering/component_physics_models.md) | Component-level physical calculations |
| [Material selection primer](engineering/material_selection_primer.md) | Enclosure material tradeoffs |
| [Composite chassis strategy](engineering/composite_chassis_strategy.md) | Chassis material and structure approach |
| [Environmental conditions](engineering/environmental_conditions.md) | Operating environment assumptions |
| [Interconnect and power](engineering/interconnect_and_power.md) | Electrical interface and delivery screening |
| [Local AI runtime modeling](engineering/local_ai_runtime_modeling.md) | Memory and runtime constraints |
| [Thermal resistance modeling](engineering/thermal_resistance_modeling.md) | Thermal pathway estimates |
| [Zone stackup modeling](engineering/zone_stackup_modeling.md) | Thickness and placement budgets |
| [Manufacturing and reliability](engineering/manufacturing_and_reliability.md) | Build and reliability screening |
| [Assembly contract](../engineering/assembly/README.md) | Provisional 3D data and coordinate frame |
| [CAD proofing](engineering/cad_proofing.md) | Solid, STEP, mesh, keepout, and stack checks with explicit limits |
| [Build-to-function gate](engineering/build_to_function.md) | Required design release and physical EVT0 evidence |
| [128 GB compute path](engineering/compute_platform_decision.md) | Public platform limits and evidence needed to prove the approved memory floor |
| [128 GB package screen](engineering/memory_package_fit.md) | Exact public 16 GB LPDDR5X package versus four assumed 32 GB board sites |
| [1 TB UFS candidate screen](engineering/storage_candidate_fit.md) | Exact public package outline, rail requirements, and unresolved integration work |
| [Battery candidate fit](engineering/battery_candidate_fit.md) | Published cell and concept pack volumes versus the complete-pack allocation; charge evidence limit |
| [Selected BOM proof](engineering/selected_bom_proof.md) | Exact part identity, supplier source binding, and interface checks |
| [Electrical netlist proof](engineering/electrical_netlist_proof.md) | Connectivity and selected electrical BOM audit contract |
| [Routed PCB proof](engineering/routed_pcb_proof.md) | KiCad schematic parity, DRC, and reproducible fabrication exports |
| [Released mechanical CAD proof](engineering/mechanical_release_proof.md) | Supplier STEP identity, assembly placement, intersections, and tolerance clearance |

The previous all-in-one overview is retained as an [archived snapshot](archive/2026-10-repository-overview.md). It is useful for history; the current program dashboard and source registries determine present status. Generated reports are views of the tracked inputs. A current hash or visible 3D solid does not promote a planning value to verified evidence.
