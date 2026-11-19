# BuildSlate

BuildSlate is a traceable engineering model for the Slate Pocket v1R device. The repository keeps product intent, planning assumptions, evidence, analyses, and gate decisions separate. Generated outputs support review; they do not certify a build.

## Start here

| Need | Entry point |
| --- | --- |
| Current program state and blockers | `python -m buildslate status` and `python -m buildslate blockers` |
| Engineering dashboard | [Program dashboard](reports/program/dashboard.md) |
| Provisional 3D assembly | [Assembly viewer](viewer/README.md) |
| Data authority and generation flow | [Architecture](ARCHITECTURE.md) |
| Repository rules | [Repository standards](docs/standards/repository.md) |
| Contributing and validation | [Contributing](CONTRIBUTING.md) |
| Support and issue reports | [Support](SUPPORT.md) |
| Sensitive security reports | [Security policy](SECURITY.md) |
| Engineering documentation | [Documentation index](docs/README.md) |

## Quick start

Requires Python 3.12 or newer. The viewer also requires Node.js 20.19 or newer.

```bash
python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt
python -m buildslate validate
python -m buildslate status
python -m buildslate.assembly --check
python scripts/ci_validate.py
```

To run the viewer:

```bash
cd viewer
npm ci
npm run dev
```

Open the local URL printed by Vite. The viewer loads generated `assembly.json` and `assembly.gltf`; regenerate them after changing an assembly input with `python -m buildslate.assembly` or the repository regeneration command.

## Repository map

| Directory | Role |
| --- | --- |
| `specs/`, `configs/` | Source intent and device profiles |
| `engineering/`, `cad/`, `simulations/` | Engineering assumptions, calculations, geometry planning, and contracts |
| `research/` | Supplier requests, candidates, and controlled response intake |
| `validation/`, `manufacturing/` | Test definitions, validation, and pilot workflows |
| `buildslate/` | Python integration and CLI |
| `viewer/` | Browser viewer and generated assembly assets |
| `reports/` | Derived status and engineering reports |
| `docs/` | Architecture, methods, procedures, and reference material |

## Current boundary

The v1R assembly is provisional. The mechanical model uses planning rectangles; the PCB model uses placeholder footprints. Supplier CAD, a released enclosure, routed board, prototype measurements, and pilot evidence are not in this repository. The viewer shows those limits on each component. See the [dashboard](reports/program/dashboard.md) for current gates and external blockers.

The earlier broad repository overview is retained in the [archive](docs/archive/2026-10-repository-overview.md). Current workflows and authority rules live in the documents linked above.
