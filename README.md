# BuildSlate

[![Validation](https://github.com/superflyad/BuildSlate/actions/workflows/validation.yml/badge.svg?branch=main)](https://github.com/superflyad/BuildSlate/actions/workflows/validation.yml)
[![Release](https://img.shields.io/github/v/release/superflyad/BuildSlate?label=release)](https://github.com/superflyad/BuildSlate/releases/latest)
[![License: MIT](https://img.shields.io/badge/license-MIT-237d91)](LICENSE.txt)

![BuildSlate cover: a schematic provisional phone assembly](assets/buildslate-cover.svg)

BuildSlate connects specifications, assumptions, evidence, models, and gate decisions for the proposed Slate Pocket v1R device. It provides a traceable Python CLI and a local 3D assembly viewer.

## Start here

- **Review the program:** [current dashboard](reports/program/dashboard.md) and `buildslate blockers`
- **Explore the model:** [assembly viewer](viewer/README.md) and [assembly contract](engineering/assembly/README.md)
- **Understand the system:** [architecture](ARCHITECTURE.md) and [documentation index](docs/README.md)
- **Contribute:** [repository standards](docs/standards/repository.md) and [contribution guide](CONTRIBUTING.md)

**Engineering status:** the device design is not released. The 3D solids are planning envelopes, with unresolved supplier, mechanical, electrical, test, and manufacturing evidence. The [dashboard](reports/program/dashboard.md) is the current source for gate status. Software release [v0.1.0](https://github.com/superflyad/BuildSlate/releases/tag/v0.1.0) does not change that engineering status.

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

Open the local address printed by Vite. Drag to rotate, select a part to inspect its source and evidence class, and use section cuts, isolation, or explode to examine the internal arrangement. The Program tab includes every component library role and identifies roles without geometry. The [viewer guide](viewer/README.md) covers the controls and generated assets. The viewer cannot establish physical fit or qualification.

## How a change moves through the repository

1. Locate the authoritative input using the [repository map](#repository-map) and [standards](docs/standards/repository.md).
2. Ask `buildslate impact --changed <repository-relative-path>` which generated nodes depend on it.
3. Change the input and record any changed authority or engineering decision in [DECISIONS.md](DECISIONS.md).
4. Run `buildslate regenerate --stale`, then review the generated diff.
5. Run the focused validator while editing. After committing, run `python scripts/ci_validate.py` from a clean tree. The gate checks all validators, Python and Markdown style, installed-package behavior, generated currency, and the viewer build.

Generated reports and `viewer/public/assembly.json` and `.gltf` are outputs. Edit their source files, then regenerate. Supplier responses and physical test results follow the [controlled intake workflow](docs/engineering/operator_workflows.md).

## Repository map

- `specs/` and `configs/` hold product targets and device profiles.
- `engineering/`, `cad/`, and `simulations/` hold model inputs, calculations, and provisional geometry.
- `research/` holds candidate research, RFQs, and supplier response intake.
- `validation/` and `manufacturing/` hold validators, tests, and pilot workflows.
- `buildslate/` contains the Python model, generation engine, and CLI.
- `viewer/` contains the static browser app and generated assembly assets.
- `reports/` contains generated reviews; `docs/` holds methods and procedures.

The [program manifest](engineering/program/program_model.yaml) maps graph authorities. The [regeneration manifest](engineering/program/regeneration.yaml) maps generated dependencies. The [documentation index](docs/README.md) provides a task-based route through the detailed guides.

## Project information

- [Roadmap](ROADMAP.md) — delivered scope, missing evidence, and future viewer work
- [Changelog](CHANGELOG.md) and [release process](docs/standards/releases.md) — software versions and artifacts
- [Contributing](CONTRIBUTING.md) — setup, change workflow, and validation
- [Support](SUPPORT.md) and [security policy](SECURITY.md) — issue and private reporting routes
- [MIT license](LICENSE.txt)
