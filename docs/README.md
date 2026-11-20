# Documentation

Use this index to move from a question to the authoritative source. The root [README](../README.md) gives a short operational path; the documents below explain the data contracts and engineering limits.

## Read by task

| Task | Start with | Then inspect |
| --- | --- | --- |
| Understand current readiness | [Program dashboard](../reports/program/dashboard.md) | [External blockers](engineering/slate-pocket-v1r-external-blockers.md) and the source registries linked by the dashboard |
| Change a profile or engineering input | [Repository standards](standards/repository.md) | [Program manifest](../engineering/program/program_model.yaml) and [regeneration manifest](../engineering/program/regeneration.yaml) |
| Review a calculated claim | [Engineering review standard](engineering/review_standard.md) | [Calculation core](engineering/calculation_core.md) and the cited input file |
| Inspect or extend the 3D model | [Assembly viewer](../viewer/README.md) | [Assembly contract](../engineering/assembly/README.md) and [architecture](../ARCHITECTURE.md) |
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
| [Program dashboard](../reports/program/dashboard.md) | Generated gates and external blockers |

## Engineering models

| Document | Purpose |
| --- | --- |
| [Feasibility methodology](engineering/feasibility_methodology.md) | Screening and validation method |
| [Calculation core](engineering/calculation_core.md) | Shared formulas and dependencies |
| [Device profiles](engineering/device_profiles.md) | Profile data and comparisons |
| [Assembly contract](../engineering/assembly/README.md) | Provisional 3D data and coordinate frame |
| [Slate Pocket v1R baseline](engineering/slate-pocket-v1r-decision-baseline.md) | Protected device decisions |

The previous all-in-one overview is retained as an [archived snapshot](archive/2026-10-repository-overview.md). It is useful for history; the current program dashboard and source registries determine present status. Generated reports are views of the tracked inputs. A current hash or visible 3D solid does not promote a planning value to verified evidence.
