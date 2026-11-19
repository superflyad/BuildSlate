# Contributing

## Working rules

- Change authoritative inputs, then regenerate. Do not hand-edit generated reports or viewer assets.
- Keep source intent, planning values, supplier claims, measurements, and verified decisions distinct.
- Preserve received evidence bytes and receipt hashes. Never add synthetic measurements to controlled evidence stores.
- Use stable part IDs and millimeters in the assembly contract. Add a source and evidence class to every new part.
- Record a design decision in `DECISIONS.md` when changing authority, generation, or viewer behavior.

## Validate a change

```bash
python -m buildslate regenerate --stale
python scripts/ci_validate.py
```

Install `requirements.txt` and `requirements-dev.txt` first. The CI gate compiles Python, checks undefined and unused names with Ruff, runs every registered repository validator, checks local documentation links and generated state, verifies assembly export currency, and builds the viewer. On a clean commit it leaves the worktree unchanged.

Run `python -m ruff format .` after editing Python. The formatter check covers the repository in CI.

For a viewer change, run `npm run dev` in `viewer/` and inspect a desktop and narrow layout. Confirm the model loads, part selection opens source details, filters and visibility controls work, and no control suggests that planning geometry is released CAD.

## Review and publication

For a pull request or a directly authorized `main` change, describe the source change, generated outputs, verification, and any new or changed evidence boundary. A report-only or viewer-only edit cannot change an engineering gate. Keep unrelated changes separate.
