# Contributing

BuildSlate changes must preserve the link between an engineering claim and its source. Start with the [architecture](ARCHITECTURE.md), [repository standards](docs/standards/repository.md), and [current dashboard](reports/program/dashboard.md) before changing a model or gate. The [support guide](SUPPORT.md) explains where to report a defect or evidence gap.

## Set up a checkout

Use Python 3.12 or newer and Node.js 20.19 or newer. From the repository root:

```bash
python -m pip install -e .
python -m pip install -r requirements-dev.txt
npm ci --prefix viewer
buildslate validate
```

`pyproject.toml` defines the installable CLI. The engineering data remains in this checkout. If you invoke an installed CLI elsewhere, use `buildslate --repo-root /path/to/BuildSlate <command>`.

## Choose the source of a change

| Change | Edit | Then verify |
| --- | --- | --- |
| Product target or profile | `specs/`, `configs/` | Profile resolution, dependent models, and generated status |
| Engineering model or provisional placement | `engineering/`, `cad/`, `simulations/` | Units, provenance, affected validators, and regenerated outputs |
| Program or generation behavior | `buildslate/`, manifests, validators | Dependency impact, deterministic outputs, and CLI behavior |
| Viewer behavior | `viewer/src/` | Generated asset contract, desktop and narrow layouts, and controls |
| Documentation | Root guides and `docs/` | Active-document lint and local links |
| Supplier or test evidence | Controlled intake paths | Original bytes, receipt, schema, review, and authorization |

Do not edit `reports/` or `viewer/public/assembly.json` and `.gltf` by hand. Do not add synthetic measurements to controlled evidence stores. Keep product intent, planning assumptions, supplier claims, measurements, and verified decisions distinct. A model result or viewer interaction cannot change an engineering gate by itself.

## Work through a change

1. Find the authoritative input. Use `buildslate impact --changed <repository-relative-path>` to see dependent generated nodes.
2. Change the input and its focused validator. Record a changed authority, generation rule, or viewer contract in [DECISIONS.md](DECISIONS.md).
3. Run `buildslate regenerate --stale`. Review `git diff` for generated changes and check that the evidence class and caveat remain accurate.
4. Run focused checks while editing: `python validation/run_all.py` for model changes, `python -m ruff check .` and `python -m ruff format --check .` for Python, or `python scripts/check_docs.py` for maintained Markdown. Stage a new Markdown file before running the documentation checker.
5. Commit the coherent change. Run `python scripts/ci_validate.py` on the clean commit. That gate checks all validators, documentation, installed-package behavior, release metadata, deterministic output currency, and the viewer build. If it fails, fix the issue, commit, and rerun.

The full gate intentionally rejects a dirty tree. It is the final check on a candidate commit, not the first check while editing. `validation/run_all.py` and the focused tools are available before the commit.

## Review the viewer

Run `npm run dev` from `viewer/` and inspect a desktop and narrow layout. Confirm that the model loads, selecting a part shows its source and evidence status, filters and visibility controls work, and the interface does not imply that planning boxes are released CAD. Run `npm run check:model`, `npm run format:check`, and `npm run build` for viewer changes. The [viewer guide](viewer/README.md) describes the asset contract.

## Handle external evidence

Supplier responses, EVT0 campaigns, calibrations, and pilot bundles have separate intake commands and review requirements in the [operator workflows](docs/engineering/operator_workflows.md). Preserve original bytes and receipts. Do not put confidential supplier material or personal data in a public issue or pull request. Use the [security policy](SECURITY.md) for sensitive reports.

## Describe the result

A pull request or directly authorized `main` change should state the authoritative inputs changed, generated outputs, checks run, and any changed claim or evidence boundary. Keep unrelated changes separate. A report-only or viewer-only change cannot promote a supplier, test, CAD, or manufacturing claim. For a software release, follow the [release process](docs/standards/releases.md) and update the [changelog](CHANGELOG.md).
