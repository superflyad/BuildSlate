# BuildSlate

BuildSlate is the engineering workspace for the proposed Slate Pocket v1R device. It connects specifications, assumptions, supplier evidence, models, and gate decisions so a reviewer can trace a result back to its source. A Python CLI generates the program views; a local browser viewer shows the provisional assembly.

The software is at [v0.1.0](https://github.com/superflyad/BuildSlate/releases/tag/v0.1.0). The device design is **not released**. The 3D solids are planning envelopes, and the current program has unresolved supplier, mechanical, electrical, test, and manufacturing evidence. See the [program dashboard](reports/program/dashboard.md) for the current gate status.

## What is here

| Capability | What it provides | Where to start |
| --- | --- | --- |
| Program graph | Traceable sources, dependencies, gates, and blockers | `buildslate status`, `buildslate blockers` |
| Engineering models | Calculations, profiles, feasibility screens, and integration contracts | [Engineering documentation](docs/README.md#engineering-models) |
| Controlled regeneration | Impact analysis and deterministic derived reports | `buildslate impact`, `buildslate regenerate` |
| Assembly viewer | Rotatable provisional geometry with part provenance and gate context | [Viewer guide](viewer/README.md) |
| Validation | Model, source, document, packaging, and web checks | [Contributing](CONTRIBUTING.md) |

BuildSlate distinguishes a target from an assumption, a supplier statement from a measurement, and a generated view from an approved decision. The [architecture](ARCHITECTURE.md) explains those boundaries.

## Get started

Use a checkout of this repository with Python 3.12 or newer. Node.js 20.19 or newer is needed for the viewer and the full validation gate.

```bash
git clone https://github.com/superflyad/BuildSlate.git
cd BuildSlate
python -m pip install -e .
buildslate validate
buildslate status
buildslate blockers
```

The package contains CLI code, not the engineering input files. From another working directory, point an installed CLI at a checkout:

```bash
buildslate --repo-root /path/to/BuildSlate status
```

The [v0.1.0 release](https://github.com/superflyad/BuildSlate/releases/tag/v0.1.0) provides a wheel, source distribution, and static viewer archive. No PyPI publication is configured.

## Inspect the assembly

```bash
python -m buildslate.assembly --check
cd viewer
npm ci
npm run dev
```

Open the local address printed by Vite. Drag to rotate, select a part to inspect its source and evidence class, and use filters, cutaway, or explode to examine the internal arrangement. The [viewer guide](viewer/README.md) covers the controls and generated assets. The viewer cannot establish physical fit or qualification.

## How a change moves through the repository

1. Locate the authoritative input using the [repository map](#repository-map) and [standards](docs/standards/repository.md).
2. Ask `buildslate impact --changed <repository-relative-path>` which generated nodes depend on it.
3. Change the input and record any changed authority or engineering decision in [DECISIONS.md](DECISIONS.md).
4. Run `buildslate regenerate --stale`, then review the generated diff.
5. Run the focused validator while editing. After committing, run `python scripts/ci_validate.py` from a clean tree. The gate checks all validators, Python and Markdown style, installed-package behavior, generated currency, and the viewer build.

Generated reports and `viewer/public/assembly.json` and `.gltf` are outputs. Edit their source files, then regenerate. Supplier responses and physical test results follow the [controlled intake workflow](docs/engineering/operator_workflows.md).

## Repository map

| Path | Role |
| --- | --- |
| `specs/`, `configs/` | Product targets and device profile choices |
| `engineering/`, `cad/`, `simulations/` | Model inputs, calculations, provisional geometry, and contracts |
| `research/` | Candidate research, RFQs, and supplier response intake |
| `validation/`, `manufacturing/` | Validators, test definitions, and pilot workflows |
| `buildslate/` | Python program model, generation engine, and CLI |
| `viewer/` | Static browser application and generated assembly assets |
| `reports/` | Generated status and engineering views |
| `docs/` | Engineering methods, procedures, and repository standards |

The [program manifest](engineering/program/program_model.yaml) maps graph authorities. The [regeneration manifest](engineering/program/regeneration.yaml) maps generated dependencies. The [documentation index](docs/README.md) provides a task-based route through the detailed guides.

## Project information

- [Roadmap](ROADMAP.md) — delivered scope, missing evidence, and future viewer work
- [Changelog](CHANGELOG.md) and [release process](docs/standards/releases.md) — software versions and artifacts
- [Contributing](CONTRIBUTING.md) — setup, change workflow, and validation
- [Support](SUPPORT.md) and [security policy](SECURITY.md) — issue and private reporting routes
- [MIT license](LICENSE.txt)
