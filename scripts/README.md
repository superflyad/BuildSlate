# Scripts

`ci_validate.py` is the local CI entry point. Run it with `python scripts/ci_validate.py` from the repository root. It runs the repository validation suite, checks generated output currency, builds the viewer, and rejects worktree drift.

`check_docs.py` lints maintained Markdown. `check_package.py` builds a wheel and tests the installed command from another directory. `check_release.py` verifies the Python and viewer versions against the changelog and can write release notes for a tag.
