# Software releases

BuildSlate versions identify the Python CLI and the static viewer. They do not approve hardware geometry, supplier parts, test evidence, or a manufacturing gate. The generated [program dashboard](../../reports/program/dashboard.md) carries those states.

## Version and artifacts

Use `MAJOR.MINOR.PATCH` versions. During the `0.x` series, a minor version may change the CLI or data contract; a patch fixes behavior without intentionally changing that contract. Keep the version in `pyproject.toml`, `viewer/package.json`, and the [changelog](../../CHANGELOG.md) aligned. Release tags use `vMAJOR.MINOR.PATCH`.

The release workflow attaches a Python wheel, a source distribution, and a static viewer archive to the GitHub release. The wheel contains the CLI code, not the engineering data. Run it against a compatible BuildSlate checkout with `--repo-root`. The viewer archive displays generated provisional geometry and is read only.

## Release sequence

1. Finish source changes and regeneration on `main`. Review the generated diff and evidence boundary.
2. Update the version and changelog entry. Run `python scripts/check_release.py` and `python scripts/ci_validate.py` from a clean commit.
3. Push `main` and confirm the GitHub validation workflow passed for that commit.
4. Tag that commit with `vMAJOR.MINOR.PATCH` and push the tag. The tag workflow verifies the tag/version match, repeats CI, builds the artifacts, and creates the GitHub release with the changelog entry.
5. Check the published artifacts and release notes. Correct a failed release with a new patch version; do not move a published tag.

No PyPI publication is configured. A source checkout is required for authoritative program inputs and regeneration.
