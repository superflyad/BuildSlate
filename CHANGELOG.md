# Changelog

Changes to the BuildSlate software and repository workflow are recorded here. Engineering claim status remains in the generated program dashboard and source registries.

## Unreleased

- Aligned the provisional v1R mechanical PCB with the 0.8 mm floorplan and compute-zone stack; added a cross-domain thickness contract.
- Added a separately proofed eight-package 128 GB reference CAD variant and 3D viewer switch; kept the fabrication and hardware qualification gates blocked.
- Added per-solid CAD proofing with anchored source checks, BREP/mesh bounds, STEP round-trip volume, exact intersections, planform keepouts, and local stack results; exposed findings in the viewer.
- Detailed the concept board, packages, battery tray, cameras, speakers, rear cover, frame, and gasket while preserving each added feature's assumption status.
- Published the concept CAD viewer through GitHub Pages after the validation and CAD export jobs pass.
- Added a 41-solid editable Slate Pocket v1R concept STEP assembly generated from the source envelopes and explicit assumptions for every component library role.
- Added a matching browser CAD view, preserved the source-envelope comparison, and validated geometry identity, coverage, and regeneration in CI.
- Completed the assembly review controls with an expanded canvas, axis section cuts, part focus and isolation, and navigation across every component library role; kept unplaced and deferred roles explicit.
- Made viewer asset loading follow the configured Vite base path and reject mismatched JSON and glTF part counts at runtime.
- Reworked the README, architecture, contribution, viewer, and documentation guides around the actual review and change workflows; added a schematic cover and mobile-friendly repository entry points.
- Indexed all active engineering guides and added a documentation coverage check; expanded CI to Windows and strengthened maintained Python checks.
- Made generated text writers use LF consistently so Windows validation does not dirty tracked reports.

## 0.1.0 - 2026-11-19

- Added an installable Python CLI for reading and validating a BuildSlate data checkout from any working directory.
- Added a provisional 3D assembly viewer with source and evidence context. Its solids remain planning envelopes.
- Established repository-wide Python formatting, static checks, documentation linting, deterministic regeneration checks, and installed-package verification in CI.
- Added contributor, support, security, and release procedures.
