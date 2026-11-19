# Repository standards

## File classes and ownership

| Class | Locations | Change rule |
| --- | --- | --- |
| Product intent | `specs/`, `configs/` | Preserve the source distinction between targets and operational fallbacks. |
| Engineering inputs | `engineering/`, `cad/`, `simulations/`, `manufacturing/`, `validation/evt0/` | Include units, provenance, maturity, and explicit missing evidence. |
| Controlled external evidence | `research/supplier-responses/`, `validation/evt0/campaigns/`, `manufacturing/pilot-results/campaigns/` | Ingest through the repository tools; preserve source bytes and receipts. |
| Implementation | `buildslate/`, `engineering/**/*.py`, `validation/*.py`, `scripts/`, `viewer/src/` | Make the smallest coherent source change and validate it. |
| Generated views | `reports/`, `viewer/public/assembly.json`, `viewer/public/assembly.gltf` | Regenerate from inputs; never edit by hand. |
| Documentation | Root guides, `docs/`, and domain READMEs | Keep links working and distinguish current guidance from archived snapshots. |

The [program manifest](../../engineering/program/program_model.yaml) maps graph authorities. The [regeneration manifest](../../engineering/program/regeneration.yaml) maps generated dependencies. A present file, current hash, or rendered object does not upgrade evidence or release status.

## Names and paths

- Use lowercase `snake_case` for Python modules and identifiers; use the existing device ID `slate-pocket-v1r` in data and artifact paths.
- Use repository-relative POSIX paths in YAML and generated metadata, including on Windows.
- Use millimeters for assembly geometry and declare units for other numerical inputs.
- Give each assembly part a stable ID and a source path. Record an evidence class for every dimension or placement.
- Prefer one canonical source for a value. Derived files may repeat it only through deterministic generation.

## Change sequence

1. Identify the authoritative input and affected generated nodes with `python -m buildslate impact --changed <path>`.
2. Change the input and update the relevant decision or operating document when the authority or workflow changes.
3. Run `python -m buildslate regenerate --stale` and review the generated diff.
4. Run `python scripts/ci_validate.py` from a clean commit. CI checks Python names with Ruff, validator registration, local documentation links, generated state, viewer geometry, and the web build.
5. Push only after the gate passes. A change to external evidence follows the separate intake and authorization procedures in the [operator workflows](../engineering/operator_workflows.md).

The Python lint baseline is configured in `pyproject.toml` and runs Ruff's `F` rules across the repository. This catches undefined names, unused imports, and other executable-code defects. Ruff formatting is enforced across all Python source files.

## Model claims

Use the five claim classes in the [engineering review standard](../engineering/review_standard.md). A screening model can identify contradictions and evidence needs. It cannot establish physical fit, qualification, certification, or production readiness. The [dashboard](../../reports/program/dashboard.md) is the current summary of those boundaries.
