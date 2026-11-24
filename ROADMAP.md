# Roadmap

This roadmap separates software work from engineering evidence. A completed repository task does not imply that a device part, test, or manufacturing gate has been released. The [program dashboard](reports/program/dashboard.md) is the current source for those gates.

## Repository quality

- [x] Curated documentation index, archive boundary, and directory ownership rules
- [x] All validators registered; local links, placeholder READMEs, and dependency pins checked in CI
- [x] Python name analysis and formatting gate across the repository
- [x] Contributor issue routes, support and security policies, and editor defaults
- [x] Establish a package/install contract and verify commands outside the repository checkout
- [x] Add documentation style checks with a clean baseline for maintained guidance
- [x] Define versioned software releases, changelog, and release artifacts
- [x] Expand static analysis beyond name errors in the maintained Python package and scripts
- [ ] Extend the stronger lint rule set through the legacy engineering models and validators in reviewed groups
- [ ] Keep command examples and review procedures current as the CLI and data contracts evolve

## Current viewer: concept CAD review

- [x] Stable part IDs and a documented coordinate system
- [x] Generated JSON and glTF from existing engineering sources
- [x] Viewer with rotation, selection, filtering, focus, isolation, axis sections, explode, keepouts, expanded view, and gate context
- [x] Surface all component library roles and distinguish modeled boxes, aggregates, deferred concepts, and unplaced parts
- [x] Generation and build checks in CI
- [x] Editable, 41-solid concept STEP assembly with explicit assumptions for all 22 component roles
- [x] Tessellated concept CAD in the browser with a source-envelope comparison view
- [x] Per-solid CAD proof, source-anchor and STEP checks, exact nominal intersections, and visible keepout and stack findings

## Next engineering inputs

The [build-to-function gate](docs/engineering/build_to_function.md) now enumerates the release and functional evidence. Both stages remain blocked; `buildslate hardware` reports each missing item.

- Supplier complete-pack battery drawing and protection geometry
- Selected compute and memory package drawings, reference design, and routing constraints
- Selected display, camera, storage, connector, speaker, and antenna drawings
- Released mechanical sections, tolerances, fasteners, seals, and assembly sequence
- Routed ECAD and measured thermal/RF data

Replace a provisional solid only when the source includes revision, units, coordinate frame, geometry license, and engineering review. The [program dashboard](reports/program/dashboard.md) tracks external blockers and gates.

## Next geometry milestone

- [ ] Define a reviewed import contract for supplier and released CAD geometry, including revision, units, frame, provenance, and license.
- [ ] Import one approved part without changing the identity or evidence status of its planning envelope.
- [ ] Check placement, scale, and section views against the source drawing before expanding to additional parts.
- [ ] Keep provisional and approved geometry visually distinct in the viewer.

## Future viewer capabilities

- Import reviewed supplier and design meshes alongside planning envelopes
- Engineering cross-section measurements and interference overlays tied to the mechanical validation result
- Electrical and thermal paths tied to released netlists and measured data
- Build and service sequences tied to authorized manufacturing instructions

These require source data that is not yet present. They are not represented as completed engineering work.
