# Scripts

These scripts check repository quality; program operations use the `buildslate` CLI. Run scripts from the repository root.

| Script | Purpose | When to run |
| --- | --- | --- |
| `check_docs.py` | Lint tracked, maintained Markdown; excludes generated reports and archived snapshots. | After editing active documentation; stage a new file first. |
| `check_package.py` | Build a wheel, install it in a fresh environment, and run the CLI outside the checkout. | After changing package metadata, imports, or CLI entry points. |
| `check_release.py` | Match Python, viewer, and lockfile versions to the changelog; optionally extract release notes. | Before tagging a software release. |
| `ci_validate.py` | Run static checks, every registered validator, documentation checks, package checks, generation currency, and viewer build. | On a clean candidate commit. |

`ci_validate.py` rejects an uncommitted change or generated worktree drift. Use focused checks while editing, then run the full gate after committing. The [contribution guide](../CONTRIBUTING.md) gives the complete sequence.
